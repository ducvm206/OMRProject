"""
Database operations utility module
Handles all database interactions for sheets, templates, exams, answer keys, and grading
Updated for new schema with exams table and unified key_info
"""
import os
import sys
import json
import datetime
import numpy as np
from pathlib import Path
import shutil

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import GradingDatabase


def _native(obj):
    """Convert NumPy types to native Python types for JSON serialization"""
    # Handle NumPy integers (compatible with NumPy 2.0)
    if isinstance(obj, np.integer):
        return int(obj)
    # Handle NumPy floats (compatible with NumPy 2.0)
    if isinstance(obj, np.floating):
        return float(obj)
    # Handle NumPy booleans
    if isinstance(obj, np.bool_):
        return bool(obj)
    # Handle NumPy arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # Handle objects with .item() method (generic NumPy scalars)
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return obj.item()
        except (ValueError, TypeError):
            pass
    # Recursively handle lists
    if isinstance(obj, list):
        return [_native(x) for x in obj]
    # Recursively handle tuples
    if isinstance(obj, tuple):
        return tuple(_native(x) for x in obj)
    # Recursively handle dicts
    if isinstance(obj, dict):
        return {k: _native(v) for k, v in obj.items()}
    return obj


class DatabaseOperations:
    """Handles all database operations for the grading system"""
    
    def __init__(self):
        """Initialize database connection"""
        try:
            self.db = GradingDatabase()
            print("[DB] Database initialized successfully")
        except Exception as e:
            print(f"[DB] Warning: Could not initialize database: {e}")
            self.db = None
    
    def is_connected(self):
        """Check if database is connected"""
        return self.db is not None
    
    # ============================================
    # GRADED SHEET OPERATIONS (FIXED)
    # ============================================
    
    def save_graded_sheet(self, exam_id, student_id, exam_name, filled_sheet_path,
                         total_mcq_questions, total_written_questions,
                         mcq_correct_count, mcq_wrong_count, mcq_blank_count,
                         written_correct_count, written_wrong_count, written_blank_count,
                         score, max_score, key_id=None, threshold=50):
        """
        Save a graded sheet to the database (FIXED VERSION)
        
        Args:
            exam_id: Exam ID (NEW SCHEMA: this is required)
            student_id: Student identifier
            exam_name: Name of the exam
            filled_sheet_path: Path to the filled answer sheet image
            total_mcq_questions: Total number of MCQ questions
            total_written_questions: Total number of written questions
            mcq_correct_count: Number of correct MCQ answers
            mcq_wrong_count: Number of incorrect MCQ answers
            mcq_blank_count: Number of blank MCQ answers
            written_correct_count: Number of correct written answers
            written_wrong_count: Number of incorrect written answers
            written_blank_count: Number of blank written answers
            score: Actual score achieved
            max_score: Maximum possible score for this exam
            key_id: Answer key ID (optional in new schema, but should be provided)
            threshold: Threshold used for detection
            
        Returns:
            graded_sheet_id if successful, None otherwise
        """
        if not self.db:
            return None
        
        try:
            # Calculate percentage
            percentage = (score / max_score * 100) if max_score > 0 else 0
            
            # Insert graded sheet - CORRECTED for new schema with key_id
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO graded_sheets 
                (exam_id, student_id, key_id, exam_name, filled_sheet_path,
                 total_mcq_questions, total_written_questions,
                 mcq_correct_count, mcq_wrong_count, mcq_blank_count,
                 written_correct_count, written_wrong_count, written_blank_count,
                 score, max_score, percentage, threshold_used, graded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (exam_id, student_id, key_id, exam_name, filled_sheet_path,
                  total_mcq_questions, total_written_questions,
                  mcq_correct_count, mcq_wrong_count, mcq_blank_count,
                  written_correct_count, written_wrong_count, written_blank_count,
                  score, max_score, percentage, threshold))
            
            graded_sheet_id = cursor.lastrowid
            self.db.conn.commit()
            
            print(f"[DB] Graded sheet saved: ID={graded_sheet_id}, Exam={exam_id}, Student={student_id}")
            return graded_sheet_id
        except Exception as e:
            print(f"[DB] Error saving graded sheet: {e}")
            import traceback
            traceback.print_exc()
            self.db.conn.rollback()
            return None
    
    def save_question_result(self, graded_sheet_id, question_number, question_type,
                            student_answer, correct_answer, is_correct, points=1.0,
                            digit_details=None):
        """
        Save a question result
        
        Args:
            graded_sheet_id: FK to graded_sheets table
            question_number: Question number
            question_type: 'mcq' or 'written'
            student_answer: Student's answer
            correct_answer: Correct answer
            is_correct: Boolean indicating if answer is correct
            points: Points for this question (default 1.0)
            digit_details: OCR metadata for written answers (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
        
        try:
            # Convert NumPy types to native Python types before JSON serialization
            if digit_details is not None:
                digit_details = _native(digit_details)
            
            digit_details_json = json.dumps(digit_details, ensure_ascii=False) if digit_details else None
            
            self.db.conn.execute(
                """INSERT INTO question_results 
                   (graded_sheet_id, question_number, question_type,
                    student_answer, correct_answer, is_correct, points, digit_details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (graded_sheet_id, question_number, question_type,
                 student_answer, correct_answer, is_correct, points, digit_details_json)
            )
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error saving question result: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================
    # STUDENT OPERATIONS (ADD MISSING METHODS)
    # ============================================
    
    def save_student(self, student_id):
        """
        Save or update student information
        
        Args:
            student_id: Student identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
        
        try:
            # Insert or ignore (student_id is unique)
            self.db.conn.execute(
                """INSERT OR IGNORE INTO students (student_id)
                   VALUES (?)""",
                (student_id,)
            )
            
            self.db.conn.commit()
            print(f"[DB] Student saved/updated: {student_id}")
            return True
        except Exception as e:
            print(f"[DB] Error saving student: {e}")
            return False
    
    def get_student(self, student_id):
        """Get student by ID"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM students WHERE student_id = ?", (student_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting student: {e}")
            return None
    
    def get_student_by_id(self, student_id):
        """Alias for get_student for compatibility"""
        return self.get_student(student_id)
    
    def _update_student_stats(self, student_id):
        """
        Update student statistics after grading
        This is handled by database triggers, but we can also call it explicitly
        """
        if not self.db:
            return
        
        try:
            # The triggers in schema.sql handle this automatically
            # But we can force a recalculation if needed
            self.db.conn.execute(
                """UPDATE students SET updated_at = CURRENT_TIMESTAMP 
                   WHERE student_id = ?""",
                (student_id,)
            )
            self.db.conn.commit()
        except Exception as e:
            print(f"[DB] Error updating student stats: {e}")

    # ============================================
    # SHEET OPERATIONS
    # ============================================
    
    def save_sheet(self, file_path, name, notes=None):
        """
        Save a blank template sheet to database
        
        Args:
            file_path: Path to the PDF file
            name: Descriptive name for the sheet
            notes: Optional notes
            
        Returns:
            sheet_id if successful, None otherwise
        """
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                """INSERT INTO sheets (file_path, name, notes)
                   VALUES (?, ?, ?)""",
                (file_path, name, notes)
            )
            self.db.conn.commit()
            sheet_id = cursor.lastrowid
            print(f"[DB] Sheet saved: {name} (ID: {sheet_id})")
            return sheet_id
        except Exception as e:
            print(f"[DB] Error saving sheet: {e}")
            return None
    
    def get_sheet_by_id(self, sheet_id):
        """Get sheet by ID"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM sheets WHERE id = ?", (sheet_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting sheet: {e}")
            return None
    
    def get_sheet_by_path(self, file_path):
        """Get sheet by file path"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM sheets WHERE file_path = ?", (file_path,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting sheet: {e}")
            return None
    
    # ============================================
    # TEMPLATE OPERATIONS
    # ============================================
    
    def save_template(self, sheet_id, name, json_path, template_data, 
                     multiple_choice_questions=0, written_answer_questions=0, 
                     has_student_id=True):
        """
        Save a template extracted from a sheet
        
        Args:
            sheet_id: FK to sheets table
            name: Template name
            json_path: Path to template JSON file
            template_data: Full template JSON as dict
            multiple_choice_questions: Number of MCQ questions
            written_answer_questions: Number of written questions
            has_student_id: Whether template has student ID field
            
        Returns:
            template_id if successful, None otherwise
        """
        if not self.db:
            return None
        
        try:
            template_info_json = json.dumps(template_data, ensure_ascii=False)
            
            cursor = self.db.conn.execute(
                """INSERT INTO templates 
                   (sheet_id, name, json_path, template_info, 
                    multiple_choice_questions, written_answer_questions, has_student_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sheet_id, name, json_path, template_info_json,
                 multiple_choice_questions, written_answer_questions, has_student_id)
            )
            self.db.conn.commit()
            template_id = cursor.lastrowid
            print(f"[DB] Template saved: {name} (ID: {template_id})")
            return template_id
        except Exception as e:
            print(f"[DB] Error saving template: {e}")
            return None
    
    def get_template_by_id(self, template_id):
        """Get template by ID"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM templates WHERE id = ?", (template_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['template_data'] = json.loads(result['template_info'])
                return result
            return None
        except Exception as e:
            print(f"[DB] Error getting template: {e}")
            return None
    
    def get_template_by_json_path(self, json_path):
        """Get template by JSON file path"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM templates WHERE json_path = ?", (json_path,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['template_data'] = json.loads(result['template_info'])
                return result
            return None
        except Exception as e:
            print(f"[DB] Error getting template: {e}")
            return None
    
    def list_templates(self):
        """List all templates"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.conn.execute(
                """SELECT id, name, multiple_choice_questions, written_answer_questions, 
                          created_at 
                   FROM templates ORDER BY created_at DESC"""
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB] Error listing templates: {e}")
            return []
    
    # ============================================
    # EXAM OPERATIONS (NEW)
    # ============================================
    
    def save_exam(self, name, description=None, max_score=100.0):
        """
        Save an exam record
        
        Args:
            name: Exam name
            description: Optional description
            max_score: Total possible points for this exam
            
        Returns:
            exam_id if successful, None otherwise
        """
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                """INSERT INTO exams (name, description, max_score)
                   VALUES (?, ?, ?)""",
                (name, description, max_score)
            )
            self.db.conn.commit()
            exam_id = cursor.lastrowid
            print(f"[DB] Exam saved: {name} (ID: {exam_id}, Max Score: {max_score})")
            return exam_id
        except Exception as e:
            print(f"[DB] Error saving exam: {e}")
            return None
    
    def get_exam_by_id(self, exam_id):
        """Get exam by ID"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM exams WHERE id = ?", (exam_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting exam: {e}")
            return None
    
    def get_exam_by_name(self, name):
        """Get exam by name"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM exams WHERE name = ?", (name,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting exam: {e}")
            return None
    
    # ============================================
    # ANSWER KEY OPERATIONS
    # ============================================
    
    def save_answer_key(self, template_id, exam_id, name, label, json_path, key_data, created_by='manual'):
        """
        Unified method to save an answer key to the database
        """
        if not self.db:
            return None
        
        try:
            # Convert key_data to JSON string
            key_info_json = json.dumps(key_data, ensure_ascii=False)
            
            cursor = self.db.conn.execute(
                """INSERT INTO answer_keys 
                   (template_id, exam_id, name, label, json_path, key_info, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (template_id, exam_id, name, label, json_path, key_info_json, created_by)
            )
            self.db.conn.commit()
            key_id = cursor.lastrowid
            print(f"[DB] Answer key saved: {name} (ID: {key_id}, created_by: {created_by})")
            return key_id
        except Exception as e:
            print(f"[DB] Error saving answer key: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_answer_key_by_exam_and_label(self, exam_id, label):
        """
        Get answer key by exam ID and label (A-E)
        """
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                """SELECT * FROM answer_keys 
                   WHERE exam_id = ? AND label = ?""",
                (exam_id, label)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['key_data'] = json.loads(result['key_info'])
                return result
            return None
        except Exception as e:
            print(f"[DB] Error getting answer key by exam and label: {e}")
            return None
    
    def get_answer_key_by_json_path(self, json_path):
        """Get answer key by JSON file path"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM answer_keys WHERE json_path = ?", (json_path,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['key_data'] = json.loads(result['key_info'])
                return result
            return None
        except Exception as e:
            print(f"[DB] Error getting answer key: {e}")
            return None

    # ============================================
    # QUERY OPERATIONS
    # ============================================
    
    def get_student_performance(self, student_id):
        """Get performance summary for a student"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM student_performance WHERE student_id = ?",
                (student_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting student performance: {e}")
            return None
    
    def get_exam_summary(self):
        """Get summary for all exams"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM exam_summary ORDER BY exam_name"
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB] Error getting exam summary: {e}")
            return []
    
    def get_recent_grades(self, limit=50):
        """Get recent grading results"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.conn.execute(
                f"""SELECT gs.id, gs.student_id, gs.exam_name, gs.graded_at,
                           gs.score, gs.max_score, gs.percentage,
                           (gs.total_mcq_questions + gs.total_written_questions) as total_questions,
                           ak.label as key_label, e.name as exam_name_full
                    FROM graded_sheets gs
                    JOIN answer_keys ak ON gs.key_id = ak.id
                    JOIN exams e ON ak.exam_id = e.id
                    ORDER BY gs.graded_at DESC
                    LIMIT {limit}"""
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB] Error getting recent grades: {e}")
            return []


# Singleton instance
_db_ops = None

def get_db_operations():
    """Get singleton instance of DatabaseOperations"""
    global _db_ops
    if _db_ops is None:
        _db_ops = DatabaseOperations()
    return _db_ops