"""
query_db.py - Database query and inspection tool (Updated for new schema)

This script provides utilities to view and query the grading system database.
Updated for the new schema with exams table and unified key_info.

Usage:
    python database/query_db.py [command]
    
Commands:
    stats     - Show database statistics
    tables    - List all tables with row counts
    views     - List all views
    students  - Show all students
    exams     - Show all exams with answer keys
    keys      - Show answer keys with question type breakdown
    recent    - Show recent grades
    schema    - Show table schemas
    export    - Export table to CSV
    questions - Show question difficulty by type
"""

import sqlite3
import os
import sys
import json
from datetime import datetime

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "grading_system.db")


# ------------------------------------------------------------
# CONNECTION
# ------------------------------------------------------------
def connect_db():
    """Connect to database"""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("\nRun 'python database/init_db.py' to create the database first.")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------
# DATABASE STATS
# ------------------------------------------------------------
def show_stats():
    """Show database statistics"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)

    print(f"\nDatabase: {DB_PATH}")
    print(f"Size: {os.path.getsize(DB_PATH)/1024:.2f} KB")

    # ---- Table Counts ----
    tables = [
        ('sheets', 'Sheets'),
        ('templates', 'Templates'),
        ('exams', 'Exams'),
        ('answer_keys', 'Answer Keys'),
        ('students', 'Students'),
        ('graded_sheets', 'Graded Sheets'),
        ('question_results', 'Question Results')
    ]
    
    print("\nTable Counts:")
    for table, disp in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {disp:.<40} {count:>5}")
        except:
            print(f"  {disp:.<40} (missing)")

    # ---- Score summary ----
    cursor.execute("SELECT COUNT(*) FROM graded_sheets")
    total = cursor.fetchone()[0]

    if total > 0:
        cursor.execute("""
            SELECT
                AVG(percentage) as avg_percentage,
                MIN(percentage) as min_percentage,
                MAX(percentage) as max_percentage,
                AVG(score) as avg_score,
                SUM(score) as total_score,
                SUM(max_score) as total_max_score
            FROM graded_sheets
        """)
        row = cursor.fetchone()
        
        print("\nGrading Stats:")
        print(f"  Total graded sheets:.............. {total}")
        print(f"  Average percentage:............... {row['avg_percentage']:.2f}%")
        print(f"  Lowest percentage:................ {row['min_percentage']:.2f}%")
        print(f"  Highest percentage:............... {row['max_percentage']:.2f}%")
        print(f"  Total score (points):............. {row['total_score']:.2f}")
        print(f"  Total possible points:............ {row['total_max_score']:.2f}")
        print(f"  Overall percentage:............... {(row['total_score']/row['total_max_score']*100 if row['total_max_score'] > 0 else 0):.2f}%")

    conn.close()


# ------------------------------------------------------------
# LIST TABLES
# ------------------------------------------------------------
def list_tables():
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("DATABASE TABLES")
    print("="*70)

    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = cursor.fetchall()

    print(f"\nTotal tables: {len(tables)}\n")

    for row in tables:
        table = row["name"]
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()

        print(f"{table}")
        print(f"  Rows: {count}, Columns: {len(cols)}")
        print(f"  Columns: {', '.join(col[1] for col in cols[:6])}"
              + ("..." if len(cols) > 6 else ""))
        print()

    conn.close()


# ------------------------------------------------------------
# LIST VIEWS
# ------------------------------------------------------------
def list_views():
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("DATABASE VIEWS")
    print("="*70)

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='view'
        ORDER BY name
    """)
    views = cursor.fetchall()

    for v in views:
        print(f"  ✓ {v['name']}")
    
    if not views:
        print("No views defined.")

    conn.close()


