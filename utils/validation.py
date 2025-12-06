"""
Validation utilities module
Handles input validation for the grading system
Updated for new schema with exams and individual key format
"""
import os
import json


def validate_positive_integer(value, min_value=1, max_value=None):
    """
    Validate that value is a positive integer within range
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value (None for no limit)
        
    Returns:
        Tuple of (is_valid, error_message, parsed_value)
    """
    try:
        num = int(value)
        if num < min_value:
            return False, f"Value must be at least {min_value}", None
        if max_value is not None and num > max_value:
            return False, f"Value must be at most {max_value}", None
        return True, None, num
    except ValueError:
        return False, "Please enter a valid number", None


def validate_number_of_questions(value):
    """
    Validate number of questions (1-200)
    
    Args:
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_value)
    """
    return validate_positive_integer(value, min_value=1, max_value=200)


def validate_threshold(value):
    """
    Validate detection threshold (20-90)
    
    Args:
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_value)
    """
    return validate_positive_integer(value, min_value=20, max_value=90)


def validate_filename(filename):
    """
    Validate filename (no invalid characters)
    
    Args:
        filename: Filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename cannot be empty"
    
    # Check for invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        if char in filename:
            return False, f"Filename cannot contain: {invalid_chars}"
    
    return True, None


def validate_file_exists(filepath):
    """
    Validate that file exists
    
    Args:
        filepath: File path to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filepath:
        return False, "File path cannot be empty"
    
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    
    if not os.path.isfile(filepath):
        return False, f"Path is not a file: {filepath}"
    
    return True, None


