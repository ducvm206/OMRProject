import sqlite3
import os
import json
import datetime
from typing import Optional, Dict, List, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def to_relative_path(absolute_path):
    """Convert absolute path to relative path from project root"""
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        # If paths are on different drives (Windows), return absolute path
        return absolute_path

class GradingDatabase:
    """Database manager for the grading system - UPDATED FOR CORRECTED SCHEMA"""
    
    def __init__(self, db_path: str = "grading_system.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        self.connect()
        
        # Check if database is initialized
        if not self._is_initialized():
            print("[DB] Warning: Database not initialized. Run 'python database/init_db.py' first")
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            print(f"[DB] Connected to database: {self.db_path}")
        except Exception as e:
            print(f"[DB] Error connecting to database: {e}")
            raise
    
    def _is_initialized(self) -> bool:
        """Check if database has been properly initialized"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sheets'")
            return cursor.fetchone() is not None
        except:
            return False

    # ============================================
    # SHEET MANAGEMENT (NEW BASE ENTITY)
    # ============================================
    
    def save_sheet(self, image_path: str, template_id: Optional[int] = None, 
                   num_questions: Optional[int] = None, settings: Optional[Dict] = None) -> Optional[int]:
        """Save a sheet (base entity) - sheets are created first, templates are extracted from them"""
        try:
            cursor = self.conn.cursor()
            
            # Check if this is a template sheet
            is_template = template_id is not None
            
            notes = f"Generated sheet with {num_questions} questions" if num_questions else None
            if settings:
                notes += f" | Settings: {json.dumps(settings)}"
            
            cursor.execute("""
                INSERT INTO sheets (image_path, is_template, notes)
                VALUES (?, ?, ?)
            """, (image_path, is_template, notes))
            
            self.conn.commit()
            sheet_id = cursor.lastrowid
            print(f"[DB] Saved sheet: {image_path} (ID: {sheet_id})")
            return sheet_id
            
        except Exception as e:
            print(f"[DB] Error saving sheet: {e}")
            return None
    
    def update_sheet(self, sheet_id: int, updates: Dict) -> bool:
        """Update sheet information"""
        try:
            cursor = self.conn.cursor()
            
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())
            values.append(sheet_id)
            
            cursor.execute(f"UPDATE sheets SET {set_clause} WHERE id = ?", values)
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"[DB] Error updating sheet: {e}")
            return False

    # ============================================
    # TEMPLATE MANAGEMENT (REFERENCES SHEETS)
    # ============================================
    
    def save_template(self, name: str, json_path: str, sheet_id: int, 
                     total_questions: int, has_student_id: bool = True,
                     metadata: Optional[Dict] = None) -> Optional[int]:
        """Save a template extracted from a sheet"""
        try:
            cursor = self.conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO templates (sheet_id, name, json_path, total_questions, has_student_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sheet_id, name, json_path, total_questions, has_student_id, metadata_json))
            
            self.conn.commit()
            template_id = cursor.lastrowid
            
            # Mark the source sheet as a template
            cursor.execute("UPDATE sheets SET is_template = 1 WHERE id = ?", (sheet_id,))
            self.conn.commit()
            
            print(f"[DB] Saved template: {name} (ID: {template_id}) from sheet {sheet_id}")
            return template_id
            
        except Exception as e:
            print(f"[DB] Error saving template: {e}")
            return None
    
    def get_template_by_json_path(self, json_path: str) -> Optional[Dict]:
        """Get template by JSON file path"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE json_path = ?", (json_path,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"[DB] Error getting template: {e}")
            return None

    # ============================================
    # ANSWER KEY MANAGEMENT
    # ============================================
    
    def save_answer_key(self, template_id: int, name: str, file_path: str, 
                       created_by: str = "manual") -> Optional[int]:
        """Save an answer key linked to a template"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO answer_keys (template_id, name, file_path, created_by)
                VALUES (?, ?, ?, ?)
            """, (template_id, name, file_path, created_by))
            
            self.conn.commit()
            key_id = cursor.lastrowid
            print(f"[DB] Saved answer key: {name} (ID: {key_id}) for template {template_id}")
            return key_id
            
        except Exception as e:
            print(f"[DB] Error saving answer key: {e}")
            return None
    
    def get_answer_key_by_file_path(self, file_path: str) -> Optional[Dict]:
        """Get answer key by file path"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM answer_keys WHERE file_path = ?", (file_path,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"[DB] Error getting answer key: {e}")
            return None

    # ============================================
    # STUDENT MANAGEMENT
    # ============================================
    
    def save_student(self, student_id: str, name: Optional[str] = None, 
                    class_name: Optional[str] = None) -> bool:
        """Save or update student information"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO students (student_id, name, class)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    name = excluded.name,
                    class = excluded.class
            """, (student_id, name, class_name))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"[DB] Error saving student: {e}")
            return False
        
    def get_student_by_id(self, student_id: str) -> Optional[Dict]:
        """Get student by student ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"[DB] Error getting student: {e}")
            return None

