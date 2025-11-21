"""
query_db.py - Database query and inspection tool

This script provides utilities to view and query the grading system database.

Usage:
    python database/query_db.py [command]
    
Commands:
    stats     - Show database statistics
    tables    - List all tables with row counts
    views     - List all views
    students  - Show all students
    sessions  - Show grading sessions
    recent    - Show recent grades
    schema    - Show table schemas
    export    - Export data to CSV
"""

import sqlite3
import os
import sys
import json
from datetime import datetime

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "grading_system.db")


def connect_db():
    """Connect to database"""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("\nRun 'python database/init_db.py' to create the database first.")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def show_stats():
    """Show database statistics"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)
    
    # Database info
    print(f"\nDatabase: {DB_PATH}")
    db_size = os.path.getsize(DB_PATH) / 1024  # KB
    print(f"Size: {db_size:.2f} KB")
    
    # Table counts
    tables = [
        ('sheets', 'Sheets'),
        ('templates', 'Templates'),
        ('answer_keys', 'Answer Keys'),
        ('students', 'Students'),
        ('grading_sessions', 'Grading Sessions'),
        ('graded_sheets', 'Graded Sheets'),
        ('question_results', 'Question Results')
    ]
    
    print("\nTable Counts:")
    for table_name, display_name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {display_name:.<40} {count:>5}")
    
    # Sheet-Template relationship stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_sheets,
            SUM(CASE WHEN is_template = 1 THEN 1 ELSE 0 END) as template_sheets,
            COUNT(DISTINCT t.id) as templates_created
        FROM sheets s
        LEFT JOIN templates t ON s.id = t.sheet_id
    """)
    sheet_stats = cursor.fetchone()
    
    print(f"\nSheet-Template Relationships:")
    print(f"  Total sheets:.................... {sheet_stats['total_sheets']}")
    print(f"  Sheets marked as templates:...... {sheet_stats['template_sheets']}")
    print(f"  Templates extracted:............. {sheet_stats['templates_created']}")
    
    # Summary statistics
    cursor.execute("SELECT COUNT(*) FROM graded_sheets")
    total_sheets = cursor.fetchone()[0]
    
    if total_sheets > 0:
        cursor.execute("SELECT AVG(percentage), MIN(percentage), MAX(percentage) FROM graded_sheets")
        avg, min_score, max_score = cursor.fetchone()
        
        print("\nGrading Statistics:")
        print(f"  Total sheets graded:............ {total_sheets}")
        print(f"  Average score:.................. {avg:.2f}%")
        print(f"  Lowest score:................... {min_score:.2f}%")
        print(f"  Highest score:.................. {max_score:.2f}%")
    
    conn.close()


def list_tables():
    """List all tables with row counts"""
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
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        col_count = len(columns)
        
        print(f"{table_name}")
        print(f"  Rows: {count}, Columns: {col_count}")
        print(f"  Columns: {', '.join([col[1] for col in columns[:5]])}" + 
              (f", ..." if col_count > 5 else ""))
        print()
    
    conn.close()


def list_views():
    """List all views"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("DATABASE VIEWS")
    print("="*70)
    
    cursor.execute("""
        SELECT name, sql FROM sqlite_master 
        WHERE type='view'
        ORDER BY name
    """)
    
    views = cursor.fetchall()
    
    print(f"\nTotal views: {len(views)}\n")
    
    for view in views:
        view_name = view[0]
        print(f"✓ {view_name}")
        
        # Test if view works
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
            count = cursor.fetchone()[0]
            print(f"    Rows: {count}")
        except Exception as e:
            print(f"    Error: {e}")
        print()
    
    conn.close()


def show_students():
    """Show all students"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("STUDENTS")
    print("="*70)
    
    cursor.execute("""
        SELECT s.student_id, s.name, s.class, s.created_at,
               COUNT(gs.id) as sheets_graded,
               ROUND(AVG(gs.percentage), 2) as avg_score
        FROM students s
        LEFT JOIN graded_sheets gs ON s.student_id = gs.student_id
        GROUP BY s.student_id
        ORDER BY s.created_at DESC
    """)
    
    students = cursor.fetchall()
    
    if not students:
        print("\nNo students found.")
        conn.close()
        return
    
    print(f"\nTotal students: {len(students)}\n")
    
    print(f"{'Student ID':<12} {'Name':<20} {'Class':<10} {'Sheets':<8} {'Avg Score':<10}")
    print("-" * 70)
    
    for student in students:
        sid = student['student_id'] or 'N/A'
        name = student['name'] or 'Unknown'
        cls = student['class'] or '-'
        sheets = student['sheets_graded']
        avg = student['avg_score'] or 0.0
        
        print(f"{sid:<12} {name:<20} {cls:<10} {sheets:<8} {avg:.2f}%")
    
    conn.close()


