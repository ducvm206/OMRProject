"""
query_db.py - Database query and inspection tool (Updated for new schema)

This script provides utilities to view and query the grading system database.
Updated to reflect that MCQ/written question counts are determined during
answer key creation based on max total points for each part.

Usage:
    python database/query_db.py [command]
    
Commands:
    stats     - Show database statistics
    tables    - List all tables with row counts
    views     - List all views
    students  - Show all students
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

    # ---- Question Type Breakdown ----
    cursor.execute("""
        SELECT 
            SUM(total_mcq_questions) as total_mcq,
            SUM(total_written_questions) as total_written
        FROM graded_sheets
    """)
    result = cursor.fetchone()
    if result and (result['total_mcq'] or result['total_written']):
        print("\nQuestion Type Distribution:")
        print(f"  Total MCQ questions graded........ {result['total_mcq'] or 0}")
        print(f"  Total Written questions graded.... {result['total_written'] or 0}")

    # ---- Score summary ----
    cursor.execute("SELECT COUNT(*) FROM graded_sheets")
    total = cursor.fetchone()[0]

    if total > 0:
        cursor.execute("""
            SELECT
                AVG(CASE
                        WHEN total_mcq_questions + total_written_questions > 0
                        THEN (mcq_correct_count + written_correct_count) * 100.0
                             / (total_mcq_questions + total_written_questions)
                END) as avg_score,
                MIN(CASE
                        WHEN total_mcq_questions + total_written_questions > 0
                        THEN (mcq_correct_count + written_correct_count) * 100.0
                             / (total_mcq_questions + total_written_questions)
                END) as min_score,
                MAX(CASE
                        WHEN total_mcq_questions + total_written_questions > 0
                        THEN (mcq_correct_count + written_correct_count) * 100.0
                             / (total_mcq_questions + total_written_questions)
                END) as max_score,
                AVG(CASE
                        WHEN total_mcq_questions > 0
                        THEN mcq_correct_count * 100.0 / total_mcq_questions
                END) as avg_mcq_score,
                AVG(CASE
                        WHEN total_written_questions > 0
                        THEN written_correct_count * 100.0 / total_written_questions
                END) as avg_written_score
            FROM graded_sheets
        """)
        row = cursor.fetchone()
        
        print("\nGrading Stats:")
        print(f"  Total graded sheets:.............. {total}")
        print(f"  Average overall score:............ {row['avg_score']:.2f}%")
        print(f"  Lowest score:..................... {row['min_score']:.2f}%")
        print(f"  Highest score:.................... {row['max_score']:.2f}%")
        
        if row['avg_mcq_score'] is not None:
            print(f"  Average MCQ score:................ {row['avg_mcq_score']:.2f}%")
        if row['avg_written_score'] is not None:
            print(f"  Average Written score:............ {row['avg_written_score']:.2f}%")

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
            s.student_id,
            s.name,
            s.class,
            s.total_exams,
            s.total_score,
            s.total_questions,
            s.avg_percentage
        FROM students s
        ORDER BY s.created_at DESC
    """)

    rows = cursor.fetchall()
    if not rows:
        print("\nNo students found.\n")
        return

    print(f"\n{'ID':<12} {'Name':<20} {'Class':<10} {'Exams':<8} "
          f"{'Correct/Total':<15} {'Avg %':<8}")
    print("-"*75)

    for s in rows:
        correct = s["total_score"]
        total = s["total_questions"]
        avg_pct = s["avg_percentage"] or 0

        print(f"{s['student_id']:<12} "
              f"{(s['name'] or 'Unknown'):<20} "
              f"{(s['class'] or '-'):<10} "
              f"{s['total_exams']:<8} "
              f"{correct}/{total:<14} "
              f"{avg_pct:>6.2f}%")

    conn.close()


