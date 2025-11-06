"""
grading.py - Grade scanned answer sheets against answer key

This module compares scanned student answers with the answer key
and generates grade reports.
"""

import json
import os
from datetime import datetime


def load_answer_key(key_path):
    """
    Load answer key from JSON file
    
    Args:
        key_path: Path to answer key JSON file
        
    Returns:
        Dictionary with answer key data
    """
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Answer key not found: {key_path}")
    
    with open(key_path, 'r', encoding='utf-8') as f:
        key_data = json.load(f)
    
    print(f"[LOADED] Answer key: {key_path}")
    print(f"  Total questions: {key_data['metadata']['total_questions']}")
    
    return key_data


def load_scanned_answers(answers_path):
    """
    Load scanned answers from JSON file
    
    Args:
        answers_path: Path to scanned answers JSON file
        
    Returns:
        Dictionary with scanned answers data
    """
    if not os.path.exists(answers_path):
        raise FileNotFoundError(f"Scanned answers not found: {answers_path}")
    
    with open(answers_path, 'r', encoding='utf-8') as f:
        answers_data = json.load(f)
    
    print(f"[LOADED] Scanned answers: {answers_path}")
    print(f"  Source image: {answers_data['metadata']['source_image']}")
    print(f"  Total questions: {answers_data['metadata']['total_questions']}")
    
    return answers_data


def grade_answers(answer_key_data, scanned_answers_data, max_points=None, partial_credit=False):
    """
    Grade scanned answers against answer key
    
    Args:
        answer_key_data: Dictionary with answer key
        scanned_answers_data: Dictionary with scanned answers
        max_points: Maximum points for the exam (default: 1 point per question)
        partial_credit: If True, give partial credit for partially correct multiple answers
        
    Returns:
        Dictionary with grading results
    """
    print("\n" + "="*70)
    print("GRADING IN PROGRESS")
    print("="*70)
    
    answer_key = answer_key_data['answer_key']
    scanned_answers = scanned_answers_data['answers']
    
    total_questions = len(answer_key)
    
    # Calculate points per question
    if max_points is None:
        max_points = float(total_questions)
        points_per_question = 1.0
    else:
        max_points = float(max_points)
        points_per_question = max_points / total_questions
    
    print(f"Max points: {max_points}")
    print(f"Points per question: {points_per_question:.2f}")
    
    results = {
        'correct': 0,
        'incorrect': 0,
        'blank': 0,
        'partial': 0,
        'total_questions': total_questions,
        'max_points': max_points,
        'points_per_question': points_per_question,
        'score': 0.0,
        'details': {}
    }
    
    # Grade each question
    for q_num_str in answer_key.keys():
        q_num = int(q_num_str)
        correct_answers = set(answer_key[q_num_str])
        
        # Get student's answers
        if q_num_str in scanned_answers:
            student_answers = set(scanned_answers[q_num_str]['selected_answers'])
        else:
            student_answers = set()
        
        # Determine correctness
        if not student_answers:
            # Blank answer
            status = 'blank'
            points = 0.0
            results['blank'] += 1
        elif student_answers == correct_answers:
            # Completely correct
            status = 'correct'
            points = points_per_question
            results['correct'] += 1
        elif partial_credit and correct_answers and student_answers:
            # Partial credit calculation
            correct_selected = len(student_answers & correct_answers)
            incorrect_selected = len(student_answers - correct_answers)
            total_correct = len(correct_answers)
            
            # Award partial credit: (correct - incorrect) / total, minimum 0
            fraction = max(0, (correct_selected - incorrect_selected) / total_correct)
            points = fraction * points_per_question
            
            if points > 0:
                status = 'partial'
                results['partial'] += 1
            else:
                status = 'incorrect'
                results['incorrect'] += 1
        else:
            # Incorrect
            status = 'incorrect'
            points = 0.0
            results['incorrect'] += 1
        
        # Store details
        results['details'][q_num] = {
            'correct_answers': sorted(list(correct_answers)),
            'student_answers': sorted(list(student_answers)),
            'status': status,
            'points': points
        }
        
        results['score'] += points
    
    # Calculate percentage
    if results['max_points'] > 0:
        results['percentage'] = (results['score'] / results['max_points']) * 100
    else:
        results['percentage'] = 0.0
    
    return results


