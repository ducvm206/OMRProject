"""
Grading Flow
Business logic for grading answer sheets
"""
import os
import sys
import json
import glob
import cv2
import numpy as np
import tempfile

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.db_operations import get_db_operations
from utils.file_utils import to_relative_path, to_absolute_path
from utils.validation import (
    validate_template_json,
    validate_answer_key_json,
    validate_file_exists,
    validate_threshold
)


class GradingFlow:
    """Handles answer sheet grading workflow"""
    
    def __init__(self):
        """Initialize the flow"""
        self.db_ops = get_db_operations()
        
        # Configuration
        self.template_path = None
        self.template_data = None
        self.answer_key_path = None
        self.answer_key_data = None
        self.threshold = 50
        
        # Database IDs for linking
        self.template_id = None
        self.answer_key_id = None
        
        # Results
        self.current_results = None
        self.batch_results = []
        
        # Processed images for display
        self.last_processed_image = None
        self.batch_processed_images = []
    
    def load_template(self, template_path):
        """
        Load template JSON
        
        Args:
            template_path: Path to template JSON file
            
        Returns:
            Tuple of (success, error_message, template_info)
        """
        valid, error, data = validate_template_json(to_absolute_path(template_path))
        if not valid:
            return False, error, None
        
        self.template_path = template_path
        self.template_data = data
        
        # Try to get template ID from database
        if self.db_ops.is_connected():
            try:
                rel_path = to_relative_path(template_path)
                template_info = self.db_ops.get_template_by_json_path(rel_path)
                if template_info:
                    self.template_id = template_info['id']
                    print(f"[FLOW] Template found in database (ID: {self.template_id})")
                else:
                    print(f"[FLOW] Warning: Template not in database")
            except Exception as e:
                print(f"[FLOW] Error checking template: {e}")
        
        page_data = data.get('page_1', {})
        total_questions = page_data.get('total_questions', len(page_data.get('questions', [])))
        
        template_info = {
            'path': template_path,
            'total_questions': total_questions,
            'has_student_id': bool(page_data.get('student_id')),
            'name': os.path.basename(template_path)
        }
        
        return True, None, template_info
    
    def load_answer_key(self, key_path):
        """
        Load answer key JSON
        
        Args:
            key_path: Path to answer key JSON file
            
        Returns:
            Tuple of (success, error_message, key_info)
        """
        valid, error, data = validate_answer_key_json(to_absolute_path(key_path))
        if not valid:
            return False, error, None
        
        self.answer_key_path = key_path
        self.answer_key_data = data
        
        # Try to get answer key ID from database
        if self.db_ops.is_connected():
            try:
                rel_path = to_relative_path(key_path)
                key_info = self.db_ops.get_answer_key_by_json_path(rel_path)
                if key_info:
                    self.answer_key_id = key_info['id']
                    print(f"[FLOW] Answer key found in database (ID: {self.answer_key_id})")
                else:
                    print(f"[FLOW] Warning: Answer key not in database")
            except Exception as e:
                print(f"[FLOW] Error checking answer key: {e}")
        
        metadata = data.get('metadata', {})
        exam_name = metadata.get('exam_name', os.path.splitext(os.path.basename(key_path))[0])
        total_questions = metadata.get('total_questions', len(data.get('answer_key', {})))
        
        key_info = {
            'path': key_path,
            'exam_name': exam_name,
            'total_questions': total_questions,
            'name': os.path.basename(key_path)
        }
        
        return True, None, key_info
    
    def set_threshold(self, threshold):
        """
        Set detection threshold
        
        Args:
            threshold: Threshold value (20-90)
            
        Returns:
            Tuple of (success, error_message)
        """
        valid, error, parsed = validate_threshold(threshold)
        if not valid:
            return False, error
        
        self.threshold = parsed
        return True, None
    
    def grade_single_sheet(self, image_path):
        """
        Grade a single answer sheet
        
        Args:
            image_path: Path to filled answer sheet image
            
        Returns:
            Tuple of (success, error_message, result_dict)
        """
        if not self.template_path:
            return False, "Template not loaded", None
        
        if not self.answer_key_path:
            return False, "Answer key not loaded", None
        
        valid, error = validate_file_exists(image_path)
        if not valid:
            return False, error, None
        
        try:
            from core.extraction import BubbleTemplate, AnswerSheetExtractor
            from core.grading import load_answer_key, grade_answers
            
            # Extract answers from sheet
            template = BubbleTemplate(self.template_path)
            extractor = AnswerSheetExtractor(template)
            
            extraction_result = extractor.extract_complete(
                image_path,
                threshold_percent=self.threshold,
                debug=False
            )
            
            if not extraction_result:
                return False, "Failed to extract answers from sheet", None
            
            # Grade answers
            answer_key_data = load_answer_key(self.answer_key_path)
            scanned_answers_data = {
                'metadata': extraction_result.get('metadata', {}),
                'answers': extraction_result.get('answers', {})
            }
            
            grade_results = grade_answers(answer_key_data, scanned_answers_data)
            
            if not isinstance(grade_results, dict):
                return False, f"Unexpected grading result format: {type(grade_results)}", None
            
            # Extract student ID
            student_id = "N/A"
            sid = extraction_result.get('student_id')
            if isinstance(sid, dict):
                student_id = sid.get('student_id', 'N/A')
            elif isinstance(sid, str):
                student_id = sid
            
            # Parse grade results
            total_q = grade_results.get('total_questions', 0)
            correct = grade_results.get('correct', 0)
            wrong = grade_results.get('wrong', 0)
            blank = grade_results.get('blank', 0)
            percentage = grade_results.get('percentage', 0.0)
            
            # Handle summary format
            if 'summary' in grade_results and isinstance(grade_results.get('summary'), dict):
                summary = grade_results['summary']
                total_q = summary.get('total_questions', total_q)
                correct = summary.get('correct', correct)
                wrong = summary.get('wrong', wrong)
                blank = summary.get('blank', blank)
                percentage = summary.get('percentage', percentage)
            
            # Calculate wrong if needed
            if wrong == 0 and total_q > 0:
                wrong = max(0, total_q - correct - blank)
            
            if total_q == 0:
                total_q = correct + wrong + blank
            if percentage == 0.0 and total_q > 0:
                percentage = (correct / total_q) * 100
            
            # Create annotated image with colored bubbles
            annotated_image = self._create_annotated_image(
                image_path, 
                extraction_result, 
                grade_results,
                template
            )
            self.last_processed_image = annotated_image
            
            # Build result
            result = {
                'image_path': image_path,
                'student_id': student_id,
                'score': correct,
                'total_questions': total_q,
                'percentage': percentage,
                'correct': correct,
                'wrong': wrong,
                'blank': blank,
                'extraction_result': extraction_result,
                'grade_results': grade_results,
                'threshold': self.threshold,
                'annotated_image': annotated_image
            }
            
            self.current_results = result
            
            # Save to database
            if self.db_ops.is_connected() and self.answer_key_id:
                try:
                    exam_name = self.answer_key_data.get('metadata', {}).get('exam_name', 'Exam')
                    
                    graded_sheet_id = self.db_ops.save_graded_sheet(
                        key_id=self.answer_key_id,
                        student_id=student_id,
                        exam_name=exam_name,
                        filled_sheet_path=to_relative_path(image_path),
                        score=correct,
                        total_questions=total_q,
                        percentage=percentage,
                        correct=correct,
                        wrong=wrong,
                        blank=blank,
                        threshold=self.threshold
                    )
                    
                    if graded_sheet_id:
                        # Save question results
                        self._save_question_results(graded_sheet_id, grade_results, extraction_result)
                        print(f"[FLOW] Grading saved to database (ID: {graded_sheet_id})")
                    else:
                        print(f"[FLOW] Warning: Failed to save to database")
                        
                except Exception as e:
                    print(f"[FLOW] Database save failed: {e}")
            
            return True, None, result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Grading failed: {str(e)}", None
    
    def _create_annotated_image(self, image_path, extraction_result, grade_results, template):
        """
        Create annotated image with colored bubbles (matching grade_sheet.py logic)
        
        Args:
            image_path: Path to original image
            extraction_result: Result from extraction
            grade_results: Result from grading
            template: BubbleTemplate object
            
        Returns:
            Annotated image as numpy array (RGB format for display)
        """
        try:
            # Load original image
            img = cv2.imread(image_path)
            if img is None:
                print(f"[FLOW] Failed to load image: {image_path}")
                return None
            
            # Convert to RGB for annotation
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width = img_rgb.shape[:2]
            
            # Get extraction data
            answers_data = extraction_result.get('answers', {})
            
            # Get correct answers from answer key
            correct_answers = self.answer_key_data.get('answer_key', {})
            
            # Build correctness map from grade_results
            details = grade_results.get('details', [])
            correctness_map = {}
            
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict):
                        q_num = str(detail.get('question_number'))
                        is_correct = detail.get('is_correct', False)
                        if not is_correct and 'status' in detail:
                            is_correct = detail.get('status') == 'correct'
                        correctness_map[q_num] = is_correct
            elif isinstance(details, dict):
                for q_num, detail_info in details.items():
                    if isinstance(detail_info, dict):
                        is_correct = detail_info.get('is_correct', False)
                        if not is_correct and 'status' in detail_info:
                            is_correct = detail_info.get('status') == 'correct'
                        correctness_map[str(q_num)] = is_correct
            
            # Calculate scale factors
            template_width = template.template_width
            template_height = template.template_height
            scale_x = width / template_width
            scale_y = height / template_height
            scale_avg = (scale_x + scale_y) / 2
            
            # Draw question bubbles with color coding
            for question in template.questions:
                q_num = str(question.question_number)
                is_correct = correctness_map.get(q_num, False)
                q_data = answers_data.get(q_num, {})
                selected = q_data.get('selected_answers', [])
                
                for bubble in question.bubbles:
                    if bubble.label in selected:
                        # Color: Green for correct, Red for wrong (RGB format)
                        color = (0, 255, 0) if is_correct else (255, 0, 0)
                        x = int(bubble.x * scale_x)
                        y = int(bubble.y * scale_y)
                        radius = int(bubble.radius * scale_avg)
                        cv2.circle(img_rgb, (x, y), radius, color, 3)
            
            # Draw student ID bubbles (purple/magenta)
            student_id_data = extraction_result.get('student_id', {})
            if student_id_data and isinstance(student_id_data, dict):
                digit_details = student_id_data.get('digit_details', [])
                
                if template.id_template:
                    selected_positions = {d['position']: d['digit'] for d in digit_details if d.get('digit') is not None}
                    
                    for column in template.id_template['digit_columns']:
                        pos = column['digit_position']
                        selected_digit = selected_positions.get(pos)
                        
                        for bubble in column['bubbles']:
                            x = int(bubble['x'] * scale_x)
                            y = int(bubble['y'] * scale_y)
                            radius = int(bubble['radius'] * scale_avg)
                            digit = bubble['digit']
                            
                            if digit == selected_digit:
                                # Purple/Magenta for student ID (RGB format)
                                cv2.circle(img_rgb, (x, y), radius, (255, 0, 255), 3)
            
            return img_rgb  # Return RGB format for direct display
            
        except Exception as e:
            print(f"[FLOW] Error creating annotated image: {e}")
            import traceback
            traceback.print_exc()
            # Return original image in RGB if annotation fails
            try:
                img = cv2.imread(image_path)
                if img is not None:
                    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            except:
                pass
            return None
    
    def grade_batch(self, folder_path):
        """
        Grade multiple sheets in a folder
        
        Args:
            folder_path: Path to folder containing images
            
        Returns:
            Tuple of (success, error_message, results_list)
        """
        if not self.template_path:
            return False, "Template not loaded", None
        
        if not self.answer_key_path:
            return False, "Answer key not loaded", None
        
        # Get all image files
        patterns = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']
        image_files = []
        for pattern in patterns:
            image_files.extend(glob.glob(os.path.join(folder_path, pattern)))
        
        if not image_files:
            return False, "No image files found in folder", None
        
        self.batch_results = []
        self.batch_processed_images = []
        errors = []
        
        for image_path in image_files:
            success, error, result = self.grade_single_sheet(image_path)
            
            if success:
                self.batch_results.append(result)
                self.batch_processed_images.append(self.last_processed_image)
            else:
                errors.append({
                    'file': os.path.basename(image_path),
                    'error': error
                })
        
        if not self.batch_results:
            return False, "No sheets were successfully graded", None
        
        # Calculate summary
        total_sheets = len(self.batch_results)
        avg_score = sum(r['percentage'] for r in self.batch_results) / total_sheets
        
        summary = {
            'total_sheets': total_sheets,
            'avg_score': avg_score,
            'errors': errors
        }
        
        return True, None, (self.batch_results, summary)
    
    def _save_question_results(self, graded_sheet_id, grade_results, extraction_result):
        """Save question-level results to database"""
        try:
            correct_answers_dict = self.answer_key_data.get('answer_key', {})
            
            # Try to get details from grade_results
            details = grade_results.get('details', [])
            
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict):
                        q_num = detail.get('question_number')
                        student_answer = detail.get('student_answer') or detail.get('student_answers', [])
                        correct_answer = detail.get('correct_answer') or detail.get('correct_answers', [])
                        
                        # FIX: Check status field first since is_correct doesn't exist
                        if 'status' in detail:
                            is_correct = detail.get('status') == 'correct'
                        else:
                            is_correct = detail.get('is_correct', False)
                        
                        # Format answers
                        if isinstance(student_answer, list):
                            student_answer_str = ','.join(sorted(str(a) for a in student_answer))
                        else:
                            student_answer_str = str(student_answer) if student_answer else ''
                        
                        if isinstance(correct_answer, list):
                            correct_answer_str = ','.join(sorted(str(a) for a in correct_answer))
                        else:
                            correct_answer_str = str(correct_answer) if correct_answer else ''
                        
                        if q_num is not None:
                            self.db_ops.save_question_result(
                                graded_sheet_id=graded_sheet_id,
                                question_number=q_num,
                                student_answer=student_answer_str,
                                correct_answer=correct_answer_str,
                                is_correct=is_correct
                            )
            
            elif isinstance(details, dict):
                for q_num_str, detail_info in details.items():
                    if isinstance(detail_info, dict):
                        try:
                            q_num = int(q_num_str)
                            student_answer = detail_info.get('student_answer') or detail_info.get('student_answers', [])
                            correct_answer = detail_info.get('correct_answer') or detail_info.get('correct_answers', [])
                            
                            # FIX: Check status field first since is_correct doesn't exist
                            if 'status' in detail_info:
                                is_correct = detail_info.get('status') == 'correct'
                            else:
                                is_correct = detail_info.get('is_correct', False)
                            
                            # Format answers
                            if isinstance(student_answer, list):
                                student_answer_str = ','.join(sorted(str(a) for a in student_answer))
                            else:
                                student_answer_str = str(student_answer) if student_answer else ''
                            
                            if isinstance(correct_answer, list):
                                correct_answer_str = ','.join(sorted(str(a) for a in correct_answer))
                            else:
                                correct_answer_str = str(correct_answer) if correct_answer else ''
                            
                            self.db_ops.save_question_result(
                                graded_sheet_id=graded_sheet_id,
                                question_number=q_num,
                                student_answer=student_answer_str,
                                correct_answer=correct_answer_str,
                                is_correct=is_correct
                            )
                        except:
                            continue
            
        except Exception as e:
            print(f"[FLOW] Error saving question results: {e}")
    
    def get_processed_image(self):
        """Get the last processed image with colored bubbles"""
        return self.last_processed_image
    
    def get_processed_image_for_sheet(self, index):
        """Get processed image for a specific sheet in batch mode"""
        if index < len(self.batch_processed_images):
            return self.batch_processed_images[index]
        return None
    
    def get_current_results(self):
        """Get current grading results"""
        return self.current_results
    
    def get_batch_results(self):
        """Get batch grading results"""
        return self.batch_results
    
    def get_configuration(self):
        """Get current configuration"""
        return {
            'template_path': self.template_path,
            'answer_key_path': self.answer_key_path,
            'threshold': self.threshold,
            'template_loaded': self.template_path is not None,
            'key_loaded': self.answer_key_path is not None
        }


def grade_sheet_quick(template_path, key_path, image_path, threshold=50):
    """
    Quick function to grade a sheet programmatically
    
    Args:
        template_path: Path to template JSON
        key_path: Path to answer key JSON
        image_path: Path to filled sheet image
        threshold: Detection threshold
        
    Returns:
        Tuple of (success, error_message, result_dict)
    """
    flow = GradingFlow()
    
    # Load resources
    success, error, _ = flow.load_template(template_path)
    if not success:
        return False, error, None
    
    success, error, _ = flow.load_answer_key(key_path)
    if not success:
        return False, error, None
    
    success, error = flow.set_threshold(threshold)
    if not success:
        return False, error, None
    
    # Grade
    return flow.grade_single_sheet(image_path)