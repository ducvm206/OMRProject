"""
Database Initialization Script (updated)
Creates and initializes the grading system database with the new schema.
This version matches the updated schema where MCQ/written counts are determined
during answer key creation based on max total points for each part.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def get_schema_path():
    """Get path to schema.sql file"""
    schema_path = os.path.join(PROJECT_ROOT, 'database', 'schema.sql')
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return schema_path


def get_db_path():
    """Get path to database file"""
    return os.path.join(PROJECT_ROOT, 'grading_system.db')


def backup_existing_database():
    """Backup existing database if it exists"""
    db_path = get_db_path()
    
    if os.path.exists(db_path):
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = db_path.replace('.db', f'_backup_{timestamp}.db')
        
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"[BACKUP] Existing database backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"[WARNING] Failed to backup database: {e}")
            return None
    
    return None


def create_database(force_recreate=False):
    """
    Create and initialize the database
    
    Args:
        force_recreate: If True, drop existing tables and recreate
        
    Returns:
        True if successful, False otherwise
    """
    db_path = get_db_path()
    schema_path = get_schema_path()
    
    # Check if database exists
    db_exists = os.path.exists(db_path)
    
    if db_exists and force_recreate:
        print(f"[INFO] Database exists. Force recreate enabled.")
        backup_existing_database()
        os.remove(db_path)
        print(f"[INFO] Removed existing database")
        db_exists = False
    
    try:
        # Connect to database (creates if doesn't exist)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Read schema file
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Execute schema
        print(f"[INFO] Executing schema from: {schema_path}")
        cursor.executescript(schema_sql)
        conn.commit()
        
        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not db_exists:
            print(f"\n[SUCCESS] Database created successfully: {db_path}")
        else:
            print(f"\n[SUCCESS] Database schema updated: {db_path}")
        
        print(f"\nTables created:")
        for table in tables:
            if not table.startswith('sqlite_'):
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                except sqlite3.Error:
                    count = 'n/a'
                print(f"  - {table:20s} ({count} records)")
        
        # Verify views
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view' 
            ORDER BY name
        """)
        
        views = [row[0] for row in cursor.fetchall()]
        
        if views:
            print(f"\nViews created:")
            for view in views:
                print(f"  - {view}")
        
        # Verify triggers
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='trigger' 
            ORDER BY name
        """)
        
        triggers = [row[0] for row in cursor.fetchall()]
        
        if triggers:
            print(f"\nTriggers created:")
            for trigger in triggers:
                print(f"  - {trigger}")
        
        # Verify indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        indexes = [row[0] for row in cursor.fetchall()]
        
        if indexes:
            print(f"\nIndexes created:")
            for index in indexes:
                print(f"  - {index}")
        
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_database_integrity():
    """Verify database integrity and foreign key constraints"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database does not exist: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            print(f"\n[VERIFY] Database integrity: OK")
        else:
            print(f"\n[WARNING] Database integrity check: {result}")
        
        # Check foreign key constraints
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        
        if not fk_errors:
            print(f"[VERIFY] Foreign key constraints: OK")
        else:
            print(f"[WARNING] Foreign key constraint violations found:")
            for error in fk_errors:
                print(f"  {error}")
        
        conn.close()
        
        return result == "ok" and not fk_errors
        
    except sqlite3.Error as e:
        print(f"[ERROR] Verification failed: {e}")
        return False