def print_grading_summary(results):
    """
    Print grading summary to console
    
    Args:
        results: Dictionary with grading results
    """
    print("\n" + "="*70)
    print("GRADING SUMMARY")
    print("="*70)
    print(f"Total questions: {results['total_questions']}")
    print(f"Correct: {results['correct']}")
    print(f"Incorrect: {results['incorrect']}")
    print(f"Blank: {results['blank']}")
    if results['partial'] > 0:
        print(f"Partial credit: {results['partial']}")
    print(f"\nScore: {results['score']:.2f} / {results['max_points']:.2f}")
    print(f"Percentage: {results['percentage']:.2f}%")
    
    # Grade letter (optional)
    percentage = results['percentage']
    if percentage >= 90:
        grade = 'A'
    elif percentage >= 80:
        grade = 'B'
    elif percentage >= 70:
        grade = 'C'
    elif percentage >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    print(f"Grade: {grade}")


def print_detailed_results(results, show_all=False, show_incorrect_only=False):
    """
    Print detailed question-by-question results
    
    Args:
        results: Dictionary with grading results
        show_all: If True, show all questions
        show_incorrect_only: If True, show only incorrect answers
    """
    print("\n" + "="*70)
    print("DETAILED RESULTS")
    print("="*70)
    
    for q_num in sorted(results['details'].keys()):
        detail = results['details'][q_num]
        
        # Filter based on options
        if show_incorrect_only and detail['status'] == 'correct':
            continue
        
        correct_str = ', '.join(detail['correct_answers']) if detail['correct_answers'] else 'No answer'
        student_str = ', '.join(detail['student_answers']) if detail['student_answers'] else 'No answer'
        
        status_symbol = {
            'correct': '[✓]',
            'incorrect': '[✗]',
            'blank': '[ ]',
            'partial': '[~]'
        }
        
        symbol = status_symbol.get(detail['status'], '[ ]')
        
        print(f"\nQuestion {q_num}: {symbol} {detail['status'].upper()}")
        print(f"  Correct answer: {correct_str}")
        print(f"  Student answer: {student_str}")
        
        if detail['status'] == 'partial':
            print(f"  Points: {detail['points']:.2f}/{results['points_per_question']:.2f}")
        
        if not show_all and q_num >= 10:
            remaining = len(results['details']) - 10
            if remaining > 0:
                print(f"\n... and {remaining} more questions")
            break


