"""
Answer Sheet Grading System - Main Application Entry Point
Simple entry point that launches the home screen
"""
import os
import sys
import tkinter as tk

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def check_database():
    """Check if database exists and offer to create it"""
    db_path = os.path.join(PROJECT_ROOT, 'grading_system.db')
    
    if not os.path.exists(db_path):
        print("[INFO] Database not found.")
        print("[INFO] Please run: python database/init_db.py")
        
        try:
            response = input("\nCreate database now? (y/n): ").lower()
            if response == 'y':
                from database.init_db import create_database
                if create_database():
                    print("[SUCCESS] Database created successfully!")
                else:
                    print("[ERROR] Failed to create database")
                    return False
            else:
                print("[INFO] Please create database before running the app")
                return False
        except (KeyboardInterrupt, EOFError):
            print("\n[CANCELLED] Database creation cancelled")
            return False
    
    return True


def main():
    """Main entry point"""
    print("=" * 70)
    print("  ANSWER SHEET GRADING SYSTEM")
    print("=" * 70)
    
    # Check database
    if not check_database():
        sys.exit(1)
    
    # Create main window
    root = tk.Tk()
    
    # Import and create home screen
    try:
        from ui.home_screen import create_home_screen
        home = create_home_screen(root)
        print("[APP] Home screen loaded successfully")
        
        # Run application
        root.mainloop()
        
    except ImportError as e:
        print(f"[ERROR] Failed to import home_screen: {e}")
        print("[INFO] Make sure home_screen.py exists in the project root")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()