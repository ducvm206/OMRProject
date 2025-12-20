"""
Answer Key Creation Flow - Multiple Keys Support
Business logic for creating answer keys with support for multiple keys (A-E)
Each exam can have up to 5 different answer keys
Now with extraction from filled answer sheets
"""
import os
import sys
import json
import datetime
import re
import random
import cv2
import numpy as np

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
    ensure_directory,
    get_project_root
)
from utils.validation import (
    validate_template_json, 
    validate_filename
)

# Try to import answer extraction processor
try:
    from core.answer_extraction.answer_extraction import AnswerSheetProcessor
    EXTRACTION_AVAILABLE = True
except ImportError:
    try:
        from core.answer_extraction import AnswerSheetProcessor
        EXTRACTION_AVAILABLE = True
    except ImportError:
        EXTRACTION_AVAILABLE = False
        print("[WARNING] Answer extraction module not available. Key extraction from sheets will be disabled.")


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
        self.extraction_processor = None
        
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
        
        # Initialize extraction processor if available
        if EXTRACTION_AVAILABLE:
            print("[FLOW] Answer extraction module loaded successfully")
    
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
    
    def extract_key_from_filled_sheet(self, sheet_image_path, target_key_letter, 
                                      threshold_percent=50, debug=False, suppress_debug_windows=True):
        """
        Extract answers from a filled answer sheet to create a key
        
        Args:
            sheet_image_path: Path to filled answer sheet (master sheet for a key)
            target_key_letter: Which key letter to populate ('A', 'B', 'C', 'D', or 'E')
            threshold_percent: Bubble detection threshold (0-100)
            debug: Show extraction visualizations
            suppress_debug_windows: If True, suppress OpenCV debug windows to avoid errors
            
        Returns:
            Tuple of (success, error_message, extraction_result)
        """
        if not EXTRACTION_AVAILABLE:
            return False, "Answer extraction module not available", None
        
        # Validate inputs
        if target_key_letter.upper() not in self.answer_keys:
            return False, f"Invalid target key letter: {target_key_letter}", None
        
        if not os.path.exists(sheet_image_path):
            return False, f"Sheet image not found: {sheet_image_path}", None
        
        if not self.current_template:
            return False, "No template loaded", None
        
        print(f"\n{'='*70}")
        print(f"EXTRACTING KEY {target_key_letter} FROM FILLED SHEET")
        print(f"{'='*70}")
        print(f"Sheet: {os.path.basename(sheet_image_path)}")
        print(f"Target key: {target_key_letter}")
        print(f"Template: {self.current_template}")
        
        try:
            # Initialize extraction processor WITH CNN model
            template_abs_path = to_absolute_path(self.current_template)
            
            # Find CNN model path
            cnn_model_path = None
            possible_paths = [
                os.path.join(get_project_root(), 'core', 'models', 'cnn_model.h5'),
                os.path.join(get_project_root(), 'files', 'core', 'models', 'cnn_model.h5'),
                'core/models/cnn_model.h5',
                'files/core/models/cnn_model.h5'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    cnn_model_path = path
                    print(f"[EXTRACTION] Found CNN model at: {cnn_model_path}")
                    break
            
            if not cnn_model_path:
                print("[EXTRACTION] WARNING: CNN model not found at any expected location")
                print("[EXTRACTION] Looking for cnn_model.h5 in:")
                for path in possible_paths:
                    print(f"  - {path}")
            
            # Initialize processor with suppress_debug_windows parameter
            print(f"[EXTRACTION] Initializing AnswerSheetProcessor (suppress_debug_windows={suppress_debug_windows})")
            self.extraction_processor = AnswerSheetProcessor(
                template_path=template_abs_path,
                cnn_model_path=cnn_model_path  # Can be None if not found
            )
            
            # Process the sheet to extract answers
            result = self.extraction_processor.process_sheet(
                image_path=sheet_image_path,
                threshold_percent=threshold_percent,
                debug=debug,
                extract_id=False,  # Don't extract student ID
                extract_mc=True,   # Extract MCQ answers
                extract_quick=True, # Extract written answers
                extract_key=False  # Don't extract key region (we're creating one)
            )
            
            if not result:
                return False, "Extraction returned no results", None
            
            print(f"\n[EXTRACTION] Extraction completed. Processing results...")
            print(f"  MCQ Answers present: {'multiple_choice_answers' in result}")
            print(f"  Quick Answers present: {'quick_answers' in result}")
            
            # Get the target key object
            target_key = self.answer_keys[target_key_letter.upper()]
            
            # Process MCQ answers from extraction
            mc_extracted = 0
            mc_errors = []
            
            if result.get('multiple_choice_answers'):
                mc_data = result['multiple_choice_answers'].get('answers', {})
                print(f"  Found {len(mc_data)} MCQ entries")
                
                for q_num_str, q_data in mc_data.items():
                    try:
                        q_num = int(q_num_str)
                        selected_answers = q_data.get('selected_answers', [])
                        
                        # Handle empty or None answers
                        if selected_answers is None:
                            selected_answers = []
                        elif isinstance(selected_answers, str):
                            selected_answers = [selected_answers] if selected_answers.strip() else []
                        
                        if selected_answers and selected_answers != ['']:
                            success, error = target_key.set_mcq_answer(q_num, selected_answers)
                            if success:
                                mc_extracted += 1
                                print(f"    Q{q_num}: Extracted answers {selected_answers}")
                            else:
                                mc_errors.append(f"Q{q_num}: {error}")
                    except (ValueError, KeyError) as e:
                        mc_errors.append(f"Q{q_num_str}: Parse error - {str(e)}")
            else:
                print("  No MCQ data found in extraction results")
            
            # Process written answers from extraction
            # Process written answers from extraction
            written_extracted = 0
            written_errors = []

            # Check if quick answers were extracted
            if result.get('quick_answers'):
                qa_data = result['quick_answers']
                print(f"  Quick answers data structure: {type(qa_data)}")
                print(f"  Quick answers keys: {list(qa_data.keys()) if isinstance(qa_data, dict) else 'N/A'}")
                
                # Handle different possible structures
                if isinstance(qa_data, dict):
                    # Check for 'quick_answers' list
                    if 'quick_answers' in qa_data:
                        qa_list = qa_data['quick_answers']
                        print(f"  Found quick_answers list with {len(qa_list)} entries")
                        
                        for qa in qa_list:
                            try:
                                q_num = qa.get('question_number')
                                answer = qa.get('answer')
                                confidence = qa.get('confidence', 0)
                                
                                # IMPORTANT FIX: Convert quick answer numbering (1-5) to written answer numbering (31-35)
                                # The extraction returns 1-5 for the 5 quick answer boxes
                                # But in the answer key, written answers should be 31-35 (after 30 MCQ questions)
                                if self.mcq_count > 0:
                                    actual_q_num = q_num + self.mcq_count
                                    print(f"    Processing Q{q_num} (adjusted to Q{actual_q_num}): answer={answer}, confidence={confidence}")
                                else:
                                    actual_q_num = q_num
                                    print(f"    Processing Q{q_num}: answer={answer}, confidence={confidence}")
                                
                                if answer is not None and str(answer).strip() and str(answer).lower() != 'none':
                                    try:
                                        numeric_answer = float(answer)
                                        # Use the adjusted question number
                                        success, error = target_key.set_written_answer(actual_q_num, numeric_answer)
                                        if success:
                                            written_extracted += 1
                                            print(f"      Q{actual_q_num}: Extracted answer '{answer}' (confidence: {confidence:.1f}%)")
                                        else:
                                            written_errors.append(f"Q{actual_q_num}: {error}")
                                    except (ValueError, TypeError) as ve:
                                        written_errors.append(f"Q{actual_q_num}: Invalid numeric answer '{answer}' - {ve}")
                            except (KeyError, AttributeError) as e:
                                written_errors.append(f"Parse error: {str(e)}")
                    else:
                        # qa_data might already be the list
                        if isinstance(qa_data.get('quick_answers', []), list):
                            qa_list = qa_data['quick_answers']
                            print(f"  Found quick_answers list via get with {len(qa_list)} entries")
                            
                            for qa in qa_list:
                                try:
                                    q_num = qa.get('question_number')
                                    answer = qa.get('answer')
                                    
                                    if answer is not None and str(answer).strip():
                                        try:
                                            numeric_answer = float(answer)
                                            success, error = target_key.set_written_answer(q_num, numeric_answer)
                                            if success:
                                                written_extracted += 1
                                                print(f"      Q{q_num}: Extracted answer '{answer}'")
                                            else:
                                                written_errors.append(f"Q{q_num}: {error}")
                                        except (ValueError, TypeError):
                                            written_errors.append(f"Q{q_num}: Invalid numeric answer '{answer}'")
                                except (KeyError, AttributeError) as e:
                                    written_errors.append(f"Parse error: {str(e)}")
                        else:
                            print("  Could not find quick_answers list in the data structure")
                            written_errors.append("Quick answers data structure not recognized")
                else:
                    print(f"  Quick answers data is not a dictionary: {type(qa_data)}")
                    written_errors.append(f"Quick answers data has unexpected type: {type(qa_data)}")
            else:
                print("  No quick_answers section in extraction results")
                # Check if there might be quick answers under a different key
                for key in result.keys():
                    if 'quick' in key.lower() or 'written' in key.lower():
                        print(f"  Found potential quick answers key: {key}")
                        if isinstance(result[key], list) and len(result[key]) > 0:
                            print(f"    Has {len(result[key])} entries")
            
            # Try alternative approach: look for any list that might contain quick answers
            if written_extracted == 0:
                print("\n[EXTRACTION] Trying alternative search for quick answers...")
                for key, value in result.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"  Checking list at key '{key}' with {len(value)} items")
                        # Check if first item has question_number and answer fields
                        if value and isinstance(value[0], dict):
                            first_item = value[0]
                            if 'question_number' in first_item and 'answer' in first_item:
                                print(f"    Found potential quick answers in '{key}'")
                                for item in value:
                                    try:
                                        q_num = item.get('question_number')
                                        answer = item.get('answer')
                                        if q_num and answer is not None:
                                            try:
                                                # Adjust question number here too
                                                q_num_int = int(q_num)
                                                if self.mcq_count > 0:
                                                    actual_q_num = q_num_int + self.mcq_count
                                                else:
                                                    actual_q_num = q_num_int
                                                
                                                numeric_answer = float(answer)
                                                success, error = target_key.set_written_answer(actual_q_num, numeric_answer)
                                                if success:
                                                    written_extracted += 1
                                                    print(f"      Q{actual_q_num}: Extracted answer '{answer}'")
                                            except (ValueError, TypeError):
                                                pass
                                    except:
                                        pass
            
            # Build extraction summary
            extraction_summary = {
                'sheet_image': sheet_image_path,
                'target_key': target_key_letter,
                'extraction_timestamp': datetime.datetime.now().isoformat(),
                'mcq_results': {
                    'extracted': mc_extracted,
                    'total_expected': self.mcq_count,
                    'errors': mc_errors,
                    'success_rate': (mc_extracted / self.mcq_count * 100) if self.mcq_count > 0 else 0
                },
                'written_results': {
                    'extracted': written_extracted,
                    'total_expected': self.written_count,
                    'errors': written_errors,
                    'success_rate': (written_extracted / self.written_count * 100) if self.written_count > 0 else 0,
                    'missing_questions': [str(i) for i in range(self.mcq_count + 1, 
                                                               self.mcq_count + self.written_count + 1)
                                         if str(i) not in target_key.written_answers]
                },
                'original_extraction_result': {
                    'metadata': result.get('metadata', {}),
                    'extraction_summary': result.get('extraction_summary', {}),
                    'has_mcq': 'multiple_choice_answers' in result,
                    'has_quick': 'quick_answers' in result,
                    'result_keys': list(result.keys())
                }
            }
            
            # Print extraction summary
            print(f"\n{'='*70}")
            print(f"EXTRACTION SUMMARY FOR KEY {target_key_letter}")
            print(f"{'='*70}")
            print(f"MCQ Answers: {mc_extracted}/{self.mcq_count} extracted")
            print(f"Written Answers: {written_extracted}/{self.written_count} extracted")
            
            if mc_errors:
                print(f"\nMCQ Errors ({len(mc_errors)}):")
                for err in mc_errors[:5]:  # Show first 5 errors
                    print(f"  - {err}")
                if len(mc_errors) > 5:
                    print(f"  ... and {len(mc_errors) - 5} more")
            
            if written_errors:
                print(f"\nWritten Errors ({len(written_errors)}):")
                for err in written_errors:
                    print(f"  - {err}")
            
            # Show key progress after extraction
            key_progress = target_key.get_progress()
            print(f"\nKey {target_key_letter} Progress:")
            print(f"  MCQ: {key_progress['mcq']['answered']}/{key_progress['mcq']['total']} ({key_progress['mcq']['percentage']:.1f}%)")
            print(f"  Written: {key_progress['written']['answered']}/{key_progress['written']['total']} ({key_progress['written']['percentage']:.1f}%)")
            print(f"  Overall: {key_progress['overall']['answered']}/{key_progress['overall']['total']} ({key_progress['overall']['percentage']:.1f}%)")
            
            # Check if extraction was successful
            success = mc_extracted > 0  # At least MCQ extracted
            if success:
                print(f"\n{'='*70}")
                print(f"[SUCCESS] Key {target_key_letter} extracted")
                print(f"{'='*70}")
            else:
                print(f"\n{'='*70}")
                print(f"[WARNING] Key {target_key_letter} partially extracted")
                print(f"{'='*70}")
            
            return success, None, extraction_summary
            
        except Exception as e:
            error_msg = f"Extraction failed: {str(e)}"
            print(f"\n{'='*70}")
            print(f"[ERROR] Extraction failed")
            print(f"{'='*70}")
            print(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg, None
    
    def extract_all_keys_from_sheets(self, sheet_images_dict, threshold_percent=50, debug=False, suppress_debug_windows=True):
        """
        Extract multiple keys from different filled sheets
        
        Args:
            sheet_images_dict: Dictionary of {key_letter: sheet_image_path}
            threshold_percent: Bubble detection threshold
            debug: Show extraction visualizations
            suppress_debug_windows: If True, suppress OpenCV debug windows
            
        Returns:
            Tuple of (success, error_message, extraction_results)
        """
        if not EXTRACTION_AVAILABLE:
            return False, "Answer extraction module not available", None
        
        if not sheet_images_dict:
            return False, "No sheet images provided", None
        
        all_results = {}
        all_errors = []
        
        print(f"\n{'='*70}")
        print(f"EXTRACTING ALL KEYS FROM FILLED SHEETS")
        print(f"{'='*70}")
        
        for key_letter, sheet_path in sheet_images_dict.items():
            print(f"\nProcessing key {key_letter} from: {os.path.basename(sheet_path)}")
            
            if key_letter.upper() not in self.answer_keys:
                error = f"Invalid key letter in sheet dict: {key_letter}"
                all_errors.append(error)
                print(f"  [ERROR] {error}")
                continue
            
            if not os.path.exists(sheet_path):
                error = f"Sheet not found: {sheet_path}"
                all_errors.append(error)
                print(f"  [ERROR] {error}")
                continue
            
            success, error, result = self.extract_key_from_filled_sheet(
                sheet_image_path=sheet_path,
                target_key_letter=key_letter,
                threshold_percent=threshold_percent,
                debug=debug,
                suppress_debug_windows=suppress_debug_windows
            )
            
            if success and result:
                all_results[key_letter] = result
                print(f"  [SUCCESS] Key {key_letter} extracted")
            else:
                if error:
                    error_msg = f"Key {key_letter}: {error}"
                else:
                    error_msg = f"Key {key_letter}: Extraction failed"
                all_errors.append(error_msg)
                print(f"  [FAILED] {error_msg}")
        
        # Overall summary
        print(f"\n{'='*70}")
        print(f"BATCH EXTRACTION COMPLETE")
        print(f"{'='*70}")
        print(f"Keys successfully extracted: {len(all_results)}/{len(sheet_images_dict)}")
        print(f"Errors: {len(all_errors)}")
        
        if all_errors:
            print(f"\nExtraction Errors:")
            for error in all_errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(all_errors) > 10:
                print(f"  ... and {len(all_errors) - 10} more")
        
        if all_results:
            success_flag = len(all_results) > 0
            error_msg = None if not all_errors else "Some extractions failed"
            return success_flag, error_msg, all_results
        else:
            return False, "All extractions failed", None
    
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
                'creation_method': 'extraction',
                'template_used': self.current_template,
                'total_keys': self.num_keys,
                'keys_present': list(self.answer_keys.keys()),
                'total_questions': self.mcq_count + self.written_count,
                'mcq_count': self.mcq_count,
                'mcq_max_points': self.mcq_max_points,
                'written_count': self.written_count,
                'written_max_points': self.written_max_points,
                'extraction_complete': self.is_extraction_complete()
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
            print(f"\n{'='*70}")
            print(f"SAVING COMPLETE EXAM FILE")
            print(f"{'='*70}")
            print(f"✓ File saved to: {file_path}")
            print(f"✓ Exam: {self.exam_name}")
            print(f"✓ Keys: {', '.join(self.answer_keys.keys())}")
            print(f"✓ MCQ: {self.mcq_count} questions")
            print(f"✓ Written: {self.written_count} questions")
            print(f"✓ Total: {self.mcq_count + self.written_count} questions")
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            print(f"\n✗ File save failed: {error_msg}")
            return False, error_msg, None
        
        result = {
            'file_path': file_path,
            'exam_id': None,
            'key_ids': {}
        }
        
        # Try to save to database
        if self.db_ops and self.db_ops.is_connected():
            try:
                # Get template info from database
                template_info = self.db_ops.get_template_by_json_path(self.current_template)
                
                if not template_info:
                    print(f"\n⚠ Template not found in database: {self.current_template}")
                    print(f"⚠ Complete exam file saved locally only")
                    return True, None, result
                
                # 1. First save the exam record
                max_score = self.mcq_max_points + self.written_max_points
                exam_id = self.db_ops.save_exam(
                    name=self.exam_name,
                    description=f"Extracted from template: {self.current_template}",
                    max_score=max_score
                )
                
                if not exam_id:
                    print(f"\n⚠ Failed to save exam to database")
                    print(f"⚠ Complete exam file saved to: {file_path}")
                    return True, None, result
                
                result['exam_id'] = exam_id
                
                # 2. Save each key individually to the database
                for letter, key in self.answer_keys.items():
                    # Create individual key file path
                    key_filename = f"{self.exam_name}_{letter}.json"
                    key_file_path = os.path.join(save_directory, key_filename)
                    
                    # Save individual key data
                    key_data = {
                        'metadata': {
                            'exam_name': self.exam_name,
                            'key_letter': letter,
                            'created_at': datetime.datetime.now().isoformat(),
                            'template_used': self.current_template
                        },
                        'answers': key.to_dict()
                    }
                    
                    try:
                        with open(key_file_path, 'w', encoding='utf-8') as f:
                            json.dump(key_data, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        print(f"⚠ Failed to save individual key file for {letter}: {e}")
                        continue
                    
                    # Save to database
                    key_id = self.db_ops.save_answer_key(
                        template_id=template_info['id'],
                        exam_id=exam_id,
                        name=f"{self.exam_name} - Key {letter}",
                        label=letter,
                        json_path=os.path.relpath(key_file_path, get_project_root()),
                        key_data=key.to_dict(),
                        created_by='extraction'
                    )
                    
                    if key_id:
                        result['key_ids'][letter] = key_id
                        print(f"  ✓ Key {letter} saved to database (ID: {key_id})")
                    else:
                        print(f"  ✗ Failed to save Key {letter} to database")
                
                print(f"\n✓ All keys saved to database (Exam ID: {exam_id})")
                print(f"✓ Individual keys saved: {list(result['key_ids'].keys())}")
                    
            except Exception as e:
                print(f"\n⚠ Database save warning: {e}")
                import traceback
                traceback.print_exc()
                # Don't return False here - file was saved successfully
        else:
            print(f"\n⚠ Database not connected - file saved locally only")
        
        return True, None, result
    
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
            'progress': self.get_all_keys_progress(),
            'is_extraction_complete': self.is_extraction_complete()
        }
    
    def clear_key(self, key_letter=None):
        """
        Clear answers for a specific key or current key
        
        Args:
            key_letter: Specific key to clear (None for current key)
            
        Returns:
            Tuple of (success, error_message)
        """
        if key_letter is None:
            if not self.current_key_letter:
                return False, "No key selected"
            key_obj = self.answer_keys[self.current_key_letter]
        else:
            key_letter = key_letter.upper()
            if key_letter not in self.answer_keys:
                return False, f"Key '{key_letter}' not found"
            key_obj = self.answer_keys[key_letter]
        
        # Clear answers
        key_obj.mcq_answers.clear()
        key_obj.written_answers.clear()
        
        return True, None
    
    def check_cnn_model_available(self):
        """
        Check if CNN model is available for handwritten digit recognition
        
        Returns:
            Tuple of (is_available, model_path_or_error_message)
        """
        possible_paths = [
            os.path.join(get_project_root(), 'core', 'models', 'cnn_model.h5'),
            os.path.join(get_project_root(), 'files', 'core', 'models', 'cnn_model.h5'),
            'core/models/cnn_model.h5',
            'files/core/models/cnn_model.h5'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return True, path
        
        return False, "CNN model not found at any expected location:\n" + "\n".join(f"  - {p}" for p in possible_paths)
    
    def is_extraction_complete(self):
        """Check if extraction is complete for all keys"""
        if not self.answer_keys:
            return False
        
        for key in self.answer_keys.values():
            progress = key.get_progress()
            if not progress['overall']['is_complete']:
                return False
        
        return True
    
    def manual_set_written_answer(self, key_letter, question_num, answer):
        """
        Manually set a written answer for a specific key
        Useful when automatic extraction fails
        
        Args:
            key_letter: Key letter ('A', 'B', etc.)
            question_num: Question number
            answer: Numeric answer
            
        Returns:
            Tuple of (success, error_message)
        """
        if key_letter.upper() not in self.answer_keys:
            return False, f"Key '{key_letter}' not found"
        
        return self.answer_keys[key_letter.upper()].set_written_answer(question_num, answer)
    
    def get_missing_written_answers(self):
        """
        Get a list of missing written answers across all keys
        
        Returns:
            Dictionary of {key_letter: [missing_question_numbers]}
        """
        missing = {}
        for letter, key in self.answer_keys.items():
            progress = key.get_progress()
            if progress['written']['missing']:
                missing[letter] = progress['written']['missing']
        return missing


def create_answer_key_manual(template_path, mcq_max_points, written_max_points,
                            mcq_answers_dict=None, written_answers_dict=None,
                            output_filename=None, exam_name=None):
    """Convenience function to create answer key programmatically"""
    flow = AnswerKeyFlow()
    
    success, error, template_info = flow.load_template(template_path)
    if not success:
        return False, error, None
    
    success, error = flow.configure_exam(exam_name or "Manual Exam", 1, mcq_max_points, written_max_points)
    if not success:
        return False, error, None
    
    if mcq_answers_dict:
        for q_num, answers in mcq_answers_dict.items():
            flow.set_mcq_answer(q_num, answers)
    
    if written_answers_dict:
        for q_num, answer in written_answers_dict.items():
            flow.set_written_answer(q_num, answer)
    
    return flow.save_exam_answer_keys(filename=output_filename)


# Example usage function
def example_extract_key_from_sheet():
    """Example of how to use the key extraction functionality"""
    flow = AnswerKeyFlow()
    
    # 1. Load template
    template_path = "template/answer_sheet_30mcq_5written_complete_template.json"
    success, error, template_info = flow.load_template(template_path)
    if not success:
        print(f"Error loading template: {error}")
        return
    
    print(f"Template loaded: {template_info['name']}")
    print(f"MCQ questions available: {template_info['mcq_questions_available']}")
    print(f"Written questions available: {template_info['written_questions_available']}")
    
    # 2. Configure exam
    success, error = flow.configure_exam(
        exam_name="Exam 1",
        num_keys=5,
        mcq_max_points=5,
        written_max_points=5
    )
    
    if not success:
        print(f"Error configuring exam: {error}")
        return
    
    print(f"\nExam configured: {flow.exam_name}")
    print(f"Keys to create: {flow.num_keys}")
    
    # 3. Check CNN model availability
    cnn_available, cnn_path_or_error = flow.check_cnn_model_available()
    if cnn_available:
        print(f"✓ CNN model found: {cnn_path_or_error}")
    else:
        print(f"⚠ CNN model not found: {cnn_path_or_error}")
        print("  Written answers will not be extracted automatically")
    
    # 4. Extract keys from filled sheets
    sheet_dict = {
        'A': 'filled_sheets/answer_sheet_A.png',
        'B': 'filled_sheets/answer_sheet_B.png',
        'C': 'filled_sheets/answer_sheet_C.png',
        'D': 'filled_sheets/answer_sheet_D.png',
        'E': 'filled_sheets/answer_sheet_E.png'
    }
    
    # Check which sheets exist
    existing_sheets = {}
    for key, path in sheet_dict.items():
        if os.path.exists(path):
            existing_sheets[key] = path
            print(f"✓ Sheet found for Key {key}: {path}")
        else:
            print(f"✗ Sheet not found for Key {key}: {path}")
    
    if existing_sheets:
        # Extract with debug windows suppressed to avoid OpenCV errors
        success, error, results = flow.extract_all_keys_from_sheets(
            sheet_images_dict=existing_sheets,
            threshold_percent=90,
            debug=False,
            suppress_debug_windows=True
        )
        
        # Check for missing written answers
        missing = flow.get_missing_written_answers()
        if missing:
            print(f"\n⚠ Missing written answers:")
            for key, questions in missing.items():
                print(f"  Key {key}: Questions {', '.join(questions)}")
            
            # You could prompt the user to enter these manually here
            # For example:
            # for key, questions in missing.items():
            #     for q in questions:
            #         answer = input(f"Enter answer for Key {key}, Q{q}: ")
            #         flow.manual_set_written_answer(key, int(q), answer)
    else:
        print("\n✗ No sheet images found for extraction")
    
    # 5. Save all keys to a complete exam file
    success, error, save_result = flow.save_exam_answer_keys(
        filename="Exam_1_Extracted_Keys.json",
        save_directory="files/answer_keys"
    )
    
    if success:
        print(f"\n{'='*70}")
        print(f"✓ ALL KEYS SAVED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"File: {save_result['file_path']}")
        if save_result['exam_id']:
            print(f"Exam ID: {save_result['exam_id']}")
        print(f"Keys: {', '.join(flow.answer_keys.keys())}")
        
        # Show what was extracted
        for letter, key in flow.answer_keys.items():
            progress = key.get_progress()
            print(f"\nKey {letter}:")
            print(f"  MCQ: {progress['mcq']['answered']}/{progress['mcq']['total']}")
            print(f"  Written: {progress['written']['answered']}/{progress['written']['total']}")
    else:
        print(f"\n✗ Failed to save keys: {error}")


if __name__ == "__main__":
    # Run example if executed directly
    if EXTRACTION_AVAILABLE:
        example_extract_key_from_sheet()
    else:
        print("Answer extraction module not available. Install required dependencies.")
        print("Required: OpenCV, NumPy, and answer_extraction module")