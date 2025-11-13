"""
test.py - Complete Answer Sheet Processing Pipeline

This script runs the entire workflow:
1. Create blank PDF template
2. Extract bubble positions and save to JSON
3. Create answer key (manual or scan master sheet)
4. Extract answers and grade (combined)
"""

import os
import sys
from datetime import datetime
import glob
import csv
import json


def print_step(step_num, step_name):
    """Print formatted step header"""
    print("\n" + "="*70)
    print(f"STEP {step_num}: {step_name}")
    print("="*70)


def step1_create_blank_sheet():
    """Step 1: Create blank PDF answer sheet"""
    print_step(1, "CREATE BLANK PDF ANSWER SHEET")
    
    try:
        from core.sheet_maker import AnswerSheetDesigner
        
        # Get user input
        print("\nAnswer Sheet Configuration:")
        num_questions = input("Number of questions (10/20/30/40): ").strip()
        if not num_questions:
            num_questions = "40"
        
        try:
            num_questions = int(num_questions)
        except ValueError:
            print("[ERROR] Invalid number. Using 40 questions.")
            num_questions = 40
        
        # Get output path
        output_path = input(f"Save as (default: answer_sheet.pdf): ").strip()
        if not output_path:
            output_path = f'answer_sheet.pdf'
        
        if not output_path.endswith('.pdf'):
            output_path += '.pdf'
        
        print(f"\nCreating {num_questions}-question answer sheet...")
        
        # Create designer and generate PDF
        designer = AnswerSheetDesigner()
        designer.set_config(include_student_id=True)
        
        # Use preset for optimal layout
        designer.create_answer_sheet(
            total_questions=num_questions,
            output_path=output_path,
            format='pdf',
            use_preset=True
        )
        
        print(f"\n[SUCCESS] Blank sheet created: {output_path}")
        return output_path
        
    except ImportError as e:
        print(f"[ERROR] Failed to import sheet_maker: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create blank sheet: {e}")
        return None