# ------------------------------------------------------------
# ANSWER KEYS WITH QUESTION BREAKDOWN
# ------------------------------------------------------------
def show_answer_keys():
    """Show answer keys with question type breakdown"""
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("ANSWER KEYS - QUESTION TYPE BREAKDOWN")
    print("="*70)
    print("\n[NOTE] MCQ and written question counts are determined from")
    print("       max total points entered during answer key creation\n")

    cursor.execute("""
        SELECT 
            ak.id,
            ak.name,
            ak.created_at,
            t.name as template_name,
            ak.key_info,
            ak.written_key_info
        FROM answer_keys ak
        JOIN templates t ON ak.template_id = t.id
        ORDER BY ak.created_at DESC
    """)

    keys = cursor.fetchall()

    if not keys:
        print("No answer keys found.\n")
        return

    for key in keys:
        print(f"\nKey ID: {key['id']}")
        print(f"Name: {key['name']}")
        print(f"Template: {key['template_name']}")
        print(f"Created: {key['created_at'][:19]}")
        
        # Parse MCQ info
        mcq_count = 0
        mcq_points = 0
        try:
            mcq_info = json.loads(key['key_info'])
            metadata = mcq_info.get('metadata', {})
            mcq_count = metadata.get('total_mcq_questions', 0)
            mcq_points = metadata.get('mcq_max_points', mcq_count)
        except:
            pass
        
        # Parse written info
        written_count = 0
        written_points = 0
        if key['written_key_info']:
            try:
                written_info = json.loads(key['written_key_info'])
                metadata = written_info.get('metadata', {})
                written_count = metadata.get('total_written_questions', 0)
                written_points = metadata.get('written_max_points', written_count)
            except:
                pass
        
        print(f"\nQuestion Breakdown:")
        print(f"  MCQ Questions:......... {mcq_count:>3} (max {mcq_points} points)")
        print(f"  Written Questions:..... {written_count:>3} (max {written_points} points)")
        print(f"  Total Questions:....... {mcq_count + written_count:>3}")
        print(f"  Total Max Points:...... {mcq_points + written_points:>3}")
        
        # Show usage stats
        cursor.execute("""
            SELECT COUNT(*) as usage_count
            FROM graded_sheets
            WHERE key_id = ?
        """, (key['id'],))
        usage = cursor.fetchone()['usage_count']
        print(f"  Times Used:............ {usage:>3}")
        
        print("-" * 70)

    conn.close()


# ------------------------------------------------------------
# RECENT GRADES
# ------------------------------------------------------------
def show_recent_grades():
    conn = connect_db()
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("RECENT GRADES (with MCQ/Written breakdown)")
    print("="*70)

    cursor.execute("""
        SELECT 
            gs.id,
            gs.student_id,
            gs.exam_name,
            gs.total_mcq_questions,
            gs.total_written_questions,
            gs.mcq_correct_count,
            gs.written_correct_count,
            gs.graded_at
        FROM graded_sheets gs
        ORDER BY gs.graded_at DESC
        LIMIT 20
    """)

    rows = cursor.fetchall()

    if not rows:
        print("\nNo grades found.")
        return

    print(f"\n{'ID':<5} {'Student':<12} {'MCQ':<12} {'Written':<12} {'Total %':<8} {'Date':<20}")
    print("-"*80)

    for g in rows:
        total_q = g["total_mcq_questions"] + g["total_written_questions"]
        total_correct = g["mcq_correct_count"] + g["written_correct_count"]
        pct = (total_correct / total_q * 100) if total_q else 0
        
        mcq_str = f"{g['mcq_correct_count']}/{g['total_mcq_questions']}" if g['total_mcq_questions'] else "-"
        written_str = f"{g['written_correct_count']}/{g['total_written_questions']}" if g['total_written_questions'] else "-"

        print(f"{g['id']:<5} "
              f"{g['student_id']:<12} "
              f"{mcq_str:<12} "
              f"{written_str:<12} "
              f"{pct:>6.2f}% "
              f"{g['graded_at'][:19]}")

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

    # MCQ difficulty
    cursor.execute("""
        SELECT * FROM mcq_difficulty
        ORDER BY success_rate ASC
        LIMIT 10
    """)
    
    mcq_results = cursor.fetchall()
    
    if mcq_results:
        print("\nMOST DIFFICULT MCQ QUESTIONS:")
        print(f"{'Key ID':<10} {'Question':<10} {'Attempts':<10} {'Correct':<10} {'Success %':<10}")
        print("-"*50)
        
        for row in mcq_results:
            print(f"{row['key_id']:<10} "
                  f"Q{row['question_number']:<9} "
                  f"{row['attempts']:<10} "
                  f"{row['correct']:<10} "
                  f"{row['success_rate']:>8.1f}%")
    
    # Written difficulty
    cursor.execute("""
        SELECT * FROM written_difficulty
        ORDER BY success_rate ASC
        LIMIT 10
    """)
    
    written_results = cursor.fetchall()
    
    if written_results:
        print("\nMOST DIFFICULT WRITTEN QUESTIONS:")
        print(f"{'Key ID':<10} {'Question':<10} {'Attempts':<10} {'Correct':<10} {'Success %':<10}")
        print("-"*50)
        
        for row in written_results:
            print(f"{row['key_id']:<10} "
                  f"Q{row['question_number']:<9} "
                  f"{row['attempts']:<10} "
                  f"{row['correct']:<10} "
                  f"{row['success_rate']:>8.1f}%")
    
    if not mcq_results and not written_results:
        print("\nNo question results found yet.")

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
            "students", "keys", "recent",
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