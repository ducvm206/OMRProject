# template_extraction.py
import cv2
import numpy as np
import json
import os
import fitz  # PyMuPDF
from datetime import datetime

# Local imports (THIS IS CORRECT FOR YOUR FOLDER STRUCTURE)
from bubble_extraction import (
    convert_pdf_to_png,
    detect_bubbles_in_image,
    save_template_to_json,
    convert_question_data_to_json_serializable
)

from quick_answers_extraction import (
    detect_quick_answers_in_image
)

# ------------------------------------------------------------------------------
# COMPLETE TEMPLATE EXTRACTION
# ------------------------------------------------------------------------------

def extract_complete_template(image_path, show_visualization=False):
    """
    Extract MCQ bubbles, Student ID bubbles, KEY bubbles, and Quick Answers
    from one image page.
    """
    print("\n" + "="*80)
    print("COMPLETE TEMPLATE EXTRACTION")
    print("="*80)

    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Image not found at {image_path}")
        return None

    height, width = image.shape[:2]

    # ----------------------------------------------------------------------
    # PHASE 1: MCQ bubble detection, Student ID detection, KEY bubble detection
    # ----------------------------------------------------------------------
    print("\n[PHASE 1] Extracting Bubble Sections...")
    # FIX: detect_bubbles_in_image now returns 4 values (added qa_region)
    mcq_questions, student_id_data, key_data, qa_region = detect_bubbles_in_image(
        image_path, show_visualization=show_visualization
    )

    # ----------------------------------------------------------------------
    # PHASE 2: Quick Answers detection
    # ----------------------------------------------------------------------
    print("\n[PHASE 2] Extracting Quick Answers...")
    quick_answers_data = detect_quick_answers_in_image(
        image_path, show_visualization=show_visualization
    )

    # ----------------------------------------------------------------------
    # Build Page Template Structure (STRUCTURE B)
    # ----------------------------------------------------------------------
    page_template = {
        "image_dimensions": {
            "width": width,
            "height": height
        },

        # MCQ section
        "mcq": {
            "questions_detected": len(mcq_questions),
            "questions": convert_question_data_to_json_serializable(mcq_questions)
        },

        # Student ID bubbles (may be None)
        "student_id": student_id_data,

        # KEY section bubbles (may be None)
        "key": key_data,

        # Quick Answers region (may be None)
        "quick_answers_region": qa_region,

        # Quick answer numeric boxes (unchanged)
        "quick_answers": quick_answers_data
    }

    # ----------------------------------------------------------------------
    # WARNINGS (no stopping)
    # ----------------------------------------------------------------------
    print("\n" + "="*80)
    print("SECTION DETECTION SUMMARY")
    print("="*80)
    print(f"MCQ Questions Detected: {len(mcq_questions)}")

    if student_id_data:
        print("Student ID: Detected ✓")
    else:
        print("Student ID: NOT detected ⚠ (This page may not contain an ID section)")

    if key_data:
        print("KEY Section: Detected ✓")
    else:
        print("KEY Section: NOT detected ⚠ (Some exams do not include a KEY box)")

    if qa_region:
        print("Quick Answers Region: Detected ✓")
    else:
        print("Quick Answers Region: NOT detected ⚠ (This page may not include quick answer boxes)")

    if quick_answers_data:
        print(f"Quick Answers Numeric: {quick_answers_data.get('total_questions', 0)} detected")
    else:
        print("Quick Answers Numeric: NOT detected ⚠")

    return page_template


# ------------------------------------------------------------------------------
# PROCESS PDF INTO COMPLETE TEMPLATE
# ------------------------------------------------------------------------------

