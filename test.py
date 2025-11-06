"""
test.py - Complete Answer Sheet Processing Pipeline

This script runs the entire workflow from creating a blank template
to grading filled answer sheets.

Pipeline Steps:
1. Generate blank PDF template
2. Extract bubble positions and save to JSON
3. Create answer key
4. Scan filled answer sheet
5. Grade the answers
"""

import os
import sys
from datetime import datetime


def print_step(step_num, step_name):
    """Print formatted step header"""
    print("\n" + "="*70)
    print(f"STEP {step_num}: {step_name}")
    print("="*70)


def step1_generate_template():
    """Step 1: Generate blank PDF template using sheet_maker"""
    print_step(1, "GENERATE BLANK PDF TEMPLATE")
    
    # Import sheet_maker if you have it, otherwise skip
    try:
        # Assuming you have a sheet_maker module
        # If not, you'll need to create the PDF manually
        print("\nNote: Please create your blank PDF template manually or using your sheet_maker")
        print("Expected output: A PDF file with bubble questions")
        
        template_pdf = input("\nEnter path to your blank template PDF: ").strip()
        if not template_pdf:
            template_pdf = 'answer_sheet.pdf'
        
        if not os.path.exists(template_pdf):
            print(f"[ERROR] Template PDF not found: {template_pdf}")
            print("Please create a blank answer sheet PDF first.")
            return None
        
        print(f"[SUCCESS] Using template: {template_pdf}")
        return template_pdf
        
    except ImportError:
        print("[INFO] sheet_maker module not found")
        print("Please provide a blank answer sheet PDF manually")
        return None


def step2_extract_bubbles(template_pdf):
    """Step 2: Extract bubble positions and save to JSON"""
    print_step(2, "EXTRACT BUBBLE POSITIONS")
    
    try:
        from core.bubble_extraction import process_pdf_answer_sheet
        
        print(f"\nProcessing PDF: {template_pdf}")
        print("This will detect all bubbles and save positions to JSON...\n")
        
        # Extract bubbles and save to template directory
        json_path = process_pdf_answer_sheet(
            pdf_path=template_pdf,
            dpi=300,
            keep_png=False,
            show_visualization=True  # Show detection for verification
        )
        
        if json_path:
            print(f"\n[SUCCESS] Template saved to: {json_path}")
            return json_path
        else:
            print("[ERROR] Failed to extract bubbles")
            return None
            
    except ImportError as e:
        print(f"[ERROR] Failed to import bubble_detector: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to extract bubbles: {e}")
        return None


def step3_create_answer_key(template_json):
    """Step 3: Create answer key"""
    print_step(3, "CREATE ANSWER KEY")
    
    try:
        from core.answer_key import load_template_info, create_answer_key_manual, create_answer_key_from_scan
        
        print(f"\nUsing template: {template_json}")
        
        # Load template info
        template_info = load_template_info(template_json)
        
        print("\nChoose answer key creation method:")
        print("1. Manual entry (type answers)")
        print("2. Scan master answer sheet (automatic)")
        
        choice = input("\nEnter choice (1-2): ").strip()
        
        if choice == '1':
            # Manual entry
            answer_key, key_json = create_answer_key_manual(template_info)
            print(f"\n[SUCCESS] Answer key created: {key_json}")
            return key_json
            
        elif choice == '2':
            # Scan master sheet
            master_sheet = input("\nEnter master answer sheet image path: ").strip()
            if not master_sheet:
                master_sheet = 'master_answer_sheet.png'
            
            if not os.path.exists(master_sheet):
                print(f"[ERROR] Master sheet not found: {master_sheet}")
                return None
            
            threshold = input("Enter detection threshold (default 50): ").strip()
            threshold = int(threshold) if threshold else 50
            
            answer_key, key_json = create_answer_key_from_scan(
                template_info,
                master_sheet,
                threshold_percent=threshold
            )
            
            if key_json:
                print(f"\n[SUCCESS] Answer key created: {key_json}")
                return key_json
            else:
                print("[ERROR] Failed to create answer key from scan")
                return None
        else:
            print("[ERROR] Invalid choice")
            return None
            
    except ImportError as e:
        print(f"[ERROR] Failed to import answer_key: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create answer key: {e}")
        return None


def step4_scan_answer_sheet(template_json):
    """Step 4: Scan filled answer sheet and save to JSON"""
    print_step(4, "SCAN FILLED ANSWER SHEET")
    
    try:
        from core.answer_extraction import BubbleTemplate, AnswerExtractor, save_answers_to_json
        
        # Get filled answer sheet path
        answer_sheet = input("\nEnter filled answer sheet image path: ").strip()
        if not answer_sheet:
            answer_sheet = 'filled_answer_sheet.png'
        
        if not os.path.exists(answer_sheet):
            print(f"[ERROR] Answer sheet not found: {answer_sheet}")
            return None
        
        # Get detection threshold
        threshold = input("Enter detection threshold (default 50): ").strip()
        threshold = int(threshold) if threshold else 50
        
        print(f"\nScanning answer sheet: {answer_sheet}")
        print(f"Detection threshold: {threshold}%\n")
        
        # Load template
        template = BubbleTemplate(template_json)
        
        # Extract answers
        extractor = AnswerExtractor(template)
        questions = extractor.extract_answers(
            answer_sheet,
            threshold_percent=threshold,
            debug=True  # Show visualization
        )
        
        if not questions:
            print("[ERROR] Failed to extract answers")
            return None
        
        # Save to JSON
        answers_json = save_answers_to_json(
            questions=questions,
            source_image_path=answer_sheet,
            template_path=template_json,
            threshold_percent=threshold
        )
        
        print(f"\n[SUCCESS] Answers saved to: {answers_json}")
        return answers_json
        
    except ImportError as e:
        print(f"[ERROR] Failed to import answer_extraction: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to scan answer sheet: {e}")
        return None


