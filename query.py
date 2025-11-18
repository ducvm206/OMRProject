import sqlite3
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pandas as pd

def debug_database_content(database_path, answer_key_id):
    """Debug function to see what data actually exists in the database"""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    
    print(f"\n=== DEBUG DATABASE CONTENT FOR ANSWER KEY ID: {answer_key_id} ===")
    
    try:
        cursor = conn.cursor()
        
        # 1. Check if answer key exists
        cursor.execute("SELECT id, name, file_path FROM answer_keys WHERE id = ?", (answer_key_id,))
        answer_key = cursor.fetchone()
        if answer_key:
            print(f"✓ Answer key found: ID={answer_key['id']}, Name='{answer_key['name']}'")
        else:
            print(f"✗ Answer key ID {answer_key_id} not found!")
            return False
        
        # 2. Check for grading sessions
        cursor.execute("""
            SELECT id, name, template_id, answer_key_id 
            FROM grading_sessions 
            WHERE answer_key_id = ?
        """, (answer_key_id,))
        sessions = cursor.fetchall()
        print(f"✓ Found {len(sessions)} grading session(s) for this answer key:")
        for session in sessions:
            print(f"  - Session ID: {session['id']}, Name: '{session['name']}'")
        
        # 3. Check for graded sheets
        cursor.execute("""
            SELECT gs.id, gs.student_id, gs.score, gs.total_questions, gs.percentage
            FROM graded_sheets gs
            JOIN grading_sessions sess ON gs.session_id = sess.id
            WHERE sess.answer_key_id = ?
        """, (answer_key_id,))
        graded_sheets = cursor.fetchall()
        print(f"✓ Found {len(graded_sheets)} graded sheet(s):")
        for sheet in graded_sheets:
            print(f"  - Sheet ID: {sheet['id']}, Student: {sheet['student_id']}, Score: {sheet['score']}/{sheet['total_questions']} ({sheet['percentage']}%)")
        
        # 4. Check for question results
        cursor.execute("""
            SELECT qr.id, qr.question_number, qr.is_correct, qr.student_answer, qr.correct_answer
            FROM question_results qr
            JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
            JOIN grading_sessions sess ON gs.session_id = sess.id
            WHERE sess.answer_key_id = ?
            LIMIT 10
        """, (answer_key_id,))
        question_results = cursor.fetchall()
        print(f"✓ Found {len(question_results)} question results (showing first 10):")
        for qr in question_results:
            status = "CORRECT" if qr['is_correct'] else "WRONG"
            print(f"  - Q{qr['question_number']}: {qr['student_answer']} → {qr['correct_answer']} [{status}]")
        
        # 5. Count wrong answers specifically
        cursor.execute("""
            SELECT COUNT(*) as wrong_count
            FROM question_results qr
            JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
            JOIN grading_sessions sess ON gs.session_id = sess.id
            WHERE sess.answer_key_id = ? AND qr.is_correct = 0
        """, (answer_key_id,))
        wrong_count = cursor.fetchone()['wrong_count']
        print(f"✓ Total wrong answers found: {wrong_count}")
        
        return len(graded_sheets) > 0
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False
    finally:
        conn.close()

