"""
Database Helper Module
Provides easy-to-use functions for database operations
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple

class GradingDatabase:
    """Database interface for grading system"""
    
    def __init__(self, db_path='grading_system.db'):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(
                f"Database not found: {db_path}\n"
                f"Run 'python database/init_db.py' first"
            )
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    
    # ==========================================
    # TEMPLATES
    # ==========================================
    
    def add_template(self, name: str, file_path: str, total_questions: int, 
                     has_student_id: bool = True, metadata: dict = None) -> int:
        """
        Add a new template
        
        Returns:
            template_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO templates (name, file_path, total_questions, has_student_id, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (name, file_path, total_questions, has_student_id, 
              json.dumps(metadata) if metadata else None))
        
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DB] Added template: {name} (ID: {template_id})")
        return template_id
    
    def get_templates(self) -> List[sqlite3.Row]:
        """Get all templates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates ORDER BY created_at DESC")
        templates = cursor.fetchall()
        conn.close()
        return templates
    
    def get_template_by_path(self, file_path: str) -> Optional[sqlite3.Row]:
        """Get template by file path"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates WHERE file_path = ?", (file_path,))
        template = cursor.fetchone()
        conn.close()
        return template
    
    # ==========================================
    # ANSWER KEYS
    # ==========================================
    
    def add_answer_key(self, template_id: int, name: str, file_path: str, 
                       created_by: str = 'manual') -> int:
        """
        Add a new answer key
        
        Returns:
            key_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO answer_keys (template_id, name, file_path, created_by)
            VALUES (?, ?, ?, ?)
        """, (template_id, name, file_path, created_by))
        
        key_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DB] Added answer key: {name} (ID: {key_id})")
        return key_id
    
    def get_answer_keys(self, template_id: Optional[int] = None) -> List[sqlite3.Row]:
        """Get answer keys, optionally filtered by template"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if template_id:
            cursor.execute("""
                SELECT * FROM answer_keys 
                WHERE template_id = ? 
                ORDER BY created_at DESC
            """, (template_id,))
        else:
            cursor.execute("SELECT * FROM answer_keys ORDER BY created_at DESC")
        
        keys = cursor.fetchall()
        conn.close()
        return keys
    
    def get_answer_key_by_path(self, file_path: str) -> Optional[sqlite3.Row]:
        """Get answer key by file path"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM answer_keys WHERE file_path = ?", (file_path,))
        key = cursor.fetchone()
        conn.close()
        return key
    
    # ==========================================
    # STUDENTS
    # ==========================================
    
    def add_or_update_student(self, student_id: str, name: str = None, 
                              class_name: str = None) -> int:
        """
        Add or update student information
        
        Returns:
            student database id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if student exists
        cursor.execute("SELECT id FROM students WHERE student_id = ?", (student_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update
            if name or class_name:
                cursor.execute("""
                    UPDATE students 
                    SET name = COALESCE(?, name), 
                        class = COALESCE(?, class)
                    WHERE student_id = ?
                """, (name, class_name, student_id))
                print(f"[DB] Updated student: {student_id}")
            db_id = existing['id']
        else:
            # Insert
            cursor.execute("""
                INSERT INTO students (student_id, name, class)
                VALUES (?, ?, ?)
            """, (student_id, name, class_name))
            db_id = cursor.lastrowid
            print(f"[DB] Added student: {student_id} (ID: {db_id})")
        
        conn.commit()
        conn.close()
        return db_id
    
    def get_student(self, student_id: str) -> Optional[sqlite3.Row]:
        """Get student by student_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        conn.close()
        return student
    
    # ==========================================
    # GRADING SESSIONS
    # ==========================================
    
    def create_session(self, name: str, template_id: int, answer_key_id: int, 
                      is_batch: bool = False) -> int:
        """
        Create a grading session
        
        Returns:
            session_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO grading_sessions (name, template_id, answer_key_id, is_batch)
            VALUES (?, ?, ?, ?)
        """, (name, template_id, answer_key_id, is_batch))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DB] Created session: {name} (ID: {session_id})")
        return session_id
    
    def get_sessions(self, limit: int = 50) -> List[sqlite3.Row]:
        """Get recent grading sessions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM session_summary 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        sessions = cursor.fetchall()
        conn.close()
        return sessions
    
    # ==========================================
    # GRADED SHEETS
    # ==========================================
    
    def save_grading_result(self, session_id: int, result: dict, 
                           threshold: int = 50) -> int:
        """
        Save complete grading result to database
        
        Args:
            session_id: Grading session ID
            result: Grading result dictionary containing:
                - image_path
                - student_id
                - grade_results
                - extraction_result
            threshold: Detection threshold used
        
        Returns:
            graded_sheet_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            grade_results = result.get('grade_results', {})
            
            # Extract values with fallbacks
            total_q = grade_results.get('total_questions', 0)
            correct = grade_results.get('correct', 0)
            wrong = grade_results.get('wrong', 0)
            blank = grade_results.get('blank', 0)
            percentage = grade_results.get('percentage', 0.0)
            
            # Handle summary structure
            if 'summary' in grade_results:
                summary = grade_results['summary']
                total_q = summary.get('total_questions', total_q)
                correct = summary.get('correct', correct)
                wrong = summary.get('wrong', wrong)
                blank = summary.get('blank', blank)
                percentage = summary.get('percentage', percentage)
            
            student_id = result.get('student_id', 'N/A')
            
            # Add/update student if valid ID
            if student_id and student_id != 'N/A':
                self.add_or_update_student(student_id)
            
            # Insert graded sheet
            cursor.execute("""
                INSERT INTO graded_sheets 
                (session_id, student_id, image_path, score, total_questions, 
                 percentage, correct_count, wrong_count, blank_count, 
                 threshold_used, extraction_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                student_id if student_id != 'N/A' else None,
                result.get('image_path', ''),
                correct,
                total_q,
                percentage,
                correct,
                wrong,
                blank,
                threshold,
                json.dumps(result.get('extraction_result', {}))
            ))
            
            sheet_id = cursor.lastrowid
            
            # Insert question results
            details = grade_results.get('details', {})
            if isinstance(details, dict):
                for q_num, detail in details.items():
                    # Check both 'is_correct' and 'status'
                    is_correct = detail.get('is_correct', False)
                    if not is_correct and 'status' in detail:
                        is_correct = detail.get('status') == 'correct'
                    
                    # Handle different field names
                    student_ans = detail.get('student_answer') or detail.get('student_answers', [])
                    correct_ans = detail.get('correct_answer') or detail.get('correct_answers', [])
                    
                    # Convert to strings
                    if isinstance(student_ans, list):
                        student_ans_str = ','.join(str(a) for a in student_ans)
                    else:
                        student_ans_str = str(student_ans) if student_ans else ''
                    
                    if isinstance(correct_ans, list):
                        correct_ans_str = ','.join(str(a) for a in correct_ans)
                    else:
                        correct_ans_str = str(correct_ans) if correct_ans else ''
                    
                    cursor.execute("""
                        INSERT INTO question_results
                        (graded_sheet_id, question_number, student_answer, 
                         correct_answer, is_correct, points)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        sheet_id,
                        int(q_num),
                        student_ans_str,
                        correct_ans_str,
                        1 if is_correct else 0,
                        detail.get('points', 1.0)
                    ))
            
            # Update session total_sheets count
            cursor.execute("""
                UPDATE grading_sessions 
                SET total_sheets = (
                    SELECT COUNT(*) FROM graded_sheets WHERE session_id = ?
                )
                WHERE id = ?
            """, (session_id, session_id))
            
            conn.commit()
            print(f"[DB] Saved grading result: Sheet ID {sheet_id}, Student {student_id}, Score {correct}/{total_q}")
            
            return sheet_id
            
        except Exception as e:
            conn.rollback()
            print(f"[DB ERROR] Failed to save grading result: {e}")
            raise
        finally:
            conn.close()
    
    def get_graded_sheets(self, session_id: Optional[int] = None, 
                         student_id: Optional[str] = None,
                         limit: int = 100) -> List[sqlite3.Row]:
        """Get graded sheets, optionally filtered"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM graded_sheets WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if student_id:
            query += " AND student_id = ?"
            params.append(student_id)
        
        query += " ORDER BY graded_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        sheets = cursor.fetchall()
        conn.close()
        return sheets
    
    # ==========================================
    # ANALYTICS & REPORTS
    # ==========================================
    
    def get_student_performance(self, student_id: str) -> Optional[sqlite3.Row]:
        """Get performance summary for a student"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM student_performance 
            WHERE student_id = ?
        """, (student_id,))
        perf = cursor.fetchone()
        conn.close()
        return perf
    
    def get_session_summary(self, session_id: int) -> Optional[sqlite3.Row]:
        """Get summary for a grading session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM session_summary 
            WHERE id = ?
        """, (session_id,))
        summary = cursor.fetchone()
        conn.close()
        return summary
    
    def get_question_difficulty(self, limit: int = 20) -> List[sqlite3.Row]:
        """Get hardest questions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM question_difficulty 
            ORDER BY success_rate ASC 
            LIMIT ?
        """, (limit,))
        questions = cursor.fetchall()
        conn.close()
        return questions
    
    def get_recent_grades(self, limit: int = 50) -> List[sqlite3.Row]:
        """Get recent grading results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM recent_grades 
            LIMIT ?
        """, (limit,))
        grades = cursor.fetchall()
        conn.close()
        return grades
    
    # ==========================================
    # UTILITY FUNCTIONS
    # ==========================================
    
    def get_or_create_template(self, file_path: str, **kwargs) -> int:
        """Get existing template or create new one"""
        template = self.get_template_by_path(file_path)
        if template:
            return template['id']
        return self.add_template(file_path=file_path, **kwargs)
    
    def get_or_create_answer_key(self, file_path: str, template_id: int, **kwargs) -> int:
        """Get existing answer key or create new one"""
        key = self.get_answer_key_by_path(file_path)
        if key:
            return key['id']
        return self.add_answer_key(template_id=template_id, file_path=file_path, **kwargs)
    
    def export_session_csv(self, session_id: int, output_path: str):
        """Export session results to CSV"""
        import csv
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                gs.student_id,
                gs.percentage,
                gs.correct_count,
                gs.wrong_count,
                gs.blank_count,
                gs.total_questions,
                gs.graded_at
            FROM graded_sheets gs
            WHERE gs.session_id = ?
            ORDER BY gs.student_id
        """, (session_id,))
        
        sheets = cursor.fetchall()
        conn.close()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Student ID', 'Percentage', 'Correct', 'Wrong', 
                           'Blank', 'Total', 'Graded At'])
            
            for sheet in sheets:
                writer.writerow([
                    sheet['student_id'],
                    sheet['percentage'],
                    sheet['correct_count'],
                    sheet['wrong_count'],
                    sheet['blank_count'],
                    sheet['total_questions'],
                    sheet['graded_at']
                ])
        
        print(f"[DB] Exported session to: {output_path}")


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_db(db_path='grading_system.db') -> GradingDatabase:
    """Get database instance"""
    return GradingDatabase(db_path)


# Example usage
if __name__ == "__main__":
    # Initialize database
    db = GradingDatabase()
    
    # Example: Add template
    template_id = db.add_template(
        name="10 Questions Test",
        file_path="template/answer_sheet_10_questions.json",
        total_questions=10
    )
    
    # Example: Add answer key
    key_id = db.add_answer_key(
        template_id=template_id,
        name="Test 1 Answer Key",
        file_path="answer_keys/test_key.json"
    )
    
    # Example: Create session
    session_id = db.create_session(
        name="Class A - Test 1",
        template_id=template_id,
        answer_key_id=key_id
    )
    
    print(f"\n[SUCCESS] Database operations completed!")
    print(f"Template ID: {template_id}")
    print(f"Answer Key ID: {key_id}")
    print(f"Session ID: {session_id}")