def validate_directory_exists(dirpath):
    """
    Validate that directory exists
    
    Args:
        dirpath: Directory path to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not dirpath:
        return False, "Directory path cannot be empty"
    
    if not os.path.exists(dirpath):
        return False, f"Directory not found: {dirpath}"
    
    if not os.path.isdir(dirpath):
        return False, f"Path is not a directory: {dirpath}"
    
    return True, None


def validate_json_file(filepath):
    """
    Validate that file is a valid JSON file
    
    Args:
        filepath: JSON file path to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_data)
    """
    # First check if file exists
    valid, error = validate_file_exists(filepath)
    if not valid:
        return False, error, None
    
    # Try to parse JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, None, data
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}", None
    except Exception as e:
        return False, f"Error reading file: {str(e)}", None


def validate_template_json(template_path):
    """
    Validate template JSON file structure
    Supports both old format (questions array) and new format (bubble_answers + quick_answers)
    
    Args:
        template_path: Path to template JSON file
        
    Returns:
        Tuple of (is_valid, error_message, data)
    """
    # Check file exists
    if not os.path.exists(template_path):
        return False, f"Template file not found: {template_path}", None
    
    # Check file extension
    if not template_path.lower().endswith('.json'):
        return False, "Template file must be a JSON file", None
    
    # Try to load JSON
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}", None
    except Exception as e:
        return False, f"Failed to read file: {str(e)}", None
    
    # Validate structure
    if not isinstance(data, dict):
        return False, "Template must be a JSON object", None
    
    # Check for page_1 section
    if 'page_1' not in data:
        return False, "Template missing 'page_1' section", None
    
    page_data = data['page_1']
    
    if not isinstance(page_data, dict):
        return False, "'page_1' must be an object", None
    
    # NEW FORMAT: Check for bubble_answers or quick_answers
    has_bubble_answers = 'bubble_answers' in page_data
    has_quick_answers = 'quick_answers' in page_data
    
    # OLD FORMAT: Check for questions array
    has_old_questions = 'questions' in page_data
    
    # Must have at least one question format
    if not (has_bubble_answers or has_quick_answers or has_old_questions):
        return False, "Template missing question data (expected 'bubble_answers', 'quick_answers', or 'questions')", None
    
    # Validate bubble_answers structure (if present)
    if has_bubble_answers:
        bubble_answers = page_data['bubble_answers']
        if not isinstance(bubble_answers, dict):
            return False, "'bubble_answers' must be an object", None
        
        # Check for questions array or questions_detected
        if 'questions' not in bubble_answers and 'questions_detected' not in bubble_answers:
            return False, "'bubble_answers' missing 'questions' or 'questions_detected'", None
        
        # Validate questions array if present
        if 'questions' in bubble_answers:
            questions = bubble_answers['questions']
            if not isinstance(questions, list):
                return False, "'bubble_answers.questions' must be an array", None
            
            # Validate first question has required structure
            if len(questions) > 0:
                first_q = questions[0]
                if not isinstance(first_q, dict):
                    return False, "Questions must be objects", None
                if 'question_number' not in first_q:
                    return False, "Questions missing 'question_number'", None
                if 'bubbles' not in first_q:
                    return False, "Questions missing 'bubbles' array", None
    
    # Validate quick_answers structure (if present)
    if has_quick_answers:
        quick_answers = page_data['quick_answers']
        if not isinstance(quick_answers, dict):
            return False, "'quick_answers' must be an object", None
        
        # Check for answer_boxes array or total_questions
        if 'answer_boxes' not in quick_answers and 'total_questions' not in quick_answers:
            return False, "'quick_answers' missing 'answer_boxes' or 'total_questions'", None
        
        # Validate answer_boxes array if present
        if 'answer_boxes' in quick_answers:
            answer_boxes = quick_answers['answer_boxes']
            if not isinstance(answer_boxes, list):
                return False, "'quick_answers.answer_boxes' must be an array", None
    
    # Validate old format questions array (if present)
    if has_old_questions:
        questions = page_data['questions']
        if not isinstance(questions, list):
            return False, "'questions' must be an array", None
        
        if len(questions) == 0:
            return False, "Template has no questions", None
    
    # All validations passed
    return True, None, data


# ============================================
# NEW VALIDATIONS FOR ANSWER KEY FORMATS
# ============================================

def validate_complete_exam_json(file_path):
    """
    Validate complete exam JSON file format (multi-key support)
    
    Args:
        file_path: Path to complete exam JSON file
        
    Returns:
        Tuple of (is_valid, error_message, data)
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}", None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", None
    except Exception as e:
        return False, f"Error reading file: {e}", None
    
    # Validate structure
    if not isinstance(data, dict):
        return False, "Root must be a dictionary", None
    
    # Check metadata
    metadata = data.get("metadata")
    if not metadata or not isinstance(metadata, dict):
        return False, "Missing or invalid 'metadata' section", None
    
    # Validate required metadata fields for complete exam
    required_meta = ["exam_name", "total_keys", "keys_present", "total_questions", 
                    "mcq_count", "written_count", "mcq_max_points", "written_max_points"]
    for field in required_meta:
        if field not in metadata:
            return False, f"Missing metadata field: {field}", None
    
    # Validate keys_present
    keys_present = metadata.get("keys_present", [])
    if not isinstance(keys_present, list) or len(keys_present) == 0:
        return False, "keys_present must be a non-empty list", None
    
    # Validate all keys are valid letters
    valid_letters = {'A', 'B', 'C', 'D', 'E'}
    for key in keys_present:
        if key not in valid_letters:
            return False, f"Invalid key letter: {key}. Must be A-E", None
    
    # Check keys section
    keys_section = data.get("keys")
    if not keys_section or not isinstance(keys_section, dict):
        return False, "Missing or invalid 'keys' section", None
    
    # Validate each key has at least one answer section (MCQ OR written)
    for key_letter in keys_present:
        if key_letter not in keys_section:
            return False, f"Key '{key_letter}' defined in keys_present but missing from keys section", None
        
        key_data = keys_section[key_letter]
        
        if not isinstance(key_data, dict):
            return False, f"Key '{key_letter}' data must be a dictionary", None
        
        # Check for key_letter in key data
        if key_data.get('key_letter') != key_letter:
            return False, f"Key '{key_letter}' key_letter field doesn't match", None
        
        # At least one section (MCQ or written) must exist
        has_mcq = "mcq_answers" in key_data and isinstance(key_data["mcq_answers"], dict)
        has_written = "written_answers" in key_data and isinstance(key_data["written_answers"], dict)
        
        if not has_mcq and not has_written:
            return False, f"Key '{key_letter}' has neither mcq_answers nor written_answers", None
        
        # Validate MCQ answers if present
        if has_mcq:
            mcq_answers = key_data["mcq_answers"]
            if not isinstance(mcq_answers, dict):
                return False, f"Key '{key_letter}' mcq_answers must be a dictionary", None
            
            # Validate each answer is a list
            for q_num, answer in mcq_answers.items():
                if not isinstance(answer, list):
                    return False, f"Key '{key_letter}' Q{q_num} answer must be a list", None
                for ans in answer:
                    if ans not in ['A', 'B', 'C', 'D']:
                        return False, f"Key '{key_letter}' Q{q_num} contains invalid answer '{ans}'. Must be A, B, C, or D", None
        
        # Validate written answers if present
        if has_written:
            written_answers = key_data["written_answers"]
            if not isinstance(written_answers, dict):
                return False, f"Key '{key_letter}' written_answers must be a dictionary", None
            
            # Validate each answer is a number
            for q_num, answer in written_answers.items():
                if not isinstance(answer, (int, float)):
                    return False, f"Key '{key_letter}' Q{q_num} written answer must be a number", None
                if answer < 0:
                    return False, f"Key '{key_letter}' Q{q_num} written answer cannot be negative", None
    
    # Validate question counts match metadata
    mcq_count = metadata.get("mcq_count", 0)
    written_count = metadata.get("written_count", 0)
    total_questions = metadata.get("total_questions", 0)
    
    if mcq_count + written_count != total_questions:
        return False, f"Question counts don't match: MCQ({mcq_count}) + Written({written_count}) != Total({total_questions})", None
    
    # Validate max points
    mcq_max = metadata.get("mcq_max_points", 0)
    written_max = metadata.get("written_max_points", 0)
    
    if mcq_max <= 0 and mcq_count > 0:
        return False, "mcq_max_points must be positive if there are MCQ questions", None
    if written_max <= 0 and written_count > 0:
        return False, "written_max_points must be positive if there are written questions", None
    
    return True, None, data


