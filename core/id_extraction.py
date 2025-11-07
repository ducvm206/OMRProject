"""
id_extraction.py - Extract Student IDs from filled answer sheets

This module loads a JSON template with student ID bubble positions
and extracts the filled ID from scanned answer sheets.
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime


class StudentIDExtractor:
    """Class to extract student IDs from scanned answer sheets"""
    
    def __init__(self, template_path):
        """
        Initialize with template JSON
        
        Args:
            template_path: Path to template JSON file with ID bubble positions
        """
        self.template_path = template_path
        self.template_data = self.load_template(template_path)
        self.id_template = self.extract_id_template()
    
    def load_template(self, template_path):
        """Load template from JSON file"""
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        print(f"[LOADED] Template: {template_path}")
        
        return template_data
    
    def extract_id_template(self):
        """
        Extract student ID template from first page
        
        Returns:
            Dictionary with ID template data or None if not found
        """
        # Get first page
        page_data = self.template_data.get('page_1')
        if not page_data:
            print("[WARNING] No page_1 found in template")
            return None
        
        id_data = page_data.get('student_id')
        if not id_data:
            print("[WARNING] No student_id found in template")
            return None
        
        # Store template dimensions for scaling
        template_width = page_data['image_dimensions']['width']
        template_height = page_data['image_dimensions']['height']
        
        id_template = {
            'template_width': template_width,
            'template_height': template_height,
            'total_digits': id_data['total_digits'],
            'digit_columns': id_data['digit_columns']
        }
        
        print(f"[INFO] ID Template: {id_template['total_digits']} digits")
        
        return id_template
    
    def scale_id_template(self, target_width, target_height):
        """
        Scale ID template coordinates to match target image dimensions
        
        Args:
            target_width: Width of answer sheet image
            target_height: Height of answer sheet image
            
        Returns:
            Scaled ID template
        """
        if not self.id_template:
            return None
        
        template_width = self.id_template['template_width']
        template_height = self.id_template['template_height']
        
        scale_x = target_width / template_width
        scale_y = target_height / template_height
        scale_avg = (scale_x + scale_y) / 2
        
        print(f"\n[SCALING] Factors: X={scale_x:.3f}, Y={scale_y:.3f}")
        
        # Scale all bubble positions
        scaled_template = {
            'total_digits': self.id_template['total_digits'],
            'digit_columns': []
        }
        
        for column in self.id_template['digit_columns']:
            scaled_column = {
                'digit_position': column['digit_position'],
                'bubbles': []
            }
            
            for bubble in column['bubbles']:
                scaled_bubble = {
                    'digit': bubble['digit'],
                    'x': int(bubble['x'] * scale_x),
                    'y': int(bubble['y'] * scale_y),
                    'radius': int(bubble['radius'] * scale_avg)
                }
                scaled_column['bubbles'].append(scaled_bubble)
            
            scaled_template['digit_columns'].append(scaled_column)
        
        return scaled_template
    
    def check_bubble_filled(self, image, bubble, threshold_percent=50):
        """
        Check if a bubble is filled
        
        Args:
            image: Grayscale image
            bubble: Bubble dictionary with x, y, radius
            threshold_percent: Percentage of dark pixels to consider filled
            
        Returns:
            Tuple of (is_filled, fill_percentage)
        """
        x = bubble['x']
        y = bubble['y']
        radius = bubble['radius']
        
        # Create circular mask
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (x, y), radius, 255, -1)
        
        # Extract circular region
        bubble_region = cv2.bitwise_and(image, image, mask=mask)
        
        # Count pixels in circle
        circle_pixels = cv2.countNonZero(mask)
        
        # Threshold to find dark pixels (filled marks)
        _, thresh = cv2.threshold(bubble_region, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Count dark pixels
        dark_pixels = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
        
        # Calculate percentage
        if circle_pixels == 0:
            return False, 0.0
        
        filled_percent = (dark_pixels / circle_pixels) * 100
        is_filled = filled_percent >= threshold_percent
        
        return is_filled, filled_percent
    
    def extract_student_id(self, image_path, threshold_percent=50, debug=True):
        """
        Extract student ID from filled answer sheet
        
        Args:
            image_path: Path to filled answer sheet image
            threshold_percent: Threshold for bubble detection (default: 50%)
            debug: If True, show visualization
            
        Returns:
            Dictionary with student ID and confidence data
        """
        print("\n" + "="*70)
        print("STUDENT ID EXTRACTION")
        print("="*70)
        
        if not self.id_template:
            print("[ERROR] No ID template available")
            return None
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] Could not load image: {image_path}")
            return None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        target_height, target_width = image.shape[:2]
        
        print(f"\nImage: {image_path}")
        print(f"Dimensions: {target_width}x{target_height}")
        print(f"Threshold: {threshold_percent}%")
        
        # Scale template to match image
        scaled_template = self.scale_id_template(target_width, target_height)
        
        # Extract ID digit by digit
        student_id = []
        id_confidence = []
        digit_details = []
        
        print("\n" + "="*70)
        print("DETECTING FILLED BUBBLES")
        print("="*70)
        
        for column in scaled_template['digit_columns']:
            digit_pos = column['digit_position']
            print(f"\nDigit Position {digit_pos}:")
            
            filled_digits = []
            
            for bubble in column['bubbles']:
                digit = bubble['digit']
                is_filled, fill_percent = self.check_bubble_filled(
                    gray, bubble, threshold_percent
                )
                
                if debug:
                    status = "●" if is_filled else "○"
                    print(f"  {status} Digit {digit}: {fill_percent:.1f}%")
                
                if is_filled:
                    filled_digits.append({
                        'digit': digit,
                        'confidence': fill_percent
                    })
            
            # Determine which digit was selected
            if len(filled_digits) == 0:
                # No digit filled - treat as blank or error
                student_id.append(None)
                id_confidence.append(0.0)
                digit_details.append({
                    'position': digit_pos,
                    'digit': None,
                    'confidence': 0.0,
                    'status': 'blank'
                })
                print(f"  → Result: BLANK (no bubble filled)")
            
            elif len(filled_digits) == 1:
                # Exactly one digit filled (correct)
                digit = filled_digits[0]['digit']
                confidence = filled_digits[0]['confidence']
                student_id.append(digit)
                id_confidence.append(confidence)
                digit_details.append({
                    'position': digit_pos,
                    'digit': digit,
                    'confidence': confidence,
                    'status': 'valid'
                })
                print(f"  → Result: {digit} (confidence: {confidence:.1f}%)")
            
            else:
                # Multiple digits filled (error/conflict)
                # Take the one with highest confidence
                best = max(filled_digits, key=lambda d: d['confidence'])
                digit = best['digit']
                confidence = best['confidence']
                student_id.append(digit)
                id_confidence.append(confidence)
                digit_details.append({
                    'position': digit_pos,
                    'digit': digit,
                    'confidence': confidence,
                    'status': 'conflict',
                    'conflicting_digits': [d['digit'] for d in filled_digits]
                })
                print(f"  → Result: {digit} (CONFLICT - multiple filled: {[d['digit'] for d in filled_digits]})")
        
        # Build ID string
        if all(d is not None for d in student_id):
            id_string = ''.join(str(d) for d in student_id)
            is_valid = True
        else:
            # Has blank digits
            id_string = ''.join(str(d) if d is not None else '_' for d in student_id)
            is_valid = False
        
        avg_confidence = np.mean(id_confidence) if id_confidence else 0.0
        
        result = {
            'student_id': id_string,
            'is_valid': is_valid,
            'average_confidence': avg_confidence,
            'digit_details': digit_details,
            'source_image': image_path,
            'extracted_at': datetime.now().isoformat()
        }
        
        # Print summary
        print("\n" + "="*70)
        print("EXTRACTION SUMMARY")
        print("="*70)
        print(f"Student ID: {id_string}")
        print(f"Valid: {is_valid}")
        print(f"Confidence: {avg_confidence:.1f}%")
        
        # Check for issues
        conflicts = [d for d in digit_details if d['status'] == 'conflict']
        blanks = [d for d in digit_details if d['status'] == 'blank']
        
        if conflicts:
            print(f"\n[WARNING] {len(conflicts)} digit(s) had multiple bubbles filled")
        if blanks:
            print(f"[WARNING] {len(blanks)} digit(s) had no bubbles filled")
        
        # Visualization
        if debug:
            self.visualize_id_extraction(image, scaled_template, digit_details)
        
        return result
    
    def visualize_id_extraction(self, image, scaled_template, digit_details):
        """
        Visualize ID extraction with color-coded bubbles
        
        Args:
            image: Answer sheet image
            scaled_template: Scaled ID template
            digit_details: List of digit extraction details
        """
        output = image.copy()
        
        # Create status lookup
        status_map = {d['position']: d for d in digit_details}
        
        for column in scaled_template['digit_columns']:
            digit_pos = column['digit_position']
            status = status_map.get(digit_pos, {})
            selected_digit = status.get('digit')
            
            for bubble in column['bubbles']:
                x = bubble['x']
                y = bubble['y']
                radius = bubble['radius']
                digit = bubble['digit']
                
                # Color based on status
                if digit == selected_digit:
                    if status.get('status') == 'conflict':
                        color = (0, 165, 255)  # Orange - conflict
                        thickness = 3
                    else:
                        color = (0, 255, 0)  # Green - selected
                        thickness = 3
                else:
                    color = (0, 0, 255)  # Red - not selected
                    thickness = 2
                
                # Draw circle
                cv2.circle(output, (x, y), radius, color, thickness)
                
                # Draw digit label
                cv2.putText(output, str(digit), (x - 5, y + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Add ID text at top
        id_text = ''.join(str(d['digit']) if d['digit'] is not None else '_' 
                         for d in digit_details)
        cv2.putText(output, f"ID: {id_text}", (50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)
        
        # Resize if needed
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('Student ID Extraction', output)
        print("\n[VISUALIZATION]")
        print("  GREEN = Selected digit")
        print("  ORANGE = Conflict (multiple filled)")
        print("  RED = Not selected")
        print("\nPress any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def save_id_to_json(self, result, output_dir='extracted_ids'):
        """
        Save extracted ID to JSON file
        
        Args:
            result: Dictionary with extraction results
            output_dir: Directory to save JSON
            
        Returns:
            Path to saved JSON file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        id_str = result['student_id'].replace('_', 'X')
        json_filename = f"id_{id_str}_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SAVED] ID saved to: {json_path}")
        
        return json_path


