"""
Answer Key Creation Flow - Multiple Keys Support
Business logic for creating answer keys with support for multiple keys (A-E)
Each exam can have up to 5 different answer keys
"""
import os
import sys
import json
import datetime
import re
import random  # Added for random answer generation

# Add project root to path
PROJECT_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_BASE not in sys.path:
    sys.path.insert(0, PROJECT_BASE)
FILES_ROOT = os.path.join(PROJECT_BASE, "files")

TEMPLATES_DIR = os.path.join(FILES_ROOT, "template")
ANSWER_KEYS_DIR = os.path.join(FILES_ROOT, "answer_keys")

from utils.db_operations import get_db_operations
from utils.file_utils import (
    save_file_dialog, 
    to_relative_path, 
    to_absolute_path,
    ensure_directory
)
from utils.validation import (
    validate_template_json, 
    validate_filename
)


class AnswerKey:
    """Represents a single answer key (A, B, C, D, or E)"""
    
    def __init__(self, key_letter, mcq_count, written_count):
        """
        Initialize answer key
        
        Args:
            key_letter: 'A', 'B', 'C', 'D', or 'E'
            mcq_count: Number of MCQ questions
            written_count: Number of written questions
        """
        self.key_letter = key_letter.upper()
        self.mcq_count = mcq_count
        self.written_count = written_count
        
        # MCQ section: {question_num: [answers]}
        self.mcq_answers = {}
        
        # Written section: {question_num: numeric_answer}
        self.written_answers = {}
    
    def set_mcq_answer(self, question_num, answers):
        """Set answer for an MCQ question"""
        if question_num < 1 or question_num > self.mcq_count:
            return False, f"MCQ question number must be between 1 and {self.mcq_count}"
        
        # Parse answers if string
        if isinstance(answers, str):
            answers = [a.strip().upper() for a in answers.split(',') if a.strip()]
        
        if not isinstance(answers, list):
            return False, "Answers must be a list or comma-separated string"
        
        if len(answers) == 0:
            return False, "At least one answer must be provided"
        
        for ans in answers:
            if ans not in ['A', 'B', 'C', 'D']:
                return False, f"Invalid MCQ answer: {ans}. Must be A, B, C, or D"
        
        self.mcq_answers[str(question_num)] = sorted(list(set(answers)))
        return True, None
    
    def set_written_answer(self, question_num, answer):
        """Set answer for a written question"""
        written_start = self.mcq_count + 1
        written_end = self.mcq_count + self.written_count
        
        if question_num < written_start or question_num > written_end:
            return False, f"Written question number must be between {written_start} and {written_end}"
        
        try:
            numeric_answer = float(answer)
        except (ValueError, TypeError):
            return False, f"Written answer must be numeric, got: {answer}"
        
        self.written_answers[str(question_num)] = numeric_answer
        return True, None
    
    def set_all_mcq_answers(self, answer_pattern):
        """
        Set all MCQ answers to a specific pattern
        
        Args:
            answer_pattern: 'all_A', 'all_B', 'all_C', 'all_D', or 'random'
        
        Returns:
            Tuple of (success, error_message, count_set)
        """
        valid_patterns = ['all_A', 'all_B', 'all_C', 'all_D', 'random']
        if answer_pattern not in valid_patterns:
            return False, f"Invalid pattern. Must be one of: {', '.join(valid_patterns)}", 0
        
        self.mcq_answers.clear()  # Clear existing MCQ answers
        
        count_set = 0
        for q_num in range(1, self.mcq_count + 1):
            if answer_pattern == 'random':
                # Randomly choose 1-2 answers from A-D
                num_answers = random.choice([1, 1, 1, 2])  # Mostly single answers, occasional double
                answers = random.sample(['A', 'B', 'C', 'D'], num_answers)
                answers.sort()
            else:
                # Extract letter from pattern (e.g., 'all_A' -> 'A')
                letter = answer_pattern.split('_')[1]
                answers = [letter]
            
            self.mcq_answers[str(q_num)] = answers
            count_set += 1
        
        return True, None, count_set
    
    def get_progress(self):
        """Get completion progress for this key"""
        mcq_answered = len(self.mcq_answers)
        written_answered = len(self.written_answers)
        
        mcq_missing = [str(i) for i in range(1, self.mcq_count + 1) if str(i) not in self.mcq_answers]
        written_start = self.mcq_count + 1
        written_missing = [str(i) for i in range(written_start, written_start + self.written_count) 
                          if str(i) not in self.written_answers]
        
        total_expected = self.mcq_count + self.written_count
        total_answered = mcq_answered + written_answered
        
        return {
            'key_letter': self.key_letter,
            'mcq': {
                'answered': mcq_answered,
                'total': self.mcq_count,
                'percentage': (mcq_answered / self.mcq_count * 100) if self.mcq_count > 0 else 0,
                'missing': mcq_missing,
                'is_complete': mcq_answered == self.mcq_count
            },
            'written': {
                'answered': written_answered,
                'total': self.written_count,
                'percentage': (written_answered / self.written_count * 100) if self.written_count > 0 else 0,
                'missing': written_missing,
                'is_complete': written_answered == self.written_count
            },
            'overall': {
                'answered': total_answered,
                'total': total_expected,
                'percentage': (total_answered / total_expected * 100) if total_expected > 0 else 0,
                'is_complete': total_answered == total_expected
            }
        }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'key_letter': self.key_letter,
            'mcq_answers': self.mcq_answers,
            'written_answers': self.written_answers
        }