def show_sessions():
    """Show grading sessions"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("GRADING SESSIONS")
    print("="*70)
    
    cursor.execute("""
        SELECT * FROM session_summary
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    sessions = cursor.fetchall()
    
    if not sessions:
        print("\nNo grading sessions found.")
        conn.close()
        return
    
    print(f"\nShowing latest {min(len(sessions), 20)} sessions:\n")
    
    for session in sessions:
        print(f"Session #{session['id']}: {session['name']}")
        print(f"  Template: {session['template_name']} ({session['total_questions']} questions)")
        print(f"  Created: {session['created_at']}")
        print(f"  Sheets graded: {session['sheets_graded']}")
        if session['sheets_graded'] > 0:
            print(f"  Avg score: {session['avg_score']:.2f}% (min: {session['min_score']:.2f}%, max: {session['max_score']:.2f}%)")
        print(f"  Batch mode: {'Yes' if session['is_batch'] else 'No'}")
        print()
    
    conn.close()


def show_recent_grades():
    """Show recent grading results"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("RECENT GRADES")
    print("="*70)
    
    cursor.execute("""
        SELECT * FROM recent_grades
        LIMIT 20
    """)
    
    grades = cursor.fetchall()
    
    if not grades:
        print("\nNo grades found.")
        conn.close()
        return
    
    print(f"\nShowing latest {len(grades)} grades:\n")
    
    print(f"{'ID':<5} {'Student ID':<12} {'Score':<10} {'%':<8} {'Session':<20} {'Date':<20}")
    print("-" * 85)
    
    for grade in grades:
        gid = grade['id']
        sid = grade['student_id'] or 'N/A'
        score = grade['score']
        pct = grade['percentage']
        session = grade['session_name'][:18]
        date = grade['graded_at'][:19]
        
        print(f"{gid:<5} {sid:<12} {score:<10} {pct:>6.2f}% {session:<20} {date}")
    
    conn.close()


def show_schema(table_name=None):
    """Show table schema"""
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
        print("-" * 70)
        
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        print(f"{'Column':<25} {'Type':<15} {'Not Null':<10} {'Default':<15} {'PK'}")
        print("-" * 70)
        
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = 'YES' if col[3] else 'NO'
            default = str(col[4]) if col[4] else ''
            pk = 'YES' if col[5] else ''
            
            print(f"{col_name:<25} {col_type:<15} {not_null:<10} {default:<15} {pk}")
    
    conn.close()


def show_sheet_relationships():
    """Show sheet-template relationships"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("SHEET-TEMPLATE RELATIONSHIPS")
    print("="*70)
    
    cursor.execute("""
        SELECT 
            s.id as sheet_id,
            s.image_path,
            s.is_template,
            s.created_at as sheet_created,
            t.id as template_id,
            t.name as template_name,
            t.total_questions
        FROM sheets s
        LEFT JOIN templates t ON s.id = t.sheet_id
        ORDER BY s.created_at DESC
        LIMIT 15
    """)
    
    relationships = cursor.fetchall()
    
    if not relationships:
        print("\nNo sheet-template relationships found.")
        conn.close()
        return
    
    print(f"\nShowing latest {len(relationships)} sheets:\n")
    
    for rel in relationships:
        print(f"Sheet #{rel['sheet_id']}: {rel['image_path']}")
        print(f"  Created: {rel['sheet_created']}")
        print(f"  Is template: {'Yes' if rel['is_template'] else 'No'}")
        
        if rel['template_id']:
            print(f"  Template: #{rel['template_id']} - {rel['template_name']}")
            print(f"  Questions: {rel['total_questions']}")
        else:
            print(f"  Template: Not extracted")
        print()
    
    conn.close()