# ------------------------------------------------------------
# STUDENTS
# ------------------------------------------------------------
def show_students():
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("STUDENTS SUMMARY")
    print("="*70)

    cursor.execute("""
        SELECT 
            student_id,
            total_exams,
            total_score,
            total_possible_points,
            avg_percentage,
            updated_at
        FROM students
        ORDER BY updated_at DESC
    """)

    rows = cursor.fetchall()
    if not rows:
        print("\nNo students found.\n")
        return

    print(f"\n{'Student ID':<12} {'Exams':<8} {'Score':<12} {'Avg %':<10} {'Last Updated'}")
    print("-"*60)

    for s in rows:
        print(f"{s['student_id']:<12} "
              f"{s['total_exams']:<8} "
              f"{s['total_score']:.2f}/{s['total_possible_points']:.2f}  "
              f"{s['avg_percentage']:>7.2f}%  "
              f"{s['updated_at'][:19]}")

    conn.close()


# ------------------------------------------------------------
# EXAMS
# ------------------------------------------------------------
def show_exams():
    """Show all exams with their answer keys"""
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("EXAMS AND ANSWER KEYS")
    print("="*70)

    cursor.execute("""
        SELECT 
            e.id,
            e.name,
            e.description,
            e.max_score as exam_max_score,
            e.created_at,
            COUNT(DISTINCT ak.id) as key_count,
            GROUP_CONCAT(DISTINCT ak.label) as key_labels
        FROM exams e
        LEFT JOIN answer_keys ak ON e.id = ak.exam_id
        GROUP BY e.id
        ORDER BY e.created_at DESC
    """)

    exams = cursor.fetchall()

    if not exams:
        print("\nNo exams found.\n")
        return

    for exam in exams:
        print(f"\nExam ID: {exam['id']}")
        print(f"Name: {exam['name']}")
        if exam['description']:
            print(f"Description: {exam['description']}")
        print(f"Max Score: {exam['exam_max_score']:.2f}")
        print(f"Keys: {exam['key_labels'] or 'No keys'}")
        print(f"Created: {exam['created_at'][:19]}")
        
        # Show detailed key information
        cursor.execute("""
            SELECT 
                ak.id,
                ak.label,
                ak.name,
                t.name as template_name,
                json_extract(ak.key_info, '$.metadata.total_max_points') as total_points
            FROM answer_keys ak
            JOIN templates t ON ak.template_id = t.id
            WHERE ak.exam_id = ?
            ORDER BY ak.label
        """, (exam['id'],))
        
        keys = cursor.fetchall()
        for key in keys:
            print(f"  Key {key['label']}: {key['name']} (Template: {key['template_name']}, Points: {key['total_points']})")
        
        print("-" * 70)

    conn.close()


# ------------------------------------------------------------
# ANSWER KEYS WITH QUESTION BREAKDOWN
# ------------------------------------------------------------
def show_answer_keys():
    """Show answer keys with question type breakdown"""
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("ANSWER KEYS - DETAILED VIEW")
    print("="*70)

    cursor.execute("""
        SELECT 
            ak.id,
            ak.label,
            ak.name,
            e.name as exam_name,
            t.name as template_name,
            ak.key_info,
            ak.created_at,
            COUNT(gs.id) as usage_count
        FROM answer_keys ak
        JOIN exams e ON ak.exam_id = e.id
        JOIN templates t ON ak.template_id = t.id
        LEFT JOIN graded_sheets gs ON ak.id = gs.key_id
        GROUP BY ak.id
        ORDER BY ak.created_at DESC
    """)

    keys = cursor.fetchall()

    if not keys:
        print("No answer keys found.\n")
        return

    for key in keys:
        print(f"\nKey ID: {key['id']}")
        print(f"Exam: {key['exam_name']}")
        print(f"Label: {key['label']}")
        print(f"Name: {key['name']}")
        print(f"Template: {key['template_name']}")
        print(f"Created: {key['created_at'][:19]}")
        print(f"Times Used: {key['usage_count']}")
        
        # Parse key_info
        try:
            key_info = json.loads(key['key_info'])
            metadata = key_info.get('metadata', {})
            
            mcq_points = metadata.get('mcq_max_points', 0)
            written_points = metadata.get('written_max_points', 0)
            total_points = metadata.get('total_max_points', 0)
            
            # Extract counts from the answer keys
            mcq_questions = len(key_info.get('mcq', {}).get('answer_key', {}))
            written_questions = len(key_info.get('written', {}).get('answer_key', {}))
            
            print(f"\nQuestion Breakdown:")
            print(f"  MCQ Questions:......... {mcq_questions:>3} (max {mcq_points} points)")
            print(f"  Written Questions:..... {written_questions:>3} (max {written_points} points)")
            print(f"  Total Questions:....... {mcq_questions + written_questions:>3}")
            print(f"  Total Max Points:...... {total_points:>3}")
            
        except Exception as e:
            print(f"\nError parsing key_info: {e}")
            print(f"Raw key_info (first 500 chars): {key['key_info'][:500]}...")
        
        print("-" * 70)

    conn.close()


