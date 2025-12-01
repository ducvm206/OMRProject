"""
Validation utilities module
Handles input validation for the grading system
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


# Example usage:
if __name__ == "__main__":
    # Test with new format template
    success, error, data = validate_template_json("test_sheet_20_complete_template.json")
    
    if success:
        page_data = data['page_1']
        
        # Count questions
        mcq_count = 0
        written_count = 0
        
        if 'bubble_answers' in page_data:
            bubble = page_data['bubble_answers']
            mcq_count = bubble.get('questions_detected', len(bubble.get('questions', [])))
        
        if 'quick_answers' in page_data:
            quick = page_data['quick_answers']
            written_count = quick.get('total_questions', len(quick.get('answer_boxes', [])))
        
        print(f"✓ Template valid!")
        print(f"  MCQ questions: {mcq_count}")
        print(f"  Written questions: {written_count}")
        print(f"  Total: {mcq_count + written_count}")
    else:
        print(f"✗ Template invalid: {error}")


def validate_answer_key_json(filepath):
    """
    Validate that file is a valid answer key JSON
    
    Args:
        filepath: Answer key JSON file path
        
    Returns:
        Tuple of (is_valid, error_message, key_data)
    """
    valid, error, data = validate_json_file(filepath)
    if not valid:
        return False, error, None
    
    # Check for required top-level fields
    if 'metadata' not in data:
        return False, "Answer key missing 'metadata' section", None
    
    if 'mcq_answers' not in data:
        return False, "Answer key missing 'mcq_answers' section", None
    
    if 'written_answers' not in data:
        return False, "Answer key missing 'written_answers' section", None
    
    # Validate metadata
    metadata = data['metadata']
    required_metadata = ['created_at', 'exam_name', 'total_questions', 
                         'mcq_count', 'written_count', 'mcq_max_points', 
                         'written_max_points']
    
    for field in required_metadata:
        if field not in metadata:
            return False, f"Metadata missing required field: {field}", None
    
    # Validate mcq_answers
    mcq_answers = data['mcq_answers']
    if not isinstance(mcq_answers, dict):
        return False, "mcq_answers must be a dictionary", None
    
    for q_num, answers in mcq_answers.items():
        if not isinstance(answers, list):
            return False, f"Question {q_num} answers must be a list", None
        
        if len(answers) == 0:
            return False, f"Question {q_num} must have at least one answer", None
        
        for ans in answers:
            if ans not in ['A', 'B', 'C', 'D']:
                return False, f"Question {q_num} has invalid answer: {ans}", None
    
    # Validate written_answers
    written_answers = data['written_answers']
    if not isinstance(written_answers, dict):
        return False, "written_answers must be a dictionary", None
    
    for q_num, points in written_answers.items():
        if not isinstance(points, (int, float)):
            return False, f"Written question {q_num} points must be a number", None
        
        if points < 0:
            return False, f"Written question {q_num} points cannot be negative", None
    
    # Validate counts match
    if len(mcq_answers) != metadata['mcq_count']:
        return False, f"mcq_answers count ({len(mcq_answers)}) doesn't match metadata mcq_count ({metadata['mcq_count']})", None
    
    if len(written_answers) != metadata['written_count']:
        return False, f"written_answers count ({len(written_answers)}) doesn't match metadata written_count ({metadata['written_count']})", None
    
    if len(mcq_answers) + len(written_answers) != metadata['total_questions']:
        return False, f"Total questions mismatch: {len(mcq_answers)} + {len(written_answers)} != {metadata['total_questions']}", None
    
    return True, None, data


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
        return False, f"Missing answers for questions: {missing[:10]}", missing
    
    return True, None, []