# diagnostic.py
import json
import sys

def diagnose_loading_issue():
    """Diagnose how your app loads the answer key"""
    
    # Method 1: Direct loading (what your app might be doing)
    print("Method 1: Direct JSON loading")
    try:
        with open("files/answer_keys/Exam_1_20251206_160110.json", "r") as f:
            direct_data = json.load(f)
        print("✓ Direct load successful")
        print(f"  Type: {type(direct_data)}")
        print(f"  Top-level keys: {list(direct_data.keys())}")
    except Exception as e:
        print(f"✗ Direct load failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Method 2: Using your validation (what should work)
    print("Method 2: Using validation module")
    try:
        from validation import validate_answer_key_json
        valid, error, val_data, key_type = validate_answer_key_json(
            "files/answer_keys/Exam_1_20251206_160110.json", 
            is_complete_exam=True
        )
        if valid:
            print(f"✓ Validation successful")
            print(f"  Key type: {key_type}")
            print(f"  Data keys: {list(val_data.keys())}")
        else:
            print(f"✗ Validation failed: {error}")
    except ImportError as e:
        print(f"✗ Cannot import validation: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Check for common issues
    print("Common issue check:")
    
    # Issue: Trying to access individual key format
    print("\n1. Checking for individual key format access:")
    if 'metadata' in direct_data:
        if 'key_label' in direct_data['metadata']:
            print(f"  Has individual key label: {direct_data['metadata']['key_label']}")
        else:
            print(f"  No key_label (expected for complete exam)")
    
    # Issue: Missing 'mcq' or 'written' sections
    print("\n2. Checking for 'mcq' and 'written' sections:")
    print(f"  Has 'mcq' section: {'mcq' in direct_data}")
    print(f"  Has 'written' section: {'written' in direct_data}")
    print(f"  Has 'keys' section: {'keys' in direct_data}")
    
    # Issue: Question numbering
    print("\n3. Checking question numbering:")
    if 'keys' in direct_data and 'A' in direct_data['keys']:
        key_a = direct_data['keys']['A']
        if 'mcq_answers' in key_a:
            mcq_nums = list(key_a['mcq_answers'].keys())
            print(f"  MCQ question numbers: {mcq_nums[:5]}... (total: {len(mcq_nums)})")
            # Check if they're strings or integers
            print(f"  First key type: {type(mcq_nums[0]) if mcq_nums else 'N/A'}")
    
    return direct_data

if __name__ == "__main__":
    data = diagnose_loading_issue()
    
    print("\n" + "="*50)
    print("RECOMMENDED FIXES BASED ON FINDINGS:")
    print("="*50)
    
    if 'keys' in data and 'mcq' not in data:
        print("\n✅ Your data is in COMPLETE EXAM format")
        print("   Use: data['keys'][key_letter]['mcq_answers']")
        print("   NOT: data['mcq']['answer_key']")
    
    elif 'mcq' in data and 'keys' not in data:
        print("\n✅ Your data is in INDIVIDUAL KEY format")
        print("   Use: data['mcq']['answer_key']")
        print("   NOT: data['keys'][key_letter]['mcq_answers']")
    
    else:
        print("\n❓ Unable to determine format automatically")
        print("   Check your grading code's data access patterns")