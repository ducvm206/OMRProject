"""
answer_key.py - Generate and manage answer keys

This module loads a template JSON file and creates answer keys for exams.
"""

import json
import os
from datetime import datetime


def load_template_info(template_path):
    """
    Load template JSON and extract question information
    
    Args:
        template_path: Path to template JSON file
        
    Returns:
        Dictionary with template information
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    print("="*70)
    print("TEMPLATE LOADED")
    print("="*70)
    print(f"Template file: {template_path}")
    print(f"Total pages: {template_data['metadata']['total_pages']}")
    print(f"Total questions: {template_data['metadata']['total_questions']}")
    
    # Extract question details
    questions_info = []
    
    for page_key in sorted(template_data.keys()):
        if page_key.startswith('page_'):
            page_data = template_data[page_key]
            
            for question in page_data['questions']:
                q_num = question['question_number']
                bubbles = [b['label'] for b in question['bubbles']]
                
                questions_info.append({
                    'question_number': q_num,
                    'bubbles': bubbles
                })
    
    # Display question info
    print(f"\nQuestions detected: {len(questions_info)}")
    print(f"Bubble options: {questions_info[0]['bubbles'] if questions_info else 'N/A'}")
    
    return {
        'template_path': template_path,
        'total_questions': len(questions_info),
        'questions_info': questions_info,
        'metadata': template_data['metadata']
    }


def create_answer_key_manual(template_info, output_dir='answer_keys'):
    """
    Create an answer key manually through console input
    
    Args:
        template_info: Dictionary with template information
        output_dir: Directory to save the answer key JSON
        
    Returns:
        Tuple of (answer_key dict, json_path)
    """
    print("\n" + "="*70)
    print("MANUAL ANSWER KEY CREATION")
    print("="*70)
    print(f"Total questions: {template_info['total_questions']}")
    
    # Get available bubble options from first question
    available_bubbles = template_info['questions_info'][0]['bubbles']
    bubbles_str = ", ".join(available_bubbles)
    
    print(f"Available options: {bubbles_str}")
    print("\nInstructions:")
    print(f"  - Enter the correct answer ({bubbles_str})")
    print(f"  - For multiple correct answers, separate with commas (e.g., A,C)")
    print("  - Press Enter to skip a question (no correct answer)")
    print()
    
    answer_key = {}
    
    for question_info in template_info['questions_info']:
        q_num = question_info['question_number']
        
        while True:
            answer_input = input(f"Question {q_num}: ").strip().upper()
            
            # Skip if empty
            if not answer_input:
                answer_key[q_num] = []
                break
            
            # Parse multiple answers (A,C or A, C)
            answers = [a.strip() for a in answer_input.replace(',', ' ').split()]
            
            # Validate answers against available bubbles
            if all(ans in available_bubbles for ans in answers):
                answer_key[q_num] = sorted(answers)
                break
            else:
                print(f"  Invalid input. Please enter only: {bubbles_str}")
    
    # Save to JSON
    json_path = save_answer_key_to_json(
        answer_key, 
        template_info, 
        output_dir,
        creation_method='manual'
    )
    
    return answer_key, json_path


def create_answer_key_from_scan(template_info, master_sheet_path, threshold_percent=50, output_dir='answer_keys'):
    """
    Create an answer key by scanning a filled master answer sheet
    
    Args:
        template_info: Dictionary with template information
        master_sheet_path: Path to filled master answer sheet image
        threshold_percent: Threshold for bubble detection (default: 50%)
        output_dir: Directory to save the answer key JSON
        
    Returns:
        Tuple of (answer_key dict, json_path)
    """
    print("\n" + "="*70)
    print("ANSWER KEY CREATION FROM SCANNED SHEET")
    print("="*70)
    print(f"Scanning master answer sheet: {master_sheet_path}")
    
    # Import here to avoid circular dependency
    from extraction import BubbleTemplate, AnswerExtractor
    
    # Load template
    template = BubbleTemplate(template_info['template_path'])
    
    # Extract answers from master sheet
    extractor = AnswerExtractor(template)
    questions = extractor.extract_answers(
        master_sheet_path,
        threshold_percent=threshold_percent,
        debug=True  # Show visualization to verify
    )
    
    if not questions:
        print("\n[ERROR] Failed to extract answers from master sheet")
        return None, None
    
    # Convert to answer key format
    answer_key = {}
    for question in questions:
        q_num = question.question_number
        answer_key[q_num] = question.get_answer()
    
    # Save to JSON
    json_path = save_answer_key_to_json(
        answer_key, 
        template_info, 
        output_dir,
        creation_method='scanned'
    )
    
    return answer_key, json_path


def save_answer_key_to_json(answer_key, template_info, output_dir='answer_keys', creation_method='manual'):
    """
    Save answer key to JSON file
    
    Args:
        answer_key: Dictionary with question numbers as keys and answers as values
        template_info: Template information dictionary
        output_dir: Directory to save the answer key
        creation_method: 'manual' or 'scanned'
        
    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare data structure
    key_data = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'creation_method': creation_method,
            'template_used': template_info['template_path'],
            'total_questions': template_info['total_questions']
        },
        'answer_key': {}
    }
    
    # Convert to string keys and ensure answers are lists
    for q_num, answers in answer_key.items():
        if not isinstance(answers, list):
            answers = [answers]
        key_data['answer_key'][str(q_num)] = sorted(answers)
    
    # Generate filename
    base_name = os.path.splitext(os.path.basename(template_info['template_path']))[0]
    json_filename = f"key_{base_name}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Save to JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(key_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] Answer key saved to: {json_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("ANSWER KEY SUMMARY")
    print("="*70)
    print(f"Template: {template_info['template_path']}")
    print(f"Total questions: {template_info['total_questions']}")
    answered = sum(1 for answers in answer_key.values() if answers)
    print(f"Questions with answers: {answered}/{template_info['total_questions']}")
    
    # Show first 10 answers
    print("\nFirst 10 answers:")
    for q_num in sorted(answer_key.keys())[:10]:
        answers = answer_key[q_num]
        if answers:
            answer_str = ", ".join(answers)
            print(f"  Question {q_num}: {answer_str}")
        else:
            print(f"  Question {q_num}: No answer")
    
    if len(answer_key) > 10:
        print(f"  ... and {len(answer_key) - 10} more questions")
    
    return json_path


