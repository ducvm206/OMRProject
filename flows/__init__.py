"""
Flows package
Business logic and workflow orchestration
"""
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import flow modules with error handling
try:
    from .key_flow import AnswerKeyFlow, create_answer_key_manual
    _key_flow_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import key_flow: {e}")
    _key_flow_available = False
    AnswerKeyFlow = None
    create_answer_key_manual = None

try:
    from .sheet_flow import SheetGenerationFlow, generate_sheet_quick, generate_sheet_with_template
    _sheet_flow_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import sheet_flow: {e}")
    _sheet_flow_available = False
    SheetGenerationFlow = None
    generate_sheet_quick = None
    generate_sheet_with_template = None

try:
    from .grading_flow import GradingFlow, grade_sheet_quick
    _grading_flow_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import grading_flow: {e}")
    _grading_flow_available = False
    GradingFlow = None
    grade_sheet_quick = None

__all__ = [
    # Answer Key Flow
    'AnswerKeyFlow',
    'create_answer_key_manual',
    # Sheet Generation Flow
    'SheetGenerationFlow',
    'generate_sheet_quick',
    'generate_sheet_with_template',
    # Grading Flow
    'GradingFlow',
    'grade_sheet_quick',
]