# ------------------------------------------------------------
# RECENT GRADES
# ------------------------------------------------------------
def show_recent_grades():
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("RECENT GRADES")
    print("="*70)

    cursor.execute("""
        SELECT 
            gs.id,
            gs.student_id,
            e.name as exam_name,
            ak.label as key_label,
            gs.score,
            gs.max_score,
            gs.percentage,
            gs.total_mcq_questions,
            gs.total_written_questions,
            gs.mcq_correct_count,
            gs.written_correct_count,
            gs.graded_at
        FROM graded_sheets gs
        JOIN answer_keys ak ON gs.key_id = ak.id
        JOIN exams e ON ak.exam_id = e.id
        ORDER BY gs.graded_at DESC
        LIMIT 20
    """)

    rows = cursor.fetchall()

    if not rows:
        print("\nNo grades found.")
        return

    print(f"\n{'ID':<5} {'Student':<12} {'Exam':<25} {'Key':<4} {'Score':<12} {'%':<8} {'Date':<20}")
    print("-"*90)

    for g in rows:
        score_str = f"{g['score']:.2f}/{g['max_score']:.2f}"
        
        print(f"{g['id']:<5} "
              f"{g['student_id']:<12} "
              f"{g['exam_name'][:24]:<25} "
              f"{g['key_label']:<4} "
              f"{score_str:<12} "
              f"{g['percentage']:>6.2f}% "
              f"{g['graded_at'][:19]}")

    # Show MCQ/Written breakdown for the first result
    if rows:
        g = rows[0]
        print(f"\nMost recent grade breakdown:")
        print(f"  MCQ: {g['mcq_correct_count']}/{g['total_mcq_questions']} correct")
        print(f"  Written: {g['written_correct_count']}/{g['total_written_questions']} correct")

    conn.close()