# Also, let me add a few other useful student methods that might be needed:

    def get_all_students(self) -> List[Dict]:
        """Get all students"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY student_id")
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[DB] Error getting students: {e}")
            return []

    def update_student(self, student_id: str, updates: Dict) -> bool:
        """Update student information"""
        try:
            cursor = self.conn.cursor()
            
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())
            values.append(student_id)
            
            cursor.execute(f"UPDATE students SET {set_clause} WHERE student_id = ?", values)
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"[DB] Error updating student: {e}")
            return False

    # ============================================
    # GRADING SESSION MANAGEMENT
    # ============================================
    
    def create_grading_session(self, name: str, template_id: int, answer_key_id: int,
                             is_batch: bool = False, total_sheets: int = 0) -> Optional[int]:
        """Create a new grading session"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO grading_sessions 
                (name, template_id, answer_key_id, is_batch, total_sheets)
                VALUES (?, ?, ?, ?, ?)
            """, (name, template_id, answer_key_id, is_batch, total_sheets))
            
            self.conn.commit()
            session_id = cursor.lastrowid
            print(f"[DB] Created grading session: {name} (ID: {session_id})")
            return session_id
            
        except Exception as e:
            print(f"[DB] Error creating grading session: {e}")
            return None

    # ============================================
    # GRADED SHEET MANAGEMENT
    # ============================================
    
    def save_graded_sheet(self, session_id: int, sheet_image_path: str, 
                         student_id: Optional[str] = None, score: int = 0,
                         total_questions: int = 0, percentage: float = 0.0,
                         correct_count: int = 0, wrong_count: int = 0, 
                         blank_count: int = 0, threshold_used: int = 50,
                         extraction_json: Optional[str] = None) -> Optional[int]:
        """Save a graded sheet result"""
        try:
            cursor = self.conn.cursor()
            
            # First, save the sheet image
            cursor.execute("""
                INSERT INTO sheets (image_path, is_template)
                VALUES (?, 0)
            """, (sheet_image_path,))
            sheet_id = cursor.lastrowid
            
            # Then save the graded sheet result
            cursor.execute("""
                INSERT INTO graded_sheets
                (session_id, sheet_id, student_id, score, total_questions, 
                 percentage, correct_count, wrong_count, blank_count, 
                 threshold_used, extraction_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, sheet_id, student_id, score, total_questions,
                  percentage, correct_count, wrong_count, blank_count, 
                  threshold_used, extraction_json))
            
            graded_sheet_id = cursor.lastrowid
            self.conn.commit()
            
            print(f"[DB] Saved graded sheet: {sheet_image_path} (ID: {graded_sheet_id})")
            return graded_sheet_id
            
        except Exception as e:
            print(f"[DB] Error saving graded sheet: {e}")
            return None
    
    def save_question_result(self, graded_sheet_id: int, question_number: int,
                           student_answer: str, correct_answer: str, 
                           is_correct: bool, points: float = 1.0) -> bool:
        """Save individual question result"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO question_results
                (graded_sheet_id, question_number, student_answer, 
                 correct_answer, is_correct, points)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (graded_sheet_id, question_number, student_answer, 
                  correct_answer, is_correct, points))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"[DB] Error saving question result: {e}")
            return False

    # ============================================
    # COMPATIBILITY METHODS (for existing code)
    # ============================================
    
    def log_sheet_generation(self, num_questions: int, output_path: str, 
                            settings: Optional[Dict] = None) -> Optional[int]:
        """Legacy method: Log sheet generation"""
        sheet_id = self.save_sheet(
            image_path=output_path,
            template_id=None,  # This is a template sheet
            num_questions=num_questions,
            settings=settings
        )
        return sheet_id
    
    def log_template_extraction(self, template_path: str, source_pdf: str = None,
                               num_questions: int = 0, extraction_method: str = "auto") -> Optional[int]:
        """Legacy method: Log template extraction"""
        # For legacy compatibility, we need to find the sheet first
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM sheets WHERE image_path = ?", (source_pdf,))
            sheet_result = cursor.fetchone()
            
            if not sheet_result:
                print(f"[DB] Source sheet not found: {source_pdf}")
                return None
            
            sheet_id = sheet_result['id']
            template_name = os.path.basename(template_path).replace('.json', '')
            
            return self.save_template(
                name=template_name,
                json_path=template_path,
                sheet_id=sheet_id,
                total_questions=num_questions,
                has_student_id=True,
                metadata={'extraction_method': extraction_method}
            )
        except Exception as e:
            print(f"[DB] Error in legacy template extraction: {e}")
            return None
    
    def log_answer_key_creation(self, key_path: str, template_path: str = None,
                               num_questions: int = 0, creation_method: str = "manual") -> Optional[int]:
        """Legacy method: Log answer key creation"""
        try:
            # Find template by JSON path
            template_info = self.get_template_by_json_path(template_path)
            if not template_info:
                print(f"[DB] Template not found: {template_path}")
                return None
            
            key_name = os.path.basename(key_path).replace('.json', '')
            
            return self.save_answer_key(
                template_id=template_info['id'],
                name=key_name,
                file_path=key_path,
                created_by=creation_method
            )
        except Exception as e:
            print(f"[DB] Error in legacy answer key creation: {e}")
            return None
    
    def log_grading_session(self, student_id: str, template_path: str, 
                          answer_key_path: str, scanned_sheet_path: str,
                          score: int, total_questions: int, percentage: float,
                          grading_mode: str = "single", threshold: int = 50,
                          batch_session_id: str = None, details: Dict = None) -> Optional[int]:
        """Legacy method: Log grading session"""
        try:
            # Find template and answer key
            template_info = self.get_template_by_json_path(template_path)
            answer_key_info = self.get_answer_key_by_file_path(answer_key_path)
            
            if not template_info or not answer_key_info:
                print(f"[DB] Template or answer key not found")
                return None
            
            # Create or use session
            if batch_session_id and batch_session_id.isdigit():
                session_id = int(batch_session_id)
            else:
                session_name = f"{grading_mode.capitalize()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                session_id = self.create_grading_session(
                    name=session_name,
                    template_id=template_info['id'],
                    answer_key_id=answer_key_info['id'],
                    is_batch=(grading_mode == 'batch'),
                    total_sheets=1
                )
            
            if not session_id:
                return None
            
            # Calculate counts
            wrong_count = total_questions - score
            blank_count = 0
            if details and 'details' in details:
                detail_list = details['details']
                if isinstance(detail_list, list):
                    for item in detail_list:
                        if isinstance(item, dict):
                            student_ans = item.get('student_answer') or item.get('student_answers')
                            if not student_ans or student_ans == [] or student_ans == '':
                                blank_count += 1
                wrong_count = total_questions - score - blank_count
            
            # Save graded sheet
            extraction_json = json.dumps(details) if details else None
            
            graded_sheet_id = self.save_graded_sheet(
                session_id=session_id,
                sheet_image_path=scanned_sheet_path,
                student_id=student_id,
                score=score,
                total_questions=total_questions,
                percentage=percentage,
                correct_count=score,
                wrong_count=wrong_count,
                blank_count=blank_count,
                threshold_used=threshold,
                extraction_json=extraction_json
            )
            
            # Save question results
            if graded_sheet_id and details and 'details' in details:
                self._insert_question_results(graded_sheet_id, details['details'])
            
            return graded_sheet_id
            
        except Exception as e:
            print(f"[DB] Error in legacy grading session: {e}")
            return None
    
    def _insert_question_results(self, sheet_id: int, details: Any):
        """Helper method for inserting question results"""
        try:
            if isinstance(details, list):
                for item in details:
                    if isinstance(item, dict):
                        q_num = item.get('question_number')
                        student_ans = item.get('student_answer') or item.get('student_answers', [])
                        correct_ans = item.get('correct_answer') or item.get('correct_answers', [])
                        is_correct = item.get('is_correct', False)
                        
                        if isinstance(student_ans, list):
                            student_ans = ','.join(str(a) for a in student_ans)
                        if isinstance(correct_ans, list):
                            correct_ans = ','.join(str(a) for a in correct_ans)
                        
                        self.save_question_result(
                            graded_sheet_id=sheet_id,
                            question_number=q_num,
                            student_answer=student_ans or '',
                            correct_answer=correct_ans,
                            is_correct=is_correct
                        )
            
        except Exception as e:
            print(f"[DB] Error inserting question results: {e}")

    # ============================================
    # QUERY METHODS (remain mostly the same)
    # ============================================
    
    def get_student_history(self, student_id: str) -> List[Dict]:
        """Get grading history for a student"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    gs.id, gs.session_id, gs.percentage, gs.score, 
                    gs.total_questions, gs.graded_at, gs.image_path,
                    sess.name as session_name
                FROM graded_sheets gs
                JOIN grading_sessions sess ON gs.session_id = sess.id
                WHERE gs.student_id = ?
                ORDER BY gs.graded_at DESC
            """, (student_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"[DB] Error fetching student history: {e}")
            return []
    
    # ... (other query methods remain the same as in original file)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[DB] Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Singleton instance
_db_instance = None

def get_database(db_path: str = "grading_system.db") -> GradingDatabase:
    """Get or create singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = GradingDatabase(db_path)
    return _db_instance

