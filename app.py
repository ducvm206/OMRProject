"""
Answer Sheet Grading System
Main application entry point
"""

import os
import sys

# Set up project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def main():
    """Launch the Answer Sheet Grading System"""
    try:
        print("=" * 60)
        print("Answer Sheet Grading System")
        print("=" * 60)
        print(f"Project Root: {PROJECT_ROOT}")
        print("Starting application...\n")
        
        # Import and launch home screen
        from flows.home_screen import create_home_screen
        
        root = create_home_screen()
        root.mainloop()
        
        print("\nApplication closed.")
        
    except KeyboardInterrupt:
        print("\n\nApplication closed by user (Ctrl+C)")
        sys.exit(0)
        
    except ImportError as e:
        print(f"\n[ERROR] Failed to import required modules:")
        print(f"  {e}")
        print("\nPlease ensure all dependencies are installed:")
        print("  pip install pillow opencv-python numpy pymupdf")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n[ERROR] Application failed to start:")
        print(f"  {e}")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()