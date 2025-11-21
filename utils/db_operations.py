"""
Database operations utility module
Handles all database interactions for sheets, templates, answer keys, and grading
"""
import os
import sys
import json
import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import GradingDatabase


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
    
    def save_template(self, sheet_id, name, json_path, template_data, total_questions, has_student_id=True):
        """
        Save a template extracted from a sheet
        
        Args:
            sheet_id: FK to sheets table
            name: Template name
            json_path: Path to template JSON file
            template_data: Full template JSON as dict
            total_questions: Number of questions
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
                   (sheet_id, name, json_path, template_info, total_questions, has_student_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sheet_id, name, json_path, template_info_json, total_questions, has_student_id)
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
                # Parse template_info JSON
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
                "SELECT id, name, total_questions, created_at FROM templates ORDER BY created_at DESC"
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB] Error listing templates: {e}")
            return []
    
    # ============================================
    # ANSWER KEY OPERATIONS
    # ============================================
    
    def save_answer_key(self, template_id, name, json_path, key_data, created_by='manual'):
        """
        Save an answer key linked to a template
        
        Args:
            template_id: FK to templates table
            name: Answer key name
            json_path: Path to answer key JSON file
            key_data: Full answer key JSON as dict
            created_by: 'manual' or 'scan'
            
        Returns:
            key_id if successful, None otherwise
        """
        if not self.db:
            return None
        
        try:
            key_info_json = json.dumps(key_data, ensure_ascii=False)
            
            cursor = self.db.conn.execute(
                """INSERT INTO answer_keys 
                   (template_id, name, json_path, key_info, created_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (template_id, name, json_path, key_info_json, created_by)
            )
            self.db.conn.commit()
            key_id = cursor.lastrowid
            print(f"[DB] Answer key saved: {name} (ID: {key_id})")
            return key_id
        except Exception as e:
            print(f"[DB] Error saving answer key: {e}")
            return None
    
    def get_answer_key_by_id(self, key_id):
        """Get answer key by ID"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM answer_keys WHERE id = ?", (key_id,)
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
    
    def list_answer_keys(self, template_id=None):
        """List answer keys, optionally filtered by template"""
        if not self.db:
            return []
        
        try:
            if template_id:
                cursor = self.db.conn.execute(
                    """SELECT id, name, created_at, created_by 
                       FROM answer_keys 
                       WHERE template_id = ? 
                       ORDER BY created_at DESC""",
                    (template_id,)
                )
            else:
                cursor = self.db.conn.execute(
                    "SELECT id, name, created_at, created_by FROM answer_keys ORDER BY created_at DESC"
                )
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB] Error listing answer keys: {e}")
            return []
    
    # ============================================
    # STUDENT OPERATIONS
    # ============================================
    
    def save_student(self, student_id, name=None, class_name=None):
        """
        Save or update student information
        
        Args:
            student_id: Student identifier
            name: Student name (optional)
            class_name: Student class (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
        
        try:
            # Insert or ignore (student_id is unique)
            self.db.conn.execute(
                """INSERT OR IGNORE INTO students (student_id, name, class)
                   VALUES (?, ?, ?)""",
                (student_id, name, class_name)
            )
            
            # Update if name or class provided
            if name or class_name:
                updates = []
                params = []
                if name:
                    updates.append("name = ?")
                    params.append(name)
                if class_name:
                    updates.append("class = ?")
                    params.append(class_name)
                
                if updates:
                    params.append(student_id)
                    self.db.conn.execute(
                        f"UPDATE students SET {', '.join(updates)} WHERE student_id = ?",
                        params
                    )
            
            self.db.conn.commit()
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
    
    # ============================================
    # GRADED SHEET OPERATIONS
    # ============================================
    
    def save_graded_sheet(self, key_id, student_id, exam_name, filled_sheet_path,
                         score, total_questions, percentage, correct, wrong, blank, threshold):
        """
        Save a graded sheet result
        
        Args:
            key_id: FK to answer_keys table
            student_id: Student identifier
            exam_name: Name of the exam
            filled_sheet_path: Path to filled/scanned sheet
            score: Total score
            total_questions: Total number of questions
            percentage: Percentage score
            correct: Number of correct answers
            wrong: Number of wrong answers
            blank: Number of blank answers
            threshold: Detection threshold used
            
        Returns:
            graded_sheet_id if successful, None otherwise
        """
        if not self.db:
            return None
        
        try:
            # Ensure student exists
            self.save_student(student_id)
            
            cursor = self.db.conn.execute(
                """INSERT INTO graded_sheets 
                   (key_id, student_id, exam_name, filled_sheet_path, score, 
                    total_questions, percentage, correct_count, wrong_count, 
                    blank_count, threshold_used)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (key_id, student_id, exam_name, filled_sheet_path, score,
                 total_questions, percentage, correct, wrong, blank, threshold)
            )
            self.db.conn.commit()
            graded_sheet_id = cursor.lastrowid
            print(f"[DB] Graded sheet saved (ID: {graded_sheet_id})")
            return graded_sheet_id
        except Exception as e:
            print(f"[DB] Error saving graded sheet: {e}")
            return None
    
    def save_question_result(self, graded_sheet_id, question_number, 
                            student_answer, correct_answer, is_correct, points=1.0):
        """
        Save a question result
        
        Args:
            graded_sheet_id: FK to graded_sheets table
            question_number: Question number
            student_answer: Student's answer (e.g., "A,C")
            correct_answer: Correct answer (e.g., "A,C")
            is_correct: Boolean indicating if answer is correct
            points: Points for this question (default 1.0)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
        
        try:
            self.db.conn.execute(
                """INSERT INTO question_results 
                   (graded_sheet_id, question_number, student_answer, correct_answer, 
                    is_correct, points)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (graded_sheet_id, question_number, student_answer, correct_answer,
                 is_correct, points)
            )
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error saving question result: {e}")
            return False
    
    def save_batch_question_results(self, graded_sheet_id, question_results):
        """
        Save multiple question results at once
        
        Args:
            graded_sheet_id: FK to graded_sheets table
            question_results: List of tuples (q_num, student_ans, correct_ans, is_correct, points)
            
        Returns:
            Number of results saved
        """
        if not self.db:
            return 0
        
        count = 0
        try:
            for result in question_results:
                q_num, student_ans, correct_ans, is_correct, points = result
                if self.save_question_result(graded_sheet_id, q_num, student_ans, 
                                           correct_ans, is_correct, points):
                    count += 1
            return count
        except Exception as e:
            print(f"[DB] Error saving batch question results: {e}")
            return count
    
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
    
    def get_exam_summary(self, exam_name):
        """Get summary for an exam"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.conn.execute(
                "SELECT * FROM exam_summary WHERE exam_name = ?",
                (exam_name,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB] Error getting exam summary: {e}")
            return None
    
    def get_recent_grades(self, limit=50):
        """Get recent grading results"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.conn.execute(
                f"SELECT * FROM recent_grades LIMIT {limit}"
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