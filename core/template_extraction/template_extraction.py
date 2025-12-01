# template_extraction.py
import cv2
import numpy as np
import json
import os
import fitz  # PyMuPDF
from datetime import datetime

try:
    # Try relative imports first
    from .bubble_extraction import (
        convert_pdf_to_png,
        detect_bubbles_in_image,
        save_template_to_json,
        convert_question_data_to_json_serializable
    )
except ImportError:
    try:
        # Fall back to absolute imports
        from core.template_extraction.bubble_extraction import (
            convert_pdf_to_png,
            detect_bubbles_in_image,
            save_template_to_json,
            convert_question_data_to_json_serializable
        )
    except ImportError as e:
        print(f"Warning: Could not import bubble_extraction functions: {e}")
        # Define fallback functions
        def convert_pdf_to_png(*args, **kwargs):
            raise ImportError("bubble_extraction not available")
        
        def detect_bubbles_in_image(*args, **kwargs):
            return [], {}
        
        def save_template_to_json(*args, **kwargs):
            return "fallback_template.json"
        
        def convert_question_data_to_json_serializable(data):
            return data

try:
    # Try relative imports first
    from .quick_answers_extraction import (
        detect_quick_answers_in_image
    )
except ImportError:
    try:
        # Fall back to absolute imports
        from core.template_extraction.quick_answers_extraction import (
            detect_quick_answers_in_image
        )
    except ImportError as e:
        print(f"Warning: Could not import quick_answers_extraction functions: {e}")
        # Define fallback function
        def detect_quick_answers_in_image(*args, **kwargs):
            return {}

# Rest of the template_extraction.py file remains the same...
def extract_complete_template(image_path, show_visualization=False):
    """
    Extract both bubble answers and quick answers from an image
    """
    print("\n" + "="*80)
    print("COMPLETE TEMPLATE EXTRACTION")
    print("="*80)
    
    # Get image dimensions
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Image not found at {image_path}")
        return None
    
    height, width = image.shape[:2]
    
    # Extract bubble answers (MCQ questions and student ID)
    print("\n[PHASE 1] Extracting Bubble Answers...")
    questions, id_data = detect_bubbles_in_image(image_path, show_visualization=show_visualization)
    
    # Extract quick answers (number answers)
    print("\n[PHASE 2] Extracting Quick Answers...")
    qa_data = detect_quick_answers_in_image(image_path, show_visualization=show_visualization)
    
    # Compile complete template data
    template_data = {
        'image_dimensions': {
            'width': width,
            'height': height
        },
        'bubble_answers': {
            'questions_detected': len(questions),
            'questions': convert_question_data_to_json_serializable(questions),
            'student_id': id_data
        },
        'quick_answers': qa_data
    }
    
    # Summary
    print("\n" + "="*80)
    print("EXTRACTION SUMMARY")
    print("="*80)
    print(f"Bubble Answers: {len(questions)} questions detected")
    if id_data:
        print(f"Student ID: {id_data.get('total_digits', 0)} digits detected")
    else:
        print(f"Student ID: Not detected")
    
    if qa_data:
        print(f"Quick Answers: {qa_data.get('total_questions', 0)} questions detected")
    else:
        print(f"Quick Answers: Not detected")
    
    return template_data

def process_pdf_complete_template(pdf_path, dpi=300, keep_png=False, show_visualization=True):
    """
    Complete workflow: Convert PDF to PNG, extract both bubble and quick answers
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for PDF conversion
        keep_png: If True, keep converted PNG files
        show_visualization: If True, show detection visualization
        
    Returns:
        Path to saved JSON template file
    """
    
    try:
        png_paths = convert_pdf_to_png(pdf_path, dpi=dpi)
    except Exception as e:
        print(f"\n[ERROR] Failed to convert PDF: {e}")
        return None
    
    complete_template_data = {}
    
    for i, png_path in enumerate(png_paths, start=1):
        print(f"\n{'='*80}")
        print(f"PROCESSING PAGE {i}/{len(png_paths)}")
        print(f"{'='*80}")
        print(f"File: {png_path}")
        
        # Extract complete template from this page
        page_data = extract_complete_template(png_path, show_visualization=show_visualization)
        
        if page_data:
            # Add PNG path if keeping files
            if keep_png:
                page_data['png_path'] = png_path
            
            complete_template_data[f"page_{i}"] = page_data
            
            print(f"\nPage {i} Summary:")
            print(f"  Bubble Questions: {page_data['bubble_answers']['questions_detected']}")
            print(f"  Student ID: {'Detected' if page_data['bubble_answers']['student_id'] else 'Not detected'}")
            print(f"  Quick Answers: {page_data['quick_answers']['total_questions'] if page_data['quick_answers'] else 'Not detected'}")
        else:
            print(f"[ERROR] Failed to process page {i}")
    
    # Save complete template to JSON
    json_path = save_complete_template_to_json(complete_template_data, pdf_path)
    
    # Cleanup PNG files if not keeping
    if not keep_png:
        print("\n" + "="*60)
        print("CLEANING UP TEMPORARY FILES")
        print("="*60)
        for png_path in png_paths:
            try:
                os.remove(png_path)
                print(f"  Deleted: {png_path}")
            except:
                pass
    
    # Final summary
    total_bubble_questions = sum(
        page['bubble_answers']['questions_detected'] 
        for page in complete_template_data.values() 
        if 'bubble_answers' in page
    )
    total_quick_questions = sum(
        page['quick_answers']['total_questions'] 
        for page in complete_template_data.values() 
        if page.get('quick_answers')
    )
    
    print(f"\n{'='*80}")
    print("FINAL COMPLETE SUMMARY")
    print(f"{'='*80}")
    print(f"Total pages processed: {len(complete_template_data)}")
    print(f"Total bubble questions: {total_bubble_questions}")
    print(f"Total quick answer questions: {total_quick_questions}")
    print(f"Complete template saved: {json_path}")
    
    return json_path


