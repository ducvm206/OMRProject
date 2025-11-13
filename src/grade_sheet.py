import os
import threading
from tkinter import Tk, filedialog

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def to_relative_path(absolute_path):
    """Convert absolute path to relative path from project root"""
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        return absolute_path

def select_file(title, filetypes):
    """Open file picker dialog and return relative path (non-blocking)"""
    file_path = [None]
    
    def open_dialog():
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path[0] = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
    
    thread = threading.Thread(target=open_dialog, daemon=True)
    thread.start()
    thread.join()
    
    if file_path[0]:
        return to_relative_path(file_path[0])
    return None

def grade_sheet(template_json, key_json, answer_sheet=None, threshold=50, show_details=False):
    """Grade a single filled answer sheet"""
    
    # Validate inputs
    if not template_json or not os.path.exists(template_json):
        print(f"[ERROR] Template JSON not found: {template_json}")
        return None
    
    if not key_json or not os.path.exists(key_json):
        print(f"[ERROR] Answer key not found: {key_json}")
        return None
    
    # Get answer sheet if not provided
    if not answer_sheet:
        answer_sheet = select_file(
            "Select filled answer sheet image",
            [("Image files", "*.png *.jpg *.jpeg *.bmp *.tif"), ("All files", "*.*")]
        )
    
    if not answer_sheet or not os.path.exists(answer_sheet):
        print(f"[ERROR] Answer sheet not found: {answer_sheet}")
        return None
    
    try:
        from core.extraction import BubbleTemplate, AnswerSheetExtractor, save_extraction_to_json
        from core.grading import load_answer_key, grade_answers, print_grading_summary, print_detailed_results, save_grade_report
        
        print(f"\n[INFO] Processing: {answer_sheet}")
        print(f"[INFO] Detection threshold: {threshold}%")
        
        # Load template and extract
        template = BubbleTemplate(template_json)
        extractor = AnswerSheetExtractor(template)
        
        result = extractor.extract_complete(
            answer_sheet,
            threshold_percent=threshold,
            debug=False  # Set to True for visualization
        )
        
        if not result:
            print("[ERROR] Failed to extract answers")
            return None
        
        # Save extraction results
        extraction_json = save_extraction_to_json(result)
        print(f"[INFO] Extraction saved: {extraction_json}")
        
        # Load answer key
        answer_key_data = load_answer_key(key_json)
        
        # Prepare scanned answers data in expected format
        scanned_answers_data = {
            'metadata': result.get('metadata', {}),
            'answers': result.get('answers', {})
        }
        
        # Grade the answers
        print("[INFO] Grading answers...")
        
        grade_results = grade_answers(
            answer_key_data,
            scanned_answers_data,
            max_points=None,
            partial_credit=False
        )
        
        # Display summary
        print_grading_summary(grade_results)
        
        # Show details if requested
        if show_details:
            print("\n[INFO] Showing detailed results...")
            print_detailed_results(grade_results, show_all=False)
        
        # Save grade report
        report_json = save_grade_report(grade_results, key_json, extraction_json)
        
        # Embed student ID if present
        student_id = None
        sid = result.get('student_id')
        if isinstance(sid, dict):
            student_id = sid.get('student_id')
        elif isinstance(sid, str):
            student_id = sid
        
        if student_id and os.path.exists(report_json):
            try:
                import json
                with open(report_json, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                report_data.setdefault('metadata', {})
                report_data['metadata']['student_id'] = student_id
                with open(report_json, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        
        print(f"\n[SUCCESS] Grade report saved: {report_json}")
        
        return {
            'extraction': extraction_json,
            'grade_report': report_json,
            'student_id': student_id,
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

def grade_sheet_legacy(template_json, key_json, show_details=False):
    """Legacy function for compatibility - prompts for answer sheet file"""
    answer_sheet = select_file(
        "Select filled answer sheet image",
        [("Image files", "*.png *.jpg *.jpeg *.bmp *.tif"), ("All files", "*.*")]
    )
    
    if not answer_sheet:
        print("[ERROR] No file selected")
        return None
    
    return grade_sheet(template_json, key_json, answer_sheet, threshold=50, show_details=show_details)