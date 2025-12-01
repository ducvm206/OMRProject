# core/template_extraction/__init__.py
"""
Template Extraction Package
"""

import os
import sys

# Add the template_extraction directory to Python path
template_extraction_dir = os.path.dirname(os.path.abspath(__file__))
if template_extraction_dir not in sys.path:
    sys.path.insert(0, template_extraction_dir)

# Import main functions for easy access
try:
    from .bubble_extraction import (
        convert_pdf_to_png,
        detect_bubbles_in_image,
        process_pdf_answer_sheet,
        save_template_to_json,
        load_template_from_json
    )
except ImportError as e:
    print(f"Warning: Could not import bubble_extraction: {e}")

try:
    from .quick_answers_extraction import (
        detect_quick_answers_in_image,
        process_pdf_quick_answers,
        save_quick_answers_template_to_json
    )
except ImportError as e:
    print(f"Warning: Could not import quick_answers_extraction: {e}")

try:
    from .template_extraction import (
        extract_complete_template,
        process_pdf_complete_template,
        save_complete_template_to_json,
        load_complete_template_from_json
    )
except ImportError as e:
    print(f"Warning: Could not import template_extraction: {e}")