def save_complete_template_to_json(template_data, source_file, output_dir='template'):
    """
    Save complete template data (bubble + quick answers) to JSON file
    
    Args:
        template_data: Dictionary containing complete template information
        source_file: Original source file path (PDF or image)
        output_dir: Directory to save JSON template
        
    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    json_filename = f"{base_name}_complete_template.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Add metadata
    template_data['metadata'] = {
        'source_file': source_file,
        'created_at': datetime.now().isoformat(),
        'total_pages': len([k for k in template_data.keys() if k.startswith('page_')]),
        'extraction_type': 'complete_bubble_and_quick_answers'
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Complete template saved to: {json_path}")
    return json_path


def load_complete_template_from_json(json_path):
    """
    Load a saved complete template from JSON file
    
    Args:
        json_path: Path to JSON template file
        
    Returns:
        Dictionary containing complete template data
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    print(f"[LOADED] Complete template from: {json_path}")
    print(f"  Pages: {template_data['metadata']['total_pages']}")
    print(f"  Type: {template_data['metadata']['extraction_type']}")
    print(f"  Created: {template_data['metadata']['created_at']}")
    
    return template_data


def validate_template_coverage(template_data):
    """
    Validate that template covers expected areas and provide coverage report
    
    Args:
        template_data: Complete template data
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        'pages_processed': 0,
        'bubble_questions_found': 0,
        'quick_questions_found': 0,
        'student_id_found': False,
        'warnings': [],
        'recommendations': []
    }
    
    for page_key, page_data in template_data.items():
        if page_key.startswith('page_'):
            validation_results['pages_processed'] += 1
            
            # Check bubble answers
            bubble_data = page_data.get('bubble_answers', {})
            bubble_questions = bubble_data.get('questions_detected', 0)
            validation_results['bubble_questions_found'] += bubble_questions
            
            if bubble_data.get('student_id'):
                validation_results['student_id_found'] = True
            
            # Check quick answers
            quick_data = page_data.get('quick_answers')
            if quick_data:
                validation_results['quick_questions_found'] += quick_data.get('total_questions', 0)
    
    # Generate warnings and recommendations
    if validation_results['bubble_questions_found'] == 0:
        validation_results['warnings'].append("No bubble questions detected")
        validation_results['recommendations'].append("Check if answer sheet has MCQ section")
    
    if validation_results['quick_questions_found'] == 0:
        validation_results['warnings'].append("No quick answer questions detected")
        validation_results['recommendations'].append("Check if answer sheet has number answer section")
    
    if not validation_results['student_id_found']:
        validation_results['warnings'].append("Student ID section not detected")
        validation_results['recommendations'].append("Verify corner markers are visible and dark enough")
    
    return validation_results


def get_pdf_filename():
    """
    Get PDF filename from user input with validation
    """
    while True:
        print("\n" + "="*50)
        print("PDF TEMPLATE EXTRACTION")
        print("="*50)
        print("Available PDF files in current directory:")
        
        # List all PDF files in current directory
        pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
        
        if pdf_files:
            for i, pdf_file in enumerate(pdf_files, 1):
                print(f"  {i}. {pdf_file}")
            print("  *. Enter custom filename")
        else:
            print("  No PDF files found in current directory")
        
        filename = input("\nEnter PDF filename (or number from list): ").strip()
        
        # If user entered a number from the list
        if filename.isdigit():
            index = int(filename) - 1
            if 0 <= index < len(pdf_files):
                selected_file = pdf_files[index]
                if os.path.exists(selected_file):
                    return selected_file
                else:
                    print(f"Error: File '{selected_file}' not found!")
            else:
                print("Invalid selection! Please choose a number from the list.")
        else:
            # User entered a custom filename
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            if os.path.exists(filename):
                return filename
            else:
                print(f"Error: File '{filename}' not found!")
                print("Please make sure the file exists in the current directory.")


def get_processing_options():
    """
    Get processing options from user
    """
    print("\nProcessing Options:")
    print("1. DPI setting (image quality)")
    print("2. Keep temporary PNG files")
    print("3. Show visualization windows")
    print("4. Use default settings")
    
    choice = input("\nChoose option (1-4) [4]: ").strip()
    
    if choice == '1':
        dpi = input("Enter DPI (150-600, default 300): ").strip()
        try:
            dpi = int(dpi) if dpi else 300
        except ValueError:
            dpi = 300
        return {'dpi': dpi, 'keep_png': False, 'show_visualization': True}
    
    elif choice == '2':
        keep = input("Keep temporary PNG files? (y/n) [n]: ").strip().lower()
        keep_png = keep in ['y', 'yes']
        return {'dpi': 300, 'keep_png': keep_png, 'show_visualization': True}
    
    elif choice == '3':
        viz = input("Show visualization windows? (y/n) [y]: ").strip().lower()
        show_viz = viz not in ['n', 'no']
        return {'dpi': 300, 'keep_png': False, 'show_visualization': show_viz}
    
    else:
        return {'dpi': 300, 'keep_png': False, 'show_visualization': True}


def main():
    """
    Main function with interactive PDF filename input
    """
    print("="*60)
    print("COMPLETE ANSWER SHEET TEMPLATE EXTRACTOR")
    print("="*60)
    
    # Get PDF filename from user
    pdf_filename = get_pdf_filename()
    
    # Get processing options
    options = get_processing_options()
    
    print(f"\nStarting extraction for: {pdf_filename}")
    print(f"Settings: DPI={options['dpi']}, Keep PNG={options['keep_png']}, Visualization={options['show_visualization']}")
    
    # Confirm processing
    confirm = input("\nStart processing? (y/n) [y]: ").strip().lower()
    if confirm in ['n', 'no']:
        print("Processing cancelled.")
        return
    
    # Process the PDF
    try:
        json_path = process_pdf_complete_template(
            pdf_path=pdf_filename,
            dpi=options['dpi'],
            keep_png=options['keep_png'],
            show_visualization=options['show_visualization']
        )
        
        if json_path:
            # Load and validate the template
            template = load_complete_template_from_json(json_path)
            validation = validate_template_coverage(template)
            
            # Display validation results
            print(f"\n" + "="*60)
            print("VALIDATION RESULTS")
            print("="*60)
            print(f"Pages processed: {validation['pages_processed']}")
            print(f"Bubble questions found: {validation['bubble_questions_found']}")
            print(f"Quick answer questions found: {validation['quick_questions_found']}")
            print(f"Student ID detected: {'YES' if validation['student_id_found'] else 'NO'}")
            
            if validation['warnings']:
                print(f"\nWARNINGS:")
                for warning in validation['warnings']:
                    print(f"  ⚠ {warning}")
            
            if validation['recommendations']:
                print(f"\nRECOMMENDATIONS:")
                for rec in validation['recommendations']:
                    print(f"  💡 {rec}")
            
            print(f"\n✅ Template successfully created: {json_path}")
            
            # Option to view template contents
            view = input("\nView template contents? (y/n) [n]: ").strip().lower()
            if view in ['y', 'yes']:
                print(f"\nTemplate structure:")
                for page_key, page_data in template.items():
                    if page_key.startswith('page_'):
                        print(f"\n{page_key}:")
                        print(f"  Image: {page_data['image_dimensions']['width']}x{page_data['image_dimensions']['height']}")
                        print(f"  Bubble questions: {page_data['bubble_answers']['questions_detected']}")
                        if page_data['quick_answers']:
                            print(f"  Quick answers: {page_data['quick_answers']['total_questions']}")
        
        else:
            print(f"\n❌ Failed to create template from {pdf_filename}")
    
    except Exception as e:
        print(f"\n❌ ERROR during processing: {e}")
        print("Please check that:")
        print("  - The PDF file is not corrupted")
        print("  - You have sufficient disk space")
        print("  - All required dependencies are installed")
    
    # Option to process another file
    another = input("\nProcess another PDF? (y/n) [n]: ").strip().lower()
    if another in ['y', 'yes']:
        main()
    else:
        print("\nThank you for using the Template Extractor!")
        print("Goodbye!")


if __name__ == "__main__":
    main()