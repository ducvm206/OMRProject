"""
answer_extraction.py - Unified Answer Sheet Extraction Pipeline

This module provides a complete extraction workflow that combines:
1. Student ID extraction (from extraction.py)
2. Multiple choice answer extraction (from extraction.py)
3. Quick answer extraction (from quick_answer_extraction.py)

Usage:
    from extraction_flow import AnswerSheetProcessor
    
    processor = AnswerSheetProcessor(
        template_path='template/sheet_template.json',
        cnn_model_path='core/models/cnn_model.h5'
    )
    
    result = processor.process_sheet(
        image_path='filled_sheets/student_sheet.png',
        threshold_percent=50,
        debug=False
    )
"""

import cv2
import numpy as np
import json
import os
import sys
from datetime import datetime
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# Fix import paths
try:
    # Try absolute import first
    from core.answer_extraction.bubble_answer_extraction import BubbleTemplate, AnswerSheetExtractor
    from core.answer_extraction.quick_answer_extraction import QuickAnswerExtraction
    from core.answer_extraction.key_extraction import KeyExtractor
except ImportError:
    try:
        # Try relative import
        from .bubble_answer_extraction import BubbleTemplate, AnswerSheetExtractor
        from .quick_answer_extraction import QuickAnswerExtraction
        from .key_extraction import KeyExtractor
    except ImportError:
        # Fallback: Add project root to path
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        from core.answer_extraction.bubble_answer_extraction import BubbleTemplate, AnswerSheetExtractor
        from core.answer_extraction.quick_answer_extraction import QuickAnswerExtraction
        from core.answer_extraction.key_extraction import KeyExtractor

def convert_numpy(o):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


