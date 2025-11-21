"""
Answer Key Creation UI
Pure UI components for answer key creation
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, StringVar, NORMAL, DISABLED

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.file_utils import select_file, get_project_root
from utils.validation import validate_answer_input
from flows.key_flow import AnswerKeyFlow


class AnswerKeyUI:
    """UI for answer key creation"""
    
    def __init__(self, root):
        """
        Initialize UI
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.flow = AnswerKeyFlow()
        
        # UI State
        self.template_var = StringVar(value="No template loaded")
        self.questions_var = StringVar(value="--")
        self.progress_var = StringVar(value="0")
        self.status_var = StringVar(value="Ready to create answer key")
        
        # Entry widgets
        self.entries = []
        
        # Setup UI
        self.setup_window()
        self.create_ui()
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("Answer Key Creator")
        self.root.geometry("950x750")
        self.root.resizable(True, True)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colors
        self.BG_COLOR = "#f5f5f5"
        self.CARD_COLOR = "#ffffff"
        
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabel", background=self.BG_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.CARD_COLOR, relief="flat")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Valid.TEntry", fieldbackground="#d4edda", relief="flat")
        style.configure("TEntry", relief="flat", padding=5)
    
    def create_ui(self):
        """Create main UI components"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_container, text="Answer Key Creator", 
                        font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333")
        title.pack(pady=(0, 30))
        
        # Template card
        self.create_template_card(main_container)
        
        # Answer entry card (initially hidden)
        self.answer_frame = tk.Frame(main_container, bg=self.BG_COLOR)
        self.answer_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.create_status_bar(main_container)
    
    def create_template_card(self, parent):
        """Create template selection card"""
        template_card = tk.Frame(parent, bg=self.CARD_COLOR, relief="flat")
        template_card.pack(fill=tk.X, pady=(0, 25))
        
        template_inner = tk.Frame(template_card, bg=self.CARD_COLOR)
        template_inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(template_inner, text="📋 Template Configuration", 
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
        
        # Template info grid
        info_frame = tk.Frame(template_inner, bg=self.CARD_COLOR)
        info_frame.pack(fill=tk.X)
        
        tk.Label(info_frame, text="Template:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR).grid(row=0, column=0, sticky="w", padx=(0, 10))
        tk.Label(info_frame, textvariable=self.template_var, 
                font=("Segoe UI", 9), bg=self.CARD_COLOR).grid(row=0, column=1, sticky="w")
        
        tk.Label(info_frame, text="Questions:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5, 0))
        tk.Label(info_frame, textvariable=self.questions_var, 
                font=("Segoe UI", 9), bg=self.CARD_COLOR).grid(row=1, column=1, sticky="w", pady=(5, 0))
        
        ttk.Button(template_inner, text="📂 Load Template", 
                  command=self.on_load_template).pack(anchor="w", pady=(15, 0))
    
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        status_frame = tk.Frame(parent, bg=self.BG_COLOR)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(15, 0))
        
        tk.Label(status_frame, textvariable=self.status_var, 
                font=("Segoe UI", 9), foreground="#666", bg=self.BG_COLOR).pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Exit", 
                  command=self.root.destroy).pack(side=tk.RIGHT)
    
    def on_load_template(self):
        """Handle template loading"""
        template_dir = os.path.join(get_project_root(), 'template')
        
        template_path = select_file(
            title="Select Template JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initial_dir=template_dir,
            return_relative=True
        )
        
        if not template_path:
            return
        
        # Load via flow
        success, error, template_info = self.flow.load_template(template_path)
        
        if not success:
            messagebox.showerror("Error", f"Failed to load template:\n{error}")
            return
        
        # Update UI
        self.template_var.set(template_info['name'])
        self.questions_var.set(str(template_info['total_questions']))
        self.status_var.set("Template loaded successfully ✓")
        
        # Show answer entry UI
        self.show_answer_entry_ui()
    
    def show_answer_entry_ui(self):
        """Show the answer entry UI"""
        # Clear existing
        for widget in self.answer_frame.winfo_children():
            widget.destroy()
        
        # Progress card
        progress_card = tk.Frame(self.answer_frame, bg=self.CARD_COLOR, relief="flat")
        progress_card.pack(fill=tk.X, pady=(0, 15))
        
        progress_inner = tk.Frame(progress_card, bg=self.CARD_COLOR)
        progress_inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        progress_text = tk.Label(progress_inner, text="Progress:", 
                                font=("Segoe UI", 10, "bold"), bg=self.CARD_COLOR)
        progress_text.pack(side=tk.LEFT)
        
        progress_label = tk.Label(progress_inner, textvariable=self.progress_var,
                                 font=("Segoe UI", 10), bg=self.CARD_COLOR)
        progress_label.pack(side=tk.LEFT, padx=(5, 0))
        
        progress_total = tk.Label(progress_inner, 
                                 text=f"/ {self.flow.total_questions} answered",
                                 font=("Segoe UI", 10), bg=self.CARD_COLOR)
        progress_total.pack(side=tk.LEFT)
        
        tk.Label(progress_inner, text="Tip: Enter multiple answers as 'A,C' or 'B,D'",
                font=("Segoe UI", 8), fg="#666", bg=self.CARD_COLOR).pack(side=tk.RIGHT)
        
        # Scrollable question area
        container = tk.Frame(self.answer_frame, bg=self.CARD_COLOR, relief="flat")
        container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        canvas = tk.Canvas(container, bg=self.CARD_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.CARD_COLOR)
        
        scrollable_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create question entries
        self.create_question_entries(scrollable_frame)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control buttons
        self.create_control_buttons(self.answer_frame)
    
    def create_question_entries(self, parent):
        """Create entry fields for questions"""
        total_q = self.flow.total_questions
        
        # Calculate layout
        if total_q <= 20:
            columns = 2
            max_per_column = (total_q + 1) // 2
        else:
            columns = 3
            max_per_column = (total_q + 2) // 3
        
        self.entries = []
        question_index = 0
        
        for col in range(columns):
            col_frame = tk.Frame(parent, bg=self.CARD_COLOR)
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=15)
            
            remaining = total_q - question_index
            questions_in_col = min(max_per_column, remaining)
            
            for row in range(questions_in_col):
                q_num = question_index + 1
                row_frame = tk.Frame(col_frame, bg=self.CARD_COLOR)
                row_frame.pack(fill=tk.X, pady=4)
                
                tk.Label(row_frame, text=f"{q_num}.", width=4, anchor="e",
                        font=("Segoe UI", 10, "bold"), bg=self.CARD_COLOR).pack(side=tk.LEFT, padx=(0, 10))
                
                entry = ttk.Entry(row_frame, width=8, font=("Segoe UI", 11), justify="center")
                entry.pack(side=tk.LEFT)
                self.entries.append(entry)
                
                # Bind events
                entry.bind('<KeyRelease>', lambda e, q=q_num, ent=entry: self.on_answer_change(q, ent))
                entry.bind('<Return>', lambda e, q=q_num: self.on_enter_press(q))
                
                question_index += 1
    
    def create_control_buttons(self, parent):
        """Create control buttons"""
        control_frame = tk.Frame(parent, bg=self.BG_COLOR)
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="Auto Fill Pattern", 
                  command=self.on_auto_fill).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Clear All", 
                  command=self.on_clear_all).pack(side=tk.LEFT)
        
        ttk.Button(control_frame, text="Cancel", 
                  command=self.root.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        
        self.save_btn = ttk.Button(control_frame, text="💾 Save Answer Key", 
                                   command=self.on_save, 
                                   state=DISABLED,
                                   style="Accent.TButton")
        self.save_btn.pack(side=tk.RIGHT)
    
    def on_answer_change(self, question_num, entry):
        """Handle answer input change"""
        answer_input = entry.get().strip().upper()
        
        if not answer_input:
            # Clear answer
            if str(question_num) in self.flow.answers:
                del self.flow.answers[str(question_num)]
            entry.config(style="TEntry")
        else:
            # Validate and parse
            valid, error, answer_list = validate_answer_input(answer_input)
            
            if valid and answer_list:
                # Save to flow
                self.flow.set_answer(question_num, answer_list)
                entry.config(style="Valid.TEntry")
            else:
                if error:
                    messagebox.showwarning("Invalid Input", error)
                    entry.delete(0, tk.END)
                entry.config(style="TEntry")
        
        # Update progress
        self.update_progress()
    
    def on_enter_press(self, question_num):
        """Handle Enter key press"""
        if str(question_num) in self.flow.answers:
            if question_num < self.flow.total_questions and question_num < len(self.entries):
                self.entries[question_num].focus()
    
    def update_progress(self):
        """Update progress display"""
        progress = self.flow.get_progress()
        self.progress_var.set(str(progress['answered']))
        
        # Enable/disable save button
        self.save_btn.config(state=NORMAL if progress['is_complete'] else DISABLED)
    
    def on_auto_fill(self):
        """Handle auto-fill button"""
        success, error = self.flow.auto_fill_pattern('sequential')
        
        if success:
            # Update all entries
            for i, entry in enumerate(self.entries):
                q_num = str(i + 1)
                if q_num in self.flow.answers:
                    entry.delete(0, tk.END)
                    entry.insert(0, ','.join(self.flow.answers[q_num]))
                    entry.config(style="Valid.TEntry")
            
            self.update_progress()
        else:
            messagebox.showerror("Error", error)
    
    def on_clear_all(self):
        """Handle clear all button"""
        self.flow.clear_answers()
        
        for entry in self.entries:
            entry.delete(0, tk.END)
            entry.config(style="TEntry")
        
        self.update_progress()
        
        if self.entries:
            self.entries[0].focus()
    
    def on_save(self):
        """Handle save button"""
        # Validate
        valid, error, missing = self.flow.validate_answers()
        if not valid:
            messagebox.showerror("Error", error)
            return
        
        # Save
        success, error, saved_path = self.flow.save_answer_key()
        
        if success:
            messagebox.showinfo("Success", 
                f"Answer key saved successfully!\n\n{os.path.basename(saved_path)}")
            self.root.destroy()
        else:
            messagebox.showerror("Error", f"Failed to save:\n{error}")
    
    def run(self):
        """Run the UI"""
        self.root.mainloop()


def create_answer_key_ui():
    """Create and run answer key UI"""
    root = tk.Tk()
    ui = AnswerKeyUI(root)
    ui.run()


if __name__ == "__main__":
    create_answer_key_ui()