def step5_grade_answers(key_json, answers_json):
    """Step 5: Grade the scanned answers"""
    print_step(5, "GRADE ANSWER SHEET")
    
    try:
        from core.grading import load_answer_key, load_scanned_answers, grade_answers
        from core.grading import print_grading_summary, print_detailed_results, save_grade_report
        
        print(f"\nAnswer key: {key_json}")
        print(f"Scanned answers: {answers_json}\n")
        
        # Load data
        answer_key_data = load_answer_key(key_json)
        scanned_answers_data = load_scanned_answers(answers_json)
        
        # Ask for grading options
        partial = input("\nEnable partial credit? (y/n, default n): ").strip().lower()
        partial_credit = (partial == 'y')
        
        max_pts = input(f"Enter maximum points (default {answer_key_data['metadata']['total_questions']}): ").strip()
        if max_pts:
            try:
                max_points = float(max_pts)
            except ValueError:
                max_points = None
        else:
            max_points = None
        
        # Grade
        results = grade_answers(
            answer_key_data,
            scanned_answers_data,
            max_points=max_points,
            partial_credit=partial_credit
        )
        
        # Display results
        print_grading_summary(results)
        
        # Ask to show details
        show_details = input("\nShow detailed results? (y/n): ").strip().lower()
        if show_details == 'y':
            show_option = input("Show (a)ll, (i)ncorrect only, or (f)irst 10? [f]: ").strip().lower()
            if show_option == 'a':
                print_detailed_results(results, show_all=True)
            elif show_option == 'i':
                print_detailed_results(results, show_incorrect_only=True)
            else:
                print_detailed_results(results, show_all=False)
        
        # Save report
        report_json = save_grade_report(results, key_json, answers_json)
        
        print(f"\n[SUCCESS] Grade report saved to: {report_json}")
        return report_json
        
    except ImportError as e:
        print(f"[ERROR] Failed to import grading: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to grade answers: {e}")
        return None


def run_full_pipeline():   
    input("\nPress Enter to start...")
    
    # Step 1: Generate/Load Template PDF
    template_pdf = step1_generate_template()
    if not template_pdf:
        print("\n[ABORTED] Pipeline stopped at Step 1")
        return
    
    # Step 2: Extract Bubbles
    template_json = step2_extract_bubbles(template_pdf)
    if not template_json:
        print("\n[ABORTED] Pipeline stopped at Step 2")
        return
    
    # Step 3: Create Answer Key
    key_json = step3_create_answer_key(template_json)
    if not key_json:
        print("\n[ABORTED] Pipeline stopped at Step 3")
        return
    
    # Step 4: Scan Answer Sheet
    answers_json = step4_scan_answer_sheet(template_json)
    if not answers_json:
        print("\n[ABORTED] Pipeline stopped at Step 4")
        return
    
    # Step 5: Grade
    report_json = step5_grade_answers(key_json, answers_json)
    if not report_json:
        print("\n[ABORTED] Pipeline stopped at Step 5")
        return
    
    # Success!
    print("\n" + "="*70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\nGenerated files:")
    print(f"  Template: {template_json}")
    print(f"  Answer key: {key_json}")
    print(f"  Scanned answers: {answers_json}")
    print(f"  Grade report: {report_json}")
    print("\nYou can now use these files for future grading!")


def run_quick_test():
    """Quick test with existing files"""
    print("="*70)
    print("QUICK TEST MODE")
    print("="*70)
    print("\nThis mode assumes you already have:")
    print("  - A template JSON file")
    print("  - An answer key JSON file")
    print("  - A filled answer sheet image")
    
    template_json = input("\nEnter template JSON path: ").strip()
    if not template_json or not os.path.exists(template_json):
        print("[ERROR] Template not found")
        return
    
    key_json = input("Enter answer key JSON path: ").strip()
    if not key_json or not os.path.exists(key_json):
        print("[ERROR] Answer key not found")
        return
    
    # Scan and grade
    answers_json = step4_scan_answer_sheet(template_json)
    if answers_json:
        step5_grade_answers(key_json, answers_json)


def main():
    """Main function"""
    print("\n" + "="*70)
    print("ANSWER SHEET PROCESSING SYSTEM - TEST PIPELINE")
    print("="*70)
    
    print("\nChoose mode:")
    print("1. Full pipeline (create everything from scratch)")
    print("2. Quick test (use existing template and answer key)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        run_full_pipeline()
    elif choice == '2':
        run_quick_test()
    elif choice == '3':
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()