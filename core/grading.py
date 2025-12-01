"""
grading.py - Grade scanned answer sheets against the new OMR exam format

Supports:
- Separate MCQ & Written sections
- Independent scoring weights
- Partial credit for MCQ (optional)
- Numeric tolerance for written (optional)
"""

import json
import os
from datetime import datetime


# -------------------------------------------------------------
# LOADING FUNCTIONS
# -------------------------------------------------------------

def load_answer_key(key_path):
    """Load the new-format answer key."""
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Answer key not found: {key_path}")

    with open(key_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]

    print(f"[OK] Loaded answer key: {key_path}")
    print(f"  MCQ Questions:     {meta['mcq_count']}")
    print(f"  Written Questions: {meta['written_count']}")
    print(f"  Total Questions:   {meta['total_questions']}")
    print(f"  MCQ Max Points:    {meta['mcq_max_points']}")
    print(f"  Written Max Points:{meta['written_max_points']}")

    return data


def load_scanned_answers(path):
    """Load extracted student answers."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scanned answers not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]

    print(f"[OK] Loaded scanned answers: {path}")
    print(f"  Source Image:      {meta['source_image']}")
    mcq_detected = len(data.get("multiple_choice_answers", {}).get("answers", {}))
    written_detected = len(data.get("quick_answers", {}).get("quick_answers", []))

    print(f"  MCQ Detected:      {mcq_detected}")
    print(f"  Written Detected:  {written_detected}")
    print(f"  Total Extracted:   {mcq_detected + written_detected}")
    return data


# -------------------------------------------------------------
# GRADING ENGINE
# -------------------------------------------------------------

def grade_answers(key_data, scan_data, partial_mcq=False, written_tolerance=0.0):
    """
    Grade answers in the new exam schema.

    Args:
        key_data: Loaded answer key dict
        scan_data: Loaded scanned answers dict
        partial_mcq: Whether to give partial credit for MCQ multiple-answer questions
        written_tolerance: Accepted numeric tolerance for written answers

    Returns:
        dict: Grading results
    """

    meta = key_data["metadata"]

    mcq_key = key_data["mcq_answers"]
    written_key = key_data["written_answers"]

    # FIX: Extract answers from the correct structure
    mcq_answers = scan_data.get("multiple_choice_answers", {}).get("answers", {})
    written_answers = scan_data.get("quick_answers", {}).get("quick_answers", [])

    mcq_count = meta["mcq_count"]
    written_count = meta["written_count"]

    mcq_pp = meta["mcq_max_points"] / mcq_count if mcq_count > 0 else 0
    written_pp = meta["written_max_points"] / written_count if written_count > 0 else 0

    results = {
        "summary": {
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

        # FIX: Use mcq_answers and get selected_answers
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

    # FIX: Convert written_answers list to a dict keyed by question number
    written_dict = {}
    for item in written_answers:
        q_num = item.get("question_number")
        if q_num:
            # Adjust question number to match the answer key (21-24 instead of 1-4)
            adjusted_q = q_num + mcq_count
            written_dict[str(adjusted_q)] = item.get("answer", "")

    for q_str, correct_value in written_key.items():
        q = int(q_str)
        correct_num = float(correct_value)

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

        # Try parse numeric
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

        # Compare
        if abs(stu_num - correct_num) <= written_tolerance:
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
            "student": stu_num,
            "status": status,
            "points": points
        }

    # ------------------------------------------------------
    # FINAL CALCS
    # ------------------------------------------------------

    max_points = meta["mcq_max_points"] + meta["written_max_points"]
    percent = (score_total / max_points) * 100 if max_points > 0 else 0

    results["summary"]["score"] = round(score_total, 3)
    results["summary"]["percentage"] = round(percent, 2)

    return results


# -------------------------------------------------------------
# SAVE REPORT
# -------------------------------------------------------------

def save_grade_report(results, key_path, scan_path, output_dir="grade_reports"):
    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(scan_path))[0]

    out_path = os.path.join(output_dir, f"grade_{base}_{ts}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Grade report → {out_path}")
    return out_path

if __name__ == "__main__":
    # Example usage
    key_file = "answer_keys/answer_key_20251126_185343.json"
    scan_file = "extraction_results/extraction_20207284_20251126_185248.json"

    answer_key = load_answer_key(key_file)
    scanned_answers = load_scanned_answers(scan_file)

    grading_results = grade_answers(answer_key, scanned_answers, partial_mcq=True, written_tolerance=0.5)

    save_grade_report(grading_results, key_file, scan_file)
