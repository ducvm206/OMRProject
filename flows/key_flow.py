"""
Answer Key Creation Flow
Business logic for creating answer keys
"""
import os
import sys
import json
import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.db_operations import get_db_operations
from utils.file_utils import save_file_dialog, to_relative_path, to_absolute_path
from utils.validation import (
    validate_template_json, 
    validate_all_answers_filled,
    validate_filename
)


class AnswerKeyFlow:
    """Handles answer key creation workflow"""
    
    def __init__(self):
        """Initialize the flow"""
        self.db_ops = get_db_operations()
        self.current_template = None
        self.template_data = None
        self.total_questions = 0
        self.answers = {}  # {question_num: [answers]}
    
    def load_template(self, template_path):
        """
        Load a template JSON file
        
        Args:
            template_path: Path to template JSON file
            
        Returns:
            Tuple of (success, error_message, template_info)
        """
        # Validate template
        valid, error, data = validate_template_json(to_absolute_path(template_path))
        if not valid:
            return False, error, None
        
        # Extract template information
        page_data = data.get('page_1', {})
        self.total_questions = page_data.get('total_questions', 0)
        
        if not self.total_questions:
            # Count questions if not specified
            self.total_questions = len(page_data.get('questions', []))
        
        if self.total_questions == 0:
            return False, "Template has no questions", None
        
        # Store template data
        self.current_template = template_path
        self.template_data = data
        self.answers = {}
        
        template_info = {
            'path': template_path,
            'total_questions': self.total_questions,
            'has_student_id': bool(page_data.get('student_id', {}).get('digit_columns')),
            'name': os.path.basename(template_path)
        }
        
        return True, None, template_info
    
    def set_answer(self, question_num, answers):
        """
        Set answer for a question
        
        Args:
            question_num: Question number (1-indexed)
            answers: List of answers ['A', 'B', 'C', 'D'] or subset
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.current_template:
            return False, "No template loaded"
        
        if question_num < 1 or question_num > self.total_questions:
            return False, f"Question number must be between 1 and {self.total_questions}"
        
        # Validate answers
        if not isinstance(answers, list):
            return False, "Answers must be a list"
        
        for ans in answers:
            if ans not in ['A', 'B', 'C', 'D']:
                return False, f"Invalid answer: {ans}"
        
        # Sort and deduplicate
        self.answers[str(question_num)] = sorted(list(set(answers)))
        return True, None
    
    def set_multiple_answers(self, answers_dict):
        """
        Set answers for multiple questions at once
        
        Args:
            answers_dict: Dictionary of {question_num: [answers]}
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.current_template:
            return False, "No template loaded"
        
        for q_num, answers in answers_dict.items():
            success, error = self.set_answer(int(q_num), answers)
            if not success:
                return False, f"Question {q_num}: {error}"
        
        return True, None
    
    def clear_answers(self):
        """Clear all answers"""
        self.answers = {}
        return True, None
    
    def auto_fill_pattern(self, pattern='sequential'):
        """
        Auto-fill answers with a pattern
        
        Args:
            pattern: 'sequential' (A,B,C,D,A,B,...) or 'all_a', 'all_b', etc.
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.current_template:
            return False, "No template loaded"
        
        self.answers = {}
        
        if pattern == 'sequential':
            options = ['A', 'B', 'C', 'D']
            for i in range(1, self.total_questions + 1):
                self.answers[str(i)] = [options[(i - 1) % 4]]
        elif pattern in ['all_a', 'all_b', 'all_c', 'all_d']:
            answer = pattern.split('_')[1].upper()
            for i in range(1, self.total_questions + 1):
                self.answers[str(i)] = [answer]
        else:
            return False, f"Unknown pattern: {pattern}"
        
        return True, None
    
    def get_progress(self):
        """
        Get progress information
        
        Returns:
            Dictionary with progress info
        """
        answered = len(self.answers)
        missing = [str(i) for i in range(1, self.total_questions + 1) if str(i) not in self.answers]
        
        return {
            'answered': answered,
            'total': self.total_questions,
            'percentage': (answered / self.total_questions * 100) if self.total_questions > 0 else 0,
            'missing': missing[:10],  # Show first 10 missing
            'is_complete': answered == self.total_questions
        }
    
    def validate_answers(self):
        """
        Validate that all answers are filled
        
        Returns:
            Tuple of (is_valid, error_message, missing_questions)
        """
        return validate_all_answers_filled(self.answers, self.total_questions)
    
    def save_answer_key(self, filename=None, exam_name=None, save_directory='answer_keys'):
        """
        Save answer key to file and database
        
        Args:
            filename: Output filename (None for auto-generate)
            exam_name: Name of the exam
            save_directory: Directory to save file
            
        Returns:
            Tuple of (success, error_message, saved_path)
        """
        if not self.current_template:
            return False, "No template loaded", None
        
        # Validate all answers are filled
        valid, error, missing = self.validate_answers()
        if not valid:
            return False, error, None
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"answer_key_{timestamp}.json"
        
        # Validate filename
        valid, error = validate_filename(filename)
        if not valid:
            return False, error, None
        
        # Ensure .json extension
        if not filename.lower().endswith('.json'):
            filename += '.json'
        
        # Create directory if needed
        from utils.file_utils import ensure_directory
        if not ensure_directory(save_directory):
            return False, f"Failed to create directory: {save_directory}", None
        
        # Build full path
        file_path = os.path.join(save_directory, filename)
        
        # Create answer key data
        answer_key_data = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'creation_method': 'manual',
                'template_used': to_relative_path(self.current_template),
                'total_questions': self.total_questions,
                'exam_name': exam_name or os.path.splitext(filename)[0]
            },
            'answer_key': self.answers
        }
        
        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(answer_key_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return False, f"Failed to save file: {str(e)}", None
        
        # Save to database
        if self.db_ops.is_connected():
            try:
                # Get or create template in database
                template_rel_path = to_relative_path(self.current_template)
                template_info = self.db_ops.get_template_by_json_path(template_rel_path)
                
                if not template_info:
                    # Template not in database - try to create it
                    print(f"[FLOW] Template not in database, attempting to create...")
                    
                    # We need a sheet_id - this is a limitation
                    # Ideally templates should be created via sheet creation flow
                    # For now, we'll skip DB save
                    print(f"[FLOW] Warning: Cannot save to DB without proper sheet/template setup")
                    print(f"[FLOW] File saved successfully at: {file_path}")
                    return True, None, file_path
                
                # Save answer key to database
                key_name = answer_key_data['metadata']['exam_name']
                key_id = self.db_ops.save_answer_key(
                    template_id=template_info['id'],
                    name=key_name,
                    json_path=to_relative_path(file_path),
                    key_data=answer_key_data,
                    created_by='manual'
                )
                
                if key_id:
                    print(f"[FLOW] Answer key saved to database (ID: {key_id})")
                else:
                    print(f"[FLOW] Warning: Failed to save to database, but file saved")
                    
            except Exception as e:
                print(f"[FLOW] Database save failed: {e}")
                print(f"[FLOW] File saved successfully at: {file_path}")
        
        return True, None, file_path
    
    def get_answer_key_data(self):
        """
        Get current answer key data
        
        Returns:
            Dictionary with answer key data
        """
        return {
            'template': self.current_template,
            'total_questions': self.total_questions,
            'answers': self.answers.copy(),
            'progress': self.get_progress()
        }


def create_answer_key_manual(template_path, answers_dict, output_filename=None, exam_name=None):
    """
    Convenience function to create answer key programmatically
    
    Args:
        template_path: Path to template JSON
        answers_dict: Dictionary of {question_num: [answers]}
        output_filename: Output filename (None for auto-generate)
        exam_name: Name of the exam
        
    Returns:
        Tuple of (success, error_message, saved_path)
    """
    flow = AnswerKeyFlow()
    
    # Load template
    success, error, template_info = flow.load_template(template_path)
    if not success:
        return False, error, None
    
    # Set answers
    success, error = flow.set_multiple_answers(answers_dict)
    if not success:
        return False, error, None
    
    # Save
    return flow.save_answer_key(filename=output_filename, exam_name=exam_name)