def validate_individual_key_json(file_path):
    """
    Validate individual answer key JSON file format (single key)
    
    Args:
        file_path: Path to individual answer key JSON file
        
    Returns:
        Tuple of (is_valid, error_message, data)
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}", None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", None
    except Exception as e:
        return False, f"Error reading file: {e}", None
    
    # Validate structure
    if not isinstance(data, dict):
        return False, "Root must be a dictionary", None
    
    # Check metadata
    metadata = data.get("metadata")
    if not metadata or not isinstance(metadata, dict):
        return False, "Missing or invalid 'metadata' section", None
    
    # Validate required metadata fields for individual key
    required_meta = ["exam_name", "key_label", "mcq_count", "written_count", 
                    "mcq_max_points", "written_max_points", "total_max_points"]
    for field in required_meta:
        if field not in metadata:
            return False, f"Missing metadata field: {field}", None
    
    # Validate key_label
    key_label = metadata.get("key_label")
    if key_label not in ['A', 'B', 'C', 'D', 'E']:
        return False, f"Invalid key_label: {key_label}. Must be A-E", None
    
    # Check for sections
    if 'mcq' not in data and 'written' not in data:
        return False, "Missing both 'mcq' and 'written' sections", None
    
    # Validate MCQ section if present
    if 'mcq' in data:
        mcq_section = data['mcq']
        if not isinstance(mcq_section, dict):
            return False, "'mcq' must be a dictionary", None
        
        answer_key = mcq_section.get('answer_key')
        if answer_key is None:
            return False, "Missing 'mcq.answer_key'", None
        
        if not isinstance(answer_key, dict):
            return False, "'mcq.answer_key' must be a dictionary", None
        
        # Validate MCQ answers
        for q_num, answer in answer_key.items():
            if not isinstance(answer, list):
                return False, f"Q{q_num} answer must be a list", None
            for ans in answer:
                if ans not in ['A', 'B', 'C', 'D']:
                    return False, f"Q{q_num} contains invalid answer '{ans}'. Must be A, B, C, or D", None
        
        # Validate count matches metadata
        mcq_count = metadata.get("mcq_count", 0)
        if len(answer_key) != mcq_count:
            return False, f"mcq_count ({mcq_count}) doesn't match number of MCQ answers ({len(answer_key)})", None
    
    # Validate written section if present
    if 'written' in data:
        written_section = data['written']
        if not isinstance(written_section, dict):
            return False, "'written' must be a dictionary", None
        
        answer_key = written_section.get('answer_key')
        if answer_key is None:
            return False, "Missing 'written.answer_key'", None
        
        if not isinstance(answer_key, dict):
            return False, "'written.answer_key' must be a dictionary", None
        
        # Validate written answers
        for q_num, answer in answer_key.items():
            if not isinstance(answer, (int, float)):
                return False, f"Q{q_num} written answer must be a number", None
            if answer < 0:
                return False, f"Q{q_num} written answer cannot be negative", None
        
        # Validate count matches metadata
        written_count = metadata.get("written_count", 0)
        if len(answer_key) != written_count:
            return False, f"written_count ({written_count}) doesn't match number of written answers ({len(answer_key)})", None
    
    # Validate max points
    mcq_max = metadata.get("mcq_max_points", 0)
    written_max = metadata.get("written_max_points", 0)
    total_max = metadata.get("total_max_points", 0)
    
    if 'mcq' in data and mcq_max <= 0:
        return False, "mcq_max_points must be positive for MCQ questions", None
    if 'written' in data and written_max <= 0:
        return False, "written_max_points must be positive for written questions", None
    if total_max != mcq_max + written_max:
        return False, f"total_max_points ({total_max}) doesn't match sum of mcq_max_points ({mcq_max}) + written_max_points ({written_max})", None
    
    return True, None, data


def validate_answer_key_json(file_path, is_complete_exam=True):
    """
    Generalized answer key validation (wrapper for complete or individual)
    
    Args:
        file_path: Path to answer key JSON file
        is_complete_exam: True for complete exam, False for individual key
        
    Returns:
        Tuple of (is_valid, error_message, data, key_type)
        key_type: 'complete' or 'individual'
    """
    if is_complete_exam:
        valid, error, data = validate_complete_exam_json(file_path)
        key_type = 'complete' if valid else None
    else:
        valid, error, data = validate_individual_key_json(file_path)
        key_type = 'individual' if valid else None
    
    return valid, error, data, key_type


def validate_answer_input(answer_string):
    """
    Validate answer input (A, B, C, D or combinations like A,C)
    
    Args:
        answer_string: Answer input string
        
    Returns:
        Tuple of (is_valid, error_message, parsed_answers)
    """
    if not answer_string:
        return True, None, []  # Blank is valid
    
    # Remove spaces and convert to uppercase
    cleaned = answer_string.replace(" ", "").upper()
    
    # Parse answers
    answer_list = []
    if "," in cleaned:
        # Multiple answers: A,C or A,B,D
        parts = cleaned.split(",")
        for part in parts:
            if part not in ['A', 'B', 'C', 'D']:
                return False, f"Invalid answer: {part}. Use A, B, C, or D", None
            if part not in answer_list:
                answer_list.append(part)
    else:
        # Single or concatenated: A or AC
        for char in cleaned:
            if char not in ['A', 'B', 'C', 'D']:
                return False, f"Invalid answer: {char}. Use A, B, C, or D", None
            if char not in answer_list:
                answer_list.append(char)
    
    # Sort answers
    answer_list.sort()
    return True, None, answer_list


def validate_student_id(student_id):
    """
    Validate student ID format
    
    Args:
        student_id: Student ID string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not student_id or student_id == "N/A":
        return True, None  # N/A is valid
    
    # Check if it's a reasonable length (e.g., 5-15 characters)
    if len(student_id) < 3:
        return False, "Student ID too short (minimum 3 characters)"
    
    if len(student_id) > 20:
        return False, "Student ID too long (maximum 20 characters)"
    
    # Check if it contains only alphanumeric characters
    if not student_id.replace("-", "").replace("_", "").isalnum():
        return False, "Student ID can only contain letters, numbers, hyphens, and underscores"
    
    return True, None


