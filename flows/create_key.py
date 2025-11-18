import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import Tk, Label, StringVar, IntVar, BooleanVar, NORMAL, DISABLED
import tempfile
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io
import threading
import json
import datetime

# Fix project root path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"[DEBUG] Project root: {PROJECT_ROOT}")

def get_parent_window():
    """Get reference to parent window if launched from home screen"""
    import tkinter as tk
    parent = None
    for widget in tk._default_root.winfo_children() if tk._default_root else []:
        if isinstance(widget, tk.Tk) and "Answer Sheet Grading System" in widget.title():
            parent = widget
            break
    return parent

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
        root.attributes('-topmost', True)

        start_dir = initial_dir or os.getcwd()
        file_path[0] = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=start_dir
        )
        root.destroy()
    
    thread = threading.Thread(target=open_dialog, daemon=True)
    thread.start()
    thread.join()
    
    if file_path[0]:
        return to_relative_path(file_path[0])
    return None

def create_key(template_json=None):
    """Main GUI for answer key creation with screen transitions"""
    
    # Initialize database
    db = None
    try:
        from core.database import GradingDatabase
        db = GradingDatabase()
        print("[DB] Database initialized successfully")
    except Exception as e:
        print(f"[DB] Warning: Could not initialize database: {e}")
    
    def main_gui():
        # Main window
        root = tk.Tk()
        root.title("Answer Key Creator")
        root.geometry("950x750")
        root.resizable(True, True)
        
        # Configure modern style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Color scheme
        BG_COLOR = "#f5f5f5"
        CARD_COLOR = "#ffffff"
        ACCENT_COLOR = "#0078d4"
        SUCCESS_COLOR = "#28a745"
        
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG_COLOR, font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background=BG_COLOR, font=("Segoe UI", 11, "bold"))
        style.configure("Card.TFrame", background=CARD_COLOR, relief="flat")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background=CARD_COLOR, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=CARD_COLOR, relief="flat", borderwidth=0)
        style.configure("TLabelframe.Label", background=CARD_COLOR, font=("Segoe UI", 10, "bold"))
        style.configure("Valid.TEntry", fieldbackground="#d4edda", relief="flat")
        style.configure("TEntry", relief="flat", padding=5)
        
        # Global variables
        current_template = None
        template_info = None
        total_questions = 0
        current_screen = None
        
        # UI state variables
        template_var = StringVar(value="No template loaded")
        questions_var = StringVar(value="--")
        status_var = StringVar(value="Ready to create answer key")
        
        # Main container for screen transitions
        main_container = tk.Frame(root, bg=BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        def load_template(file_path=None):
            """Load template from file"""
            nonlocal current_template, template_info, total_questions
            
            if not file_path:
                file_path = filedialog.askopenfilename(
                    title="Select Template JSON File",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialdir=PROJECT_ROOT
                )
            
            if file_path and os.path.exists(file_path):
                try:
                    from core.answer_key import load_template_info
                    template_info = load_template_info(file_path)
                    current_template = file_path
                    total_questions = template_info.get('total_questions', 0)
                    
                    # Update UI state
                    template_var.set(os.path.basename(file_path))
                    questions_var.set(str(total_questions))
                    status_var.set("Template loaded successfully ✓")
                    
                    # Refresh main screen to update button states
                    refresh_main_screen()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load template: {e}")
            else:
                status_var.set("No template selected")
        
        def show_screen(screen_name):
            """Transition between screens"""
            nonlocal current_screen
            
            # Hide current screen
            if current_screen:
                current_screen.destroy()
            
            # Show new screen
            if screen_name == "main":
                current_screen = create_main_screen()
            elif screen_name == "manual_entry":
                current_screen = create_manual_entry_screen()
            elif screen_name == "scan":
                current_screen = create_scan_screen()
            
            if current_screen:
                current_screen.pack(fill=tk.BOTH, expand=True)
        
        def refresh_main_screen():
            """Refresh the main screen to update button states"""
            if current_screen:
                show_screen("main")
        
        def create_main_screen():
            """Create the main selection screen"""
            frame = tk.Frame(main_container, bg=BG_COLOR)
            
            # Title
            title = tk.Label(frame, text="Answer Key Creator", 
                           font=("Segoe UI", 16, "bold"), bg=BG_COLOR, fg="#333")
            title.pack(pady=(0, 30))
            
            # Template card
            template_card = tk.Frame(frame, bg=CARD_COLOR, relief="flat")
            template_card.pack(fill=tk.X, pady=(0, 25))
            
            template_inner = tk.Frame(template_card, bg=CARD_COLOR)
            template_inner.pack(fill=tk.BOTH, padx=20, pady=20)
            
            tk.Label(template_inner, text="📋 Template Configuration", 
                    font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
            
            # Template info grid
            info_frame = tk.Frame(template_inner, bg=CARD_COLOR)
            info_frame.pack(fill=tk.X)
            
            tk.Label(info_frame, text="Template:", 
                    font=("Segoe UI", 9, "bold"), bg=CARD_COLOR).grid(row=0, column=0, sticky="w", padx=(0, 10))
            tk.Label(info_frame, textvariable=template_var, 
                    font=("Segoe UI", 9), bg=CARD_COLOR).grid(row=0, column=1, sticky="w")
            
            tk.Label(info_frame, text="Questions:", 
                    font=("Segoe UI", 9, "bold"), bg=CARD_COLOR).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5, 0))
            tk.Label(info_frame, textvariable=questions_var, 
                    font=("Segoe UI", 9), bg=CARD_COLOR).grid(row=1, column=1, sticky="w", pady=(5, 0))
            
            ttk.Button(template_inner, text="📂 Load Template", 
                      command=lambda: load_template()).pack(anchor="w", pady=(15, 0))
            
            # Method selection card
            method_card = tk.Frame(frame, bg=CARD_COLOR, relief="flat")
            method_card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            method_inner = tk.Frame(method_card, bg=CARD_COLOR)
            method_inner.pack(fill=tk.BOTH, padx=20, pady=20)
            
            tk.Label(method_inner, text="✨ Choose Creation Method", 
                    font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 20))
            
            # Method buttons
            methods_container = tk.Frame(method_inner, bg=CARD_COLOR)
            methods_container.pack(fill=tk.BOTH, expand=True)
            
            # Manual entry option
            manual_frame = tk.Frame(methods_container, bg=CARD_COLOR)
            manual_frame.pack(fill=tk.X, pady=(0, 15))
            
            manual_btn = ttk.Button(manual_frame, text="⌨️ Manual Entry", 
                                   command=lambda: show_screen("manual_entry"),
                                   state=NORMAL if current_template else DISABLED,
                                   width=25)
            manual_btn.pack(anchor="w", pady=(0, 5))
            
            tk.Label(manual_frame, text="Type answers for each question manually (supports multiple answers)",
                    font=("Segoe UI", 9), foreground="#666", 
                    bg=CARD_COLOR).pack(anchor="w")
            
            # Scan option
            scan_frame = tk.Frame(methods_container, bg=CARD_COLOR)
            scan_frame.pack(fill=tk.X)
            
            scan_btn = ttk.Button(scan_frame, text="📷 Scan Master Sheet", 
                                 command=lambda: show_screen("scan"),
                                 state=NORMAL if current_template else DISABLED,
                                 width=25)
            scan_btn.pack(anchor="w", pady=(0, 5))
            
            tk.Label(scan_frame, text="Automatically detect answers from filled sheet",
                    font=("Segoe UI", 9), foreground="#666",
                    bg=CARD_COLOR).pack(anchor="w")
            
            # Status bar
            status_frame = tk.Frame(frame, bg=BG_COLOR)
            status_frame.pack(fill=tk.X, side=tk.BOTTOM)
            
            tk.Label(status_frame, textvariable=status_var, 
                    font=("Segoe UI", 9), foreground="#666", bg=BG_COLOR).pack(side=tk.LEFT)
            
            ttk.Button(status_frame, text="Exit", 
                      command=root.destroy).pack(side=tk.RIGHT)
            
            return frame
        
        def create_manual_entry_screen():
            """Create the manual answer entry screen with multiple answer support"""
            frame = tk.Frame(main_container, bg=BG_COLOR)
            
            if not current_template or total_questions == 0:
                messagebox.showerror("Error", "Please load a template first")
                show_screen("main")
                return frame
            
            # Use dictionary to store answers in correct format
            answers = {}  # Format: {"1": ["A"], "2": ["B", "C"], ...}
            entries = []  # Store all entry widgets
            
            # Header
            header = tk.Frame(frame, bg=BG_COLOR)
            header.pack(fill=tk.X, pady=(0, 20))
            
            ttk.Button(header, text="← Back", 
                      command=lambda: show_screen("main")).pack(side=tk.LEFT)
            
            tk.Label(header, text="Manual Answer Entry", 
                    font=("Segoe UI", 16, "bold"), bg=BG_COLOR, fg="#333").pack(side=tk.LEFT, padx=(20, 0))
            
            info_label = tk.Label(header, 
                                 text=f"{os.path.basename(current_template)} • {total_questions} questions",
                                 font=("Segoe UI", 10), bg=BG_COLOR)
            info_label.pack(side=tk.RIGHT)
            
            # Progress card
            progress_card = tk.Frame(frame, bg=CARD_COLOR, relief="flat")
            progress_card.pack(fill=tk.X, pady=(0, 15))
            
            progress_inner = tk.Frame(progress_card, bg=CARD_COLOR)
            progress_inner.pack(fill=tk.BOTH, padx=20, pady=15)
            
            progress_var = StringVar(value="0")
            progress_text = tk.Label(progress_inner, 
                                    text="Progress:", 
                                    font=("Segoe UI", 10, "bold"),
                                    bg=CARD_COLOR)
            progress_text.pack(side=tk.LEFT)
            
            progress_label = tk.Label(progress_inner,
                                     textvariable=progress_var,
                                     font=("Segoe UI", 10),
                                     bg=CARD_COLOR)
            progress_label.pack(side=tk.LEFT, padx=(5, 0))
            
            progress_total = tk.Label(progress_inner,
                                     text=f"/ {total_questions} answered",
                                     font=("Segoe UI", 10),
                                     bg=CARD_COLOR)
            progress_total.pack(side=tk.LEFT)
            
            # Info label for multiple answers
            tk.Label(progress_inner,
                    text="Tip: Enter multiple answers as 'A,C' or 'B,D'",
                    font=("Segoe UI", 8),
                    fg="#666",
                    bg=CARD_COLOR).pack(side=tk.RIGHT)
            
            # Scrollable question area
            container = tk.Frame(frame, bg=CARD_COLOR, relief="flat")
            container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            canvas = tk.Canvas(container, bg=CARD_COLOR, highlightthickness=0)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=CARD_COLOR)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Calculate layout
            if total_questions <= 20:
                columns = 2
                max_per_column = (total_questions + 1) // 2
            else:
                columns = 3
                max_per_column = (total_questions + 2) // 3
            
            # Create question grid
            question_index = 0
            for col in range(columns):
                col_frame = tk.Frame(scrollable_frame, bg=CARD_COLOR)
                col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=15)
                
                remaining_questions = total_questions - question_index
                questions_in_column = min(max_per_column, remaining_questions)
                
                for row in range(questions_in_column):
                    question_num = question_index + 1
                    row_frame = tk.Frame(col_frame, bg=CARD_COLOR)
                    row_frame.pack(fill=tk.X, pady=4)
                    
                    tk.Label(row_frame, text=f"{question_num}.", 
                            width=4, anchor="e", 
                            font=("Segoe UI", 10, "bold"),
                            bg=CARD_COLOR).pack(side=tk.LEFT, padx=(0, 10))
                    
                    entry = ttk.Entry(row_frame, width=8, 
                                    font=("Segoe UI", 11), 
                                    justify="center")
                    entry.pack(side=tk.LEFT)
                    entries.append(entry)
                    
                    def make_answer_handler(q_num, e):
                        def on_answer_change(event=None):
                            answer_input = e.get().strip().upper()
                            
                            if not answer_input:
                                # Empty input
                                if str(q_num) in answers:
                                    del answers[str(q_num)]
                                e.config(style="TEntry")
                            else:
                                # Parse multiple answers (A,C or A, C or AC)
                                answer_list = []
                                cleaned = answer_input.replace(" ", "")
                                
                                if "," in cleaned:
                                    # Format: A,C or A,B,D
                                    parts = cleaned.split(",")
                                    for part in parts:
                                        if part in ['A', 'B', 'C', 'D']:
                                            answer_list.append(part)
                                else:
                                    # Single answer or concatenated (AC, BCD)
                                    for char in cleaned:
                                        if char in ['A', 'B', 'C', 'D']:
                                            answer_list.append(char)
                                
                                if answer_list:
                                    # Valid answers found
                                    answer_list = sorted(list(set(answer_list)))
                                    answers[str(q_num)] = answer_list
                                    e.config(style="Valid.TEntry")
                                else:
                                    # Invalid input
                                    messagebox.showwarning("Invalid Input", 
                                        "Please enter A, B, C, or D.\nFor multiple answers use: A,C or AC")
                                    e.delete(0, tk.END)
                                    if str(q_num) in answers:
                                        del answers[str(q_num)]
                                    e.config(style="TEntry")
                            
                            # Update progress
                            answered = len(answers)
                            progress_var.set(str(answered))
                            save_btn.config(state=NORMAL if answered == total_questions else DISABLED)
                        return on_answer_change
                    
                    def make_enter_handler(q_num):
                        def on_enter_press(event):
                            if str(q_num) in answers:
                                if q_num < total_questions and q_num < len(entries):
                                    entries[q_num].focus()
                        return on_enter_press
                    
                    entry.bind('<KeyRelease>', make_answer_handler(question_num, entry))
                    entry.bind('<Return>', make_enter_handler(question_num))
                    
                    question_index += 1
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Control buttons
            control_frame = tk.Frame(frame, bg=BG_COLOR)
            control_frame.pack(fill=tk.X)
            
            def auto_fill_pattern():
                for i in range(total_questions):
                    answer = ['A', 'B', 'C', 'D'][i % 4]
                    if i < len(entries):
                        entries[i].delete(0, tk.END)
                        entries[i].insert(0, answer)
                        answers[str(i + 1)] = [answer]
                        entries[i].config(style="Valid.TEntry")
                
                progress_var.set(str(total_questions))
                save_btn.config(state=NORMAL)
            
            def clear_all():
                for i, entry in enumerate(entries):
                    entry.delete(0, tk.END)
                    entry.config(style="TEntry")
                
                answers.clear()
                progress_var.set("0")
                save_btn.config(state=DISABLED)
                if entries:
                    entries[0].focus()
            
            def save_answer_key():
                if len(answers) < total_questions:
                    unanswered = [i+1 for i in range(total_questions) if str(i+1) not in answers]
                    messagebox.showerror("Error", 
                        f"Please answer all questions.\nMissing: {', '.join(map(str, unanswered[:10]))}")
                    return
                
                try:
                    answer_key_data = {
                        'metadata': {
                            'created_at': datetime.datetime.now().isoformat(),
                            'creation_method': 'manual',
                            'template_used': to_relative_path(current_template),
                            'total_questions': total_questions
                        },
                        'answer_key': answers
                    }
                    
                    filename = filedialog.asksaveasfilename(
                        title="Save Answer Key As",
                        defaultextension=".json",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                        initialfile=f"answer_key_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        initialdir=PROJECT_ROOT
                    )
                    
                    if filename:
                        if not filename.lower().endswith('.json'):
                            filename += '.json'
                        
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(answer_key_data, f, indent=2, ensure_ascii=False)
                        
                        # Log to database - UPDATED FOR CORRECTED SCHEMA
                        if db and current_template:
                            try:
                                # Convert absolute path to relative path for database lookup
                                template_relative_path = to_relative_path(current_template)
                                
                                # First, we need to find the template_id from the template path
                                template_info = db.get_template_by_json_path(template_relative_path)
                                if template_info:
                                    template_id = template_info['id']
                                    
                                    # Save answer key with proper template relationship
                                    key_id = db.save_answer_key(
                                        template_id=template_id,
                                        name=f"Manual Key {datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                        file_path=to_relative_path(filename),
                                        created_by='manual'
                                    )
                                    
                                    if key_id:
                                        print(f"[DB] Answer key saved with template_id: {template_id}, key_id: {key_id}")
                                    else:
                                        print(f"[DB] Failed to save answer key")
                                else:
                                    print(f"[DB] Template not found in database: {template_relative_path}")
                                    print(f"[DB] Available templates in database:")
                                    
                                    # Debug: List all templates in database
                                    try:
                                        cursor = db.conn.cursor()
                                        cursor.execute("SELECT id, name, json_path FROM templates")
                                        templates = cursor.fetchall()
                                        for template in templates:
                                            print(f"  - {template['json_path']} (ID: {template['id']})")
                                    except Exception as debug_e:
                                        print(f"[DB] Debug error: {debug_e}")
                                    
                                    # Try to create template record if not found
                                    try:
                                        print(f"[DB] Attempting to create template record...")
                                        template_name = os.path.basename(current_template).replace('.json', '')
                                        
                                        # First create a sheet record
                                        sheet_id = db.save_sheet(
                                            image_path=f"templates/{template_name}.pdf",  # Placeholder
                                            template_id=None,
                                            num_questions=total_questions,
                                            settings={'created_for_template': True}
                                        )
                                        
                                        if sheet_id:
                                            # Then create template record
                                            template_id = db.save_template(
                                                name=template_name,
                                                json_path=template_relative_path,
                                                sheet_id=sheet_id,
                                                total_questions=total_questions,
                                                has_student_id=True
                                            )
                                            
                                            if template_id:
                                                # Now save answer key with the new template
                                                key_id = db.save_answer_key(
                                                    template_id=template_id,
                                                    name=f"Manual Key {datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                                    file_path=to_relative_path(filename),
                                                    created_by='manual'
                                                )
                                                print(f"[DB] Created template and saved answer key: template_id={template_id}, key_id={key_id}")
                                            else:
                                                print(f"[DB] Failed to create template record")
                                        else:
                                            print(f"[DB] Failed to create sheet record")
                                            
                                    except Exception as create_e:
                                        print(f"[DB] Failed to create template: {create_e}")
                                        
                            except Exception as e:
                                print(f"[DB] Failed to save answer key to database: {e}")
                                # Try legacy method as fallback
                                try:
                                    if hasattr(db, 'log_answer_key_creation'):
                                        db.log_answer_key_creation(
                                            key_path=filename,
                                            template_path=current_template,
                                            num_questions=total_questions,
                                            creation_method='manual'
                                        )
                                        print(f"[DB] Used legacy method to save answer key")
                                except Exception as legacy_e:
                                    print(f"[DB] Legacy method also failed: {legacy_e}")
                        
                        messagebox.showinfo("Success", f"Answer key saved!\n{os.path.basename(filename)}")
                        show_screen("main")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save:\n{str(e)}")
            
            ttk.Button(control_frame, text="Auto Fill Pattern", 
                      command=auto_fill_pattern).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(control_frame, text="Clear All", 
                      command=clear_all).pack(side=tk.LEFT)
            
            ttk.Button(control_frame, text="Cancel", 
                      command=lambda: show_screen("main")).pack(side=tk.RIGHT, padx=(10, 0))
            
            save_btn = ttk.Button(control_frame, text="💾 Save Answer Key", 
                                 command=save_answer_key, 
                                 state=DISABLED,
                                 style="Accent.TButton")
            save_btn.pack(side=tk.RIGHT)
            
            if entries:
                root.after(100, lambda: entries[0].focus())
            
            return frame
        
        def create_scan_screen():
            """Create the scan screen - placeholder"""
            frame = tk.Frame(main_container, bg=BG_COLOR)
            
            ttk.Button(frame, text="← Back", 
                      command=lambda: show_screen("main")).pack(anchor="w")
            
            tk.Label(frame, text="Scan feature coming soon...",
                    font=("Segoe UI", 12), bg=BG_COLOR).pack(pady=50)
            
            return frame
        
        # Show main screen initially
        show_screen("main")
        
        # If template provided as argument, load it
        if template_json and os.path.exists(template_json):
            load_template(template_json)
        
        return root
    
    # Start the GUI
    root = main_gui()
    root.mainloop()

if __name__ == "__main__":
    create_key()