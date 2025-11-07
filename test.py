"""
test.py - Complete Answer Sheet Processing Pipeline (updated)

This version keeps the original 5-step flow but is tolerant to changes
in core/bubble_extraction.py. It will try the newer high-level
process_pdf_answer_sheet and fall back to lower-level helpers if needed.

Updated to use core.extraction (extractor.extract_complete) for scanning
and to include the student ID in the saved grade report.
"""
import os
import sys
import json
import tempfile
from datetime import datetime

def print_step(step_num, step_name):
    """Print formatted step header"""
    print("\n" + "="*70)
    print(f"STEP {step_num}: {step_name}")
    print("="*70)

def step1_generate_template():
    """Step 1: Ask for blank PDF template path"""
    print_step(1, "GENERATE / SELECT BLANK PDF TEMPLATE")
    template_pdf = input("\nEnter path to your blank template PDF (leave empty for 'answer_sheet.pdf'): ").strip()
    if not template_pdf:
        template_pdf = 'answer_sheet.pdf'
    if not os.path.exists(template_pdf):
        print(f"[ERROR] Template PDF not found: {template_pdf}")
        return None
    print(f"[SUCCESS] Using template: {template_pdf}")
    return template_pdf

def _save_template_json(data, out_path=None):
    """Save template info to JSON and return path"""
    if out_path is None:
        out_path = os.path.join(os.getcwd(), f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return out_path

def step2_extract_bubbles(template_pdf):
    """Step 2: Extract bubble positions and save to JSON

    Tries to call process_pdf_answer_sheet (preferred). If not available,
    attempts a fallback using lower-level helpers from core.bubble_extraction.
    """
    print_step(2, "EXTRACT BUBBLE POSITIONS FROM TEMPLATE")
    try:
        from core.bubble_extraction import process_pdf_answer_sheet
        print(f"\nCalling process_pdf_answer_sheet on: {template_pdf}")
        json_path = process_pdf_answer_sheet(pdf_path=template_pdf, dpi=300, keep_png=False, show_visualization=True)
        if json_path and os.path.exists(json_path):
            print(f"[SUCCESS] Template JSON: {json_path}")
            return json_path
        else:
            print("[WARNING] process_pdf_answer_sheet returned no file, falling back to helpers.")
    except Exception as e:
        print(f"[INFO] High-level function not available or failed: {e}")
        print("[INFO] Trying fallback extraction using lower-level functions...")

    # Fallback: try to use lower-level helpers
    try:
        from core.bubble_extraction import convert_pdf_to_png, detect_question_bubbles, detect_id_bubbles
    except Exception as e:
        print(f"[ERROR] Required fallback functions not available: {e}")
        return None

    try:
        tmpdir = tempfile.mkdtemp(prefix="omr_template_")
        pngs = convert_pdf_to_png(template_pdf, output_folder=tmpdir, dpi=300)
        if isinstance(pngs, (list, tuple)) and len(pngs) > 0:
            png_path = pngs[0]
        elif isinstance(pngs, str) and os.path.exists(pngs):
            png_path = pngs
        else:
            # if convert_pdf_to_png returns None or unexpected, try default png path
            png_path = os.path.join(tmpdir, 'page-1.png')

        if not os.path.exists(png_path):
            print(f"[ERROR] Could not locate converted PNG: {png_path}")
            return None

        # Detect question bubbles and id bubbles (functions should return structured data)
        questions = detect_question_bubbles(png_path, id_region=None, show_visualization=True)
        id_info = detect_id_bubbles(png_path, id_region=None, show_visualization=True)

        template_info = {
            'metadata': {
                'source_pdf': template_pdf,
                'generated_at': datetime.now().isoformat()
            },
            'questions': questions,
            'id_region': id_info
        }
        json_path = _save_template_json(template_info)
        print(f"[SUCCESS] Template JSON saved to: {json_path}")
        return json_path

    except Exception as e:
        print(f"[ERROR] Fallback extraction failed: {e}")
        return None

def step3_create_answer_key(template_json):
    """Step 3: Create answer key"""
    print_step(3, "CREATE ANSWER KEY")
    try:
        from core.answer_key import load_template_info, create_answer_key_manual, create_answer_key_from_scan

        print(f"\nUsing template: {template_json}")
        template_info = load_template_info(template_json)

        print("\nChoose answer key creation method:")
        print("1. Manual entry (type answers)")
        print("2. Scan master answer sheet (automatic)")

        choice = input("\nEnter choice (1-2): ").strip()
        if choice == '1':
            answer_key, key_json = create_answer_key_manual(template_info)
            print(f"[SUCCESS] Answer key created: {key_json}")
            return key_json
        elif choice == '2':
            master_sheet = input("\nEnter master answer sheet image path: ").strip() or 'master_answer_sheet.png'
            if not os.path.exists(master_sheet):
                print(f"[ERROR] Master sheet not found: {master_sheet}")
                return None
            threshold = input("Enter detection threshold (default 50): ").strip()
            threshold = int(threshold) if threshold else 50
            answer_key, key_json = create_answer_key_from_scan(template_info, master_sheet, threshold_percent=threshold)
            if key_json:
                print(f"[SUCCESS] Answer key created: {key_json}")
                return key_json
            print("[ERROR] Failed to create answer key from scan")
            return None
        else:
            print("[ERROR] Invalid choice")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to create answer key: {e}")
        return None

def step4_scan_answer_sheet(template_json):
    """Step 4: Scan filled answer sheet and save to JSON (uses core.extraction)"""
    print_step(4, "SCAN FILLED ANSWER SHEET")
    try:
        from core.extraction import BubbleTemplate, AnswerSheetExtractor, save_extraction_to_json

        answer_sheet = input("\nEnter filled answer sheet image path: ").strip() or 'filled_answer_sheet.png'
        if not os.path.exists(answer_sheet):
            print(f"[ERROR] Answer sheet not found: {answer_sheet}")
            return None

        threshold = input("Enter detection threshold (default 50): ").strip()
        threshold = int(threshold) if threshold else 50

        print(f"\nScanning: {answer_sheet} (threshold {threshold}%)")
        template = BubbleTemplate(template_json)
        extractor = AnswerSheetExtractor(template)
        result = extractor.extract_complete(answer_sheet, threshold_percent=threshold, debug=True)
        if not result:
            print("[ERROR] Failed to extract answers")
            return None

        answers_json = save_extraction_to_json(result)
        print(f"[SUCCESS] Answers saved to: {answers_json}")
        return answers_json

    except Exception as e:
        print(f"[ERROR] Failed to scan answer sheet: {e}")
        return None

def step5_grade_answers(key_json, answers_json):
    """Step 5: Grade the scanned answers and include student ID in the report"""
    print_step(5, "GRADE ANSWER SHEET")
    try:
        from core.grading import load_answer_key, load_scanned_answers, grade_answers
        from core.grading import print_grading_summary, print_detailed_results, save_grade_report

        print(f"\nAnswer key: {key_json}")
        print(f"Scanned answers: {answers_json}\n")

        answer_key_data = load_answer_key(key_json)
        scanned_answers_data = load_scanned_answers(answers_json)

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

        results = grade_answers(answer_key_data, scanned_answers_data, max_points=max_points, partial_credit=partial_credit)
        print_grading_summary(results)

        show_details = input("\nShow detailed results? (y/n): ").strip().lower()
        if show_details == 'y':
            show_option = input("Show (a)ll, (i)ncorrect only, or (f)irst 10? [f]: ").strip().lower()
            if show_option == 'a':
                print_detailed_results(results, show_all=True)
            elif show_option == 'i':
                print_detailed_results(results, show_incorrect_only=True)
            else:
                print_detailed_results(results, show_all=False)

        # Save grade report (existing function)
        report_json = save_grade_report(results, key_json, answers_json)
        print(f"[SUCCESS] Grade report saved to: {report_json}")

        # Attempt to embed student id into the grade report JSON (best-effort)
        try:
            student_id = None
            if scanned_answers_data and isinstance(scanned_answers_data, dict):
                sid = scanned_answers_data.get('student_id')
                if isinstance(sid, dict):
                    student_id = sid.get('student_id')
                elif isinstance(sid, str):
                    student_id = sid
            if student_id and os.path.exists(report_json):
                with open(report_json, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                report_data.setdefault('metadata', {})
                report_data['metadata']['student_id'] = student_id
                with open(report_json, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                print(f"[SUCCESS] Embedded student ID ({student_id}) into grade report")
        except Exception:
            pass

        return report_json

    except Exception as e:
        print(f"[ERROR] Failed to grade answers: {e}")
        return None

def run_full_pipeline():
    input("\nPress Enter to start...")
    template_pdf = step1_generate_template()
    if not template_pdf:
        print("\n[ABORTED] Pipeline stopped at Step 1")
        return
    template_json = step2_extract_bubbles(template_pdf)
    if not template_json:
        print("\n[ABORTED] Pipeline stopped at Step 2")
        return
    key_json = step3_create_answer_key(template_json)
    if not key_json:
        print("\n[ABORTED] Pipeline stopped at Step 3")
        return
    answers_json = step4_scan_answer_sheet(template_json)
    if not answers_json:
        print("\n[ABORTED] Pipeline stopped at Step 4")
        return
    report_json = step5_grade_answers(key_json, answers_json)
    if not report_json:
        print("\n[ABORTED] Pipeline stopped at Step 5")
        return

    print("\n" + "="*70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\nGenerated files:")
    print(f"  Template: {template_json}")
    print(f"  Answer key: {key_json}")
    print(f"  Scanned answers: {answers_json}")
    print(f"  Grade report: {report_json}")

def run_quick_test():
    """Quick test with existing files"""
    print("="*70)
    print("QUICK TEST MODE")
    print("="*70)
    template_json = input("\nEnter template JSON path: ").strip()
    if not template_json or not os.path.exists(template_json):
        print("[ERROR] Template not found")
        return
    key_json = input("Enter answer key JSON path: ").strip()
    if not key_json or not os.path.exists(key_json):
        print("[ERROR] Answer key not found")
        return
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