def validate_exam_name(exam_name):
    """
    Validate exam name
    
    Args:
        exam_name: Exam name string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not exam_name:
        return False, "Exam name cannot be empty"
    
    if len(exam_name) < 3:
        return False, "Exam name too short (minimum 3 characters)"
    
    if len(exam_name) > 100:
        return False, "Exam name too long (maximum 100 characters)"
    
    return True, None


def validate_key_label(label):
    """
    Validate answer key label (A-E)
    
    Args:
        label: Key label string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not label:
        return False, "Key label cannot be empty"
    
    label = label.upper().strip()
    if label not in ['A', 'B', 'C', 'D', 'E']:
        return False, "Key label must be A, B, C, D, or E"
    
    return True, None, label


def validate_max_points(value, min_value=1, max_value=1000):
    """
    Validate maximum points value
    
    Args:
        value: Points value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Tuple of (is_valid, error_message, parsed_value)
    """
    try:
        points = float(value)
        if points < min_value:
            return False, f"Points must be at least {min_value}", None
        if points > max_value:
            return False, f"Points cannot exceed {max_value}", None
        return True, None, points
    except ValueError:
        return False, "Please enter a valid number", None


def validate_mcq_count(value):
    """
    Validate MCQ question count
    
    Args:
        value: MCQ count to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_value)
    """
    return validate_positive_integer(value, min_value=0, max_value=200)


