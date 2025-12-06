"""
grading.py - Grade scanned answer sheets against the new OMR exam format

Complete workflow:
1. Takes template JSON, answer key JSON, and PNG image of filled sheet
2. Rescales image to 1700x2200 for consistent processing
3. Extracts answers, student ID, and chosen key from PNG
4. Grades against appropriate key version
5. Exports results with visualization

Supports:
- Separate MCQ & Written sections
- Independent scoring weights
- Partial credit for MCQ (optional)
- Numeric tolerance for written (optional)
"""

import json
import os
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import matplotlib.pyplot as plt


# -------------------------------------------------------------
# IMAGE PROCESSING & EXTRACTION FUNCTIONS
# -------------------------------------------------------------

def rescale_image(image: np.ndarray, target_width: int = 1700, target_height: int = 2200) -> np.ndarray:
    """
    Rescale image to target dimensions while maintaining aspect ratio.
    Adds padding if needed.
    
    Args:
        image: Input image
        target_width: Target width
        target_height: Target height
    
    Returns:
        Rescaled image
    """
    # Get original dimensions
    h, w = image.shape[:2]
    
    # Calculate scaling factor
    scale = min(target_width / w, target_height / h)
    
    # Calculate new dimensions
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # Resize image
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Create padded image
    padded = np.ones((target_height, target_width, 3), dtype=np.uint8) * 255
    
    # Calculate padding offsets (center the image)
    y_offset = (target_height - new_h) // 2
    x_offset = (target_width - new_w) // 2
    
    # Place resized image in center
    padded[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
    
    print(f"[RESCALE] Original: {w}x{h} -> Rescaled: {target_width}x{target_height}")
    
    return padded


def extract_from_image(image_path: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract answers, student ID, and key from a filled answer sheet PNG.
    
    Args:
        image_path: Path to PNG image of filled answer sheet
        template_data: Template JSON with bubble coordinates
    
    Returns:
        Dict containing extracted answers, student ID, and key
    """
    print(f"[EXTRACTING] Loading image: {image_path}")
    
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")
    
    print(f"[EXTRACTING] Original image: {image.shape}")
    
    # Rescale image to 1700x2200
    image = rescale_image(image, 1700, 2200)
    print(f"[EXTRACTING] Rescaled image: {image.shape}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply threshold to detect filled bubbles
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    
    extracted_data = {
        "metadata": {
            "source_image": os.path.basename(image_path),
            "extraction_date": datetime.now().isoformat(),
            "image_dimensions": f"{image.shape[1]}x{image.shape[0]}"
        },
        "answer_key": {
            "answer_key": None
        },
        "student_id": {
            "extracted_digits": None
        },
        "multiple_choice_answers": {
            "answers": {}
        },
        "quick_answers": {
            "quick_answers": []
        }
    }
    
    # Scale coordinates from template (2550x3300) to resized image (1700x2200)
    scale_x = 1700 / 2550
    scale_y = 2200 / 3300
    
    # -------------------------------------------------
    # 1. Extract chosen key (A/B/C)
    # -------------------------------------------------
    key_bubbles = template_data.get("page_1", {}).get("key", [])
    if key_bubbles:
        print("[EXTRACTING] Detecting chosen key...")
        key_fill_percentages = []
        
        for key_bubble in key_bubbles:
            # Scale coordinates
            x = int(key_bubble["x"] * scale_x)
            y = int(key_bubble["y"] * scale_y)
            radius = int(key_bubble.get("radius", 35) * min(scale_x, scale_y))
            
            # Define ROI around bubble
            y_min = max(0, y - radius)
            y_max = min(image.shape[0], y + radius)
            x_min = max(0, x - radius)
            x_max = min(image.shape[1], x + radius)
            
            if y_min >= y_max or x_min >= x_max:
                key_fill_percentages.append(0)
                continue
                
            roi = thresh[y_min:y_max, x_min:x_max]
            
            if roi.size > 0:
                fill_percentage = np.sum(roi > 0) / roi.size
                key_fill_percentages.append(fill_percentage)
            else:
                key_fill_percentages.append(0)
        
        # Find the most filled bubble
        if key_fill_percentages:
            max_index = np.argmax(key_fill_percentages)
            key_letter = chr(65 + max_index)  # A=0, B=1, C=2, etc.
            extracted_data["answer_key"]["answer_key"] = key_letter
            print(f"[EXTRACTING] Detected key: {key_letter}")
    
    # -------------------------------------------------
    # 2. Extract student ID
    # -------------------------------------------------
    print("[EXTRACTING] Extracting student ID...")
    digit_columns = template_data.get("page_1", {}).get("student_id", {}).get("digit_columns", [])
    student_id_digits = []
    
    for column in digit_columns:
        digit_position = column["digit_position"]
        bubbles = column.get("bubbles", [])
        
        digit_fill_percentages = []
        for bubble in bubbles:
            # Scale coordinates
            x = int(bubble["x"] * scale_x)
            y = int(bubble["y"] * scale_y)
            radius = int(bubble.get("radius", 31) * min(scale_x, scale_y))
            
            # Define ROI
            y_min = max(0, y - radius)
            y_max = min(image.shape[0], y + radius)
            x_min = max(0, x - radius)
            x_max = min(image.shape[1], x + radius)
            
            if y_min >= y_max or x_min >= x_max:
                digit_fill_percentages.append(0)
                continue
                
            roi = thresh[y_min:y_max, x_min:x_max]
            
            if roi.size > 0:
                fill_percentage = np.sum(roi > 0) / roi.size
                digit_fill_percentages.append(fill_percentage)
            else:
                digit_fill_percentages.append(0)
        
        # Find the most filled digit for this position
        if digit_fill_percentages:
            max_index = np.argmax(digit_fill_percentages)
            digit = max_index  # 0-9
            student_id_digits.append(str(digit))
    
    if student_id_digits:
        student_id = "".join(student_id_digits)
        extracted_data["student_id"]["extracted_digits"] = student_id
        print(f"[EXTRACTING] Extracted student ID: {student_id}")
    
    # -------------------------------------------------
    # 3. Extract MCQ answers
    # -------------------------------------------------
    print("[EXTRACTING] Extracting MCQ answers...")
    mcq_questions = template_data.get("page_1", {}).get("mcq", {}).get("questions", [])
    
    for question in mcq_questions:
        q_num = question["question_number"]
        bubbles = question.get("bubbles", [])
        
        selected_answers = []
        bubble_fill_percentages = []
        
        for bubble in bubbles:
            label = bubble["label"]
            # Scale coordinates
            x = int(bubble["x"] * scale_x)
            y = int(bubble["y"] * scale_y)
            radius = int(bubble.get("radius", 35) * min(scale_x, scale_y))
            
            # Define ROI
            y_min = max(0, y - radius)
            y_max = min(image.shape[0], y + radius)
            x_min = max(0, x - radius)
            x_max = min(image.shape[1], x + radius)
            
            if y_min >= y_max or x_min >= x_max:
                bubble_fill_percentages.append((label, 0))
                continue
                
            roi = thresh[y_min:y_max, x_min:x_max]
            
            if roi.size > 0:
                fill_percentage = np.sum(roi > 0) / roi.size
                bubble_fill_percentages.append((label, fill_percentage))
            else:
                bubble_fill_percentages.append((label, 0))
        
        # Find bubbles with significant fill (threshold: 40%)
        threshold = 0.4
        for label, fill_pct in bubble_fill_percentages:
            if fill_pct > threshold:
                selected_answers.append(label)
        
        extracted_data["multiple_choice_answers"]["answers"][str(q_num)] = {
            "question_number": q_num,
            "selected_answers": selected_answers
        }
    
    print(f"[EXTRACTING] Extracted {len(mcq_questions)} MCQ answers")
    
    # -------------------------------------------------
    # 4. Extract written answers (Simplified)
    # -------------------------------------------------
    print("[EXTRACTING] Marking written answer regions...")
    quick_answers = template_data.get("page_1", {}).get("quick_answers", {}).get("answer_boxes", [])
    
    for answer_box in quick_answers:
        q_num = answer_box.get("question_number", 1)
        # Scale coordinates
        x = int(answer_box["x"] * scale_x)
        y = int(answer_box["y"] * scale_y)
        width = int(answer_box["width"] * scale_x)
        height = int(answer_box["height"] * scale_y)
        
        # For demonstration: mark as filled
        # In production, integrate OCR here
        answer = f"Student answer for written question {q_num}"
        
        extracted_data["quick_answers"]["quick_answers"].append({
            "question_number": q_num,
            "answer": answer
        })
    
    print(f"[EXTRACTING] Marked {len(quick_answers)} written answer regions")
    print("[EXTRACTING] Extraction complete!")
    
    return extracted_data


# -------------------------------------------------------------
# LOADING FUNCTIONS
# -------------------------------------------------------------

def load_answer_key(key_path: str) -> Dict[str, Any]:
    """Load the new-format answer key."""
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Answer key not found: {key_path}")

    with open(key_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    keys = data["keys"]

    print(f"[OK] Loaded answer key: {key_path}")
    print(f"  Exam: {meta.get('exam_name')}")
    print(f"  MCQ Questions:     {meta['mcq_count']}")
    print(f"  Written Questions: {meta['written_count']}")
    print(f"  Total Questions:   {meta['total_questions']}")
    print(f"  MCQ Max Points:    {meta['mcq_max_points']}")
    print(f"  Written Max Points:{meta['written_max_points']}")
    print(f"  Available keys:    {list(keys.keys())}")

    return data


def load_template(template_path: str) -> Dict[str, Any]:
    """Load the template JSON."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[OK] Loaded template: {template_path}")
    print(f"  Source: {data.get('metadata', {}).get('source_file')}")
    
    mcq_count = len(data.get("page_1", {}).get("mcq", {}).get("questions", []))
    written_count = len(data.get("page_1", {}).get("quick_answers", {}).get("answer_boxes", []))
    
    print(f"  MCQ bubbles: {mcq_count}")
    print(f"  Written boxes: {written_count}")
    print(f"  Template dimensions: 2550x3300 -> Will be scaled to 1700x2200")

    return data


# -------------------------------------------------------------
# GRADING ENGINE
# -------------------------------------------------------------

def grade_answers(key_data: Dict[str, Any], scan_data: Dict[str, Any], 
                  partial_mcq: bool = False, written_tolerance: float = 0.0) -> Dict[str, Any]:
    """
    Grade answers in the new exam schema with multi-key support.
    
    Args:
        key_data: Loaded answer key dict (with A/B/C keys)
        scan_data: Extracted scanned answers dict
        partial_mcq: Whether to give partial credit for MCQ multiple-answer questions
        written_tolerance: Accepted numeric tolerance for written answers
    
    Returns:
        dict: Grading results
    """
    
    # Get the key letter from student's sheet
    student_key = scan_data.get("answer_key", {}).get("answer_key")
    if not student_key:
        raise ValueError("No answer key detected in student's sheet")
    
    print(f"[GRADING] Using key: {student_key}")
    
    # Get the correct answers for this key version
    keys_block = key_data.get("keys", {})
    if student_key not in keys_block:
        raise ValueError(f"Key '{student_key}' not found in answer key file")
    
    correct_key = keys_block[student_key]
    mcq_key = correct_key.get("mcq_answers", {})
    written_key = correct_key.get("written_answers", {})
    
    meta = key_data["metadata"]

    # Get student answers
    mcq_answers = scan_data.get("multiple_choice_answers", {}).get("answers", {})
    written_answers = scan_data.get("quick_answers", {}).get("quick_answers", [])

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
            "max_score": meta["mcq_max_points"] + meta["written_max_points"],
            "mcq_points_per_question": mcq_pp,
            "written_points_per_question": written_pp,
        },
        "details": {}
    }

    score_total = 0.0

    # ------------------------------------------------------
    # GRADE MCQ QUESTIONS
    # ------------------------------------------------------

    for q_str, correct_list in mcq_key.items():
        q = int(q_str)
        correct_set = set(correct_list)

        # Get student's answer
        if q_str not in mcq_answers:
            student_set = None
        else:
            student_set = set(mcq_answers[q_str].get("selected_answers", []))

        # Blank
        if not student_set:
            results["summary"]["mcq_blank"] += 1
            results["details"][q] = {
                "type": "mcq",
                "correct": list(correct_set),
                "student": [],
                "status": "blank",
                "points": 0.0
            }
            continue

        # Too many selected → automatic zero
        if student_set and len(student_set) > len(correct_set):
            points = 0.0
            status = "too_many_selected"
            results["summary"]["mcq_incorrect"] += 1

        # Exact match → full credit
        elif student_set == correct_set:
            points = mcq_pp
            status = "correct"
            results["summary"]["mcq_correct"] += 1

        # Partial credit (only if student selected <= correct answers)
        elif partial_mcq and len(correct_set) > 1:
            correct_sel = len(student_set & correct_set)

            # Here we know student_set has NO extra answers
            fraction = correct_sel / len(correct_set)
            points = fraction * mcq_pp

            if points > 0:
                status = "partial"
                results["summary"]["mcq_partial"] += 1
            else:
                status = "incorrect"
                points = 0.0
                results["summary"]["mcq_incorrect"] += 1

        # Any other case → wrong
        else:
            points = 0.0
            status = "incorrect"
            results["summary"]["mcq_incorrect"] += 1

        score_total += points

        results["details"][q] = {
            "type": "mcq",
            "correct": list(correct_set),
            "student": list(student_set),
            "status": status,
            "points": points
        }

    # ------------------------------------------------------
    # GRADE WRITTEN QUESTIONS
    # ------------------------------------------------------
    
    # Convert written_answers list to a dict keyed by question number
    written_dict = {}
    for item in written_answers:
        q_num = item.get("question_number")
        if q_num:
            # Adjust question number to match the answer key (21-25 instead of 1-5)
            adjusted_q = q_num + mcq_count
            written_dict[str(adjusted_q)] = item.get("answer", "")

    for q_str, correct_value in written_key.items():
        q = int(q_str)
        
        # Try to get correct value as float
        try:
            correct_num = float(correct_value)
        except (ValueError, TypeError):
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

        # Numeric comparison
        if isinstance(correct_num, (int, float)):
            try:
                stu_num = float(student_val)
            except:
                results["summary"]["written_incorrect"] += 1
                results["details"][q] = {
                    "type": "written",
                    "correct": correct_num,
                    "student": student_val,
                    "status": "incorrect",
                    "points": 0.0
                }
                continue

            # Compare with tolerance
            if abs(stu_num - correct_num) <= written_tolerance:
                points = written_pp
                status = "correct"
                results["summary"]["written_correct"] += 1
            else:
                points = 0.0
                status = "incorrect"
                results["summary"]["written_incorrect"] += 1
        else:
            # String comparison (case-insensitive)
            if str(student_val).strip().lower() == str(correct_num).strip().lower():
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
            "student": student_val,
            "status": status,
            "points": points
        }

    # ------------------------------------------------------
    # FINAL CALCULATIONS
    # ------------------------------------------------------

    max_points = meta["mcq_max_points"] + meta["written_max_points"]
    percent = (score_total / max_points) * 100 if max_points > 0 else 0

    results["summary"]["score"] = round(score_total, 3)
    results["summary"]["percentage"] = round(percent, 2)
    
    # Add student ID if available
    student_id = scan_data.get("student_id", {}).get("extracted_digits")
    if student_id:
        results["summary"]["student_id"] = student_id

    return results


