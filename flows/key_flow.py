"""
Answer Key Creation Flow
Business logic for creating answer keys with MCQ and written answer support
"""
import os
import sys
import json
import datetime
import re

# Add project root to path
PROJECT_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_ROOT = os.path.join(PROJECT_BASE, "files")

BLANK_SHEETS_DIR = os.path.join(FILES_ROOT, "blank_sheets")
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


class AnswerKeyFlow:
    """Handles answer key creation workflow with MCQ and written answer support"""
    
    def __init__(self):
        """Initialize the flow"""
        self.db_ops = get_db_operations()
        self.current_template = None
        self.template_data = None
        
        # MCQ section
        self.mcq_answers = {}  # {question_num: [answers]}
        self.mcq_count = 0
        self.mcq_max_points = 0
        
        # Written answer section
        self.written_answers = {}  # {question_num: numeric_answer}
        self.written_count = 0
        self.written_max_points = 0
        
        self.total_questions = 0
    
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
        
        # Count MCQ bubble questions
        bubble_answers = page_data.get('bubble_answers', {})
        mcq_questions_available = bubble_answers.get('questions_detected', 0)
        if not mcq_questions_available:
            mcq_questions_available = len(bubble_answers.get('questions', []))
        
        # Count written answer boxes
        quick_answers = page_data.get('quick_answers', {})
        written_questions_available = quick_answers.get('total_questions', 0)
        if not written_questions_available:
            written_questions_available = len(quick_answers.get('answer_boxes', []))
        
        # Total questions is sum of both types
        self.total_questions = mcq_questions_available + written_questions_available
        
        if self.total_questions == 0:
            return False, "Template has no questions (no bubble_answers or quick_answers found)", None
        
        # Get relative path from project root/files and ensure forward slashes
        rel_path = os.path.relpath(abs_path, FILES_ROOT).replace("\\", "/")
        self.current_template = rel_path
        self.template_data = data
        self.mcq_answers = {}
        self.written_answers = {}
        
        # Check for student ID section
        has_student_id = bool(bubble_answers.get('student_id', {}).get('digit_columns'))
        
        template_info = {
            'path': self.current_template,
            'total_questions': self.total_questions,
            'mcq_questions_available': mcq_questions_available,
            'written_questions_available': written_questions_available,
            'has_student_id': has_student_id,
            'name': os.path.basename(self.current_template)
        }
        
        return True, None, template_info
    
    def set_question_counts(self, mcq_max_points, written_max_points):
        """
        Set the maximum points for MCQ and written sections
        
        Args:
            mcq_max_points: Maximum total points for MCQ section
            written_max_points: Maximum total points for written section
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.current_template:
            return False, "No template loaded"
        
        if mcq_max_points < 0 or written_max_points < 0:
            return False, "Max points must be non-negative"
        
        if mcq_max_points == 0 and written_max_points == 0:
            return False, "At least one section must have points"
        
        # Get available questions from template
        page_data = self.template_data.get('page_1', {})
        
        bubble_answers = page_data.get('bubble_answers', {})
        mcq_questions_available = bubble_answers.get('questions_detected', 0)
        if not mcq_questions_available:
            mcq_questions_available = len(bubble_answers.get('questions', []))
        
        quick_answers = page_data.get('quick_answers', {})
        written_questions_available = quick_answers.get('total_questions', 0)
        if not written_questions_available:
            written_questions_available = len(quick_answers.get('answer_boxes', []))
        
        # Validate we can use the sections
        if mcq_max_points > 0 and mcq_questions_available == 0:
            return False, "MCQ points specified but template has no MCQ questions"
        
        if written_max_points > 0 and written_questions_available == 0:
            return False, "Written points specified but template has no written answer boxes"
        
        # Set the counts and points
        self.mcq_count = mcq_questions_available if mcq_max_points > 0 else 0
        self.mcq_max_points = mcq_max_points
        
        self.written_count = written_questions_available if written_max_points > 0 else 0
        self.written_max_points = written_max_points
        
        return True, None
    
    def set_mcq_answer(self, question_num, answers):
        """Set answer for an MCQ question"""
        if not self.current_template:
            return False, "No template loaded"
        
        if self.mcq_count == 0:
            return False, "MCQ section not configured. Call set_question_counts first."
        
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
        """Set answer for a written answer question"""
        if not self.current_template:
            return False, "No template loaded"
        
        if self.written_count == 0:
            return False, "Written answer section not configured. Call set_question_counts first."
        
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
    
    def set_multiple_mcq_answers(self, answers_dict):
        """Set answers for multiple MCQ questions at once"""
        if not self.current_template:
            return False, "No template loaded"
        
        for q_num, answers in answers_dict.items():
            success, error = self.set_mcq_answer(int(q_num), answers)
            if not success:
                return False, f"MCQ Question {q_num}: {error}"
        
        return True, None
    
    def set_multiple_written_answers(self, answers_dict):
        """Set answers for multiple written questions at once"""
        if not self.current_template:
            return False, "No template loaded"
        
        for q_num, answer in answers_dict.items():
            success, error = self.set_written_answer(int(q_num), answer)
            if not success:
                return False, f"Written Question {q_num}: {error}"
        
        return True, None
    
    def parse_mcq_input(self, text_input):
        """Parse MCQ answers from text input"""
        if not text_input or not text_input.strip():
            return False, "Empty input", None
        
        parsed = {}
        entries = re.split(r'\s+', text_input.strip())
        
        for entry in entries:
            if not entry:
                continue
            
            if ':' not in entry:
                return False, f"Invalid format: {entry}. Use 'question:answer' format", None
            
            parts = entry.split(':', 1)
            if len(parts) != 2:
                return False, f"Invalid format: {entry}", None
            
            try:
                q_num = int(parts[0])
                answers = parts[1]
                parsed[q_num] = answers
            except ValueError:
                return False, f"Invalid question number: {parts[0]}", None
        
        return True, None, parsed
    
    def parse_written_input(self, text_input):
        """Parse written answers from text input"""
        if not text_input or not text_input.strip():
            return False, "Empty input", None
        
        parsed = {}
        entries = re.split(r'\s+', text_input.strip())
        
        for entry in entries:
            if not entry:
                continue
            
            if ':' not in entry:
                return False, f"Invalid format: {entry}. Use 'question:answer' format", None
            
            parts = entry.split(':', 1)
            if len(parts) != 2:
                return False, f"Invalid format: {entry}", None
            
            try:
                q_num = int(parts[0])
                answer = float(parts[1])
                parsed[q_num] = answer
            except ValueError as e:
                return False, f"Invalid format in {entry}: {str(e)}", None
        
        return True, None, parsed
    
    def clear_answers(self):
        """Clear all answers"""
        self.mcq_answers = {}
        self.written_answers = {}
        return True, None
    
    def auto_fill_mcq_pattern(self, pattern='sequential'):
        """Auto-fill MCQ answers with a pattern"""
        if not self.current_template:
            return False, "No template loaded"
        
        if self.mcq_count == 0:
            return False, "MCQ section not configured"
        
        self.mcq_answers = {}
        
        if pattern == 'sequential':
            options = ['A', 'B', 'C', 'D']
            for i in range(1, self.mcq_count + 1):
                self.mcq_answers[str(i)] = [options[(i - 1) % 4]]
        elif pattern in ['all_a', 'all_b', 'all_c', 'all_d']:
            answer = pattern.split('_')[1].upper()
            for i in range(1, self.mcq_count + 1):
                self.mcq_answers[str(i)] = [answer]
        else:
            return False, f"Unknown pattern: {pattern}"
        
        return True, None
    
    def auto_fill_written_pattern(self, value=0):
        """Auto-fill written answers with a constant value"""
        if not self.current_template:
            return False, "No template loaded"
        
        if self.written_count == 0:
            return False, "Written answer section not configured"
        
        self.written_answers = {}
        written_start = self.mcq_count + 1
        
        for i in range(written_start, written_start + self.written_count):
            self.written_answers[str(i)] = float(value)
        
        return True, None
    
    def get_progress(self):
        """Get progress information"""
        mcq_answered = len(self.mcq_answers)
        written_answered = len(self.written_answers)
        
        mcq_missing = [str(i) for i in range(1, self.mcq_count + 1) if str(i) not in self.mcq_answers]
        written_start = self.mcq_count + 1
        written_missing = [str(i) for i in range(written_start, written_start + self.written_count) 
                          if str(i) not in self.written_answers]
        
        total_expected = self.mcq_count + self.written_count
        total_answered = mcq_answered + written_answered
        
        return {
            'mcq': {
                'answered': mcq_answered,
                'total': self.mcq_count,
                'percentage': (mcq_answered / self.mcq_count * 100) if self.mcq_count > 0 else 0,
                'missing': mcq_missing[:10],
                'is_complete': mcq_answered == self.mcq_count
            },
            'written': {
                'answered': written_answered,
                'total': self.written_count,
                'percentage': (written_answered / self.written_count * 100) if self.written_count > 0 else 0,
                'missing': written_missing[:10],
                'is_complete': written_answered == self.written_count
            },
            'overall': {
                'answered': total_answered,
                'total': total_expected,
                'percentage': (total_answered / total_expected * 100) if total_expected > 0 else 0,
                'is_complete': total_answered == total_expected
            }
        }
    
    def validate_answers(self):
        """Validate that all answers are filled"""
        progress = self.get_progress()
        
        if not progress['mcq']['is_complete']:
            missing = progress['mcq']['missing']
            return False, f"Missing {len(missing)} MCQ answers: {', '.join(missing[:5])}", progress
        
        if not progress['written']['is_complete']:
            missing = progress['written']['missing']
            return False, f"Missing {len(missing)} written answers: {', '.join(missing[:5])}", progress
        
        return True, None, progress
    
    def save_answer_key(self, filename=None, exam_name=None, save_directory='files/answer_keys'):
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
        if not ensure_directory(save_directory):
            return False, f"Failed to create directory: {save_directory}", None
        
        # Build full path
        file_path = os.path.join(save_directory, filename)
        
        # Create MCQ answer key data
        mcq_key_data = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'creation_method': 'manual',
                'template_used': self.current_template,
                'total_mcq_questions': self.mcq_count,
                'mcq_max_points': self.mcq_max_points,
                'exam_name': exam_name or os.path.splitext(filename)[0]
            },
            'answer_key': self.mcq_answers
        }
        
        # Create written answer key data (if any)
        written_key_data = None
        if self.written_count > 0:
            written_key_data = {
                'metadata': {
                    'total_written_questions': self.written_count,
                    'written_max_points': self.written_max_points
                },
                'answer_key': self.written_answers
            }
        
        # Combined data structure for file storage
        combined_data = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'creation_method': 'manual',
                'template_used': self.current_template,
                'exam_name': exam_name or os.path.splitext(filename)[0],
                'total_questions': self.mcq_count + self.written_count,
                'mcq_count': self.mcq_count,
                'written_count': self.written_count,
                'mcq_max_points': self.mcq_max_points,
                'written_max_points': self.written_max_points
            },
            'mcq_answers': self.mcq_answers if self.mcq_count > 0 else {},
            'written_answers': self.written_answers if self.written_count > 0 else {}
        }
        
        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return False, f"Failed to save file: {str(e)}", None
        
        # Save to database
        if self.db_ops.is_connected():
            try:
                # DEBUG: Show what we're looking for and what's in the database
                print(f"[FLOW DEBUG] Looking for template: '{self.current_template}'")
                
                cursor = self.db_ops.db.conn.execute(
                    "SELECT id, name, json_path FROM templates"
                )
                print(f"[FLOW DEBUG] Templates in database:")
                for row in cursor.fetchall():
                    print(f"[FLOW DEBUG]   ID={row[0]}, name='{row[1]}', path='{row[2]}'")
                
                # Get template from database using the normalized path
                template_info = self.db_ops.get_template_by_json_path(self.current_template)
                
                if not template_info:
                    print(f"[FLOW] Template not found in database: '{self.current_template}'")
                    print(f"[FLOW] Warning: Answer key saved to file but not linked to database")
                    print(f"[FLOW] File saved successfully at: {file_path}")
                    return True, None, file_path
                
                # Save answer key to database
                key_name = combined_data['metadata']['exam_name']
                
                # Normalize the answer key path too
                rel_key_path = os.path.relpath(file_path, FILES_ROOT).replace("\\", "/")
                
                key_id = self.db_ops.save_answer_key(
                    template_id=template_info['id'],
                    name=key_name,
                    json_path=rel_key_path,
                    key_data=mcq_key_data,
                    written_key_data=written_key_data,
                    created_by='manual'
                )
                
                if key_id:
                    print(f"[FLOW] Answer key saved to database (ID: {key_id})")
                else:
                    print(f"[FLOW] Warning: Failed to save to database, but file saved")
                    
            except Exception as e:
                print(f"[FLOW] Database save failed: {e}")
                import traceback
                traceback.print_exc()
                print(f"[FLOW] File saved successfully at: {file_path}")
        
        return True, None, file_path
    
    def get_answer_key_data(self):
        """Get current answer key data"""
        return {
            'template': self.current_template,
            'mcq_count': self.mcq_count,
            'written_count': self.written_count,
            'mcq_max_points': self.mcq_max_points,
            'written_max_points': self.written_max_points,
            'mcq_answers': self.mcq_answers.copy(),
            'written_answers': self.written_answers.copy(),
            'progress': self.get_progress()
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