def save_grade_report(results, answer_key_path, scanned_answers_path, output_dir='grade_reports'):
    """
    Save grade report to JSON file
    
    Args:
        results: Dictionary with grading results
        answer_key_path: Path to answer key used
        scanned_answers_path: Path to scanned answers
        output_dir: Directory to save grade report
        
    Returns:
        Path to saved grade report
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare report data
    report_data = {
        'metadata': {
            'graded_at': datetime.now().isoformat(),
            'answer_key_used': answer_key_path,
            'scanned_answers_file': scanned_answers_path
        },
        'summary': {
            'total_questions': results['total_questions'],
            'correct': results['correct'],
            'incorrect': results['incorrect'],
            'blank': results['blank'],
            'partial': results['partial'],
            'max_points': results['max_points'],
            'points_per_question': results['points_per_question'],
            'score': results['score'],
            'percentage': results['percentage']
        },
        'details': {}
    }
    
    # Convert details (int keys to string for JSON)
    for q_num, detail in results['details'].items():
        report_data['details'][str(q_num)] = detail
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract student name from scanned answers filename if possible
    base_name = os.path.splitext(os.path.basename(scanned_answers_path))[0]
    json_filename = f"grade_report_{base_name}_{timestamp}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Save to JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] Grade report saved to: {json_path}")
    
    return json_path


def compare_multiple_students(answer_key_path, scanned_answers_folder='scanned_answers', max_points=None, partial_credit=False):
    """
    Grade multiple student answer sheets at once
    
    Args:
        answer_key_path: Path to answer key JSON file
        scanned_answers_folder: Folder containing scanned answer JSON files
        max_points: Maximum points for the exam
        partial_credit: If True, give partial credit
        
    Returns:
        Dictionary with all students' results
    """
    print("="*70)
    print("BATCH GRADING")
    print("="*70)
    
    # Load answer key once
    answer_key_data = load_answer_key(answer_key_path)
    
    # Find all scanned answer files
    if not os.path.exists(scanned_answers_folder):
        print(f"[ERROR] Folder not found: {scanned_answers_folder}")
        return None
    
    answer_files = [
        f for f in os.listdir(scanned_answers_folder)
        if f.endswith('.json') and f.startswith('filled_')
    ]
    
    if not answer_files:
        print(f"[ERROR] No answer files found in {scanned_answers_folder}")
        return None
    
    print(f"\nFound {len(answer_files)} answer sheet(s) to grade\n")
    
    all_results = {}
    
    for answer_file in answer_files:
        answer_path = os.path.join(scanned_answers_folder, answer_file)
        print(f"\n{'='*70}")
        print(f"Grading: {answer_file}")
        print(f"{'='*70}")
        
        try:
            # Load and grade
            scanned_answers_data = load_scanned_answers(answer_path)
            results = grade_answers(answer_key_data, scanned_answers_data, max_points, partial_credit)
            
            # Print summary
            print_grading_summary(results)
            
            # Save report
            report_path = save_grade_report(results, answer_key_path, answer_path)
            
            all_results[answer_file] = {
                'results': results,
                'report_path': report_path
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to grade {answer_file}: {e}")
    
    # Print overall summary
    if all_results:
        print("\n" + "="*70)
        print("BATCH GRADING SUMMARY")
        print("="*70)
        for filename, data in all_results.items():
            res = data['results']
            print(f"\n{filename}:")
            print(f"  Score: {res['score']:.2f}/{res['total_questions']} ({res['percentage']:.2f}%)")
    
    return all_results


def main():
    """Main function - grade answer sheets"""
    
    print("="*70)
    print("ANSWER SHEET GRADING SYSTEM")
    print("="*70)
    
    print("\nChoose an option:")
    print("1. Grade single answer sheet")
    print("2. Grade multiple answer sheets (batch)")
    print("3. View saved grade report")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        # Single grading
        print("\n--- Single Answer Sheet Grading ---")
        
        # Load answer key
        key_path = input("\nEnter answer key path (or press Enter for default): ").strip()
        if not key_path:
            # Try to find most recent answer key
            if os.path.exists('answer_keys'):
                key_files = [f for f in os.listdir('answer_keys') if f.startswith('answer_key_')]
                if key_files:
                    key_path = os.path.join('answer_keys', sorted(key_files)[-1])
                    print(f"Using most recent: {key_path}")
        
        if not key_path or not os.path.exists(key_path):
            print("[ERROR] Answer key not found")
            return
        
        # Load scanned answers
        answers_path = input("Enter scanned answers path: ").strip()
        if not answers_path or not os.path.exists(answers_path):
            print("[ERROR] Scanned answers not found")
            return
        
        # Partial credit option
        partial = input("Enable partial credit? (y/n, default n): ").strip().lower()
        partial_credit = (partial == 'y')
        
        # Grade
        answer_key_data = load_answer_key(key_path)
        scanned_answers_data = load_scanned_answers(answers_path)
        results = grade_answers(answer_key_data, scanned_answers_data, partial_credit)
        
        # Display results
        print_grading_summary(results)
        
        # Show details
        show_details = input("\nShow detailed results? (y/n): ").strip().lower()
        if show_details == 'y':
            show_option = input("Show (a)ll, (i)ncorrect only, or (f)irst 10? [f]: ").strip().lower()
            if show_option == 'a':
                print_detailed_results(results, show_all=True)
            elif show_option == 'i':
                print_detailed_results(results, show_incorrect_only=True)
            else:
                print_detailed_results(results, show_all=False)
        
        # Save report
        save_report = input("\nSave grade report? (y/n): ").strip().lower()
        if save_report == 'y':
            save_grade_report(results, key_path, answers_path)
    
    elif choice == '2':
        # Batch grading
        print("\n--- Batch Grading ---")
        
        key_path = input("\nEnter answer key path (or press Enter for default): ").strip()
        if not key_path:
            if os.path.exists('answer_keys'):
                key_files = [f for f in os.listdir('answer_keys') if f.startswith('answer_key_')]
                if key_files:
                    key_path = os.path.join('answer_keys', sorted(key_files)[-1])
                    print(f"Using most recent: {key_path}")
        
        if not key_path or not os.path.exists(key_path):
            print("[ERROR] Answer key not found")
            return
        
        answers_folder = input("Enter scanned answers folder (default 'scanned_answers'): ").strip()
        if not answers_folder:
            answers_folder = 'scanned_answers'
        
        partial = input("Enable partial credit? (y/n, default n): ").strip().lower()
        partial_credit = (partial == 'y')
        
        compare_multiple_students(key_path, answers_folder, partial_credit)
    
    elif choice == '3':
        # View saved report
        report_path = input("\nEnter grade report path: ").strip()
        
        if not os.path.exists(report_path):
            print("[ERROR] Grade report not found")
            return
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        print("\n" + "="*70)
        print("GRADE REPORT")
        print("="*70)
        print(f"Graded at: {report_data['metadata']['graded_at']}")
        print(f"Answer key: {report_data['metadata']['answer_key_used']}")
        
        summary = report_data['summary']
        print(f"\nTotal questions: {summary['total_questions']}")
        print(f"Correct: {summary['correct']}")
        print(f"Incorrect: {summary['incorrect']}")
        print(f"Blank: {summary['blank']}")
        print(f"\nScore: {summary['score']:.2f}/{summary['total_questions']}")
        print(f"Percentage: {summary['percentage']:.2f}%")
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()