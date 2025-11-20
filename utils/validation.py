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


def validate_template_json(filepath):
    """
    Validate that file is a valid template JSON
    
    Args:
        filepath: Template JSON file path
        
    Returns:
        Tuple of (is_valid, error_message, template_data)
    """
    valid, error, data = validate_json_file(filepath)
    if not valid:
        return False, error, None
    
    # Check for required template fields
    if 'page_1' not in data:
        return False, "Template missing 'page_1' section", None
    
    page_data = data['page_1']
    
    if 'questions' not in page_data:
        return False, "Template missing 'questions' section", None
    
    if not isinstance(page_data['questions'], list):
        return False, "Template 'questions' must be a list", None
    
    return True, None, data


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
    
    # Check for required answer key fields
    if 'answer_key' not in data:
        return False, "Answer key missing 'answer_key' section", None
    
    answer_key = data['answer_key']
    
    if not isinstance(answer_key, dict):
        return False, "Answer key must be a dictionary", None
    
    # Validate answer format
    for q_num, answers in answer_key.items():
        if not isinstance(answers, list):
            return False, f"Question {q_num} answers must be a list", None
        
        for ans in answers:
            if ans not in ['A', 'B', 'C', 'D']:
                return False, f"Question {q_num} has invalid answer: {ans}", None
    
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