def load_answer_key_from_json(json_path):
    """
    Load an answer key from JSON file
    
    Args:
        json_path: Path to answer key JSON file
        
    Returns:
        Dictionary with answer key data
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Answer key not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        key_data = json.load(f)
    
    print(f"[LOADED] Answer key: {json_path}")
    print(f"  Created: {key_data['metadata']['created_at']}")
    print(f"  Method: {key_data['metadata']['creation_method']}")
    print(f"  Template: {key_data['metadata']['template_used']}")
    print(f"  Total questions: {key_data['metadata']['total_questions']}")
    
    return key_data


def edit_answer_key(json_path):
    """
    Edit an existing answer key
    
    Args:
        json_path: Path to answer key JSON file
    """
    print("="*70)
    print("EDIT ANSWER KEY")
    print("="*70)
    
    # Load existing key
    key_data = load_answer_key_from_json(json_path)
    answer_key = key_data['answer_key']
    
    print("\nCurrent answers:")
    for q_num in sorted(answer_key.keys(), key=int):
        answers = answer_key[q_num]
        answer_str = ", ".join(answers) if answers else "No answer"
        print(f"  Question {q_num}: {answer_str}")
    
    print("\nEnter question numbers to edit (comma-separated), or 'done' to finish:")
    edit_input = input("> ").strip()
    
    if edit_input.lower() == 'done':
        return
    
    # Parse question numbers to edit
    questions_to_edit = [int(q.strip()) for q in edit_input.split(',') if q.strip().isdigit()]
    
    for q_num in questions_to_edit:
        q_key = str(q_num)
        if q_key not in answer_key:
            print(f"\nQuestion {q_num} not found, skipping...")
            continue
        
        current = ", ".join(answer_key[q_key]) if answer_key[q_key] else "No answer"
        print(f"\nQuestion {q_num} (current: {current})")
        new_answer = input("New answer (or comma-separated for multiple): ").strip().upper()
        
        if not new_answer:
            answer_key[q_key] = []
        else:
            answers = [a.strip() for a in new_answer.replace(',', ' ').split()]
            answer_key[q_key] = sorted(answers)
    
    # Save updated key
    key_data['answer_key'] = answer_key
    key_data['metadata']['last_modified'] = datetime.now().isoformat()
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(key_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] Updated answer key: {json_path}")


def main():
    """Main function - create answer key from template"""
    
    print("="*70)
    print("ANSWER KEY GENERATOR")
    print("="*70)
    
    # Step 1: Load template
    template_path = input("\nEnter template JSON path (press Enter for default): ").strip()
    if not template_path:
        template_path = 'template/answer_sheet_template.json'
    
    try:
        template_info = load_template_info(template_path)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        return
    
    # Step 2: Choose creation method
    print("\n" + "="*70)
    print("CHOOSE ANSWER KEY CREATION METHOD")
    print("="*70)
    print("1. Manual entry (type answers in console)")
    print("2. Scan master answer sheet (automatic detection)")
    print("3. Edit existing answer key")
    print("4. View existing answer key")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        # Manual entry
        answer_key, json_path = create_answer_key_manual(template_info)
        print(f"\nAnswer key created: {json_path}")
    
    elif choice == '2':
        # Scan master sheet
        master_sheet = input("\nEnter master answer sheet image path: ").strip()
        if not master_sheet:
            master_sheet = 'master_answer_sheet.png'
        
        if not os.path.exists(master_sheet):
            print(f"[ERROR] Master sheet not found: {master_sheet}")
            return
        
        threshold = input("Enter threshold percent (default 50): ").strip()
        threshold = int(threshold) if threshold else 50
        
        answer_key, json_path = create_answer_key_from_scan(
            template_info,
            master_sheet,
            threshold_percent=threshold
        )
        
        if json_path:
            print(f"\n[SUCCESS] Answer key created: {json_path}")
    
    elif choice == '3':
        # Edit existing key
        key_path = input("\nEnter answer key JSON path: ").strip()
        if os.path.exists(key_path):
            edit_answer_key(key_path)
        else:
            print(f"[ERROR] Answer key not found: {key_path}")
    
    elif choice == '4':
        # View existing key
        key_path = input("\nEnter answer key JSON path: ").strip()
        if os.path.exists(key_path):
            key_data = load_answer_key_from_json(key_path)
            print("\n" + "="*70)
            print("ANSWER KEY CONTENTS")
            print("="*70)
            for q_num in sorted(key_data['answer_key'].keys(), key=int):
                answers = key_data['answer_key'][q_num]
                answer_str = ", ".join(answers) if answers else "No answer"
                print(f"  Question {q_num}: {answer_str}")
        else:
            print(f"[ERROR] Answer key not found: {key_path}")
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()