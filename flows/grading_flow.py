"""
Grading Flow
Business logic for grading answer sheets - aligned with core/grading.py
"""
import os
import sys
import json
import glob
import cv2
import numpy as np
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_ROOT = os.path.join(PROJECT_ROOT, "files")

BLANK_SHEETS_DIR = os.path.join(FILES_ROOT, "blank_sheets")
TEMPLATES_DIR = os.path.join(FILES_ROOT, "template")
ANSWER_KEYS_DIR = os.path.join(FILES_ROOT, "answer_keys")

if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

from utils.db_operations import get_db_operations
from utils.file_utils import to_relative_path, to_absolute_path
from utils.validation import (
    validate_template_json,
    validate_answer_key_json,
    validate_file_exists,
    validate_threshold
)


class GradingFlow:
    """Handles answer sheet grading workflow for the new formats"""

    def __init__(self):
        self.db_ops = get_db_operations()

        # Configuration / state
        self.template_path = None
        self.template_data = None
        self.answer_key_path = None
        self.answer_key_data = None
        self.threshold = 50

        # DB ids (optional)
        self.template_id = None
        self.answer_key_id = None

        # Results & images
        self.current_results = None
        self.batch_results = []
        self.last_processed_image = None
        self.batch_processed_images = []

    def load_template(self, template_path):
        """Load and validate template JSON"""
        abs_path = to_absolute_path(template_path)
        valid, error, data = validate_template_json(abs_path)
        if not valid:
            return False, error, None

        self.template_path = template_path
        self.template_data = data

        if self.db_ops.is_connected():
            try:
                rel = to_relative_path(template_path)
                tinfo = self.db_ops.get_template_by_json_path(rel)
                if tinfo:
                    self.template_id = tinfo.get("id")
            except Exception:
                pass

        page_data = data.get("page_1", {})
        
        # FIX: Check both possible keys for MCQ questions
        # Template uses "mcq" but code expects "bubble_answers"
        mcq_section = page_data.get("mcq", {}) or page_data.get("bubble_answers", {})
        quick_section = page_data.get("quick_answers", {})
        
        # Get MCQ count - check multiple possible keys
        mcq_count = 0
        if "questions_detected" in mcq_section:
            mcq_count = mcq_section.get("questions_detected", 0)
        elif "questions" in mcq_section:
            mcq_count = len(mcq_section.get("questions", []))
        
        # Get written count
        written_count = quick_section.get("total_questions", 0)
        total_q = mcq_count + written_count
        
        info = {
            "path": template_path,
            "total_questions": total_q,
            "mcq_questions": mcq_count,
            "written_questions": written_count,
            "has_student_id": bool(page_data.get("student_id")),
            "name": os.path.basename(template_path)
        }
        
        print(f"[FLOW] Template loaded: {mcq_count} MCQ, {written_count} written = {total_q} total")
        return True, None, info

    def load_answer_key(self, key_path):
        """Load and validate answer key JSON"""
        abs_path = to_absolute_path(key_path)
        
        # FIXED: validate_answer_key_json returns 4 values (valid, error, data, key_type)
        # Default to checking for complete exam format first
        valid, error, data, key_type = validate_answer_key_json(abs_path, is_complete_exam=True)
        
        # If complete exam validation fails, try individual key format
        if not valid:
            valid, error, data, key_type = validate_answer_key_json(abs_path, is_complete_exam=False)
        
        if not valid:
            return False, error, None

        self.answer_key_path = key_path
        self.answer_key_data = data

        if self.db_ops.is_connected():
            try:
                rel = to_relative_path(key_path)
                kinfo = self.db_ops.get_answer_key_by_json_path(rel)
                if kinfo:
                    self.answer_key_id = kinfo.get("id")
            except Exception:
                pass

        meta = data.get("metadata", {})
        exam_name = meta.get("exam_name", os.path.splitext(os.path.basename(key_path))[0])
        total_questions = meta.get("total_questions", 0)
        mcq_count = meta.get("mcq_count", 0)
        written_count = meta.get("written_count", 0)
        
        key_info = {
            "path": key_path,
            "exam_name": exam_name,
            "total_questions": total_questions,
            "mcq_count": mcq_count,
            "written_count": written_count,
            "name": os.path.basename(key_path),
            "key_type": key_type  # Add key_type to info
        }
        
        print(f"[FLOW] Answer key loaded: {exam_name}, {total_questions} questions ({mcq_count} MCQ, {written_count} written), Type: {key_type}")
        return True, None, key_info

    def set_threshold(self, threshold):
        """Set detection threshold"""
        valid, error, parsed = validate_threshold(threshold)
        if not valid:
            return False, error
        self.threshold = parsed
        return True, None

    def grade_single_sheet(self, image_path, partial_mcq=False, written_tolerance=0.0):
        """Grade a single sheet using the correct extraction flow"""
        if not self.template_path:
            return False, "Template not loaded", None
        if not self.answer_key_path:
            return False, "Answer key not loaded", None

        valid, error = validate_file_exists(image_path)
        if not valid:
            return False, error, None

        try:
            # FIX: Correct import path for extraction_flow
            from core.answer_extraction.answer_extraction import AnswerSheetProcessor
        except Exception as e:
            return False, f"Missing extraction_flow module: {e}", None

        try:
            # 1) Extract answers using the correct processor
            processor = AnswerSheetProcessor(
                template_path=self.template_path,
                cnn_model_path="core/cnn_model/cnn_model.h5"
            )
            
            extraction_result = processor.process_sheet(
                image_path=image_path,
                threshold_percent=self.threshold,
                debug=False,
                extract_id=True,
                extract_mc=True,
                extract_quick=True
            )

            if not extraction_result:
                return False, "Failed to extract answers from sheet", None

            # 2) Grade using the key (grader expects extraction_result structure)
            grade_results = self._grade_with_key(
                self.answer_key_data, 
                extraction_result, 
                partial_mcq=partial_mcq,
                written_tolerance=written_tolerance
            )

            # 3) Extract student ID
            student_id = "N/A"
            sid = extraction_result.get("student_id", {})
            if isinstance(sid, dict):
                student_id = sid.get("student_id", student_id)
            elif isinstance(sid, str):
                student_id = sid

            # 4) Create annotated image
            annotated = self._create_annotated_image(image_path, extraction_result, grade_results, processor)
            self.last_processed_image = annotated

            # 5) Build result object
            summary = grade_results.get("summary", {})
            result = {
                "image_path": image_path,
                "student_id": student_id,
                "score": summary.get("score", 0.0),
                "total_points": summary.get("mcq_points_total", 0.0) + summary.get("written_points_total", 0.0),
                "percentage": summary.get("percentage", 0.0),
                "details": grade_results.get("details", {}),
                "summary": summary,
                "extraction_result": extraction_result,
                "annotated_image": annotated,
                "threshold": self.threshold
            }

            self.current_results = result

            # 6) Save to DB if available
            if self.db_ops.is_connected():
                try:
                    metadata = self.answer_key_data.get("metadata", {})
                    exam_name = metadata.get("exam_name", "Exam")
                    mcq_max_points = metadata.get("mcq_max_points", 0.0)
                    written_max_points = metadata.get("written_max_points", 0.0)
                    max_score = mcq_max_points + written_max_points
                    
                    # Extract student_key from extraction_result
                    answer_key_info = extraction_result.get("answer_key", {})
                    if isinstance(answer_key_info, dict):
                        student_key = answer_key_info.get("answer_key")
                    else:
                        student_key = answer_key_info
                        
                    # If no key detected, default to 'A'
                    if not student_key:
                        student_key = 'A'
                        print(f"[FLOW] No answer key detected in sheet, defaulting to: {student_key}")
                    
                    key_letter = str(student_key).upper() if student_key else 'A'
                    
                    # 1. Get or create exam
                    exam = self.db_ops.get_exam_by_name(exam_name)
                    if exam:
                        exam_id = exam['id']
                    else:
                        exam_id = self.db_ops.save_exam(
                            name=exam_name,
                            description=f"Created from grading",
                            max_score=max_score
                        )
                    
                    # 2. Get or create answer key for this exam
                    key_id = None
                    if exam_id:
                        # First try to find existing answer key for this exam and label
                        existing_key = self.db_ops.get_answer_key_by_exam_and_label(exam_id, key_letter)
                        if existing_key:
                            key_id = existing_key['id']
                            print(f"[FLOW] Found existing answer key: ID={key_id}")
                        else:
                            # Create a new answer key record
                            key_data = {
                                'metadata': {
                                    'exam_name': exam_name,
                                    'key_label': key_letter,
                                    'mcq_count': metadata.get('mcq_count', 0),
                                    'mcq_max_points': mcq_max_points,
                                    'written_count': metadata.get('written_count', 0),
                                    'written_max_points': written_max_points,
                                    'total_max_points': max_score,
                                    'created_at': datetime.now().isoformat()
                                },
                                'mcq': {
                                    'answer_key': self.answer_key_data.get('keys', {}).get(key_letter, {}).get('mcq_answers', {})
                                },
                                'written': {
                                    'answer_key': self.answer_key_data.get('keys', {}).get(key_letter, {}).get('written_answers', {})
                                }
                            }
                            
                            # Get template ID if not already set
                            template_id = self.template_id
                            if not template_id:
                                rel_template = to_relative_path(self.template_path)
                                tinfo = self.db_ops.get_template_by_json_path(rel_template)
                                if tinfo:
                                    template_id = tinfo.get("id")
                            
                            if template_id:
                                # Save answer key
                                key_id = self.db_ops.save_answer_key(
                                    template_id=template_id,
                                    exam_id=exam_id,
                                    name=f"{exam_name} - Key {key_letter}",
                                    label=key_letter,
                                    json_path=self.answer_key_path,  # Use original answer key path
                                    key_data=key_data,
                                    created_by='grading'
                                )
                                print(f"[FLOW] Created new answer key: ID={key_id}")
                    
                    # 3. Save graded sheet with BOTH exam_id AND key_id
                    print(f"[FLOW] Saving graded sheet with exam_id={exam_id}, key_id={key_id}")
                    
                    graded_sheet_id = self.db_ops.save_graded_sheet(
                        exam_id=exam_id,
                        student_id=student_id,
                        exam_name=exam_name,
                        filled_sheet_path=to_relative_path(image_path),
                        total_mcq_questions=summary.get("mcq_count", 0),
                        total_written_questions=summary.get("written_count", 0),
                        mcq_correct_count=summary.get("mcq_correct", 0),
                        mcq_wrong_count=summary.get("mcq_incorrect", 0),
                        mcq_blank_count=summary.get("mcq_blank", 0),
                        written_correct_count=summary.get("written_correct", 0),
                        written_wrong_count=summary.get("written_incorrect", 0),
                        written_blank_count=summary.get("written_blank", 0),
                        score=summary.get("score", 0.0),
                        max_score=max_score,
                        key_id=key_id,  # Pass key_id parameter
                        threshold=self.threshold
                    )
                    
                    if graded_sheet_id:
                        print(f"[FLOW] Successfully saved graded sheet with ID: {graded_sheet_id}")
                        self._save_question_results(graded_sheet_id, grade_results, extraction_result)
                    else:
                        print(f"[FLOW] Failed to save graded sheet")
                            
                except Exception as e:
                    print(f"[FLOW] DB save error: {e}")
                    import traceback
                    traceback.print_exc()

            return True, None, result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Grading failed: {e}", None

    def _grade_with_key(self, key_data, extraction_result, partial_mcq=True, written_tolerance=0.0):
        """
        Grade using answer key - UPDATED for the new answer key format
        """
        meta = key_data["metadata"]
        
        # FIX: Get the selected key version from extraction result
        student_key = None
        key_info = extraction_result.get("answer_key", {})
        if isinstance(key_info, dict):
            student_key = key_info.get("answer_key")
        elif isinstance(key_info, str):
            student_key = key_info
        
        # If no key detected, default to first available key
        if not student_key:
            keys_present = meta.get("keys_present", ["A"])
            student_key = keys_present[0]
            print(f"[FLOW] No key detected, defaulting to: {student_key}")
        
        print(f"[FLOW] Using answer key version: {student_key}")
        
        # Get the correct key version from the keys object
        keys_block = key_data.get("keys", {})
        if student_key not in keys_block:
            # Try uppercase
            student_key = student_key.upper()
            if student_key not in keys_block:
                # Fallback to first available key
                available_keys = list(keys_block.keys())
                if available_keys:
                    student_key = available_keys[0]
                    print(f"[FLOW] Key {student_key} not found, using: {student_key}")
                else:
                    raise ValueError(f"No answer keys found in the answer key file")
        
        correct_key = keys_block[student_key]
        mcq_key = correct_key.get("mcq_answers", {})
        written_key = correct_key.get("written_answers", {})

        # Extract from extraction_result
        mcq_data = extraction_result.get("multiple_choice_answers", {})
        mcq_answers = mcq_data.get("answers", {})
        
        written_data = extraction_result.get("quick_answers", {})
        written_answers = written_data.get("quick_answers", [])  # list of {question_number, answer}

        mcq_count = meta["mcq_count"]
        written_count = meta["written_count"]

        mcq_pp = meta["mcq_max_points"] / mcq_count if mcq_count > 0 else 0
        written_pp = meta["written_max_points"] / written_count if written_count > 0 else 0

        results = {
            "summary": {
                "student_key": student_key,
                "total_questions": meta["total_questions"],
                "mcq_correct": 0,
                "mcq_incorrect": 0,
                "mcq_partial": 0,
                "mcq_blank": 0,
                "written_correct": 0,
                "written_incorrect": 0,
                "written_blank": 0,
                "score": 0.0,
                "percentage": 0.0,
                "mcq_points_total": meta["mcq_max_points"],
                "written_points_total": meta["written_max_points"],
                "mcq_points_per_question": mcq_pp,
                "written_points_per_question": written_pp,
                "mcq_count": mcq_count,
                "written_count": written_count
            },
            "details": {}
        }

        score_total = 0.0

        # --------------------------
        # GRADE MCQ
        # --------------------------
        for q_str, correct_list in mcq_key.items():
            q = int(q_str)
            correct_set = set([str(x).upper() for x in (correct_list or [])])

            # Extract student answers (normalize keys)
            student_entry = mcq_answers.get(q_str) or mcq_answers.get(str(int(q_str)))
            
            if not student_entry:
                student_set = set()
            else:
                sel = student_entry.get("selected_answers") or student_entry.get("selected", [])
                student_set = set([str(x).upper() for x in (sel or [])])

            # Debug: show first question processing
            if q == 1:
                print(f"\n[DEBUG GRADE] Q{q}: Correct {correct_set}, Student {student_set}")

            # ---------------------------
            # Blank
            # ---------------------------
            if not student_set:
                results["summary"]["mcq_blank"] += 1
                results["details"][q] = {
                    "type": "mcq",
                    "correct": sorted(correct_set),
                    "student": [],
                    "status": "blank",
                    "points": 0.0
                }
                continue

            # ---------------------------
            # Too many picks → auto zero
            # ---------------------------
            if len(student_set) > len(correct_set):
                points = 0.0
                status = "too_many_selected"
                results["summary"]["mcq_incorrect"] += 1

            # ---------------------------
            # Exact match → full credit
            # ---------------------------
            elif student_set == correct_set:
                points = mcq_pp
                status = "correct"
                results["summary"]["mcq_correct"] += 1

            # ---------------------------
            # Partial credit mode
            # matches / len(correct_set)
            # ---------------------------
            elif partial_mcq and len(correct_set) > 0:
                matches = len(student_set & correct_set)
                fraction = matches / len(correct_set)
                points = fraction * mcq_pp

                if matches > 0:
                    status = "partial"
                    results["summary"]["mcq_partial"] += 1
                else:
                    status = "incorrect"
                    results["summary"]["mcq_incorrect"] += 1
                    points = 0.0

            # ---------------------------
            # Incorrect (no partial allowed)
            # ---------------------------
            else:
                points = 0.0
                status = "incorrect"
                results["summary"]["mcq_incorrect"] += 1

            # Save MCQ result
            score_total += points
            results["details"][q] = {
                "type": "mcq",
                "correct": sorted(correct_set),
                "student": sorted(student_set),
                "status": status,
                "points": points
            }

        # --------------------------
        # GRADE WRITTEN
        # --------------------------
        written_dict = {}
        for item in written_answers:
            q_num = item.get("question_number")
            if q_num is None:
                continue
            try:
                q_num = int(q_num)
            except:
                continue
            adjusted_q = mcq_count + q_num  # Written questions start after MCQ
            written_dict[str(adjusted_q)] = item.get("answer", "")

        for q_str, correct_value in written_key.items():
            q = int(q_str)

            # Parse correct value (numeric or string)
            try:
                correct_num = float(correct_value)
            except:
                correct_num = correct_value

            student_val = written_dict.get(q_str, "")

            # Blank
            if student_val is None or student_val == "":
                results["summary"]["written_blank"] += 1
                results["details"][q] = {
                    "type": "written",
                    "correct": correct_num,
                    "student": "",
                    "status": "blank",
                    "points": 0.0
                }
                continue

            # Try numeric compare
            stu_num = None
            numeric_match = False
            try:
                stu_num = float(student_val)
                if isinstance(correct_num, (int, float)) and abs(stu_num - float(correct_num)) <= float(written_tolerance):
                    numeric_match = True
            except:
                numeric_match = False

            if numeric_match:
                points = written_pp
                status = "correct"
                results["summary"]["written_correct"] += 1
            else:
                points = 0.0
                status = "incorrect"
                results["summary"]["written_incorrect"] += 1

            score_total += points
            results["details"][q] = {
                "type": "written",
                "correct": correct_num,
                "student": stu_num if stu_num is not None else student_val,
                "status": status,
                "points": points
            }

        # --------------------------
        # FINAL SCORE
        # --------------------------
        max_points = meta["mcq_max_points"] + meta["written_max_points"]
        percent = (score_total / max_points) * 100 if max_points > 0 else 0

        results["summary"]["score"] = round(score_total, 3)
        results["summary"]["percentage"] = round(percent, 2)

        # Debug Summary
        print(f"\n[DEBUG GRADE] Final Summary:")
        print(f"  Answer Key Used: {student_key}")
        print(f"  MCQ: {results['summary']['mcq_correct']} correct, {results['summary']['mcq_incorrect']} incorrect, {results['summary']['mcq_blank']} blank")
        print(f"  Written: {results['summary']['written_correct']} correct, {results['summary']['written_incorrect']} incorrect, {results['summary']['written_blank']} blank")
        print(f"  Score: {results['summary']['score']} / {max_points} ({results['summary']['percentage']}%)")

        return results

    def _create_annotated_image(self, image_path, extraction_result, grade_results, processor):
        """Annotate image with grading results - RGB colors, single circle per bubble"""
        try:
            img_bgr = cv2.imread(image_path)
            if img_bgr is None:
                return None
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_h, img_w = img_rgb.shape[:2]

            # Get template data from processor
            template_data = {}
            try:
                template_data = processor.bubble_template.template_data if hasattr(processor, 'bubble_template') else {}
            except Exception:
                template_data = getattr(processor, "template_data", {}) or {}

            page1 = template_data.get("page_1", {})

            if not page1:
                # Fallback to loaded template data
                page1 = self.template_data.get("page_1", {}) if self.template_data else {}
                if not page1:
                    return img_rgb

            dims = page1.get("image_dimensions", {})
            template_width = float(dims.get("width", img_w))
            template_height = float(dims.get("height", img_h))

            sx = img_w / template_width
            sy = img_h / template_height

            # Status map from grading results
            details = grade_results.get("details", {})
            status_map = {str(k): v.get("status", "") for k, v in details.items()}

            # Extraction data - extraction_flow structure
            mcq_data = extraction_result.get("multiple_choice_answers", {})
            mc_extraction = mcq_data.get("answers", {})
            
            quick_data = extraction_result.get("quick_answers", {})
            quick_extraction = quick_data.get("quick_answers", [])

            # Color definitions in RGB format (correct for OpenCV since we're using RGB image)
            GREEN = (0, 255, 0)      # Correct MCQ answers (R=0, G=255, B=0)
            RED = (255, 0, 0)        # Wrong MCQ answers (R=255, G=0, B=0)  
            BLUE = (0, 0, 255)       # Selected answer key (R=0, G=0, B=255)
            MAGENTA = (255, 0, 255)  # Student ID digits (R=255, G=0, B=255)
            ORANGE = (255, 165, 0)   # Partial credit (R=255, G=165, B=0)
            GRAY = (128, 128, 128)   # Blank (R=128, G=128, B=128)
            YELLOW = (255, 255, 0)   # Other (R=255, G=255, B=0)

            # --------------------------
            # 1. Draw MCQ bubbles with colors - SINGLE THIN CIRCLE
            # --------------------------
            mcq_section = page1.get("mcq", {}) or page1.get("bubble_answers", {})
            questions = mcq_section.get("questions", [])

            for q in questions:
                qnum = q.get("question_number")
                q_str = str(qnum)
                bubbles = q.get("bubbles", [])

                ext_q = mc_extraction.get(q_str, {}) or mc_extraction.get(str(qnum), {})
                sel = ext_q.get("selected_answers", None)
                if sel is None:
                    sel = ext_q.get("selected", [])
                selected_answers = [str(x).upper() for x in (sel or [])]

                q_status = status_map.get(q_str)
                
                # Get correct answers from grade results
                correct_answers = set()
                if qnum in details:
                    correct_set = details[qnum].get("correct", [])
                    correct_answers = set(str(x).upper() for x in correct_set)

                # Draw each selected bubble
                for b in bubbles:
                    label = str(b.get("label", "")).upper()
                    if label not in selected_answers:
                        continue

                    bx = b.get("x")
                    by = b.get("y")
                    br = b.get("radius", 35)

                    if bx is None or by is None:
                        continue

                    x_px = int(bx * sx)
                    y_px = int(by * sy)
                    r_px = int(br * ((sx + sy) / 2.0))

                    # Determine color based on correctness - using RGB colors
                    if q_status == "correct" and label in correct_answers:
                        color = GREEN  # Correct MCQ answer
                    elif q_status == "incorrect":
                        color = RED    # Wrong MCQ answer
                    elif q_status == "partial":
                        color = ORANGE # Partial credit
                    elif q_status == "blank":
                        color = GRAY   # Blank
                    else:
                        color = YELLOW # Other

                    # Draw SINGLE thin circle right at the bubble edge
                    # Just 1-2 pixels outside the bubble, thickness 1-2
                    circle_radius = r_px + 1  # Very close to bubble edge
                    line_thickness = 2  # Slightly thicker for better visibility
                    cv2.circle(img_rgb, (x_px, y_px), circle_radius, color, line_thickness)

            # --------------------------
            # 2. Draw answer key bubbles (BLUE) - SINGLE THIN CIRCLE
            # --------------------------
            key_section = page1.get("key", [])
            if key_section:
                # Try to extract which key was selected
                answer_key_data = extraction_result.get("answer_key", {})
                selected_key = answer_key_data.get("answer_key", "")
                
                if selected_key and key_section:
                    try:
                        # Convert key letter to index (A=0, B=1, C=2, etc.)
                        key_index = ord(selected_key.upper()) - 65
                        if 0 <= key_index < len(key_section):
                            key_bubble = key_section[key_index]
                            bx = key_bubble.get("x")
                            by = key_bubble.get("y")
                            br = key_bubble.get("radius", 35)
                            
                            if bx is not None and by is not None:
                                x_px = int(bx * sx)
                                y_px = int(by * sy)
                                r_px = int(br * ((sx + sy) / 2.0))
                                
                                # Draw SINGLE thin blue circle
                                circle_radius = r_px + 2  # Slightly more visible for key
                                cv2.circle(img_rgb, (x_px, y_px), circle_radius, BLUE, 2)
                    except Exception as e:
                        print(f"[VIS] Error drawing key bubble: {e}")

            # --------------------------
            # 3. Draw student ID bubbles (MAGENTA) - SINGLE THIN CIRCLE
            # --------------------------
            sid_result = extraction_result.get("student_id", {})
            digit_details = sid_result.get("digit_details", [])

            digit_selections = {}
            for d in digit_details:
                pos = d.get("position")
                digit = d.get("digit")
                if pos is not None and digit is not None:
                    digit_selections[str(pos - 1)] = digit

            student_id_template = page1.get("student_id", {})
            digit_columns = student_id_template.get("digit_columns", [])

            for col_index, col_data in enumerate(digit_columns):
                bubbles = col_data.get("bubbles", [])
                selected_digit = digit_selections.get(str(col_index))
                if selected_digit is None:
                    continue

                for bubble in bubbles:
                    if str(bubble.get("digit")) != str(selected_digit):
                        continue

                    bx = bubble.get("x")
                    by = bubble.get("y")
                    br = bubble.get("radius", 30)

                    if bx is None or by is None:
                        continue

                    x_px = int(bx * sx)
                    y_px = int(by * sy)
                    r_px = int(br * ((sx + sy) / 2.0))

                    # Draw SINGLE thin magenta circle
                    circle_radius = r_px + 1
                    cv2.circle(img_rgb, (x_px, y_px), circle_radius, MAGENTA, 2)

            # --------------------------
            # 4. Draw written answer boxes - THIN BORDERS
            # --------------------------
            quick_section = page1.get("quick_answers", {}) or {}
            answer_boxes = quick_section.get("answer_boxes", [])
            mcq_count = int(self.answer_key_data.get("metadata", {}).get("mcq_count", 0))

            quick_answer_map = {}
            for qa in quick_extraction:
                try:
                    q_quick = int(qa.get("question_number"))
                except Exception:
                    continue
                answer_val = qa.get("answer", "")
                quick_answer_map[q_quick] = answer_val

            for box in answer_boxes:
                try:
                    q_quick = int(box.get("question_number"))
                except Exception:
                    continue
                overall_q = mcq_count + q_quick
                q_str = str(overall_q)

                if q_quick not in quick_answer_map:
                    continue

                answer_val = quick_answer_map[q_quick]
                if not answer_val or str(answer_val).strip() == "":
                    continue

                status = status_map.get(q_str)
                if status == "correct":
                    color = GREEN  # Green for correct written
                elif status == "incorrect":
                    color = RED    # Red for incorrect written
                elif status == "blank":
                    color = GRAY   # Gray for blank
                else:
                    continue

                bx = box.get("x")
                by = box.get("y")
                bw = box.get("width")
                bh = box.get("height")

                if bx is None or by is None or bw is None or bh is None:
                    cx = box.get("center_x")
                    cy = box.get("center_y")
                    if cx is not None and cy is not None and bw and bh:
                        x1 = int((cx - bw/2) * sx)
                        y1 = int((cy - bh/2) * sy)
                        x2 = int((cx + bw/2) * sx)
                        y2 = int((cy + bh/2) * sy)
                    else:
                        continue
                else:
                    x1 = int(bx * sx)
                    y1 = int(by * sy)
                    x2 = int((bx + bw) * sx)
                    y2 = int((by + bh) * sy)

                # Draw thin rectangle
                cv2.rectangle(img_rgb, (x1, y1), (x2, y2), color, 2)         
            return img_rgb

        except Exception as e:
            print(f"[FLOW] Annotation failed: {e}")
            import traceback
            traceback.print_exc()
            try:
                img = cv2.imread(image_path)
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None
            except:
                return None
        
    def grade_batch(self, folder_path, partial_mcq=False, written_tolerance=0.0):
        """Grade all images in a folder"""
        if not self.template_path or not self.answer_key_path:
            return False, "Template or answer key not loaded", None

        patterns = ["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff"]
        files = []
        for p in patterns:
            files.extend(glob.glob(os.path.join(folder_path, p)))

        if not files:
            return False, "No image files found in folder", None

        self.batch_results = []
        self.batch_processed_images = []
        errors = []

        for fp in files:
            ok, err, res = self.grade_single_sheet(fp, partial_mcq=partial_mcq, written_tolerance=written_tolerance)
            if ok:
                self.batch_results.append(res)
                self.batch_processed_images.append(self.last_processed_image)
            else:
                errors.append({"file": os.path.basename(fp), "error": err})

        if not self.batch_results:
            return False, "No sheets successfully graded", None

        total = len(self.batch_results)
        avg_pct = sum(r.get("percentage", 0.0) for r in self.batch_results) / total if total > 0 else 0.0
        summary = {"total_sheets": total, "avg_percentage": avg_pct, "errors": errors}
        return True, None, (self.batch_results, summary)

    def _save_question_results(self, graded_sheet_id, grade_results, extraction_result=None):
        """Save question-level results to DB"""
        try:
            details = grade_results.get("details", {})
            for qnum, info in details.items():
                try:
                    qn = int(qnum)
                except Exception:
                    continue

                # Determine type
                q_type = info.get("type", "mcq")

                # Student & correct formatting
                student = info.get("student") or info.get("student_answers") or info.get("student_answer") or info.get("value")
                correct = info.get("correct") or info.get("correct_answers") or info.get("correct_answer")

                if isinstance(student, list):
                    student_str = ",".join(str(x) for x in student)
                else:
                    student_str = "" if student is None else str(student)

                if isinstance(correct, list):
                    correct_str = ",".join(str(x) for x in correct)
                else:
                    correct_str = "" if correct is None else str(correct)

                is_correct = (info.get("status") == "correct")
                points = float(info.get("points", 0.0))

                # Attempt to attach digit details for written if present in extraction_result
                digit_details = None
                if q_type == "written" and extraction_result:
                    # written question numbering uses quick_answers question_number + mcq_count mapping
                    # find the quick answer entry used earlier
                    try:
                        mcq_count = int(self.answer_key_data.get("metadata", {}).get("mcq_count", 0))
                        quick_list = extraction_result.get("quick_answers", {}).get("quick_answers", [])
                        # find matching quick entry
                        for qa in quick_list:
                            q_quick = qa.get("question_number")
                            if q_quick is None:
                                continue
                            if (mcq_count + int(q_quick)) == qn:
                                # store the raw qa dict as digit_details
                                digit_details = qa.get("digit_details", qa)
                                break
                    except Exception:
                        digit_details = None

                # Save to DB
                try:
                    self.db_ops.save_question_result(
                        graded_sheet_id=graded_sheet_id,
                        question_number=qn,
                        question_type=q_type,
                        student_answer=student_str,
                        correct_answer=correct_str,
                        is_correct=1 if is_correct else 0,
                        points=points,
                        digit_details=digit_details
                    )
                except Exception:
                    # do not break flow on DB save errors
                    pass

        except Exception as e:
            print(f"[FLOW] _save_question_results error: {e}")

    def get_processed_image(self):
        return self.last_processed_image

    def get_processed_image_for_sheet(self, index):
        if 0 <= index < len(self.batch_processed_images):
            return self.batch_processed_images[index]
        return None

    def get_current_results(self):
        return self.current_results

    def get_batch_results(self):
        return self.batch_results

    def get_configuration(self):
        return {
            "template_path": self.template_path,
            "answer_key_path": self.answer_key_path,
            "threshold": self.threshold,
            "template_loaded": bool(self.template_path),
            "key_loaded": bool(self.answer_key_path)
        }
    
    def debug_extraction_detailed(self, image_path):
        """Detailed debug of the extraction process"""
        try:
            from core.answer_extraction.bubble_answer_extraction import BubbleTemplate, AnswerSheetExtractor
            
            template = BubbleTemplate(self.template_path)
            extractor = AnswerSheetExtractor(template)
            
            print("\n=== DETAILED EXTRACTION DEBUG ===")
            
            # Test individual extraction components
            print("\n[DEBUG] Testing MCQ extraction...")
            mcq_result = extractor.extract_multiple_choice(image_path, threshold_percent=self.threshold)
            print(f"MCQ extraction result: {bool(mcq_result)}")
            if mcq_result:
                print(f"MCQ answers found: {len(mcq_result.get('answers', {}))}")
            
            print("\n[DEBUG] Testing written answers extraction...")
            written_result = extractor.extract_quick_answers(image_path)
            print(f"Written extraction result: {bool(written_result)}")
            if written_result:
                print(f"Written answers found: {len(written_result.get('quick_answers', []))}")
                for qa in written_result.get('quick_answers', []):
                    print(f"  Q{qa.get('question_number')}: '{qa.get('answer')}'")
            
            print("\n[DEBUG] Testing student ID extraction...")
            id_result = extractor.extract_student_id(image_path, threshold_percent=self.threshold)
            print(f"Student ID extraction result: {bool(id_result)}")
            if id_result:
                print(f"Student ID: {id_result.get('student_id', 'N/A')}")
            
            # Now test the complete extraction
            print("\n[DEBUG] Testing complete extraction...")
            complete_result = extractor.extract_complete(image_path, threshold_percent=self.threshold, debug=True)
            
            return complete_result
        except Exception as e:
            print(f"Detailed extraction debug failed: {e}")
            import traceback
            traceback.print_exc()
            return None


def grade_sheet_quick(template_path, key_path, image_path, threshold=50, partial_mcq=False, written_tolerance=0.0):
    """Convenience function for quick grading using extraction_flow"""
    flow = GradingFlow()
    ok, err, _ = flow.load_template(template_path)
    if not ok:
        return False, err, None
    ok, err, _ = flow.load_answer_key(key_path)
    if not ok:
        return False, err, None
    ok, err = flow.set_threshold(threshold)
    if not ok:
        return False, err, None
    return flow.grade_single_sheet(image_path, partial_mcq=partial_mcq, written_tolerance=written_tolerance)