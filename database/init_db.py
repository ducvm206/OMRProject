"""
init_db.py - Initialize the grading system database

This script creates the SQLite database with all tables, indexes, and views
based on the schema.sql file.

Usage:
    python database/init_db.py
    
    Or from project root:
    python -m database.init_db
"""

import sqlite3
import os
import sys
import json

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "grading_system.db")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "database", "schema.sql")


def read_schema():
    """Read schema.sql file"""
    if not os.path.exists(SCHEMA_PATH):
        print(f"[ERROR] Schema file not found: {SCHEMA_PATH}")
        print("\nExpected location: database/schema.sql")
        sys.exit(1)
    
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    return schema_sql


def create_database(force_recreate=False):
    """
    Create database and execute schema
    
    Args:
        force_recreate: If True, delete existing database and recreate
    """
    print("="*70)
    print("GRADING SYSTEM DATABASE INITIALIZATION")
    print("="*70)
    
    # Check if database already exists
    db_exists = os.path.exists(DB_PATH)
    
    if db_exists and not force_recreate:
        print(f"\n[INFO] Database already exists: {DB_PATH}")
        response = input("\nDo you want to recreate it? This will DELETE all existing data! (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n[CANCELLED] Database initialization cancelled.")
            print("To view existing database, run: python database/query_db.py")
            return False
        
        force_recreate = True
    
    # Delete existing database if recreating
    if force_recreate and db_exists:
        print(f"\n[WARNING] Deleting existing database: {DB_PATH}")
        os.remove(DB_PATH)
        print("[SUCCESS] Existing database deleted")
    
    # Read schema
    print(f"\n[STEP 1] Reading schema from: {SCHEMA_PATH}")
    schema_sql = read_schema()
    print(f"[SUCCESS] Schema file loaded ({len(schema_sql)} characters)")
    
    # Create database connection
    print(f"\n[STEP 2] Creating database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    try:
        # Execute schema (split by semicolon for multiple statements)
        print("\n[STEP 3] Executing schema SQL...")
        
        # Split schema into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement.upper().startswith(('CREATE TABLE', 'CREATE VIEW', 'CREATE INDEX')):
                # Extract object name for logging
                if 'TABLE' in statement.upper():
                    obj_type = "Table"
                elif 'VIEW' in statement.upper():
                    obj_type = "View"
                else:
                    obj_type = "Index"
                
                # Execute statement
                cursor.execute(statement)
                
                # Parse name
                parts = statement.split()
                name_idx = parts.index('EXISTS') + 1 if 'EXISTS' in parts else 3
                if name_idx < len(parts):
                    obj_name = parts[name_idx].strip('(')
                    print(f" {obj_type} created: {obj_name}")
            else:
                # Execute other statements silently (PRAGMA, etc.)
                cursor.execute(statement)
        
        conn.commit()
        print(f"\n[SUCCESS] Schema executed successfully ({len(statements)} statements)")
        
    except sqlite3.Error as e:
        print(f"\n[ERROR] Database creation failed: {e}")
        conn.close()
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        return False
    
    # Verify database structure
    print("\n[STEP 4] Verifying database structure...")
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n  Tables created ({len(tables)}):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"    • {table} ({count} rows)")
    
    # Check views
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = [row[0] for row in cursor.fetchall()]
    print(f"\n  Views created ({len(views)}):")
    for view in views:
        print(f"    • {view}")
    
    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    indexes = [row[0] for row in cursor.fetchall()]
    print(f"\n  Indexes created ({len(indexes)}):")
    for index in indexes:
        print(f"    • {index}")
    
    conn.close()
    
    # Final summary
    print("\n" + "="*70)
    print("DATABASE INITIALIZATION COMPLETE")
    print("="*70)
    print(f"\nDatabase location: {DB_PATH}")
    print(f"Tables: {len(tables)}")
    print(f"Views: {len(views)}")
    print(f"Indexes: {len(indexes)}")
    
    print("\n✓  Database is ready to use!")
    print("\nNext steps:")
    print("  1. Run your grading application: python app.py")
    print("  2. View database contents: python database/query_db.py")
    print("  3. Backup database: copy grading_system.db to a safe location")
    
    return True


