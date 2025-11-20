"""
Setup Verification Script
Run this to check if all components are properly installed
"""
import os
import sys

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def check_mark(success):
    return "✓" if success else "✗"

def test_directory_structure():
    """Check if all required directories exist"""
    print_header("CHECKING DIRECTORY STRUCTURE")
    
    required_dirs = ['utils', 'flows', 'ui', 'database', 'core']
    all_exist = True
    
    for dir_name in required_dirs:
        exists = os.path.isdir(dir_name)
        print(f"  {check_mark(exists)} {dir_name}/")
        if not exists:
            all_exist = False
            print(f"      → Missing! Please create this directory")
    
    return all_exist

def test_required_files():
    """Check if all required files exist"""
    print_header("CHECKING REQUIRED FILES")
    
    required_files = [
        'utils/__init__.py',
        'utils/db_operations.py',
        'utils/file_utils.py',
        'utils/validation.py',
        'flows/__init__.py',
        'flows/key_flow.py',
        'flows/sheet_flow.py',
        'flows/grading_flow.py',
        'ui/__init__.py',
        'ui/key_ui.py',
        'ui/sheet_ui.py',
        'ui/grading_ui.py',
        'database/schema.sql',
        'database/init_db.py',
        'app.py'
    ]
    
    all_exist = True
    
    for file_path in required_files:
        exists = os.path.isfile(file_path)
        size = os.path.getsize(file_path) if exists else 0
        
        print(f"  {check_mark(exists)} {file_path:40s}", end="")
        if exists:
            print(f" ({size:,} bytes)")
        else:
            print(f" → Missing!")
            all_exist = False
    
    return all_exist

def test_imports():
    """Test if all modules can be imported"""
    print_header("TESTING MODULE IMPORTS")
    
    tests = [
        ('utils', 'get_db_operations'),
        ('utils', 'select_file'),
        ('utils', 'validate_number_of_questions'),
        ('flows', 'AnswerKeyFlow'),
        ('flows', 'SheetGenerationFlow'),
        ('flows', 'GradingFlow'),
        ('ui', 'create_answer_key_ui'),
        ('ui', 'create_sheet_ui'),
        ('ui', 'create_grading_ui'),
    ]
    
    all_success = True
    
    for module, item in tests:
        try:
            exec(f"from {module} import {item}")
            print(f"  ✓ from {module} import {item}")
        except ImportError as e:
            print(f"  ✗ from {module} import {item}")
            print(f"      Error: {e}")
            all_success = False
        except Exception as e:
            print(f"  ✗ from {module} import {item}")
            print(f"      Unexpected error: {e}")
            all_success = False
    
    return all_success

def test_core_modules():
    """Test if core modules exist"""
    print_header("CHECKING CORE MODULES")
    
    core_files = [
        'core/answer_key.py',
        'core/bubble_extraction.py',
        'core/extraction.py',
        'core/grading.py',
        'core/sheet_maker.py',
    ]
    
    all_exist = True
    
    for file_path in core_files:
        exists = os.path.isfile(file_path)
        print(f"  {check_mark(exists)} {file_path:40s}")
        if not exists:
            print(f"      → This core module is needed!")
            all_exist = False
    
    # Try importing database
    try:
        from core.database import GradingDatabase
        print(f"  ✓ core.database.GradingDatabase")
    except ImportError as e:
        print(f"  ✗ core.database.GradingDatabase")
        print(f"      Error: {e}")
        all_exist = False
    
    return all_exist

def test_python_packages():
    """Test if required Python packages are installed"""
    print_header("CHECKING PYTHON PACKAGES")
    
    packages = [
        ('PIL', 'pillow'),
        ('cv2', 'opencv-python'),
        ('fitz', 'PyMuPDF'),
        ('numpy', 'numpy'),
    ]
    
    all_installed = True
    
    for module, package in packages:
        try:
            __import__(module)
            print(f"  ✓ {package:20s} (import {module})")
        except ImportError:
            print(f"  ✗ {package:20s} (import {module})")
            print(f"      → Install with: pip install {package}")
            all_installed = False
    
    return all_installed

def test_database():
    """Test database"""
    print_header("CHECKING DATABASE")
    
    db_path = 'grading_system.db'
    exists = os.path.isfile(db_path)
    
    print(f"  {check_mark(exists)} Database file: {db_path}")
    
    if exists:
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"      Size: {size_mb:.2f} MB")
        
        # Try to connect
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = cursor.fetchall()
            
            if tables:
                print(f"      Tables: {len(tables)}")
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    print(f"        - {table[0]:20s} {count:>5} records")
            else:
                print(f"      No tables found - run: python database/init_db.py")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"      Error connecting: {e}")
            return False
    else:
        print(f"      → Create with: python database/init_db.py")
        return False

def provide_recommendations():
    """Provide setup recommendations"""
    print_header("RECOMMENDATIONS")
    
    if not os.path.isfile('grading_system.db'):
        print("  1. Initialize database:")
        print("     python database/init_db.py --sample-data")
    
    print("\n  2. Test the application:")
    print("     python app.py")
    
    print("\n  3. Or test individual components:")
    print("     python ui/key_ui.py      # Answer key creator")
    print("     python ui/sheet_ui.py    # Sheet generator")
    print("     python ui/grading_ui.py  # Grading interface")
    
    print("\n  4. If you encounter import errors:")
    print("     - Make sure all __init__.py files exist")
    print("     - Run from project root directory")
    print("     - Check file names match exactly (case-sensitive)")

def main():
    """Main verification routine"""
    print("\n" + "█" * 70)
    print("█  ANSWER SHEET GRADING SYSTEM - SETUP VERIFICATION")
    print("█" * 70)
    
    print(f"\nPython Version: {sys.version}")
    print(f"Current Directory: {os.getcwd()}")
    
    # Run all tests
    results = {
        'Directory Structure': test_directory_structure(),
        'Required Files': test_required_files(),
        'Module Imports': test_imports(),
        'Core Modules': test_core_modules(),
        'Python Packages': test_python_packages(),
        'Database': test_database(),
    }
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {test_name:25s} [{status}]")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("  🎉 ALL CHECKS PASSED! 🎉")
        print("=" * 70)
        print("\n  You're ready to run the application:")
        print("  python app.py")
    else:
        print("  ⚠️  SOME CHECKS FAILED")
        print("=" * 70)
        print("\n  Please fix the issues above before running the application.")
        provide_recommendations()
    
    print("\n")

if __name__ == "__main__":
    main()