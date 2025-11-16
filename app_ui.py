import os
import threading
from src import create_sheet, create_key, extract_bubbles, grade_sheet, batch_grade
from tkinter import *
from tkinter import filedialog, Button
import tkinter as tk
from src import *

# Get project root (directory containing this app.py file)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def to_relative_path(absolute_path):
    """Convert absolute path to relative path from project root"""
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        # If paths are on different drives (Windows), return absolute path
        return absolute_path

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
        root = tk.Tk()
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

# Main Window
def main_menu_screen():
    root = Tk()
    # Title and size
    title = root.title("Answer Sheet Grading System")
    label = Label(root, text="Automatic Answer Sheet Grading System", font=("Lato", 18, "bold"))
    label.pack(pady=20)
    root.geometry("600x400")

    # Buttons
    btn_create_sheet = tk.Button(root, text="1. Create Blank Answer Sheet", command=create_sheet.create_sheet, width=40, height=2)
    btn_create_sheet.pack(pady=10)
    btn_extract_bubbles = tk.Button(root, text="2. Extract Bubble Positions from Template", command=extract_bubbles.extract_bubbles, width=40, height=2)
    btn_extract_bubbles.pack(pady=10)
    btn_create_key = tk.Button(root, text="3. Create Answer Key", command=create_key.create_key, width=40, height=2)
    btn_create_key.pack(pady=10)
    btn_grade_sheet = tk.Button(root, text="4. Grade Single Answer Sheet", command=grade_sheet.grade_sheet, width=40, height=2)
    btn_grade_sheet.pack(pady=10)
    btn_batch_grade = tk.Button(root, text="5. Batch Grade Multiple Answer Sheets",
                                    command=batch_grade.batch_grade, width=40, height=2)
    btn_batch_grade.pack(pady=10)

    root.mainloop()

def create_sheet_ui():
    return create_sheet.create_sheet()




if __name__ == "__main__":
    main_menu_screen()