def insert_sample_data(conn):
    """Insert sample data for testing (optional)"""
    cursor = conn.cursor()
    
    print("\n[OPTIONAL] Inserting sample data...")
    
    try:
        # Create necessary directories for file paths
        sample_dirs = ['templates', 'answer_keys', 'sheets']
        for dir_name in sample_dirs:
            dir_path = os.path.join(PROJECT_ROOT, dir_name)
            os.makedirs(dir_path, exist_ok=True)
        
        # Sample sheet (this would be the physical/digital sheet first)
        cursor.execute("""
            INSERT INTO sheets (image_path, is_template, notes)
            VALUES ('sheets/sample_template_sheet.jpg', 1, 'Sample 40Q answer sheet used as template')
        """)
        sheet_id = cursor.lastrowid
        print("✓ Sample sheet inserted")
        
        # Sample template extracted from the sheet
        cursor.execute("""
            INSERT INTO templates (sheet_id, name, json_path, total_questions, has_student_id, metadata)
            VALUES (?, 'Sample 40Q Template', 'templates/sample_40q.json', 40, 1, ?)
        """, (sheet_id, json.dumps({"description": "Sample multiple choice template", "version": "1.0"})))
        template_id = cursor.lastrowid
        print("✓ Sample template inserted")
        
        # Sample answer key
        cursor.execute("""
            INSERT INTO answer_keys (template_id, name, file_path, created_by)
            VALUES (?, 'Sample Answer Key', 'answer_keys/sample_key.json', 'manual')
        """, (template_id,))
        answer_key_id = cursor.lastrowid
        print("✓ Sample answer key inserted")
        
        # Sample student
        cursor.execute("""
            INSERT INTO students (student_id, name, class)
            VALUES ('12345678', 'Test Student', 'Class A')
        """)
        print("✓ Sample student inserted")
        
        # Sample grading session
        cursor.execute("""
            INSERT INTO grading_sessions (name, template_id, answer_key_id, is_batch, total_sheets)
            VALUES (?, ?, ?, 1, 1)
        """, ('Sample Grading Session', template_id, answer_key_id))
        session_id = cursor.lastrowid
        print("✓ Sample grading session inserted")
        
        # Another sample sheet (graded sheet)
        cursor.execute("""
            INSERT INTO sheets (image_path, notes)
            VALUES ('sheets/sample_graded_sheet.jpg', 'Student answer sheet for grading')
        """)
        graded_sheet_id = cursor.lastrowid
        
        # Sample graded sheet result
        cursor.execute("""
            INSERT INTO graded_sheets (session_id, sheet_id, student_id, score, total_questions, 
                                     percentage, correct_count, wrong_count, blank_count, threshold_used)
            VALUES (?, ?, '12345678', 32, 40, 80.0, 32, 8, 0, 50)
        """, (session_id, graded_sheet_id))
        graded_sheet_id = cursor.lastrowid
        print("✓ Sample graded sheet inserted")
        
        # Sample question results
        sample_questions = [
            (1, "A", "A", 1, 1.0),
            (2, "B", "C", 0, 1.0),
            (3, "C", "C", 1, 1.0),
            (4, "", "D", 0, 1.0),  # Blank answer
        ]
        
        for q_num, student_ans, correct_ans, is_correct, points in sample_questions:
            cursor.execute("""
                INSERT INTO question_results (graded_sheet_id, question_number, student_answer, 
                                           correct_answer, is_correct, points)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (graded_sheet_id, q_num, student_ans, correct_ans, is_correct, points))
        print("✓ Sample question results inserted")
        
        conn.commit()
        print("\n[SUCCESS] Sample data inserted successfully!")
        
        # Display sample data summary
        print("\n" + "="*50)
        print("SAMPLE DATA SUMMARY")
        print("="*50)
        
        cursor.execute("SELECT COUNT(*) FROM sheets")
        print(f"Sheets: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM templates")
        print(f"Templates: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM students")
        print(f"Students: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM grading_sessions")
        print(f"Grading Sessions: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM graded_sheets")
        print(f"Graded Sheets: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM question_results")
        print(f"Question Results: {cursor.fetchone()[0]}")
        
        print("\nYou can now test the database with:")
        print("  python database/query_db.py")
        
    except sqlite3.Error as e:
        print(f"\n[ERROR] Failed to insert sample data: {e}")
        conn.rollback()
        raise


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Initialize the grading system database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python database/init_db.py              # Interactive mode
  python database/init_db.py --force      # Force recreate without prompt
  python database/init_db.py --sample     # Include sample data
        """
    )
    
    parser.add_argument('--force', '-f', action='store_true',
                      help='Force recreate database without prompt')
    parser.add_argument('--sample', '-s', action='store_true',
                      help='Insert sample data after creation')
    
    args = parser.parse_args()
    
    # Create database
    success = create_database(force_recreate=args.force)
    
    if not success:
        sys.exit(1)
    
    # Insert sample data if requested
    if args.sample:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            insert_sample_data(conn)
        except Exception as e:
            print(f"\n[ERROR] Sample data insertion failed: {e}")
            sys.exit(1)
        finally:
            conn.close()
    
    print("\nDatabase setup complete! ✓")


if __name__ == "__main__":
    main()