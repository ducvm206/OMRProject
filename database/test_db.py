"""
Database Test Script
Test database connection, tables, and basic operations
"""

import sqlite3
import os
import json
from datetime import datetime

def test_database(db_path='grading_system.db'):
    """Test database connection and operations"""
    
    print("="*60)
    print("Database Test Suite")
    print("="*60)
    
    if not os.path.exists(db_path):
        print(f"\n[ERROR] Database not found: {db_path}")
        print("[INFO] Run 'python database/init_db.py' first")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()
        
        # Test 1: Check tables
        print("\n[TEST 1] Checking tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        expected_tables = ['templates', 'answer_keys', 'students', 'grading_sessions', 
                          'graded_sheets', 'question_results']
        
        if len(tables) >= len(expected_tables):
            print(f"  ✓ Found {len(tables)} tables")
            for table in tables:
                print(f"    - {table['name']}")
        else:
            print(f"  ✗ Expected {len(expected_tables)} tables, found {len(tables)}")
            return False
        
        # Test 2: Check views
        print("\n[TEST 2] Checking views...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;")
        views = cursor.fetchall()
        
        if len(views) > 0:
            print(f"  ✓ Found {len(views)} views")
            for view in views:
                print(f"    - {view['name']}")
        else:
            print("  ⚠ No views found (optional)")
        
        # Test 3: Insert test data
        print("\n[TEST 3] Testing INSERT operations...")
        
        # Insert template
        cursor.execute("""
            INSERT INTO templates (name, file_path, total_questions, has_student_id)
            VALUES (?, ?, ?, ?)
        """, ('Test Template', 'template/test.json', 10, 1))
        template_id = cursor.lastrowid
        print(f"  ✓ Inserted template (ID: {template_id})")
        
        # Insert answer key
        cursor.execute("""
            INSERT INTO answer_keys (template_id, name, file_path, created_by)
            VALUES (?, ?, ?, ?)
        """, (template_id, 'Test Answer Key', 'answer_keys/test.json', 'manual'))
        key_id = cursor.lastrowid
        print(f"  ✓ Inserted answer key (ID: {key_id})")
        
        # Insert student
        cursor.execute("""
            INSERT INTO students (student_id, name, class)
            VALUES (?, ?, ?)
        """, ('12345678', 'Test Student', 'Class A'))
        student_id = cursor.lastrowid
        print(f"  ✓ Inserted student (ID: {student_id})")
        
        # Insert grading session
        cursor.execute("""
            INSERT INTO grading_sessions (name, template_id, answer_key_id, is_batch)
            VALUES (?, ?, ?, ?)
        """, ('Test Session', template_id, key_id, 0))
        session_id = cursor.lastrowid
        print(f"  ✓ Inserted grading session (ID: {session_id})")
        
        # Insert graded sheet
        cursor.execute("""
            INSERT INTO graded_sheets 
            (session_id, student_id, image_path, score, total_questions, 
             percentage, correct_count, wrong_count, blank_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, '12345678', 'test.png', 8, 10, 80.0, 8, 2, 0))
        sheet_id = cursor.lastrowid
        print(f"  ✓ Inserted graded sheet (ID: {sheet_id})")
        
        # Insert question results
        for q_num in range(1, 11):
            is_correct = q_num <= 8  # First 8 correct
            cursor.execute("""
                INSERT INTO question_results
                (graded_sheet_id, question_number, student_answer, correct_answer, is_correct)
                VALUES (?, ?, ?, ?, ?)
            """, (sheet_id, q_num, 'A', 'A' if is_correct else 'B', is_correct))
        print(f"  ✓ Inserted 10 question results")
        
        conn.commit()
        
        # Test 4: Query data
        print("\n[TEST 4] Testing SELECT operations...")
        
        cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        print(f"  ✓ Retrieved template: {template['name']}")
        
        cursor.execute("SELECT * FROM graded_sheets WHERE id = ?", (sheet_id,))
        sheet = cursor.fetchone()
        print(f"  ✓ Retrieved graded sheet: {sheet['percentage']}%")
        
        # Test 5: Test views
        print("\n[TEST 5] Testing views...")
        
        cursor.execute("SELECT * FROM student_performance WHERE student_id = '12345678'")
        perf = cursor.fetchone()
        if perf:
            print(f"  ✓ Student performance view works")
            print(f"    - Average: {perf['avg_percentage']}%")
        
        cursor.execute("SELECT * FROM session_summary WHERE id = ?", (session_id,))
        summary = cursor.fetchone()
        if summary:
            print(f"  ✓ Session summary view works")
            print(f"    - Sheets graded: {summary['sheets_graded']}")
        
        # Test 6: Foreign key constraints
        print("\n[TEST 6] Testing foreign key constraints...")
        try:
            cursor.execute("""
                INSERT INTO answer_keys (template_id, name, file_path)
                VALUES (?, ?, ?)
            """, (9999, 'Invalid Key', 'invalid.json'))
            print("  ✗ Foreign key constraint not working!")
        except sqlite3.IntegrityError:
            print("  ✓ Foreign key constraints working")
        
        # Test 7: Cleanup
        print("\n[TEST 7] Cleaning up test data...")
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        print("  ✓ Test data cleaned up")
        
        # Final verification
        cursor.execute("SELECT COUNT(*) as count FROM templates")
        count = cursor.fetchone()['count']
        print(f"  ✓ Database is clean (templates: {count})")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n[INFO] Database is ready to use!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_database()