# -------------------------------------------------------------
# VISUALIZATION & REPORTING
# -------------------------------------------------------------

def create_visualization(image_path: str, template_data: Dict[str, Any], 
                        results: Dict[str, Any], output_path: str = None):
    """
    Create a visualization of grading results on the original image.
    
    Colors:
    - Green circle: Correct MCQ answer bubble
    - Red circle: Wrong MCQ answer bubble  
    - Blue circle: Filled key bubble
    - Magenta circle: Filled student ID bubbles
    
    Args:
        image_path: Path to original PNG
        template_data: Template JSON
        results: Grading results
        output_path: Path to save visualization (optional)
    """
    print("[VISUALIZATION] Creating result visualization...")
    
    # Load and rescale original image
    image = cv2.imread(image_path)
    if image is None:
        print("[WARNING] Could not load image for visualization")
        return
    
    # Rescale to 1700x2200
    image = rescale_image(image, 1700, 2200)
    
    # Create a copy for drawing
    vis_image = image.copy()
    
    # Scale coordinates
    scale_x = 1700 / 2550
    scale_y = 2200 / 3300
    
    # Color definitions (BGR format for OpenCV)
    GREEN = (0, 255, 0)      # Correct MCQ answers
    RED = (0, 0, 255)        # Wrong MCQ answers
    BLUE = (255, 0, 0)       # Key bubble
    MAGENTA = (255, 0, 255)  # Student ID bubbles
    YELLOW = (0, 255, 255)   # Partial credit (if needed)
    GRAY = (128, 128, 128)   # Blank
    
    # -------------------------------------------------
    # 1. Draw circles around filled MCQ bubbles
    # -------------------------------------------------
    print("[VISUALIZATION] Drawing MCQ bubbles...")
    mcq_questions = template_data.get("page_1", {}).get("mcq", {}).get("questions", [])
    
    for question in mcq_questions:
        q_num = question["question_number"]
        detail = results["details"].get(q_num)
        
        if detail and detail["type"] == "mcq":
            status = detail["status"]
            correct_answers = set(detail["correct"])
            student_answers = set(detail["student"])
            
            bubbles = question.get("bubbles", [])
            
            for bubble in bubbles:
                label = bubble["label"]
                x = int(bubble["x"] * scale_x)
                y = int(bubble["y"] * scale_y)
                radius = int(bubble.get("radius", 35) * min(scale_x, scale_y))
                
                # Check if this bubble was filled by student
                if label in student_answers:
                    # Determine color based on correctness
                    if label in correct_answers:
                        # Correct answer (student selected right option)
                        color = GREEN
                        thickness = 3
                    else:
                        # Wrong answer (student selected wrong option)
                        color = RED
                        thickness = 3
                    
                    # Draw circle around the bubble
                    cv2.circle(vis_image, (x, y), radius + 5, color, thickness)
                    
                    # For wrong answers, also draw a smaller inner circle
                    if color == RED:
                        cv2.circle(vis_image, (x, y), radius - 2, color, 2)
    
    # -------------------------------------------------
    # 2. Draw blue circle around filled key bubble
    # -------------------------------------------------
    print("[VISUALIZATION] Drawing key bubble...")
    key_bubbles = template_data.get("page_1", {}).get("key", [])
    
    if key_bubbles:
        student_key = results["summary"].get("student_key", "")
        if student_key:
            # Find the index of the student's key (A=0, B=1, C=2)
            key_index = ord(student_key.upper()) - 65
            
            if 0 <= key_index < len(key_bubbles):
                key_bubble = key_bubbles[key_index]
                x = int(key_bubble["x"] * scale_x)
                y = int(key_bubble["y"] * scale_y)
                radius = int(key_bubble.get("radius", 35) * min(scale_x, scale_y))
                
                # Draw blue circle around key bubble
                cv2.circle(vis_image, (x, y), radius + 8, BLUE, 4)
                # Add label
                cv2.putText(vis_image, f"Key: {student_key}", 
                          (x - 40, y - radius - 15), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, BLUE, 2)
    
    # -------------------------------------------------
    # 3. Draw magenta circles around filled student ID bubbles
    # -------------------------------------------------
    print("[VISUALIZATION] Drawing student ID bubbles...")
    student_id = results["summary"].get("student_id", "")
    
    if student_id:
        digit_columns = template_data.get("page_1", {}).get("student_id", {}).get("digit_columns", [])
        
        for i, column in enumerate(digit_columns):
            digit_position = column["digit_position"]
            bubbles = column.get("bubbles", [])
            
            # Get the digit at this position
            if i < len(student_id):
                digit = int(student_id[i])
                
                # Find the bubble for this digit (0-9)
                if 0 <= digit < len(bubbles):
                    bubble = bubbles[digit]
                    x = int(bubble["x"] * scale_x)
                    y = int(bubble["y"] * scale_y)
                    radius = int(bubble.get("radius", 31) * min(scale_x, scale_y))
                    
                    # Draw magenta circle around student ID bubble
                    cv2.circle(vis_image, (x, y), radius + 6, MAGENTA, 3)
        
        # Add student ID label
        cv2.putText(vis_image, f"ID: {student_id}", 
                  (50, 150), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, MAGENTA, 2)
    
    # -------------------------------------------------
    # 4. Add score overlay and legend
    # -------------------------------------------------
    print("[VISUALIZATION] Adding score overlay...")
    summary = results["summary"]
    
    # Create semi-transparent overlay
    overlay = vis_image.copy()
    cv2.rectangle(overlay, (10, 10), (500, 180), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, vis_image, 0.3, 0, vis_image)
    
    # Add text
    score_text = f"Score: {summary['score']}/{summary['max_score']} ({summary['percentage']}%)"
    key_text = f"Key: {summary.get('student_key', 'N/A')}"
    student_text = f"Student ID: {summary.get('student_id', 'N/A')}"
    
    # Score header
    cv2.putText(vis_image, "GRADING RESULTS", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    
    # Score details
    y_offset = 70
    cv2.putText(vis_image, score_text, (20, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(vis_image, key_text, (20, y_offset + 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(vis_image, student_text, (20, y_offset + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Add legend
    legend_y = y_offset + 90
    cv2.putText(vis_image, "LEGEND:", (20, legend_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # Green - Correct MCQ
    cv2.circle(vis_image, (25, legend_y + 20), 8, GREEN, -1)
    cv2.putText(vis_image, "Correct MCQ", (45, legend_y + 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Red - Wrong MCQ
    cv2.circle(vis_image, (25, legend_y + 45), 8, RED, -1)
    cv2.putText(vis_image, "Wrong MCQ", (45, legend_y + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Blue - Key
    cv2.circle(vis_image, (150, legend_y + 20), 8, BLUE, -1)
    cv2.putText(vis_image, "Answer Key", (170, legend_y + 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Magenta - Student ID
    cv2.circle(vis_image, (150, legend_y + 45), 8, MAGENTA, -1)
    cv2.putText(vis_image, "Student ID", (170, legend_y + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # -------------------------------------------------
    # 5. Save or show the visualization
    # -------------------------------------------------
    if output_path:
        cv2.imwrite(output_path, vis_image)
        print(f"[VISUALIZATION] Saved to: {output_path}")
    else:
        # Create default output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        student_id = summary.get('student_id', 'unknown')
        output_path = f"grading_visualization_{student_id}_{timestamp}.png"
        cv2.imwrite(output_path, vis_image)
        print(f"[VISUALIZATION] Saved to: {output_path}")
    
    return output_path


def save_grade_report(results: Dict[str, Any], key_path: str, 
                     template_path: str, image_path: str, 
                     output_dir: str = "grade_reports") -> str:
    """Save complete grading report."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    student_id = results["summary"].get("student_id", "unknown")
    
    # Create report filename
    report_path = os.path.join(output_dir, f"grade_{student_id}_{timestamp}.json")
    
    # Add metadata to results
    results["metadata"] = {
        "graded_at": datetime.now().isoformat(),
        "answer_key": key_path,
        "template": template_path,
        "source_image": image_path,
        "student_id": student_id,
        "image_rescaled_to": "1700x2200"
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[REPORT] Grade report saved: {report_path}")
    
    # Also save a summary text file
    summary_path = os.path.join(output_dir, f"summary_{student_id}_{timestamp}.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("GRADING SUMMARY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Student ID: {student_id}\n")
        f.write(f"Answer Key: {results['summary'].get('student_key', 'N/A')}\n")
        f.write(f"Score: {results['summary']['score']}/{results['summary']['max_score']}\n")
        f.write(f"Percentage: {results['summary']['percentage']}%\n")
        f.write(f"Image Rescaled: 1700x2200\n\n")
        
        f.write("MCQ Results:\n")
        f.write(f"  Correct: {results['summary']['mcq_correct']}\n")
        f.write(f"  Incorrect: {results['summary']['mcq_incorrect']}\n")
        f.write(f"  Partial: {results['summary']['mcq_partial']}\n")
        f.write(f"  Blank: {results['summary']['mcq_blank']}\n\n")
        
        f.write("Written Results:\n")
        f.write(f"  Correct: {results['summary']['written_correct']}\n")
        f.write(f"  Incorrect: {results['summary']['written_incorrect']}\n")
        f.write(f"  Blank: {results['summary']['written_blank']}\n")
    
    print(f"[REPORT] Summary saved: {summary_path}")
    
    return report_path


# -------------------------------------------------------------
# SIMPLIFIED TEST FUNCTION
# -------------------------------------------------------------

def test_grading_simulation():
    """
    Test function that simulates grading without requiring an actual PNG.
    Useful for development and testing the logic.
    """
    print("=" * 60)
    print("TEST MODE: SIMULATED GRADING")
    print("=" * 60)
    
    # Load files
    TEMPLATE_FILE = "test_sheet_with_key_complete_template.json"
    ANSWER_KEY_FILE = "Exam_1_20251203_214556.json"
    
    try:
        template_data = load_template(TEMPLATE_FILE)
        key_data = load_answer_key(ANSWER_KEY_FILE)
        
        # Create simulated extracted data
        print("\n[TEST] Creating simulated student data...")
        simulated_data = {
            "metadata": {
                "source_image": "simulated_test.png",
                "extraction_date": datetime.now().isoformat(),
                "image_dimensions": "1700x2200"
            },
            "answer_key": {
                "answer_key": "A"  # Student chose key A
            },
            "student_id": {
                "extracted_digits": "12345678"
            },
            "multiple_choice_answers": {
                "answers": {}
            },
            "quick_answers": {
                "quick_answers": []
            }
        }
        
        # Simulate MCQ answers (student answered all "A" for key A - perfect!)
        for i in range(1, 21):
            simulated_data["multiple_choice_answers"]["answers"][str(i)] = {
                "question_number": i,
                "selected_answers": ["A"]
            }
        
        # Simulate written answers (perfect for key A)
        for i in range(1, 6):
            simulated_data["quick_answers"]["quick_answers"].append({
                "question_number": i,
                "answer": "1.0"  # Correct for key A
            })
        
        # Grade the simulated data
        print("\n[TEST] Grading simulated answers...")
        results = grade_answers(key_data, simulated_data, partial_mcq=True, written_tolerance=0.5)
        
        # Display results
        summary = results["summary"]
        print(f"\n[TEST RESULTS]")
        print(f"Student ID: {summary.get('student_id', 'N/A')}")
        print(f"Key Used: {summary.get('student_key', 'N/A')}")
        print(f"Score: {summary['score']}/{summary['max_score']} ({summary['percentage']}%)")
        
        if summary['percentage'] == 100:
            print("✓ Perfect score achieved!")
        else:
            print(f"Note: Score is {summary['percentage']}% - check if answers match key A")
        
        return results
        
    except Exception as e:
        print(f"\n[TEST ERROR] {str(e)}")
        import traceback
        traceback.print_exc()


# -------------------------------------------------------------
# MAIN WORKFLOW FUNCTION
# -------------------------------------------------------------

def grade_complete_workflow(image_path: str, template_path: str, key_path: str,
                           partial_mcq: bool = False, written_tolerance: float = 0.0,
                           save_visualization: bool = True) -> Dict[str, Any]:
    """
    Complete grading workflow:
    1. Extract answers from PNG (rescaled to 1700x2200)
    2. Grade against answer key
    3. Save reports and visualization
    
    Args:
        image_path: Path to filled answer sheet PNG
        template_path: Path to template JSON
        key_path: Path to answer key JSON
        partial_mcq: Enable partial credit for multi-answer MCQs
        written_tolerance: Tolerance for numeric written answers
        save_visualization: Whether to save visualization image
    
    Returns:
        Grading results
    """
    print("=" * 60)
    print("COMPLETE GRADING WORKFLOW")
    print("=" * 60)
    print("Image will be rescaled to 1700x2200 for consistent processing")
    
    # Check if files exist
    if not os.path.exists(image_path):
        print(f"[ERROR] Image file not found: {image_path}")
        print("[INFO] Please provide a valid PNG file path.")
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Step 1: Load template and answer key
    print("\n[STEP 1] Loading files...")
    template_data = load_template(template_path)
    key_data = load_answer_key(key_path)
    
    # Step 2: Extract answers from PNG (with rescaling)
    print("\n[STEP 2] Extracting answers from image (rescaled to 1700x2200)...")
    extracted_data = extract_from_image(image_path, template_data)
    
    # Step 3: Grade the answers
    print("\n[STEP 3] Grading answers...")
    results = grade_answers(key_data, extracted_data, partial_mcq, written_tolerance)
    
    # Step 4: Save reports
    print("\n[STEP 4] Saving reports...")
    report_path = save_grade_report(results, key_path, template_path, image_path)
    
    # Step 5: Create visualization
    if save_visualization:
        print("\n[STEP 5] Creating visualization...")
        try:
            vis_path = create_visualization(image_path, template_data, results)
        except Exception as e:
            print(f"[WARNING] Visualization failed: {str(e)}")
    
    # Step 6: Display summary
    print("\n" + "=" * 60)
    print("GRADING COMPLETE")
    print("=" * 60)
    
    summary = results["summary"]
    print(f"\nStudent ID: {summary.get('student_id', 'N/A')}")
    print(f"Detected Key: {summary.get('student_key', 'N/A')}")
    print(f"Final Score: {summary['score']}/{summary['max_score']} ({summary['percentage']}%)")
    print(f"\nMCQ: {summary['mcq_correct']} ✓, {summary['mcq_incorrect']} ✗, "
          f"{summary['mcq_partial']} ~, {summary['mcq_blank']} □")
    print(f"Written: {summary['written_correct']} ✓, {summary['written_incorrect']} ✗, "
          f"{summary['written_blank']} □")
    
    return results


# -------------------------------------------------------------
# COMMAND LINE INTERFACE
# -------------------------------------------------------------

def run_from_command_line():
    """Run grading from command line with user input."""
    print("=" * 60)
    print("OMR GRADING SYSTEM")
    print("Image Processing: Rescales to 1700x2200")
    print("=" * 60)
    
    print("\nAvailable modes:")
    print("1. Test Mode (simulated data - no PNG required)")
    print("2. Full Grading (with actual PNG image)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        # Test mode with simulated data
        results = test_grading_simulation()
        
    elif choice == "2":
        # Full workflow with actual PNG
        print("\nPlease provide file paths:")
        
        # Get file paths with defaults
        default_image = "filled_sheet.png"
        image_file = input(f"Enter PNG image path [default: {default_image}]: ").strip()
        if not image_file:
            image_file = default_image
        
        template_file = "files/template/test_sheet_with_key_complete_template.json"
        answer_key_file = "files/answer_keys/Exam_1_20251203_214556.json"
        
        print(f"\nUsing files:")
        print(f"  Image: {image_file}")
        print(f"  Template: {template_file}")
        print(f"  Answer Key: {answer_key_file}")
        
        # Check if files exist
        missing_files = []
        if not os.path.exists(image_file):
            missing_files.append(image_file)
        if not os.path.exists(template_file):
            missing_files.append(template_file)
        if not os.path.exists(answer_key_file):
            missing_files.append(answer_key_file)
        
        if missing_files:
            print(f"\n[ERROR] Missing files: {', '.join(missing_files)}")
            print("Please make sure all files exist in the current directory.")
            exit(1)
        
        # Get grading options
        partial_mcq = input("\nEnable partial credit for multi-answer MCQs? (y/n) [default: y]: ").strip().lower()
        partial_mcq = partial_mcq != 'n' if partial_mcq else True
        
        written_tol = input("Enter tolerance for written answers [default: 0.5]: ").strip()
        try:
            written_tolerance = float(written_tol) if written_tol else 0.5
        except:
            written_tolerance = 0.5
        
        # Run complete grading workflow
        results = grade_complete_workflow(
            image_path=image_file,
            template_path=template_file,
            key_path=answer_key_file,
            partial_mcq=partial_mcq,
            written_tolerance=written_tolerance,
            save_visualization=True
        )
        
    else:
        print("Invalid choice. Running test mode...")
        results = test_grading_simulation()
    
    return results


# -------------------------------------------------------------
# MAIN EXECUTION
# -------------------------------------------------------------

if __name__ == "__main__":
    try:
        results = run_from_command_line()
        print("\n" + "=" * 60)
        print("GRADING PROCESS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Grading failed: {str(e)}")
        import traceback
        traceback.print_exc()