def process_pdf_complete_template(pdf_path, dpi=300, keep_png=False, show_visualization=True):
    """
    Convert PDF -> PNG -> extract full MCQ + ID + KEY + quick answers template.
    Saves a combined complete template JSON.
    """
    try:
        png_paths = convert_pdf_to_png(pdf_path, dpi=dpi)
    except Exception as e:
        print(f"\n[ERROR] Failed to convert PDF: {e}")
        return None

    complete_template_data = {}

    for i, png_path in enumerate(png_paths, start=1):
        print("\n" + "="*80)
        print(f"PROCESSING PAGE {i}/{len(png_paths)}")
        print("="*80)

        page_data = extract_complete_template(png_path, show_visualization=show_visualization)
        if not page_data:
            print(f"[ERROR] Failed to process page {i}")
            continue

        if keep_png:
            page_data["png_path"] = png_path

        complete_template_data[f"page_{i}"] = page_data

    # Save JSON
    json_path = save_complete_template_to_json(complete_template_data, pdf_path)

    # Cleanup temp PNGs
    if not keep_png:
        print("\nCleaning up temporary PNG files...")
        for p in png_paths:
            try:
                os.remove(p)
                print(f"  Deleted {p}")
            except:
                pass

    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    print(f"Total pages: {len(complete_template_data)}")
    print(f"Template saved to: {json_path}")

    return json_path


# ------------------------------------------------------------------------------
# SAVE / LOAD COMPLETE TEMPLATE
# ------------------------------------------------------------------------------

def save_complete_template_to_json(template_data, source_file, output_dir='template'):
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(source_file))[0]
    json_filename = f"{base_name}_complete_template.json"
    json_path = os.path.join(output_dir, json_filename)

    template_data['metadata'] = {
        "source_file": source_file,
        "created_at": datetime.now().isoformat(),
        "total_pages": len([k for k in template_data.keys() if k.startswith("page_")]),
        "extraction_type": "complete_bubble_quick_key"
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Saved complete template: {json_path}")
    return json_path


def load_complete_template_from_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    print(f"[LOADED] {json_path}")
    print(f"Pages: {template['metadata']['total_pages']}")
    return template


# ------------------------------------------------------------------------------
# VALIDATION UTILITIES
# ------------------------------------------------------------------------------

def validate_template_coverage(template_data):
    """
    Check coverage of MCQ, ID, KEY, Quick Answers sections.
    Only produces warnings — never stops extraction.
    """
    results = {
        "pages_processed": 0,
        "total_mcq": 0,
        "total_quick": 0,
        "id_found": False,
        "key_found": False,
        "warnings": [],
    }

    for k, page in template_data.items():
        if not k.startswith("page_"):
            continue

        results["pages_processed"] += 1

        mcq = page.get("mcq", {})
        results["total_mcq"] += mcq.get("questions_detected", 0)

        qa = page.get("quick_answers")
        if qa:
            results["total_quick"] += qa.get("total_questions", 0)

        if page.get("student_id"):
            results["id_found"] = True

        if page.get("key"):
            results["key_found"] = True

    # Warnings
    if not results["id_found"]:
        results["warnings"].append("Student ID bubbles not detected on any page.")

    if not results["key_found"]:
        results["warnings"].append("KEY selection markers not detected on any page.")

    if results["total_mcq"] == 0:
        results["warnings"].append("No MCQ questions detected.")

    if results["total_quick"] == 0:
        results["warnings"].append("No quick-answer numeric boxes detected.")

    return results


# ------------------------------------------------------------------------------
# INTERACTIVE CLI
# ------------------------------------------------------------------------------

def main():
    print("="*60)
    print("COMPLETE ANSWER SHEET TEMPLATE EXTRACTOR")
    print("="*60)

    pdf_filename = input("Enter PDF filename: ").strip()
    if not pdf_filename.lower().endswith(".pdf"):
        pdf_filename += ".pdf"

    if not os.path.exists(pdf_filename):
        print(f"[ERROR] File not found: {pdf_filename}")
        return

    # Default settings
    dpi = 300
    keep_png = False
    show_viz = True

    json_path = process_pdf_complete_template(
        pdf_filename, dpi=dpi, keep_png=keep_png, show_visualization=show_viz
    )

    if json_path:
        template = load_complete_template_from_json(json_path)
        validation = validate_template_coverage(template)

        print("\n" + "="*60)
        print("VALIDATION RESULTS")
        print("="*60)
        print(validation)


if __name__ == "__main__":
    main()
