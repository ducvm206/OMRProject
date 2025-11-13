import os
import threading
from src import create_sheet, create_key, extract_bubbles, grade_sheet, batch_grade
from tkinter import Tk, filedialog

# Get project root (directory containing this app.py file)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def to_relative_path(absolute_path):
    """Convert absolute path to relative path from project root"""
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        # If paths are on different drives (Windows), return absolute path
        return absolute_path

print("\n" + "="*70)
print("Automatic Answer Sheet Grading System")
print("="*70)

def print_menu():
    print("\n1. Create blank answer sheet (PDF)")
    print("2. Create answer key (manual or scan master)")
    print("3. Extract bubble positions from template")
    print("4. Grade single answer sheet")
    print("5. Batch grade multiple answer sheets")
    print("6. Exit")

def select_file(title, filetypes, initial_dir=None):
    """Open file picker dialog and return relative path (non-blocking)"""
    file_path = [None]
    
    def open_dialog():
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring to front

        # Set default starting directory (fallback to current folder)
        start_dir = initial_dir or os.getcwd()
        file_path[0] = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=start_dir
        )
        root.destroy()
    
    thread = threading.Thread(target=open_dialog, daemon=True)
    thread.start()
    thread.join()  # Wait for dialog to close
    
    if file_path[0]:
        return to_relative_path(file_path[0])
    return None

def select_folder(title, initial_dir=None):
    """Open folder picker dialog and return relative path (non-blocking)"""
    folder_path = [None]
    
    def open_dialog():
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring to front
        folder_path[0] = filedialog.askdirectory(title=title)
        root.destroy()
    
    thread = threading.Thread(target=open_dialog, daemon=True)
    thread.start()
    thread.join()  # Wait for dialog to close
    
    if folder_path[0]:
        return to_relative_path(folder_path[0])
    return None

def main():
    while True:
        print_menu()
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            print("\n[INFO] Creating blank answer sheet...")
            create_sheet.create_sheet()
            print("[SUCCESS] Blank answer sheet created!")
        
        elif choice == '2':
            print("\n[INFO] Creating answer key...")
            template_json = select_file("Select template JSON", [("JSON files", "*.json")], initial_dir=os.path.join(PROJECT_ROOT, 'template'))
            create_key.create_key(template_json=template_json)
            print("[SUCCESS] Answer key created!")
        
        elif choice == '3':
            print("\n[INFO] Extracting bubble positions...")
            template_pdf = select_file("Select template PDF", [("PDF files", "*.pdf")], initial_dir=os.path.join(PROJECT_ROOT))
            if not template_pdf:
                print("[ERROR] No file selected")
                continue
            extract_bubbles.extract_bubbles(template_pdf)
            print("[SUCCESS] Bubble positions extracted!")
        
        elif choice == '4':
            print("\n[INFO] Grading single answer sheet...")
            template_json = select_file("Select template JSON", [("JSON files", "*.json")], initial_dir=os.path.join(PROJECT_ROOT, 'template'))
            if not template_json or not os.path.exists(template_json):
                print(f"[ERROR] Template JSON not found: {template_json}")
                continue
            
            key_json = select_file("Select answer key JSON", [("JSON files", "*.json")], initial_dir=os.path.join(PROJECT_ROOT, 'answer_keys'))
            if not key_json or not os.path.exists(key_json):
                print(f"[ERROR] Answer key JSON not found: {key_json}")
                continue
            
            answer_sheet = select_file("Select filled answer sheet image", [("Image files", "*.png *.jpg *.jpeg *.bmp")], initial_dir=os.path.join(PROJECT_ROOT))
            if not answer_sheet or not os.path.exists(answer_sheet):
                print(f"[ERROR] Answer sheet image not found: {answer_sheet}")
                continue
            
            threshold = input("Enter detection threshold (default 80): ").strip()
            threshold = int(threshold) if threshold else 80
            
            print("\n[INFO] Grading...")
            grade_sheet.grade_sheet(template_json, key_json, answer_sheet, threshold)
            print("[SUCCESS] Grading complete!")
        
        elif choice == '5':
            print("\n[INFO] Batch grading answer sheets...")
            template_json = select_file("Select template JSON", [("JSON files", "*.json")], initial_dir=os.path.join(PROJECT_ROOT, 'template'))
            if not template_json or not os.path.exists(template_json):
                print(f"[ERROR] Template JSON not found: {template_json}")
                continue
            
            key_json = select_file("Select answer key JSON", [("JSON files", "*.json")], initial_dir=os.path.join(PROJECT_ROOT, 'answer_keys'))
            if not key_json or not os.path.exists(key_json):
                print(f"[ERROR] Answer key JSON not found: {key_json}")
                continue
            
            images_dir = select_folder("Select folder containing answer sheet images", initial_dir=os.path.join(PROJECT_ROOT))
            if not images_dir or not os.path.isdir(images_dir):
                print(f"[ERROR] Images directory not found: {images_dir}")
                continue
            
            output_csv = input("Enter path to output CSV file (default: grades_report.csv): ").strip()
            if not output_csv:
                output_csv = 'grades_report.csv'
            if os.path.isabs(output_csv):
                output_csv = to_relative_path(output_csv)
            
            threshold = input("Enter detection threshold (default 50): ").strip()
            threshold = int(threshold) if threshold else 50
            
            print("\n[INFO] Starting batch grading...")
            batch_grade.batch_grade(template_json, key_json, images_dir, output_csv, threshold)
            print(f"[SUCCESS] Results saved to: {output_csv}")
        
        elif choice == '6':
            print("\nExiting...")
            break
        
        else:
            print("[ERROR] Invalid choice. Please try again.")

if __name__ == "__main__":
    main()