def show_question_difficulty():
    """Show question difficulty analysis"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("QUESTION DIFFICULTY ANALYSIS")
    print("="*70)
    
    cursor.execute("""
        SELECT * FROM question_difficulty
        ORDER BY question_number
    """)
    
    questions = cursor.fetchall()
    
    if not questions:
        print("\nNo question data found.")
        conn.close()
        return
    
    print(f"\nTotal questions analyzed: {len(questions)}\n")
    
    print(f"{'Q#':<4} {'Attempts':<10} {'Correct':<10} {'Wrong':<10} {'Success Rate':<12}")
    print("-" * 50)
    
    for q in questions:
        q_num = q['question_number']
        attempts = q['total_attempts']
        correct = q['correct_count']
        wrong = q['wrong_count']
        success = q['success_rate']
        
        print(f"{q_num:<4} {attempts:<10} {correct:<10} {wrong:<10} {success:>10.2f}%")
    
    # Show most and least difficult questions
    cursor.execute("""
        SELECT * FROM question_difficulty 
        ORDER BY success_rate ASC 
        LIMIT 5
    """)
    hardest = cursor.fetchall()
    
    cursor.execute("""
        SELECT * FROM question_difficulty 
        ORDER BY success_rate DESC 
        LIMIT 5
    """)
    easiest = cursor.fetchall()
    
    print(f"\nTop 5 Most Difficult Questions:")
    for q in hardest:
        print(f"  Q{q['question_number']}: {q['success_rate']:.2f}% success")
    
    print(f"\nTop 5 Easiest Questions:")
    for q in easiest:
        print(f"  Q{q['question_number']}: {q['success_rate']:.2f}% success")
    
    conn.close()


def export_table(table_name, output_dir='exports'):
    """Export table to CSV"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Create exports directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"\nTable '{table_name}' is empty. Nothing to export.")
        conn.close()
        return
    
    # Export to CSV
    import csv
    output_path = os.path.join(output_dir, f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([description[0] for description in cursor.description])
        
        # Write rows
        writer.writerows(rows)
    
    print(f"\n✓ Exported {len(rows)} rows to: {output_path}")
    
    conn.close()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Query and inspect the grading system database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('command', nargs='?', default='stats',
                      choices=['stats', 'tables', 'views', 'students', 'sessions', 
                              'recent', 'schema', 'export', 'sheets', 'questions'],
                      help='Command to execute')
    
    parser.add_argument('--table', '-t', help='Table name (for schema and export commands)')
    parser.add_argument('--output', '-o', default='exports', help='Output directory for exports')
    
    args = parser.parse_args()
    
    # Execute command
    if args.command == 'stats':
        show_stats()
    elif args.command == 'tables':
        list_tables()
    elif args.command == 'views':
        list_views()
    elif args.command == 'students':
        show_students()
    elif args.command == 'sessions':
        show_sessions()
    elif args.command == 'recent':
        show_recent_grades()
    elif args.command == 'schema':
        show_schema(args.table)
    elif args.command == 'export':
        if not args.table:
            print("[ERROR] Please specify a table with --table")
            sys.exit(1)
        export_table(args.table, args.output)
    elif args.command == 'sheets':
        show_sheet_relationships()
    elif args.command == 'questions':
        show_question_difficulty()


if __name__ == "__main__":
    main()