class AnswerSheetProcessor:
    """
    Unified processor for complete answer sheet extraction.
    Handles student ID, multiple choice answers, and quick answers.
    """
    
    def __init__(self, template_path, cnn_model_path=None):
        """
        Initialize the processor with template and optional CNN model.
        
        Args:
            template_path: Path to template JSON file
            cnn_model_path: Path to CNN model for quick answer extraction (optional)
        """
        self.template_path = template_path
        self.cnn_model_path = cnn_model_path
        
        # Load template for MC and ID extraction
        print(f"\n{'='*70}")
        print("INITIALIZING ANSWER SHEET PROCESSOR")
        print(f"{'='*70}")
        
        try:
            self.bubble_template = BubbleTemplate(template_path)
            self.mc_extractor = AnswerSheetExtractor(self.bubble_template)
        except Exception as e:
            print(f"[ERROR] Failed to load template: {e}")
            # Try to continue with partial initialization
            self.bubble_template = None
            self.mc_extractor = None
        
        # Initialize quick answer extractor if CNN model provided
        self.quick_extractor = None
        if cnn_model_path and os.path.exists(cnn_model_path):
            print(f"[INFO] Loading CNN model for quick answers: {cnn_model_path}")
            try:
                self.quick_extractor = QuickAnswerExtraction(cnn_model_path, template_path)
            except Exception as e:
                print(f"[ERROR] Failed to load CNN model: {e}")
                self.quick_extractor = None
        else:
            print("[INFO] No CNN model provided - quick answers will be skipped")
        
        # Initialize key extractor
        self.key_extractor = KeyExtractor()
        
        print(f"[SUCCESS] Processor initialized")
        print(f"  Template: {os.path.basename(template_path)}")
        
        if self.bubble_template:
            print(f"  Total MC Questions: {len(self.bubble_template.questions)}")
            print(f"  Student ID Template: {'Available' if self.bubble_template.id_template else 'Not Available'}")
        else:
            print(f"  [WARNING] Template loading had issues")
            
        print(f"  Quick Answer Support: {'Enabled' if self.quick_extractor else 'Disabled'}")
    
    def process_sheet(self, image_path, threshold_percent=50, debug=False, 
                     extract_id=True, extract_mc=True, extract_quick=True,
                     extract_key=True):
        """
        Complete extraction pipeline for a filled answer sheet.
        
        Args:
            image_path: Path to filled answer sheet image
            threshold_percent: Bubble fill detection threshold (0-100)
            debug: If True, show visualizations
            extract_id: Extract student ID
            extract_mc: Extract multiple choice answers
            extract_quick: Extract quick answers (requires CNN model)
            extract_key: Extract answer key (requires key template)
            
        Returns:
            Dictionary containing all extraction results
        """
        print(f"\n{'='*70}")
        print("PROCESSING ANSWER SHEET")
        print(f"{'='*70}")
        print(f"Image: {os.path.basename(image_path)}")
        print(f"Threshold: {threshold_percent}%")
        print(f"Extraction modes: ID={extract_id}, MC={extract_mc}, Quick={extract_quick}, Key={extract_key}")
        
        # Validate image exists
        if not os.path.exists(image_path):
            print(f"[ERROR] Image not found: {image_path}")
            return None
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] Could not load image: {image_path}")
            return None
        
        # Store original dimensions
        original_height, original_width = image.shape[:2]
        print(f"Original image dimensions: {original_width}x{original_height}")
        
        # ========================================
        # RESIZE IMAGE TO STANDARD DIMENSIONS
        # ========================================
        # Resize to 1700x2200 for consistent processing
        target_processing_width = 1700
        target_processing_height = 2200
        
        image_resized = cv2.resize(image, (target_processing_width, target_processing_height), 
                                   interpolation=cv2.INTER_CUBIC)
        
        print(f"Resized for processing: {target_processing_width}x{target_processing_height}")
        
        gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)
        target_height, target_width = image_resized.shape[:2]
        
        # Initialize local variables for visualization
        scaled_questions = None
        scaled_id_template = None
        questions = None
        
        # Initialize result structure
        result = {
            'metadata': {
                'source_image': image_path,
                'processed_at': datetime.now().isoformat(),
                'template_used': self.template_path,
                'threshold_percent': threshold_percent,
                'original_image_dimensions': {
                    'width': original_width,
                    'height': original_height
                },
                'processing_image_dimensions': {
                    'width': target_processing_width,
                    'height': target_processing_height
                }
            },
            'student_id': None,
            'multiple_choice_answers': None,
            'quick_answers': None,
            'answer_key': None,
            'extraction_summary': {
                'student_id_extracted': False,
                'mc_extracted': False,
                'quick_extracted': False,
                'key_extracted': False
            }
        }
        
        # ========================================
        # 1. EXTRACT STUDENT ID
        # ========================================
        if extract_id and self.bubble_template and self.bubble_template.id_template:
            print(f"\n{'='*70}")
            print("STEP 1: EXTRACTING STUDENT ID")
            print(f"{'='*70}")
            
            try:
                scaled_id_template = self.mc_extractor.scale_id_template(
                    target_width, target_height
                )
                id_result = self.mc_extractor.extract_student_id(
                    gray, scaled_id_template, threshold_percent
                )
                
                result['student_id'] = id_result
                result['extraction_summary']['student_id_extracted'] = True
                
                if id_result:
                    print(f"[SUCCESS] Student ID: {id_result['student_id']}")
                    print(f"  Valid: {id_result['is_valid']}")
                    print(f"  Confidence: {id_result['average_confidence']:.1f}%")
                else:
                    print("[WARNING] Student ID extraction returned None")
                    
            except Exception as e:
                print(f"[ERROR] Student ID extraction failed: {e}")
                result['student_id'] = {'error': str(e)}
        
        elif extract_id and (not self.bubble_template or not self.bubble_template.id_template):
            print("\n[INFO] Student ID extraction skipped - no ID template in sheet")
        
        # ========================================
        # 2. EXTRACT MULTIPLE CHOICE ANSWERS
        # ========================================
        if extract_mc and self.bubble_template and self.bubble_template.questions:
            print(f"\n{'='*70}")
            print("STEP 2: EXTRACTING MULTIPLE CHOICE ANSWERS")
            print(f"{'='*70}")
            
            try:
                # Scale questions to match resized image
                scaled_questions = self.mc_extractor.scale_questions(
                    target_width, target_height
                )
                
                # Extract answers
                questions = self.mc_extractor.extract_answers(
                    image_resized, gray, scaled_questions, threshold_percent
                )
                
                # Format MC answers
                mc_answers = {
                    'total_questions': len(questions),
                    'answers': {}
                }
                
                for question in questions:
                    q_num = question.question_number
                    bubbles_data = []
                    
                    for bubble in question.bubbles:
                        bubbles_data.append({
                            'label': bubble.label,
                            'filled': bubble.filled,
                            'fill_percentage': round(bubble.fill_percentage, 2)
                        })
                    
                    mc_answers['answers'][str(q_num)] = {
                        'question_number': q_num,
                        'selected_answers': question.get_answer(),
                        'bubbles': bubbles_data
                    }
                
                result['multiple_choice_answers'] = mc_answers
                result['extraction_summary']['mc_extracted'] = True
                
                # Count filled answers
                filled_count = sum(1 for q in questions if q.get_answer())
                print(f"[SUCCESS] Extracted {len(questions)} MC questions")
                print(f"  Answered: {filled_count}/{len(questions)}")
                print(f"  Blank: {len(questions) - filled_count}")
                
            except Exception as e:
                print(f"[ERROR] Multiple choice extraction failed: {e}")
                result['multiple_choice_answers'] = {'error': str(e)}

        elif extract_mc and (not self.bubble_template or not self.bubble_template.questions):
            print("\n[INFO] Multiple choice extraction skipped - no questions in template")
        
        # ========================================
        # 3. EXTRACT QUICK ANSWERS (CNN-based)
        # ========================================
        if extract_quick and self.quick_extractor:
            print(f"\n{'='*70}")
            print("STEP 3: EXTRACTING QUICK ANSWERS (HANDWRITTEN DIGITS)")
            print(f"{'='*70}")
            
            try:
                quick_results = self.quick_extractor.extract_all_quick_answers(
                    image_resized, debug_mode=debug
                )
                
                result['quick_answers'] = quick_results
                result['extraction_summary']['quick_extracted'] = True
                
                # Count detected answers
                detected = sum(1 for qa in quick_results['quick_answers'] 
                             if qa['answer'] is not None)
                total = quick_results['total_questions']
                
                print(f"[SUCCESS] Extracted {total} quick answer regions")
                print(f"  Detected: {detected}/{total}")
                print(f"  Not detected: {total - detected}")
                
            except Exception as e:
                print(f"[ERROR] Quick answer extraction failed: {e}")
                result['quick_answers'] = {'error': str(e)}

        elif extract_quick and not self.quick_extractor:
            print("\n[INFO] Quick answer extraction skipped - no CNN model loaded")
        
        # ========================================
        # NEW: EXTRACT ANSWER KEY
        # ========================================
        if extract_key and self.bubble_template and self.bubble_template.template_data:
            print(f"\n{'='*70}")
            print("STEP 4: EXTRACTING ANSWER KEY")
            print(f"{'='*70}")
            
            try:
                # For key extraction, we need to work with the resized image
                # Save it temporarily or pass it directly
                key_result = self.key_extractor.extract_key_from_sheet(
                    image_path=image_path,
                    template_path=self.template_path,
                    threshold_percent=threshold_percent,
                    debug=debug
                )
                
                result['answer_key'] = key_result
                result['extraction_summary']['key_extracted'] = True
                
                if key_result:
                    print(f"[SUCCESS] Answer Key: {key_result.get('answer_key', 'Not marked')}")
                else:
                    print("[INFO] No KEY region in sheet")
                    
            except Exception as e:
                print(f"[ERROR] Key extraction failed: {e}")
                result['answer_key'] = {'error': str(e)}

        elif extract_key and (not self.bubble_template or not self.bubble_template.template_data):
            print("\n[INFO] Answer key extraction skipped - no KEY region in template")

        # ========================================
        # 4. VISUALIZATION (if debug enabled)
        # ========================================
        if debug:
            print(f"\n{'='*70}")
            print("GENERATING VISUALIZATION")
            print(f"{'='*70}")
            
            self._visualize_complete_extraction(
                image_resized, result,      # Use resized image for visualization
                scaled_questions,           # Already scaled to 1700x2200
                scaled_id_template          # Already scaled to 1700x2200
            )
        
        # ========================================
        # FINAL SUMMARY
        # ========================================
        print(f"\n{'='*70}")
        print("EXTRACTION COMPLETE")
        print(f"{'='*70}")
        
        if result['student_id']:
            print(f"Student ID: {result['student_id'].get('student_id', 'N/A')}")
        
        if result['multiple_choice_answers']:
            mc_count = result['multiple_choice_answers'].get('total_questions', 0)
            print(f"Multiple Choice: {mc_count} questions")
        
        if result['quick_answers']:
            qa_count = result['quick_answers'].get('total_questions', 0)
            print(f"Quick Answers: {qa_count} questions")
        
        if result['answer_key']:
            ak_result = result['answer_key']
            print(f"Answer Key: {ak_result.get('answer_key', 'N/A')}")
        
        return result
    
    def _visualize_complete_extraction(self, image, result, scaled_questions, scaled_id_template):
        """
        Create visualization showing all extracted data.
        
        Args:
            image: Original answer sheet image (1700x2200)
            result: Extraction result dictionary
            scaled_questions: Scaled MC questions (or None)
            scaled_id_template: Scaled ID template (or None)
        """
        output = image.copy()
        
        # Get processing image dimensions
        proc_height, proc_width = output.shape[:2]  # Should be 1700x2200
        
        # Get template dimensions (from bubble_template if available)
        template_width = None
        template_height = None
        
        if self.bubble_template:
            template_width = self.bubble_template.template_width
            template_height = self.bubble_template.template_height
        
        # Calculate scale factors for bubbles/regions that came from template
        if template_width and template_height:
            scale_x = proc_width / template_width
            scale_y = proc_height / template_height
        else:
            scale_x = 1.0
            scale_y = 1.0
        
        print(f"[DEBUG] Template dims: {template_width}x{template_height}, "
              f"Processing dims: {proc_width}x{proc_height}, "
              f"Scale: {scale_x:.3f}x{scale_y:.3f}")
        
        # Draw MC answer bubbles
        if scaled_questions:
            for question in scaled_questions:
                for bubble in question.bubbles:
                    x, y, radius = bubble.x, bubble.y, bubble.radius
                    color = (0, 255, 0) if bubble.filled else (0, 0, 255)
                    thickness = 3 if bubble.filled else 2
                    cv2.circle(output, (x, y), radius, color, thickness)
        
        # Draw ID bubbles
        if scaled_id_template and result['student_id']:
            id_result = result['student_id']
            status_map = {d['position']: d for d in id_result.get('digit_details', [])}
            
            for column in scaled_id_template['digit_columns']:
                digit_pos = column['digit_position']
                status = status_map.get(digit_pos, {})
                selected_digit = status.get('digit')
                
                for bubble in column['bubbles']:
                    x, y = bubble['x'], bubble['y']
                    radius = bubble['radius']
                    digit = bubble['digit']
                    
                    if digit == selected_digit:
                        color = (255, 0, 255)  # Magenta for selected
                        thickness = 3
                    else:
                        color = (128, 0, 128)  # Purple for unselected
                        thickness = 1
                    
                    cv2.circle(output, (x, y), radius, color, thickness)
            
            # Add ID text
            if id_result.get('student_id'):
                cv2.putText(output, f"ID: {id_result['student_id']}", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3)
        
        # Draw quick answer regions (SCALED)
        if result['quick_answers'] and self.quick_extractor:
            try:
                for qa in result['quick_answers']['quick_answers']:
                    q_num = qa['question_number']
                    region = next((r for r in self.quick_extractor.quick_answer_regions 
                                 if r['question_number'] == q_num), None)
                    
                    if region:
                        # Scale quick answer regions from template to processing dimensions
                        x = int(region['x'] * scale_x)
                        y = int(region['y'] * scale_y)
                        w = int(region['width'] * scale_x)
                        h = int(region['height'] * scale_y)

                        cv2.rectangle(output, (x, y), (x + w, y + h), (255, 165, 0), 2)

                        if qa['answer']:
                            label = f"Q{q_num}: {qa['answer']}"
                            cv2.putText(output, label, (x, y + h + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
            except Exception as e:
                print(f"[WARNING] Could not visualize quick answers: {e}")
        
        # Draw answer key region (SCALED)
        if result['answer_key']:
            ak_result = result['answer_key']
            try:
                # If we have key_bubbles, draw them (they're from template, need scaling)
                if ak_result.get('key_bubbles'):
                    for bubble_data in ak_result['key_bubbles']:
                        x_orig = bubble_data.get('x')
                        y_orig = bubble_data.get('y')
                        radius_orig = bubble_data.get('radius')
                        filled = bubble_data.get('filled', False)
                        
                        if x_orig and y_orig and radius_orig:
                            # Scale from template dimensions to processing dimensions
                            x = int(x_orig * scale_x)
                            y = int(y_orig * scale_y)
                            radius = int(radius_orig * ((scale_x + scale_y) / 2))
                            
                            color = (0, 255, 0) if filled else (0, 0, 255)
                            thickness = 3 if filled else 2
                            cv2.circle(output, (x, y), radius, color, thickness)
            except Exception as e:
                print(f"[WARNING] Could not visualize answer key: {e}")
        
        # ========================================
        # RESIZE FOR DISPLAY
        # ========================================
        # Scale down for comfortable display (max 900px height)
        height, width = output.shape[:2]
        display_max_height = 900
        
        if height > display_max_height:
            display_scale = display_max_height / height
            display_width = int(width * display_scale)
            display_height = int(height * display_scale)
            
            output_display = cv2.resize(output, (display_width, display_height), 
                                       interpolation=cv2.INTER_LINEAR)
            
            print(f"\n[DISPLAY] Scaled visualization: {display_width}x{display_height} "
                  f"(from 1700x2200, scale: {display_scale:.2f}x)")
        else:
            output_display = output
            print(f"\n[DISPLAY] Visualization dimensions: {width}x{height}")
        
        cv2.imshow('Complete Extraction Visualization', output_display)
        print("\n[VISUALIZATION LEGEND]")
        print("  GREEN/RED = Multiple choice bubbles (filled/empty)")
        print("  MAGENTA = Selected ID digit")
        print("  ORANGE = Quick answer boxes")
        print("  GREEN/RED = Answer key bubbles (filled/empty)")
        print("\nPress any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def save_results(self, result, output_dir='extraction_results'):
        """
        Save extraction results to JSON file.
        
        Args:
            result: Extraction result dictionary
            output_dir: Directory to save results
            
        Returns:
            Path to saved JSON file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Build filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Include student ID in filename if available
        student_id = "NOID"
        if result['student_id'] and result['student_id'].get('student_id'):
            student_id = result['student_id']['student_id'].replace('_', 'X')
        
        filename = f"extraction_{student_id}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=convert_numpy)
        
        print(f"\n[SAVED] Results saved to: {filepath}")
        
        return filepath
    
    def batch_process(self, image_folder, threshold_percent=50, debug=False,
                     extract_id=True, extract_mc=True, extract_quick=True,
                     output_dir='extraction_results'):
        """
        Process multiple answer sheets in batch.
        
        Args:
            image_folder: Folder containing filled answer sheets
            threshold_percent: Bubble detection threshold
            debug: Show visualization for each sheet
            extract_id: Extract student IDs
            extract_mc: Extract multiple choice
            extract_quick: Extract quick answers
            output_dir: Directory to save results
            
        Returns:
            List of extraction results
        """
        print(f"\n{'='*70}")
        print("BATCH PROCESSING ANSWER SHEETS")
        print(f"{'='*70}")
        
        # Find all images
        image_files = []
        for filename in os.listdir(image_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(image_folder, filename))
        
        print(f"Found {len(image_files)} image(s) to process\n")
        
        results = []
        
        for i, image_path in enumerate(image_files, 1):
            print(f"\n{'='*70}")
            print(f"PROCESSING {i}/{len(image_files)}: {os.path.basename(image_path)}")
            print(f"{'='*70}")
            
            try:
                # Process sheet
                result = self.process_sheet(
                    image_path=image_path,
                    threshold_percent=threshold_percent,
                    debug=debug,
                    extract_id=extract_id,
                    extract_mc=extract_mc,
                    extract_quick=extract_quick
                )
                
                if result:
                    # Save results
                    json_path = self.save_results(result, output_dir)
                    result['metadata']['saved_to'] = json_path
                    results.append(result)
                else:
                    print(f"[ERROR] Processing returned None for {image_path}")
                    
            except Exception as e:
                print(f"[ERROR] Failed to process {image_path}: {e}")
                import traceback
                traceback.print_exc()
        
        # Print batch summary
        self._print_batch_summary(results)
        
        return results
    
    def _print_batch_summary(self, results):
        """Print summary of batch processing results."""
        print(f"\n{'='*70}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*70}")
        
        print(f"Total processed: {len(results)}")
        
        if results:
            # Student ID summary
            valid_ids = sum(1 for r in results 
                          if r['student_id'] and r['student_id'].get('is_valid'))
            print(f"\nStudent IDs:")
            print(f"  Valid: {valid_ids}/{len(results)}")
            
            # MC answers summary
            mc_processed = sum(1 for r in results 
                             if r['multiple_choice_answers'] is not None)
            print(f"\nMultiple Choice:")
            print(f"  Processed: {mc_processed}/{len(results)}")
            
            # Quick answers summary
            qa_processed = sum(1 for r in results 
                             if r['quick_answers'] is not None)
            print(f"\nQuick Answers:")
            print(f"  Processed: {qa_processed}/{len(results)}")
            
            # Answer key summary
            key_processed = sum(1 for r in results 
                             if r['answer_key'] is not None)
            print(f"\nAnswer Key:")
            print(f"  Processed: {key_processed}/{len(results)}")
            
            # List all student IDs
            print(f"\n{'='*70}")
            print("EXTRACTED STUDENT IDS")
            print(f"{'='*70}")
            for result in results:
                if result['student_id']:
                    id_str = result['student_id'].get('student_id', 'N/A')
                    valid = result['student_id'].get('is_valid', False)
                    status = "✓" if valid else "✗"
                    print(f"  {status} {id_str}")


def main():
    """Example usage of the extraction flow."""
    
    print("="*70)
    print("ANSWER SHEET EXTRACTION FLOW - EXAMPLE")
    print("="*70)
    
    # Configuration
    template_path = 'template/test_sheet_with_key_complete_template.json'
    cnn_model_path = 'core/models/cnn_model.h5'
    test_image = 'filled_sheet.png'
    
    # Validate files exist
    if not os.path.exists(template_path):
        print(f"[ERROR] Template not found: {template_path}")
        return
    
    if not os.path.exists(test_image):
        print(f"[ERROR] Test image not found: {test_image}")
        return
    
    # Initialize processor
    processor = AnswerSheetProcessor(
        template_path=template_path,
        cnn_model_path=cnn_model_path if os.path.exists(cnn_model_path) else None
    )
    
    # Process single sheet
    result = processor.process_sheet(
        image_path=test_image,
        threshold_percent=50,
        debug=True,  # Show visualization
        extract_id=True,
        extract_mc=True,
        extract_quick=True
    )
    
    if result:
        # Save results
        processor.save_results(result, output_dir='extraction_results')
        
        print("\n" + "="*70)
        print("PROCESSING COMPLETE")
        print("="*70)
    
    # Example: Batch processing
    # results = processor.batch_process(
    #     image_folder='filled_sheets',
    #     threshold_percent=50,
    #     debug=False,
    #     output_dir='batch_results'
    # )


if __name__ == "__main__":
    main()