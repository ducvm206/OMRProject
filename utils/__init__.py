"""
Utilities package
Provides database operations, file handling, and validation
"""
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import utility modules with error handling
try:
    from .db_operations import DatabaseOperations, get_db_operations
    _db_ops_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import db_operations: {e}")
    _db_ops_available = False
    DatabaseOperations = None
    get_db_operations = None

try:
    from .file_utils import (
        get_project_root,
        to_relative_path,
        to_absolute_path,
        ensure_directory,
        select_file,
        select_files,
        select_directory,
        save_file_dialog,
        sanitize_filename,
        create_temp_file,
        cleanup_temp_files,
    )
    _file_utils_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import file_utils: {e}")
    _file_utils_available = False

try:
    from .validation import (
        validate_positive_integer,
        validate_number_of_questions,
        validate_threshold,
        validate_filename,
        validate_file_exists,
        validate_directory_exists,
        validate_json_file,
        validate_template_json,
        validate_answer_key_json,
        validate_answer_input,
        validate_student_id,
        validate_exam_name,
        validate_all_answers_filled,
    )
    _validation_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import validation: {e}")
    _validation_available = False

try:
    from .screen_manager import ScreenManager, WindowManager
    _screen_manager_available = True
except ImportError as e:
    print(f"[WARNING] Failed to import screen_manager: {e}")
    _screen_manager_available = False
    ScreenManager = None
    WindowManager = None

__all__ = [
    # Database
    'DatabaseOperations',
    'get_db_operations',
    # File utilities
    'get_project_root',
    'to_relative_path',
    'to_absolute_path',
    'ensure_directory',
    'select_file',
    'select_files',
    'select_directory',
    'save_file_dialog',
    'sanitize_filename',
    'create_temp_file',
    'cleanup_temp_files',
    # Validation
    'validate_positive_integer',
    'validate_number_of_questions',
    'validate_threshold',
    'validate_filename',
    'validate_file_exists',
    'validate_directory_exists',
    'validate_json_file',
    'validate_template_json',
    'validate_answer_key_json',
    'validate_answer_input',
    'validate_student_id',
    'validate_exam_name',
    'validate_all_answers_filled',
    # Screen manager
    'ScreenManager',
    'WindowManager'
]