def insert_sample_data():
    """Insert sample data for testing (updated for new schema)"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n[INFO] Inserting sample data...")
        
        # Sample sheet
        cursor.execute("""
            INSERT INTO sheets (file_path, name, notes)
            VALUES ('blank_sheets/sample_mixed.pdf', 'Sample Mixed Question Sheet', 
                    'Sample sheet with MCQ and written questions')
        """)
        sheet_id = cursor.lastrowid
        
        # Sample template (with template_info JSON)
        # NOTE: multiple_choice_questions and written_answer_questions are set to 0
        # They will be determined during answer key creation
        import json
        template_data = {
            'page_1': {
                'questions': [{'question_number': i, 'bubbles': []} for i in range(1, 51)],
                'student_id': {'digit_columns': []}
            }
        }
        
        cursor.execute("""
            INSERT INTO templates (sheet_id, name, json_path, template_info, 
                                   multiple_choice_questions, written_answer_questions, has_student_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sheet_id, 'Sample Template 50Q', 'template/sample_50q.json', 
              json.dumps(template_data), 0, 0, 1))
        template_id = cursor.lastrowid
        
        # Sample answer key with MCQ (Q1-40) and written (Q41-50)
        # User specified: MCQ max points = 40, Written max points = 10
        # This means 40 MCQ questions and 10 written questions
        key_data = {
            'metadata': {
                'exam_name': 'Sample Mixed Exam',
                'total_mcq_questions': 40,
                'mcq_max_points': 40
            },
            'answer_key': {str(i): ['A'] for i in range(1, 41)}
        }
        
        written_key_data = {
            'metadata': {
                'total_written_questions': 10,
                'written_max_points': 10
            },
            'answer_key': {str(i): 5 for i in range(41, 51)}  # Q41-50, each answer is 5
        }
        
        cursor.execute("""
            INSERT INTO answer_keys (template_id, name, json_path, key_info, written_key_info, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (template_id, 'Sample Answer Key (Mixed)', 'answer_keys/sample_mixed_key.json',
              json.dumps(key_data), json.dumps(written_key_data), 'manual'))
        key_id = cursor.lastrowid
        
        # Sample students
        students = [
            ('S001', 'John Doe', 'Class A'),
            ('S002', 'Jane Smith', 'Class A'),
            ('S003', 'Bob Johnson', 'Class B')
        ]
        
        for student_id, name, class_name in students:
            cursor.execute("""
                INSERT INTO students (student_id, name, class)
                VALUES (?, ?, ?)
            """, (student_id, name, class_name))
        
        # Sample graded sheets - updated structure:
        # The counts are determined from the answer key:
        # - total_mcq_questions = 40 (from key_data)
        # - total_written_questions = 10 (from written_key_data)
        graded_data = [
            # S001: 38/40 MCQ correct, 8/10 written correct
            (key_id, 'S001', 'Sample Mixed Exam', 'filled_sheets/s001.png', 
             40, 10, 38, 2, 0, 8, 2, 0, 50),
            # S002: 35/40 MCQ (4 wrong, 1 blank), 7/10 written (2 wrong, 1 blank)
            (key_id, 'S002', 'Sample Mixed Exam', 'filled_sheets/s002.png', 
             40, 10, 35, 4, 1, 7, 2, 1, 50),
            # S003: perfect score
            (key_id, 'S003', 'Sample Mixed Exam', 'filled_sheets/s003.png', 
             40, 10, 40, 0, 0, 10, 0, 0, 50)
        ]
        
        for data in graded_data:
            cursor.execute("""
                INSERT INTO graded_sheets (
                    key_id, student_id, exam_name, filled_sheet_path,
                    total_mcq_questions, total_written_questions,
                    mcq_correct_count, mcq_wrong_count, mcq_blank_count,
                    written_correct_count, written_wrong_count, written_blank_count,
                    threshold_used
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            graded_sheet_id = cursor.lastrowid
            
            # Add some question results (first 5 MCQ + first 3 written)
            mcq_correct = data[6]
            written_correct = data[9]
            
            # MCQ results (Q1-5)
            for q_num in range(1, 6):
                is_correct = 1 if q_num <= mcq_correct else 0
                cursor.execute("""
                    INSERT INTO question_results
                    (graded_sheet_id, question_number, question_type, student_answer, correct_answer, is_correct)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (graded_sheet_id, q_num, 'mcq', 'A', 'A', is_correct))
            
            # Written results (Q41-43)
            for q_num in range(41, 44):
                is_correct = 1 if (q_num - 40) <= written_correct else 0
                cursor.execute("""
                    INSERT INTO question_results
                    (graded_sheet_id, question_number, question_type, student_answer, correct_answer, is_correct)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (graded_sheet_id, q_num, 'written', '5', '5', is_correct))
        
        conn.commit()
        
        print(f"[SUCCESS] Sample data inserted:")
        print(f"  - 1 sheet")
        print(f"  - 1 template")
        print(f"  - 1 answer key (40 MCQ + 10 written)")
        print(f"  - {len(students)} students")
        print(f"  - {len(graded_data)} graded sheets")
        print(f"\n[NOTE] MCQ and written question counts are determined from answer key creation")
        print(f"        MCQ: 40 questions (max 40 points)")
        print(f"        Written: 10 questions (max 10 points)")
        
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to insert sample data: {e}")
        conn.rollback()
        conn.close()
        return False


def drop_all_tables():
    """Drop all tables (use with caution!)"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"[INFO] Database does not exist: {db_path}")
        return True
    
    try:
        # Backup first
        backup_existing_database()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Disable foreign keys temporarily
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get all views
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view'
        """)
        views = [row[0] for row in cursor.fetchall()]
        
        # Get all triggers
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='trigger'
        """)
        triggers = [row[0] for row in cursor.fetchall()]
        
        # Drop triggers
        for trigger in triggers:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
            print(f"[DROP] Trigger: {trigger}")
        
        # Drop views
        for view in views:
            cursor.execute(f"DROP VIEW IF EXISTS {view}")
            print(f"[DROP] View: {view}")
        
        # Drop tables
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"[DROP] Table: {table}")
        
        conn.commit()
        conn.close()
        
        print(f"\n[SUCCESS] All database objects dropped")
        
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to drop tables: {e}")
        return False


def main():
    """Main function to initialize database"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize grading system database')
    parser.add_argument('--force', action='store_true',
                       help='Force recreate database (drops existing tables)')
    parser.add_argument('--sample-data', action='store_true',
                       help='Insert sample data for testing')
    parser.add_argument('--verify', action='store_true',
                       help='Verify database integrity only')
    parser.add_argument('--drop', action='store_true',
                       help='Drop all tables (use with caution!)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("GRADING SYSTEM DATABASE INITIALIZATION")
    print("=" * 70)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Database Path: {get_db_path()}")
    print("=" * 70)
    
    if args.drop:
        print("\n[WARNING] This will drop all tables and data!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() == 'yes':
            if drop_all_tables():
                print("\n[INFO] Database objects dropped. Run without --drop to recreate.")
        else:
            print("[CANCELLED] No changes made.")
        return
    
    if args.verify:
        print("\nVerifying database...")
        if verify_database_integrity():
            print("\n[SUCCESS] Database verification passed")
        else:
            print("\n[ERROR] Database verification failed")
        return
    
    # Create/update database
    if create_database(force_recreate=args.force):
        # Verify integrity
        verify_database_integrity()
        
        # Insert sample data if requested
        if args.sample_data:
            insert_sample_data()
        
        print("\n" + "=" * 70)
        print("DATABASE INITIALIZATION COMPLETE")
        print("=" * 70)
        print(f"\nDatabase ready at: {get_db_path()}")
        print("\nYou can now:") 
        print("  1. Run the application: python app.py")
        print("  2. Create answer keys: python ui/key_ui.py")
        print("  3. Generate sheets: python ui/sheet_ui.py")
        print("  4. Grade sheets: python ui/grading_ui.py")
        print("\nFor help:")
        print("  python database/init_db.py --help")
        
    else:
        print("\n[ERROR] Database initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()