# ------------------------------------------------------------
# QUESTION DIFFICULTY BY TYPE
# ------------------------------------------------------------
def show_question_difficulty():
    """Show question difficulty broken down by type"""
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("QUESTION DIFFICULTY ANALYSIS")
    print("="*70)

    # Check if we have any question results
    cursor.execute("SELECT COUNT(*) FROM question_results")
    total_questions = cursor.fetchone()[0]
    
    if total_questions == 0:
        print("\nNo question results found yet.")
        return

    # Overall question difficulty
    cursor.execute("""
        SELECT * FROM overall_question_difficulty
        WHERE success_rate IS NOT NULL
        ORDER BY success_rate ASC
        LIMIT 15
    """)
    
    results = cursor.fetchall()
    
    if results:
        print("\nMOST DIFFICULT QUESTIONS:")
        print(f"{'Key':<6} {'Q#':<6} {'Type':<10} {'Attempts':<10} {'Correct':<10} {'Success %':<10}")
        print("-"*60)
        
        for row in results:
            print(f"{row['key_label']:<6} "
                  f"Q{row['question_number']:<5} "
                  f"{row['question_type']:<10} "
                  f"{row['attempts']:<10} "
                  f"{row['correct']:<10} "
                  f"{row['success_rate']:>8.1f}%")
    
    # Show easiest questions too
    cursor.execute("""
        SELECT * FROM overall_question_difficulty
        WHERE success_rate IS NOT NULL AND attempts >= 3
        ORDER BY success_rate DESC
        LIMIT 10
    """)
    
    easy_results = cursor.fetchall()
    
    if easy_results:
        print(f"\nEASIEST QUESTIONS (min 3 attempts):")
        print(f"{'Key':<6} {'Q#':<6} {'Type':<10} {'Attempts':<10} {'Success %':<10}")
        print("-"*60)
        
        for row in easy_results:
            print(f"{row['key_label']:<6} "
                  f"Q{row['question_number']:<5} "
                  f"{row['question_type']:<10} "
                  f"{row['attempts']:<10} "
                  f"{row['success_rate']:>8.1f}%")
    
    # Type breakdown
    cursor.execute("""
        SELECT 
            question_type,
            COUNT(*) as total_questions,
            AVG(CASE WHEN is_correct = 1 THEN 100.0 ELSE 0 END) as avg_success_rate
        FROM question_results
        GROUP BY question_type
    """)
    
    type_results = cursor.fetchall()
    
    if type_results:
        print(f"\nQUESTION TYPE SUMMARY:")
        for row in type_results:
            print(f"  {row['question_type'].title()}: {row['total_questions']} questions, "
                  f"{row['avg_success_rate']:.1f}% average success rate")

    conn.close()


# ------------------------------------------------------------
# SCHEMA VIEWER
# ------------------------------------------------------------
def show_schema(table_name=None):
    conn = connect_db()
    cursor = conn.cursor()

    if table_name:
        tables = [table_name]
    else:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]

    print("\n" + "="*70)
    print("TABLE SCHEMAS")
    print("="*70)

    for table in tables:
        print(f"\nTable: {table}")
        print("-"*70)

        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()

        print(f"{'Column':<30} {'Type':<15} {'NotNull':<8} {'Default':<12} {'PK'}")
        print("-"*70)

        for col in cols:
            print(f"{col[1]:<30} {col[2]:<15} "
                  f"{('YES' if col[3] else 'NO'):<8} "
                  f"{str(col[4] or ''):<12} "
                  f"{('YES' if col[5] else '')}")

    conn.close()


# ------------------------------------------------------------
# EXPORT TABLE TO CSV
# ------------------------------------------------------------
def export_table(table_name, output_dir="exports"):
    conn = connect_db()
    cursor = conn.cursor()

    os.makedirs(output_dir, exist_ok=True)

    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    if not rows:
        print(f"[INFO] Table '{table_name}' is empty.")
        return

    output_path = os.path.join(
        output_dir, f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    import csv
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([col[0] for col in cursor.description])
        writer.writerows(rows)

    print(f"\n✓ Exported {len(rows)} rows to {output_path}")
    conn.close()


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Query the database")
    parser.add_argument(
        "command",
        nargs="?",
        default="stats",
        choices=[
            "stats", "tables", "views",
            "students", "exams", "keys", "recent",
            "schema", "export", "questions"
        ]
    )
    parser.add_argument("--table")
    parser.add_argument("--output", default="exports")

    args = parser.parse_args()

    if args.command == "stats":
        show_stats()
    elif args.command == "tables":
        list_tables()
    elif args.command == "views":
        list_views()
    elif args.command == "students":
        show_students()
    elif args.command == "exams":
        show_exams()
    elif args.command == "keys":
        show_answer_keys()
    elif args.command == "recent":
        show_recent_grades()
    elif args.command == "schema":
        show_schema(args.table)
    elif args.command == "export":
        if not args.table:
            print("[ERROR] --table required for export")
        else:
            export_table(args.table, args.output)
    elif args.command == "questions":
        show_question_difficulty()


if __name__ == "__main__":
    main()