class AnswerKeyFlow:
    """Handles answer key creation workflow with support for multiple keys (A-E)"""
    
    def __init__(self):
        """Initialize the flow"""
        self.db_ops = get_db_operations()
        
        # Exam configuration
        self.exam_name = None
        self.num_keys = 0  # 1-5 keys
        self.mcq_count = 0
        self.written_count = 0
        self.mcq_max_points = 0
        self.written_max_points = 0
        
        # Template
        self.current_template = None
        self.template_data = None
        
        # Answer keys: {key_letter: AnswerKey}
        self.answer_keys = {}  # {'A': AnswerKey, 'B': AnswerKey, ...}
        self.current_key_letter = None
    
    def configure_exam(self, exam_name, num_keys, mcq_max_points, written_max_points):
        """
        Configure exam parameters
        
        Args:
            exam_name: Name of the exam
            num_keys: Number of keys (1-5)
            mcq_max_points: Maximum points for MCQ section
            written_max_points: Maximum points for written section
            
        Returns:
            Tuple of (success, error_message)
        """
        # Validate inputs
        if not exam_name or not exam_name.strip():
            return False, "Exam name cannot be empty"
        
        if not isinstance(num_keys, int) or num_keys < 1 or num_keys > 5:
            return False, "Number of keys must be between 1 and 5"
        
        if mcq_max_points < 0 or written_max_points < 0:
            return False, "Max points must be non-negative"
        
        if mcq_max_points == 0 and written_max_points == 0:
            return False, "At least one section must have points"
        
        # Load template if not already loaded
        if not self.current_template or not self.template_data:
            return False, "No template loaded"
        
        page_data = self.template_data.get('page_1', {})
        
        # Get available questions from template
        mcq_data = page_data.get('mcq', {})
        mcq_available = len(mcq_data.get('questions', []))
        
        qa_data = page_data.get('quick_answers', {})
        written_available = qa_data.get('total_questions', 0)
        
        # Validate sections
        if mcq_max_points > 0 and mcq_available == 0:
            return False, "MCQ points specified but template has no MCQ questions"
        
        if written_max_points > 0 and written_available == 0:
            return False, "Written points specified but template has no written answer boxes"
        
        # Set configuration
        self.exam_name = exam_name.strip()
        self.num_keys = num_keys
        self.mcq_count = mcq_available if mcq_max_points > 0 else 0
        self.written_count = written_available if written_max_points > 0 else 0
        self.mcq_max_points = mcq_max_points
        self.written_max_points = written_max_points
        
        # Create answer key objects for each key letter
        self.answer_keys = {}
        key_letters = ['A', 'B', 'C', 'D', 'E']
        
        for i in range(num_keys):
            letter = key_letters[i]
            self.answer_keys[letter] = AnswerKey(letter, self.mcq_count, self.written_count)
        
        # Set current key to first key
        self.current_key_letter = key_letters[0]
        
        return True, None
    
    def load_template(self, template_path):
        """
        Load a template JSON file
        
        Args:
            template_path: Path to template JSON file
            
        Returns:
            Tuple of (success, error_message, template_info)
        """
        # Validate template
        abs_path = to_absolute_path(template_path)
        valid, error, data = validate_template_json(abs_path)
        if not valid:
            return False, error, None
        
        # Extract template information
        page_data = data.get('page_1', {})
        
        # Count MCQ questions
        mcq_data = page_data.get('mcq', {})
        mcq_available = len(mcq_data.get('questions', []))
        
        # Count written questions
        qa_data = page_data.get('quick_answers', {})
        written_available = qa_data.get('total_questions', 0)
        
        total_questions = mcq_available + written_available
        
        if total_questions == 0:
            return False, "Template has no questions", None
        
        # Get relative path
        rel_path = os.path.relpath(abs_path, FILES_ROOT).replace("\\", "/")
        self.current_template = rel_path
        self.template_data = data
        
        template_info = {
            'path': self.current_template,
            'total_questions': total_questions,
            'mcq_questions_available': mcq_available,
            'written_questions_available': written_available,
            'name': os.path.basename(self.current_template)
        }
        
        return True, None, template_info
    
    def switch_key(self, key_letter):
        """
        Switch to a different key for editing
        
        Args:
            key_letter: 'A', 'B', 'C', 'D', or 'E'
            
        Returns:
            Tuple of (success, error_message)
        """
        key_letter = key_letter.upper()
        
        if key_letter not in self.answer_keys:
            return False, f"Key '{key_letter}' not configured for this exam"
        
        self.current_key_letter = key_letter
        return True, None
    
    def set_mcq_answer(self, question_num, answers):
        """Set MCQ answer for current key"""
        if not self.current_key_letter:
            return False, "No key selected"
        
        return self.answer_keys[self.current_key_letter].set_mcq_answer(question_num, answers)
    
    def set_written_answer(self, question_num, answer):
        """Set written answer for current key"""
        if not self.current_key_letter:
            return False, "No key selected"
        
        return self.answer_keys[self.current_key_letter].set_written_answer(question_num, answer)
    
    def set_all_mcq_answers(self, answer_pattern, key_letter=None):
        """
        Set all MCQ answers for a key to a specific pattern
        
        Args:
            answer_pattern: 'all_A', 'all_B', 'all_C', 'all_D', or 'random'
            key_letter: Specific key to set (None for current key)
            
        Returns:
            Tuple of (success, error_message, count_set)
        """
        if key_letter is None:
            if not self.current_key_letter:
                return False, "No key selected", 0
            key_obj = self.answer_keys[self.current_key_letter]
        else:
            key_letter = key_letter.upper()
            if key_letter not in self.answer_keys:
                return False, f"Key '{key_letter}' not found", 0
            key_obj = self.answer_keys[key_letter]
        
        return key_obj.set_all_mcq_answers(answer_pattern)
    
    def set_all_mcq_answers_all_keys(self, answer_pattern):
        """
        Set all MCQ answers for ALL keys to a specific pattern
        
        Args:
            answer_pattern: 'all_A', 'all_B', 'all_C', 'all_D', or 'random'
            
        Returns:
            Tuple of (success, error_message, results_dict)
        """
        if self.mcq_count == 0:
            return False, "No MCQ questions in this exam", {}
        
        results = {}
        for letter, key_obj in self.answer_keys.items():
            success, error, count_set = key_obj.set_all_mcq_answers(answer_pattern)
            results[letter] = {
                'success': success,
                'error': error,
                'count_set': count_set if success else 0
            }
        
        return True, None, results
    
    def get_current_key_progress(self):
        """Get progress for current key"""
        if not self.current_key_letter:
            return None
        
        return self.answer_keys[self.current_key_letter].get_progress()
    
    def get_all_keys_progress(self):
        """Get progress for all keys"""
        progress = {}
        for letter, key in self.answer_keys.items():
            progress[letter] = key.get_progress()
        return progress
    
    def validate_all_keys(self):
        """Validate that all keys are complete"""
        all_complete = True
        incomplete_keys = []
        
        for letter, key in self.answer_keys.items():
            progress = key.get_progress()
            if not progress['overall']['is_complete']:
                all_complete = False
                incomplete_keys.append(letter)
        
        if not all_complete:
            return False, f"Incomplete keys: {', '.join(incomplete_keys)}", None
        
        return True, None, self.get_all_keys_progress()
    
    def save_exam_answer_keys(self, filename=None, save_directory='files/answer_keys'):
        """
        Save all answer keys for the exam to a single JSON file and database
        
        Args:
            filename: Output filename (None for auto-generate)
            save_directory: Directory to save file
            
        Returns:
            Tuple of (success, error_message, result_dict)
            result_dict contains: {'file_path': str, 'exam_id': int, 'key_ids': dict}
        """
        if not self.current_template:
            return False, "No template loaded", None
        
        if not self.exam_name:
            return False, "Exam not configured", None
        
        # Validate all keys are complete
        valid, error, progress = self.validate_all_keys()
        if not valid:
            return False, error, None
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.exam_name.replace(' ', '_')}_{timestamp}.json"
        
        # Validate filename
        valid, error = validate_filename(filename)
        if not valid:
            return False, error, None
        
        # Ensure .json extension
        if not filename.lower().endswith('.json'):
            filename += '.json'
        
        # Create directory if needed
        if not ensure_directory(save_directory):
            return False, f"Failed to create directory: {save_directory}", None
        
        # Build full path
        file_path = os.path.join(save_directory, filename)
        
        # Build exam data with all keys (for the complete file)
        exam_data = {
            'metadata': {
                'exam_name': self.exam_name,
                'created_at': datetime.datetime.now().isoformat(),
                'creation_method': 'manual',
                'template_used': self.current_template,
                'total_keys': self.num_keys,
                'keys_present': list(self.answer_keys.keys()),
                'total_questions': self.mcq_count + self.written_count,
                'mcq_count': self.mcq_count,
                'mcq_max_points': self.mcq_max_points,
                'written_count': self.written_count,
                'written_max_points': self.written_max_points
            },
            'keys': {}
        }
        
        # Add each key's data
        for letter, key in self.answer_keys.items():
            exam_data['keys'][letter] = key.to_dict()
        
        # Save complete exam file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(exam_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return False, f"Failed to save file: {str(e)}", None
        
        result = {
            'file_path': file_path,
            'exam_id': None,
            'key_ids': {}
        }
        
        # FIXED: Save to database using import_complete_exam
        if self.db_ops.is_connected():
            try:
                # Get template info from database
                template_info = self.db_ops.get_template_by_json_path(self.current_template)
                
                if not template_info:
                    print(f"[FLOW] Warning: Template not found in database: {self.current_template}")
                    print(f"[FLOW] Complete exam file saved to: {file_path}")
                    print(f"[FLOW] Use import_complete_exam to add to database later")
                    return True, None, result
                
                # Use import_complete_exam to split and save individual keys
                import_result = self.db_ops.import_complete_exam(
                    exam_file_path=file_path,
                    template_id=template_info['id'],
                    output_dir=save_directory
                )
                
                if import_result:
                    exam_id, key_ids = import_result
                    result['exam_id'] = exam_id
                    result['key_ids'] = key_ids
                    print(f"[FLOW] Exam saved to database (Exam ID: {exam_id})")
                    print(f"[FLOW] Individual keys saved: {list(key_ids.keys())}")
                else:
                    print(f"[FLOW] Warning: Failed to save to database")
                    print(f"[FLOW] Complete exam file saved to: {file_path}")
                        
            except Exception as e:
                print(f"[FLOW] Database save warning: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[FLOW] Database not connected - file saved locally only")
        
        return True, None, result  # result contains {'file_path': str, 'exam_id': int, 'key_ids': dict}
    
    def get_exam_data(self):
        """Get current exam configuration and answers"""
        return {
            'exam_name': self.exam_name,
            'template': self.current_template,
            'num_keys': self.num_keys,
            'mcq_count': self.mcq_count,
            'written_count': self.written_count,
            'mcq_max_points': self.mcq_max_points,
            'written_max_points': self.written_max_points,
            'current_key': self.current_key_letter,
            'keys_data': {letter: key.to_dict() for letter, key in self.answer_keys.items()},
            'progress': self.get_all_keys_progress()
        }


def create_answer_key_manual(template_path, mcq_max_points, written_max_points,
                            mcq_answers_dict=None, written_answers_dict=None,
                            output_filename=None, exam_name=None):
    """Convenience function to create answer key programmatically"""
    flow = AnswerKeyFlow()
    
    success, error, template_info = flow.load_template(template_path)
    if not success:
        return False, error, None
    
    success, error = flow.set_question_counts(mcq_max_points, written_max_points)
    if not success:
        return False, error, None
    
    if mcq_answers_dict:
        success, error = flow.set_multiple_mcq_answers(mcq_answers_dict)
        if not success:
            return False, error, None
    
    if written_answers_dict:
        success, error = flow.set_multiple_written_answers(written_answers_dict)
        if not success:
            return False, error, None
    
    return flow.save_answer_key(filename=output_filename, exam_name=exam_name)