def insert_answer_key(self, key_data: Dict) -> Optional[int]:
    """Alternative method for inserting answer key - for compatibility"""
    try:
        return self.save_answer_key(
            template_id=key_data.get('template_id'),
            name=key_data.get('name', 'Unknown Key'),
            file_path=key_data.get('file_path'),
            created_by=key_data.get('created_by', 'manual')
        )
    except Exception as e:
        print(f"[DB] Error in insert_answer_key: {e}")
        return None
    
def create_batch_session(self, template_path: str, answer_key_path: str,
                       total_sheets: int) -> Optional[str]:
    """Create a new batch grading session - COMPATIBILITY METHOD"""
    try:
        # Convert paths to relative for database lookup
        template_relative = to_relative_path(template_path)
        key_relative = to_relative_path(answer_key_path)
        
        # Find template and answer key IDs
        template_info = self.get_template_by_json_path(template_relative)
        answer_key_info = self.get_answer_key_by_file_path(key_relative)
        
        if not template_info or not answer_key_info:
            print(f"[DB] Template or answer key not found for batch session")
            return None
        
        # Create session using existing method
        session_name = f"Batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.create_grading_session(
            name=session_name,
            template_id=template_info['id'],
            answer_key_id=answer_key_info['id'],
            is_batch=True,
            total_sheets=total_sheets
        )
        
        print(f"[DB] Created batch session: {session_name} (ID: {session_id})")
        return str(session_id) if session_id else None
        
    except Exception as e:
        print(f"[DB] Error creating batch session: {e}")
        return None

if __name__ == "__main__":
    print("Testing database connectivity...")
    
    try:
        with GradingDatabase("grading_system.db") as db:
            stats = db.get_statistics()
            print(f"\nDatabase Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print("\n✓ Database is ready!")
    except Exception as e:
        print(f"\n✗ Database error: {e}")
        print("\nRun 'python database/init_db.py' to initialize the database first.")