def batch_extract_ids(template_path, image_folder, threshold_percent=50, debug=False):
    """
    Extract student IDs from multiple answer sheets
    
    Args:
        template_path: Path to template JSON
        image_folder: Folder containing filled answer sheets
        threshold_percent: Detection threshold
        debug: Show visualization for each
        
    Returns:
        List of extraction results
    """
    print("="*70)
    print("BATCH STUDENT ID EXTRACTION")
    print("="*70)
    
    extractor = StudentIDExtractor(template_path)
    
    # Find all image files
    image_files = []
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_files.append(os.path.join(image_folder, filename))
    
    print(f"\nFound {len(image_files)} image(s) to process\n")
    
    results = []
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n{'='*70}")
        print(f"Processing {i}/{len(image_files)}: {os.path.basename(image_path)}")
        print(f"{'='*70}")
        
        try:
            result = extractor.extract_student_id(
                image_path,
                threshold_percent=threshold_percent,
                debug=debug
            )
            
            if result:
                # Save to JSON
                json_path = extractor.save_id_to_json(result)
                result['json_path'] = json_path
                results.append(result)
        
        except Exception as e:
            print(f"[ERROR] Failed to process {image_path}: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("BATCH EXTRACTION SUMMARY")
    print("="*70)
    print(f"Total processed: {len(results)}/{len(image_files)}")
    
    valid_ids = [r for r in results if r['is_valid']]
    print(f"Valid IDs: {len(valid_ids)}")
    
    conflicts = [r for r in results if any(d['status'] == 'conflict' for d in r['digit_details'])]
    print(f"IDs with conflicts: {len(conflicts)}")
    
    blanks = [r for r in results if any(d['status'] == 'blank' for d in r['digit_details'])]
    print(f"IDs with blanks: {len(blanks)}")
    
    print("\nExtracted IDs:")
    for result in results:
        status = "✓" if result['is_valid'] else "✗"
        print(f"  {status} {result['student_id']} ({result['average_confidence']:.1f}%)")
    
    return results


def main():
    """Example usage"""
    
    print("="*70)
    print("STUDENT ID EXTRACTION SYSTEM")
    print("="*70)
    
    # Single ID extraction
    template_path = 'template/answer_sheet_10q.json'
    answer_sheet = 'filled_answer_sheet.png'
    
    if not os.path.exists(template_path):
        print(f"[ERROR] Template not found: {template_path}")
        return
    
    if not os.path.exists(answer_sheet):
        print(f"[ERROR] Answer sheet not found: {answer_sheet}")
        return
    
    # Extract ID
    extractor = StudentIDExtractor(template_path)
    result = extractor.extract_student_id(
        answer_sheet,
        threshold_percent=50,
        debug=True
    )
    
    if result:
        # Save to JSON
        extractor.save_id_to_json(result)
        
        print("\n" + "="*70)
        print("EXTRACTION COMPLETE")
        print("="*70)
        print(f"Student ID: {result['student_id']}")
        print(f"Valid: {result['is_valid']}")
        print(f"Confidence: {result['average_confidence']:.1f}%")


if __name__ == "__main__":
    main()