def step2_extract_bubble_positions(pdf_path):
    """Step 2: Extract bubble positions from PDF and save to JSON"""
    print_step(2, "EXTRACT BUBBLE POSITIONS")
    
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found: {pdf_path}")
        
        # Ask user to provide PDF
        pdf_path = input("\nEnter path to blank PDF template: ").strip()
        if not pdf_path or not os.path.exists(pdf_path):
            print("[ERROR] Invalid PDF path")
            return None
    
    try:
        from core.bubble_extraction import process_pdf_answer_sheet
        
        print(f"\nProcessing PDF: {pdf_path}")
        
        # Get options
        dpi_input = input("DPI quality (150/300, default 300): ").strip()
        dpi = int(dpi_input) if dpi_input else 300
        
        show_viz = input("Show visualization? (y/n, default y): ").strip().lower()
        show_visualization = show_viz != 'n'
        
        print("\nExtracting bubble positions...")
        print("This will detect questions AND student ID bubbles...\n")
        
        # Extract bubbles and save to JSON
        json_path = process_pdf_answer_sheet(
            pdf_path=pdf_path,
            dpi=dpi,
            keep_png=False,
            show_visualization=show_visualization
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
    """Step 3: Create answer key (manual or scan master sheet)"""
    print_step(3, "CREATE ANSWER KEY")
    
    if not template_json or not os.path.exists(template_json):
        print(f"[ERROR] Template JSON not found: {template_json}")
        
        # Ask user to provide template
        template_json = input("\nEnter path to template JSON: ").strip()
        if not template_json or not os.path.exists(template_json):
            print("[ERROR] Invalid template path")
            return None
    
    try:
        from core.answer_key import load_template_info, create_answer_key_manual, create_answer_key_from_scan
        
        print(f"\nUsing template: {template_json}")
        
        # Load template info
        template_info = load_template_info(template_json)
        
        print("\nChoose answer key creation method:")
        print("1. Manual entry (type answers for each question)")
        print("2. Scan master answer sheet (automatic detection)")
        
        choice = input("\nEnter choice (1-2, default 1): ").strip()
        if not choice:
            choice = '1'
        
        if choice == '1':
            # Manual entry
            print("\n[MANUAL ENTRY MODE]")
            print("You will be prompted to enter the correct answer for each question.")
            print("Press Enter when ready...")
            input()
            
            answer_key, key_json = create_answer_key_manual(template_info)
            print(f"\n[SUCCESS] Answer key created: {key_json}")
            return key_json
            
        elif choice == '2':
            # Scan master sheet
            master_sheet = input("\nEnter path to master answer sheet image: ").strip()
            if not master_sheet:
                master_sheet = 'master_answer_sheet.png'
            
            if not os.path.exists(master_sheet):
                print(f"[ERROR] Master sheet not found: {master_sheet}")
                return None
            
            threshold = input("Detection threshold (20-80, default 50): ").strip()
            threshold = int(threshold) if threshold else 50
            
            print("\nScanning master answer sheet...")
            
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


def step4_extract_and_grade(template_json, key_json, show_details = False):
    """Step 4: Extract answers from filled sheet and grade"""
    print_step(4, "EXTRACT ANSWERS & GRADE")
    
    if not template_json or not os.path.exists(template_json):
        print(f"[ERROR] Template JSON not found: {template_json}")
        return None
    
    if not key_json or not os.path.exists(key_json):
        print(f"[ERROR] Answer key not found: {key_json}")
        return None
    
    try:
        from core.extraction import BubbleTemplate, AnswerSheetExtractor, save_extraction_to_json
        from core.grading import load_answer_key, grade_answers, print_grading_summary, save_grade_report
        
        # Get filled answer sheet
        answer_sheet = input("\nEnter path to filled answer sheet image: ").strip()
        if not answer_sheet:
            answer_sheet = 'filled_answer_sheet.png'
        
        if not os.path.exists(answer_sheet):
            print(f"[ERROR] Answer sheet not found: {answer_sheet}")
            return None
        
        # Get extraction options
        threshold = input("Detection threshold (20-80, default 50): ").strip()
        threshold = int(threshold) if threshold else 50
        
        show_viz = input("Show visualization? (y/n, default y): ").strip().lower()
        show_visualization = show_viz != 'n'
        
        print("\n" + "="*70)
        print("PART A: EXTRACTING ANSWERS & STUDENT ID")
        print("="*70)
        
        # Load template and extract
        template = BubbleTemplate(template_json)
        extractor = AnswerSheetExtractor(template)
        
        result = extractor.extract_complete(
            answer_sheet,
            threshold_percent=threshold,
            debug=show_visualization
        )
        
        if not result:
            print("[ERROR] Failed to extract answers")
            return None
        
        # Save extraction results
        extraction_json = save_extraction_to_json(result)
        
        print("\n" + "="*70)
        print("PART B: GRADING")
        print("="*70)
        
        # Load answer key
        answer_key_data = load_answer_key(key_json)
        
        # Prepare scanned answers data in expected format
        scanned_answers_data = {
            'metadata': result['metadata'],
            'answers': result['answers']
        }
        
        # Get grading options
        max_pts = input(f"\nMaximum points (default: {len(result['answers'])}): ").strip()
        if max_pts:
            try:
                max_points = float(max_pts)
            except ValueError:
                max_points = None
        else:
            max_points = None
        
        partial = input("Enable partial credit? (y/n, default n): ").strip().lower()
        partial_credit = (partial == 'y')
        
        # Grade the answers
        print("\nGrading answers...")
        
        grade_results = grade_answers(
            answer_key_data,
            scanned_answers_data,
            max_points=max_points,
            partial_credit=partial_credit
        )
        
        # Display results
        print_grading_summary(grade_results)

        if show_details == True:
            # Show details?
            show_details = input("\nShow detailed results? (y/n): ").strip().lower()
            if show_details == 'y':
                from core.grading import print_detailed_results
                
                show_option = input("Show (a)ll, (i)ncorrect only, or (f)irst 10? [f]: ").strip().lower()
                if show_option == 'a':
                    print_detailed_results(grade_results, show_all=True)
                elif show_option == 'i':
                    print_detailed_results(grade_results, show_incorrect_only=True)
                else:
                    print_detailed_results(grade_results, show_all=False)
        
        # Save grade report
        report_json = save_grade_report(grade_results, key_json, extraction_json)
        print(f"\n[SUCCESS] Grade report saved: {report_json}")
        
        return {
            'extraction': extraction_json,
            'grade_report': report_json,
            'student_id': result.get('student_id'),
            'grade_results': grade_results
        }
        
    except ImportError as e:
        print(f"[ERROR] Failed to import required modules: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to extract and grade: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_full_pipeline():
    """Run the complete pipeline"""
    print("="*70)
    print("COMPLETE ANSWER SHEET PROCESSING PIPELINE")
    print("="*70)
    print("\nThis pipeline will guide you through:")
    print("  1. Creating a blank PDF answer sheet")
    print("  2. Extracting bubble positions (questions + student ID)")
    print("  3. Creating an answer key")
    print("  4. Extracting answers and grading")
    
    input("\nPress Enter to start...")
    
    # Step 1: Create blank PDF
    pdf_path = step1_create_blank_sheet()
    if not pdf_path:
        print("\n[ABORTED] Pipeline stopped at Step 1")
        return
    
    # Step 2: Extract bubble positions
    template_json = step2_extract_bubble_positions(pdf_path)
    if not template_json:
        print("\n[ABORTED] Pipeline stopped at Step 2")
        return
    
    # Step 3: Create answer key
    key_json = step3_create_answer_key(template_json)
    if not key_json:
        print("\n[ABORTED] Pipeline stopped at Step 3")
        return
    
    # Step 4: Extract and grade
    final_results = step4_extract_and_grade(template_json, key_json)
    if not final_results:
        print("\n[ABORTED] Pipeline stopped at Step 4")
        return
    
    # Success!
    print("\n" + "="*70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\nGenerated files:")
    print(f"  1. Blank template: {pdf_path}")
    print(f"  2. Template JSON: {template_json}")
    print(f"  3. Answer key: {key_json}")
    print(f"  4. Extracted answers: {final_results['extraction']}")
    print(f"  5. Grade report: {final_results['grade_report']}")
    
    if final_results.get('student_id'):
        print(f"\nStudent ID: {final_results['student_id']['student_id']}")
    
    print(f"\nFinal Score: {final_results['grade_results']['score']:.2f} / {final_results['grade_results']['max_points']:.2f}")
    print(f"Percentage: {final_results['grade_results']['percentage']:.2f}%")
    
    print("\n✓ All files saved and ready for use!")

def batch_grade_images(template_json, key_json, images_path, output_dir=None, threshold=50, partial_credit=False, show_visualization=False):
    """
    Batch process and grade a folder (or list) of filled answer sheet images.
    Saves two summaries:
      - batch_summary.json (existing detailed summary)
      - batch_results_compact.csv (compact CSV with format:
          student_id,score,percentage,Q1,Q2,...,Qn
        where Qk is 1 for correct, 0 for wrong)
    """
    from core.extraction import BubbleTemplate, AnswerSheetExtractor, save_extraction_to_json
    from core.grading import load_answer_key, grade_answers, save_grade_report

    import glob
    import csv
    import json
    import os

    # Resolve images list
    if isinstance(images_path, str) and os.path.isdir(images_path):
        patterns = ['*.png', '*.jpg', '*.jpeg', '*.tif', '*.tiff', '*.bmp']
        image_files = []
        for p in patterns:
            image_files.extend(sorted(glob.glob(os.path.join(images_path, p))))
    elif isinstance(images_path, str) and (',' in images_path):
        image_files = [p.strip() for p in images_path.split(',') if p.strip()]
    else:
        image_files = [images_path] if images_path else []

    image_files = [p for p in image_files if os.path.exists(p)]
    if not image_files:
        print(f"[ERROR] No valid images found for: {images_path}")
        return None

    if output_dir is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join(os.getcwd(), f"batch_results_{ts}")
    os.makedirs(output_dir, exist_ok=True)

    answer_key_data = load_answer_key(key_json)
    # Attempt to get canonical answer mapping and number of questions
    key_answers = answer_key_data.get('answers') if isinstance(answer_key_data, dict) else None
    try:
        total_questions = int(answer_key_data.get('metadata', {}).get('total_questions') or len(key_answers or {}))
    except Exception:
        total_questions = None

    template = BubbleTemplate(template_json)
    extractor = AnswerSheetExtractor(template)

    summary = []
    compact_rows = []  # rows for the compact CSV: [student_id, score, percentage, q1,...,qN]

    def _per_question_outcomes_from_grade(grade_results, total_q=None):
        """
        Try to extract per-question correct(1)/wrong(0) sequence from grader output.
        Returns list length total_q if known, else best-effort list.
        """
        outcomes = []
        # Preferred: grade_results['details'] where each question has 'points' and full points known
        details = grade_results.get('details') if isinstance(grade_results, dict) else None
        summary = grade_results.get('summary') if isinstance(grade_results, dict) else None

        points_per_q = None
        if summary and isinstance(summary, dict):
            points_per_q = summary.get('points_per_question') or None
            if points_per_q is None:
                maxp = summary.get('max_points') or summary.get('max_score') or None
                tq = summary.get('total_questions') or summary.get('total') or None
                try:
                    if maxp is not None and tq:
                        points_per_q = float(maxp) / int(tq)
                except Exception:
                    points_per_q = None

            if total_q is None:
                total_q = summary.get('total_questions') or summary.get('total') or total_q

        if details and isinstance(details, dict):
            # details keys may be "1","2",...
            ordered_keys = sorted(details.keys(), key=lambda k: int(k))
            for k in ordered_keys:
                info = details[k] or {}
                pts = info.get('points')
                if pts is None:
                    # maybe boolean 'correct'
                    correct_flag = info.get('correct')
                    outcomes.append(1 if correct_flag else 0)
                else:
                    if points_per_q is not None:
                        outcomes.append(1 if abs(float(pts) - float(points_per_q)) < 1e-6 else 0)
                    else:
                        outcomes.append(1 if float(pts) > 0 else 0)
            # pad/truncate to total_q if known
            if total_q:
                outcomes = (outcomes + [0]*total_q)[:total_q]
            return outcomes

        # Fallback: try grade_results['answers_correct'] or similar structures
        if isinstance(grade_results.get('answers'), dict):
            # compare each answer with key if available
            if key_answers:
                for q in sorted(key_answers.keys(), key=lambda kk: int(kk)):
                    correct_ans = key_answers.get(q)
                    scanned_ans = grade_results.get('answers', {}).get(q)  # sometimes included
                    outcomes.append(1 if scanned_ans == correct_ans else 0)
                if total_q:
                    outcomes = (outcomes + [0]*total_q)[:total_q]
                return outcomes

        return outcomes

    for img_path in image_files:
        try:
            print(f"\n[INFO] Processing: {img_path}")
            result = extractor.extract_complete(img_path, threshold_percent=threshold, debug=show_visualization)
            if not result:
                print(f"[WARN] Extraction failed for {img_path}")
                summary.append({'image': img_path, 'status': 'extraction_failed'})
                continue

            extraction_json = save_extraction_to_json(result, output_dir=output_dir)

            # Prepare scanned answers format expected by grader
            scanned_answers_data = {
                'metadata': result.get('metadata', {}),
                'answers': result.get('answers', {})
            }

            grade_results = grade_answers(answer_key_data, scanned_answers_data, max_points=None, partial_credit=partial_credit)
            report_json = save_grade_report(grade_results, key_json, extraction_json)

            # Extract student id if present
            student_id = None
            sid = result.get('student_id')
            if isinstance(sid, dict):
                student_id = sid.get('student_id')
            elif isinstance(sid, str):
                student_id = sid

            # Extract core score/percentage
            score = None
            percentage = None
            try:
                sc = grade_results.get('summary', {}).get('score') if isinstance(grade_results.get('summary'), dict) else grade_results.get('score')
                mp = grade_results.get('summary', {}).get('max_points') if isinstance(grade_results.get('summary'), dict) else grade_results.get('max_points')
                pct = grade_results.get('summary', {}).get('percentage') if isinstance(grade_results.get('summary'), dict) else grade_results.get('percentage')
                if sc is not None:
                    score = sc
                if pct is not None:
                    percentage = pct
                elif score is not None and mp is not None:
                    percentage = (float(score) / float(mp) * 100.0) if mp else None
            except Exception:
                pass

            # Determine per-question outcomes (1/0)
            outcomes = _per_question_outcomes_from_grade(grade_results, total_q=total_questions)
            # If outcomes empty and we have scanned answers + key, compute directly
            if (not outcomes or len(outcomes) == 0) and key_answers:
                scanned = scanned_answers_data.get('answers') or {}
                ordered_qs = sorted(key_answers.keys(), key=lambda kk: int(kk))
                for q in ordered_qs:
                    outcomes.append(1 if str(scanned.get(q)).strip() == str(key_answers.get(q)).strip() else 0)
                if total_questions:
                    outcomes = (outcomes + [0]*total_questions)[:total_questions]

            # Prepare compact row
            sid_display = student_id if student_id else ""
            score_display = score if score is not None else grade_results.get('score')
            pct_display = percentage if percentage is not None else grade_results.get('percentage')

            compact_row = [sid_display, score_display, pct_display]
            compact_row.extend(outcomes)

            # Print simple line as requested
            # Print student id, score, correct/total
            correct_count = sum(outcomes) if outcomes else None
            total_q_display = total_questions if total_questions is not None else (len(outcomes) if outcomes else "N/A")
            if correct_count is not None:
                print(f"{sid_display} | score: {score_display} | {correct_count}/{total_q_display}")
            else:
                print(f"{sid_display} | score: {score_display} | details unavailable")

            summary.append({
                'image': img_path,
                'status': 'ok',
                'student_id': student_id,
                'extraction_json': extraction_json,
                'report_json': report_json,
                'score': score_display,
                'max_points': grade_results.get('max_points'),
                'percentage': pct_display
            })
            compact_rows.append(compact_row)

        except Exception as e:
            print(f"[ERROR] Processing {img_path} failed: {e}")
            summary.append({'image': img_path, 'status': 'error', 'error': str(e)})

    # Save detailed summary JSON (existing)
    summary_json_path = os.path.join(output_dir, 'batch_summary.json')
    with open(summary_json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Build and save compact CSV with header: student_id,score,percentage,Q1,Q2,...Qn
    csv_path = os.path.join(output_dir, 'batch_results.csv')
    # determine max question columns present
    max_qcols = 0
    for row in compact_rows:
        qcols = max(0, len(row) - 3)
        if qcols > max_qcols:
            max_qcols = qcols
    # If total_questions known prefer that
    if total_questions:
        max_qcols = total_questions

    headers = ['student_id', 'score', 'percentage'] + [f"Q{i+1}" for i in range(max_qcols)]
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(headers)
        for row in compact_rows:
            # ensure row length equals 3 + max_qcols
            base = row[:3]
            qvals = row[3:] if len(row) > 3 else []
            qvals = qvals + [0] * (max_qcols - len(qvals))
            writer.writerow(base + qvals)

    print(f"\n[SUMMARY] Batch finished. Compact CSV saved to: {csv_path}")
    return {'output_dir': output_dir, 'summary_json': summary_json_path, 'compact_csv': csv_path, 'items': summary}


def run_steps_individually():
    """Run individual steps"""
    print("="*70)
    print("INDIVIDUAL STEP MODE")
    print("="*70)
    print("\nChoose which step to run:")
    print("1. Create blank PDF sheet")
    print("2. Extract bubble positions from PDF")
    print("3. Create answer key")
    print("4. Extract answers and grade")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        step1_create_blank_sheet()
    
    elif choice == '2':
        pdf_path = input("Enter PDF path: ").strip()
        step2_extract_bubble_positions(pdf_path)
    
    elif choice == '3':
        template_json = input("Enter template JSON path: ").strip()
        step3_create_answer_key(template_json)
    
    elif choice == '4':
        template_json = input("Enter template JSON path: ").strip()
        key_json = input("Enter answer key JSON path: ").strip()
        step4_extract_and_grade(template_json, key_json)
    
    else:
        print("Invalid choice")


def main():
    """Main function"""
    print("\n" + "="*70)
    print("ANSWER SHEET PROCESSING SYSTEM - TEST PIPELINE")
    print("="*70)

    print("\nChoose mode:")
    print("1. Full pipeline (run all steps from scratch)")
    print("2. Batch grade images (folder or list)")
    print("0. Exit")

    choice = input("\nEnter choice (1-5): ").strip()
    if choice == '1':
        run_full_pipeline()
    elif choice == '0':
        print("Exiting...")
    elif choice == '2':
        pdf_path = step1_create_blank_sheet()
        template_json = step2_extract_bubble_positions(pdf_path)
        key_json = step3_create_answer_key(template_json)
        images = input("Enter images folder path or comma-separated list of images: ").strip()
        out_dir = input("Output directory (leave empty for auto): ").strip() or None
        thr = input("Detection threshold (default 50): ").strip()
        thr = int(thr) if thr else 50
        pc = input("Enable partial credit? (y/n, default n): ").strip().lower() == 'y'
        batch_grade_images(template_json, key_json, images, output_dir=out_dir, threshold=thr, partial_credit=pc, show_visualization=False)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()