def validate_written_count(value):
    """
    Validate written question count
    
    Args:
        value: Written count to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_value)
    """
    return validate_positive_integer(value, min_value=0, max_value=200)


def validate_all_answers_filled(answers_dict, total_questions):
    """
    Validate that all questions have answers
    
    Args:
        answers_dict: Dictionary of {question_num: [answers]}
        total_questions: Expected total number of questions
        
    Returns:
        Tuple of (is_valid, error_message, missing_questions)
    """
    missing = []
    for i in range(1, total_questions + 1):
        if str(i) not in answers_dict or not answers_dict[str(i)]:
            missing.append(i)
    
    if missing:
        # Limit error message to first 10 missing questions
        missing_str = ', '.join(str(q) for q in missing[:10])
        if len(missing) > 10:
            missing_str += f" ... and {len(missing) - 10} more"
        return False, f"Missing answers for questions: {missing_str}", missing
    
    return True, None, []


def validate_template_compatibility(template_data, mcq_count, written_count):
    """
    Validate that template supports the specified number of questions
    
    Args:
        template_data: Template JSON data
        mcq_count: Number of MCQ questions required
        written_count: Number of written questions required
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not template_data or 'page_1' not in template_data:
        return False, "Invalid template data"
    
    page_data = template_data['page_1']
    
    # Check MCQ capacity
    if mcq_count > 0:
        if 'bubble_answers' not in page_data:
            return False, "Template does not support MCQ questions (missing bubble_answers)"
        
        bubble_data = page_data['bubble_answers']
        template_mcq_count = bubble_data.get('questions_detected', len(bubble_data.get('questions', [])))
        
        if mcq_count > template_mcq_count:
            return False, f"Template only supports {template_mcq_count} MCQ questions (requested {mcq_count})"
    
    # Check written capacity
    if written_count > 0:
        if 'quick_answers' not in page_data:
            return False, "Template does not support written questions (missing quick_answers)"
        
        quick_data = page_data['quick_answers']
        template_written_count = quick_data.get('total_questions', len(quick_data.get('answer_boxes', [])))
        
        if written_count > template_written_count:
            return False, f"Template only supports {template_written_count} written questions (requested {written_count})"
    
    return True, None


# Example usage:
if __name__ == "__main__":
    print("=== Testing Complete Exam Validation ===")
    success, error, data, key_type = validate_answer_key_json("Test_Exam_20251204_162726.json", is_complete_exam=True)
    if success:
        print(f"✓ Complete exam valid! Type: {key_type}")
        print(f"  Exam: {data['metadata']['exam_name']}")
        print(f"  Keys: {data['metadata']['keys_present']}")
    else:
        print(f"✗ Validation failed: {error}")
    
    print("\n=== Testing Individual Key Validation ===")
    # Create a sample individual key for testing
    test_individual_key = {
        "metadata": {
            "exam_name": "Test Exam",
            "key_label": "A",
            "mcq_count": 30,
            "mcq_max_points": 6,
            "written_count": 6,
            "written_max_points": 4,
            "total_max_points": 10
        },
        "mcq": {
            "answer_key": {"1": ["A"], "2": ["B"], "3": ["C"]}
        },
        "written": {
            "answer_key": {"31": 1.0, "32": 2.0}
        }
    }
    
    # Save to temp file for testing
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_individual_key, f)
        temp_file = f.name
    
    success, error, data, key_type = validate_answer_key_json(temp_file, is_complete_exam=False)
    if success:
        print(f"✓ Individual key valid! Type: {key_type}")
        print(f"  Key: {data['metadata']['key_label']}")
    else:
        print(f"✗ Validation failed: {error}")
    
    os.unlink(temp_file)