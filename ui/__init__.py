"""
UI package
Tkinter user interface components
"""
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import UI modules with error handling
try:
    from .key_ui import AnswerKeyUI, create_answer_key_ui
    _key_ui_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import key_ui: {e}")
    _key_ui_available = False
    AnswerKeyUI = None
    create_answer_key_ui = None

try:
    from .sheet_ui import SheetGenerationUI, create_sheet_ui
    _sheet_ui_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import sheet_ui: {e}")
    _sheet_ui_available = False
    SheetGenerationUI = None
    create_sheet_ui = None

try:
    from .grading_ui import GradingUI, create_grading_ui
    _grading_ui_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import grading_ui: {e}")
    _grading_ui_available = False
    GradingUI = None
    create_grading_ui = None

__all__ = [
    'AnswerKeyUI',
    'create_answer_key_ui',
    'SheetGenerationUI',
    'create_sheet_ui',
    'GradingUI',
    'create_grading_ui',
]