def create_wrong_answers_histogram(database_path, answer_key_id, window_name="Wrong Answers Histogram"):
    """
    Create a histogram showing wrong answers by question number
    """
    
    def get_wrong_answers_data(database_path, answer_key_id):
        """Fetch wrong answer counts for each question"""
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            # Get exam info
            cursor.execute("""
                SELECT ak.name, ak.file_path, t.name as template_name, t.total_questions
                FROM answer_keys ak
                JOIN templates t ON ak.template_id = t.id
                WHERE ak.id = ?
            """, (answer_key_id,))
            exam_info = cursor.fetchone()
            
            # Get wrong answer counts for each question - FIXED QUERY
            wrong_answer_query = """
            SELECT 
                qr.question_number,
                COUNT(*) AS total_attempts,
                SUM(CASE WHEN qr.is_correct = 0 THEN 1 ELSE 0 END) AS wrong_count,
                ROUND((SUM(CASE WHEN qr.is_correct = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) AS wrong_percentage
            FROM question_results qr
            JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
            JOIN grading_sessions sess ON gs.session_id = sess.id
            WHERE sess.answer_key_id = ?
            GROUP BY qr.question_number
            ORDER BY qr.question_number
            """
            cursor.execute(wrong_answer_query, (answer_key_id,))
            wrong_answers = cursor.fetchall()
            
            print(f"[DEBUG] Raw wrong answers query returned {len(wrong_answers)} rows")
            
            # Get total number of students for this answer key
            cursor.execute("""
                SELECT COUNT(DISTINCT gs.id) as total_students
                FROM graded_sheets gs
                JOIN grading_sessions sess ON gs.session_id = sess.id
                WHERE sess.answer_key_id = ?
            """, (answer_key_id,))
            total_students_result = cursor.fetchone()
            total_students = total_students_result['total_students'] if total_students_result else 0
            
            return {
                'exam_info': dict(exam_info) if exam_info else {},
                'wrong_answers': [dict(row) for row in wrong_answers],
                'total_students': total_students
            }
            
        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            conn.close()
    
    def matplotlib_figure_to_opencv(fig):
        """Convert matplotlib figure to OpenCV image"""
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        buf = canvas.buffer_rgba()
        img = np.asarray(buf)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        return img_bgr
    
    def create_histogram_image(data):
        """Create the histogram image"""
        if not data or not data['wrong_answers']:
            # Create more informative error image
            error_img = np.ones((600, 800, 3), dtype=np.uint8) * 255
            cv2.putText(error_img, "No wrong answer data available", 
                       (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(error_img, f"Answer Key ID: {answer_key_id}", 
                       (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(error_img, "Run debug_database_content() to check data", 
                       (150, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            return error_img
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Extract data
        questions = [wa['question_number'] for wa in data['wrong_answers']]
        wrong_counts = [wa['wrong_count'] for wa in data['wrong_answers']]
        wrong_percentages = [wa['wrong_percentage'] for wa in data['wrong_answers']]
        
        print(f"[DEBUG] Creating histogram for {len(questions)} questions")
        print(f"[DEBUG] Questions: {questions}")
        print(f"[DEBUG] Wrong counts: {wrong_counts}")
        
        # Create the histogram (bar chart)
        bars = ax.bar(questions, wrong_counts, 
                     color='lightcoral', alpha=0.7, edgecolor='darkred', linewidth=1,
                     width=0.8)
        
        # Customize the appearance
        ax.set_xlabel('Question Number', fontsize=12, fontweight='bold')
        ax.set_ylabel('Times Answered Incorrectly', fontsize=12, fontweight='bold')
        
        # Set title with exam information
        title = f"Wrong Answers by Question\n"
        title += f"Exam: {data['exam_info'].get('name', 'Unknown')} | "
        title += f"Total Students: {data['total_students']} | "
        title += f"Questions: {len(questions)}"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Set x-axis to show question numbers
        ax.set_xticks(questions)
        
        # Add grid for better readability
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # Add value labels on top of each bar
        for i, (bar, count, percentage) in enumerate(zip(bars, wrong_counts, wrong_percentages)):
            height = bar.get_height()
            # Position the label above the bar
            label_y = height + (max(wrong_counts) * 0.01)
            
            # Show count and percentage
            label_text = f'{count}\n({percentage}%)'
            
            ax.text(bar.get_x() + bar.get_width()/2., label_y, label_text,
                   ha='center', va='bottom', fontsize=8, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
        
        # Highlight problematic questions (more than 50% wrong)
        for i, (q, count, percentage) in enumerate(zip(questions, wrong_counts, wrong_percentages)):
            if percentage > 50:
                bars[i].set_color('red')
                bars[i].set_alpha(0.9)
                # Add special annotation for high-error questions
                ax.text(bar.get_x() + bar.get_width()/2., label_y + (max(wrong_counts) * 0.05),
                       "High Error!", ha='center', va='bottom', fontsize=8, 
                       color='red', fontweight='bold')
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Convert to OpenCV image
        opencv_img = matplotlib_figure_to_opencv(fig)
        plt.close(fig)
        
        return opencv_img
    
    def create_sample_data_demo():
        """Create a demo with sample data for testing"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Sample data
        questions = list(range(1, 21))
        wrong_counts = [5, 3, 8, 2, 12, 4, 6, 1, 9, 7, 3, 11, 2, 5, 8, 4, 10, 3, 6, 2]
        
        bars = ax.bar(questions, wrong_counts, color='lightcoral', alpha=0.7, edgecolor='darkred')
        
        ax.set_xlabel('Question Number', fontsize=12, fontweight='bold')
        ax.set_ylabel('Times Answered Incorrectly', fontsize=12, fontweight='bold')
        ax.set_title('SAMPLE DATA: Wrong Answers by Question\n(Demo - No real data found)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(questions)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels
        for bar, count in zip(bars, wrong_counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1, f'{count}',
                   ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        plt.tight_layout()
        opencv_img = matplotlib_figure_to_opencv(fig)
        plt.close(fig)
        
        return opencv_img
    
    # Main function to display the histogram
    def show_histogram():
        # First, debug what data we have
        has_data = debug_database_content(database_path, answer_key_id)
        
        # Fetch data
        data = get_wrong_answers_data(database_path, answer_key_id)
        
        # Create images
        if data and data['wrong_answers']:
            histogram_img = create_histogram_image(data)
            show_sample = False
        else:
            print("\nNo real data found. Showing sample demo...")
            histogram_img = create_sample_data_demo()
            show_sample = True
        
        # Create OpenCV window
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1200, 800)
        
        print("\nControls:")
        print("ESC - Exit")
        if show_sample:
            print("Note: Showing sample data - no real data found in database")
        
        while True:
            cv2.imshow(window_name, histogram_img)
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC key
                break
            elif key == ord('s') or key == ord('S'):  # Save image
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                filename = f"wrong_answers_{answer_key_id}_{timestamp}.png"
                cv2.imwrite(filename, histogram_img)
                print(f"Image saved as: {filename}")
        
        cv2.destroyAllWindows()
    
    # Run the histogram viewer
    show_histogram()

# List available answer keys
def list_answer_keys(database_path):
    """List all available answer keys in the database"""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ak.id, ak.name, ak.file_path, t.name as template_name, 
                   COUNT(gs.id) as graded_count
            FROM answer_keys ak
            JOIN templates t ON ak.template_id = t.id
            LEFT JOIN grading_sessions sess ON ak.id = sess.answer_key_id
            LEFT JOIN graded_sheets gs ON sess.id = gs.session_id
            GROUP BY ak.id
            ORDER BY ak.id
        """)
        
        answer_keys = cursor.fetchall()
        
        print("Available Answer Keys:")
        print("-" * 80)
        print(f"{'ID':<4} {'Name':<20} {'Template':<15} {'Graded Sheets':<12} {'File Path'}")
        print("-" * 80)
        
        for ak in answer_keys:
            print(f"{ak['id']:<4} {ak['name']:<20} {ak['template_name']:<15} "
                  f"{ak['graded_count']:<12} {ak['file_path']}")
        
        return [dict(ak) for ak in answer_keys]
        
    except Exception as e:
        print(f"Error listing answer keys: {e}")
        return []
    finally:
        conn.close()

# Test function to populate with sample data
def create_sample_data(database_path):
    """Create sample data for testing if database is empty"""
    conn = sqlite3.connect(database_path)
    
    try:
        cursor = conn.cursor()
        
        # Check if we already have data
        cursor.execute("SELECT COUNT(*) as count FROM graded_sheets")
        count = cursor.fetchone()['count']
        
        if count == 0:
            print("No data found. Creating sample data...")
            
            # Create sample answer key, sessions, and graded sheets
            # This is a simplified version - you'd need to adapt to your actual schema
            cursor.execute("""
                INSERT OR IGNORE INTO answer_keys (id, template_id, name, file_path) 
                VALUES (1, 1, 'Sample Math Test', 'sample_key.json')
            """)
            
            cursor.execute("""
                INSERT OR IGNORE INTO grading_sessions (id, name, template_id, answer_key_id, is_batch, total_sheets)
                VALUES (1, 'Sample Session', 1, 1, 1, 5)
            """)
            
            # Add sample graded sheets and question results
            for i in range(5):
                cursor.execute("""
                    INSERT INTO graded_sheets (session_id, sheet_id, student_id, score, total_questions, percentage, correct_count, wrong_count, blank_count)
                    VALUES (1, 1, ? , 15, 20, 75.0, 15, 5, 0)
                """, (f"STU{1000+i}",))
                
                graded_sheet_id = cursor.lastrowid
                
                # Add sample question results with some wrong answers
                for q in range(1, 21):
                    is_correct = 1 if q % 5 != 0 else 0  # Every 5th question is wrong
                    cursor.execute("""
                        INSERT INTO question_results (graded_sheet_id, question_number, student_answer, correct_answer, is_correct)
                        VALUES (?, ?, ?, ?, ?)
                    """, (graded_sheet_id, q, 'A', 'B' if q % 5 == 0 else 'A', is_correct))
            
            conn.commit()
            print("Sample data created successfully!")
        else:
            print(f"Database already contains {count} graded sheets")
            
    except Exception as e:
        print(f"Error creating sample data: {e}")
    finally:
        conn.close()

# Example usage
if __name__ == "__main__":
    database_path = "grading_system.db"  # Update with your database path
    
    # First, list available answer keys
    answer_keys = list_answer_keys(database_path)
    
    if not answer_keys:
        print("No answer keys found. The database might be empty.")
        create_sample_data(database_path)
        # List again after creating sample data
        answer_keys = list_answer_keys(database_path)
    
    if answer_keys:
        print(f"\nFound {len(answer_keys)} answer key(s)")
        try:
            # Use the first answer key ID, or prompt user for input
            user_input = input("\nEnter answer key ID to analyze (or press Enter for first one): ").strip()
            answer_key_id = int(user_input) if user_input else answer_keys[0]['id']
            
            # Verify the answer key exists
            if any(ak['id'] == answer_key_id for ak in answer_keys):
                print(f"Creating wrong answers histogram for answer key ID: {answer_key_id}")
                create_wrong_answers_histogram(database_path, answer_key_id)
            else:
                print(f"Error: Answer key ID {answer_key_id} not found!")
                
        except ValueError:
            print("Please enter a valid numeric ID")
    else:
        print("No answer keys found in the database even after creating sample data!")