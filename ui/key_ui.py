"""
Answer Key Creation UI
Pure UI components for answer key creation with MCQ and Written sections
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, StringVar, IntVar, NORMAL, DISABLED

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.file_utils import select_file, get_project_root
from utils.validation import validate_filename
from flows.key_flow import AnswerKeyFlow


class AnswerKeyUI:
    """UI for answer key creation with MCQ and Written sections"""
    
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
        self.mcq_count_var = IntVar(value=0)
        self.written_count_var = IntVar(value=0)
        self.mcq_progress_var = StringVar(value="0")
        self.written_progress_var = StringVar(value="0")
        self.status_var = StringVar(value="Ready to create answer key")
        
        # Available question counts from template
        self.mcq_available = 0
        self.written_available = 0
        
        # Entry widgets
        self.mcq_entries = []
        self.written_entries = []
        
        # Setup UI
        self.setup_window()
        self.create_ui()
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("Answer Key Creator - MCQ & Written Answers")
        
        # Make window fullscreen or very large
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Use 90% of screen size
        width = int(screen_width * 0.9)
        height = int(screen_height * 0.9)
        
        # Center the window
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(True, True)
        
        # Set minimum window size
        self.root.minsize(1400, 800)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colors
        self.BG_COLOR = "#f5f5f5"
        self.CARD_COLOR = "#ffffff"
        self.MCQ_COLOR = "#e3f2fd"  # Light blue
        self.WRITTEN_COLOR = "#fff3e0"  # Light orange
        
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabel", background=self.BG_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.CARD_COLOR, relief="flat")
        style.configure("MCQ.TFrame", background=self.MCQ_COLOR)
        style.configure("Written.TFrame", background=self.WRITTEN_COLOR)
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Valid.TEntry", fieldbackground="#d4edda", relief="flat")
        style.configure("TEntry", relief="flat", padding=5)
    
    def create_ui(self):
        """Create main UI components"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 5))
        
        # Title
        title = tk.Label(main_container, text="Answer Key Creator", 
                        font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333")
        title.pack(pady=(0, 20))
        
        # Template card
        self.create_template_card(main_container)
        
        # Configuration card (shown after template loaded)
        self.config_frame = tk.Frame(main_container, bg=self.BG_COLOR)
        self.config_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Answer entry area (initially hidden)
        self.answer_frame = tk.Frame(main_container, bg=self.BG_COLOR)
        self.answer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Status bar
        self.create_status_bar(main_container)
    
    def create_template_card(self, parent):
        """Create template selection card"""
        template_card = tk.Frame(parent, bg=self.CARD_COLOR, relief="flat")
        template_card.pack(fill=tk.X, pady=(0, 5))
        
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
        
        tk.Label(info_frame, text="Total Questions:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5, 0))
        tk.Label(info_frame, textvariable=self.questions_var, 
                font=("Segoe UI", 9), bg=self.CARD_COLOR).grid(row=1, column=1, sticky="w", pady=(5, 0))
        
        ttk.Button(template_inner, text="📂 Load Template", 
                  command=self.on_load_template).pack(anchor="w", pady=(15, 0))
    
    def create_config_card(self):
        """Create question count configuration card"""
        # Clear existing
        for widget in self.config_frame.winfo_children():
            widget.destroy()
        
        config_card = tk.Frame(self.config_frame, bg=self.CARD_COLOR, relief="flat")
        config_card.pack(fill=tk.X)
        
        config_inner = tk.Frame(config_card, bg=self.CARD_COLOR)
        config_inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(config_inner, text="⚙️ Question Scoring Configuration", 
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
        
        tk.Label(config_inner, text="Specify the maximum total points for each section:", 
                font=("Segoe UI", 9), bg=self.CARD_COLOR, fg="#666").pack(anchor="w", pady=(0, 5))
        
        tk.Label(config_inner, text="Points per question = Max Points ÷ Number of Questions", 
                font=("Segoe UI", 9, "italic"), bg=self.CARD_COLOR, fg="#999").pack(anchor="w", pady=(0, 10))
        
        # Input grid
        input_frame = tk.Frame(config_inner, bg=self.CARD_COLOR)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        
        # MCQ section
        tk.Label(input_frame, text="MCQ Max Points:", 
                font=("Segoe UI", 10, "bold"), bg=self.CARD_COLOR).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.mcq_spinbox = ttk.Spinbox(input_frame, from_=0, to=1000, 
                                       textvariable=self.mcq_count_var, width=10)
        self.mcq_spinbox.grid(row=0, column=1, sticky="w")
        
        self.mcq_info_label = tk.Label(input_frame, text=f"({self.mcq_available} MCQ questions available)", 
                font=("Segoe UI", 8), bg=self.CARD_COLOR, fg="#666")
        self.mcq_info_label.grid(row=0, column=2, sticky="w", padx=(10, 0))
        
        # Written section
        tk.Label(input_frame, text="Written Max Points:", 
                font=("Segoe UI", 10, "bold"), bg=self.CARD_COLOR).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        self.written_spinbox = ttk.Spinbox(input_frame, from_=0, to=1000, 
                                           textvariable=self.written_count_var, width=10)
        self.written_spinbox.grid(row=1, column=1, sticky="w", pady=(10, 0))
        
        self.written_info_label = tk.Label(input_frame, text=f"({self.written_available} written questions available)", 
                font=("Segoe UI", 8), bg=self.CARD_COLOR, fg="#666")
        self.written_info_label.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(10, 0))
        
        # Bind spinbox changes
        self.mcq_count_var.trace_add('write', self.on_count_change)
        self.written_count_var.trace_add('write', self.on_count_change)
        
        # Continue button
        self.continue_btn = ttk.Button(config_inner, text="Continue to Answer Entry", 
                                      command=self.on_configure_sections,
                                      style="Accent.TButton")
        self.continue_btn.pack(anchor="w", pady=(10, 0))
    
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        status_frame = tk.Frame(parent, bg=self.BG_COLOR)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(15, 0))
        
        tk.Label(status_frame, textvariable=self.status_var, 
                font=("Segoe UI", 9), foreground="#666", bg=self.BG_COLOR).pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Exit", 
                  command=self.root.destroy).pack(side=tk.RIGHT)
    
    def on_count_change(self, *args):
        """Handle count change safely (Spinbox may return empty string)"""
        
        def safe_int(var):
            try:
                value = var.get()
                return int(value)
            except Exception:
                return 0

        mcq_points = safe_int(self.mcq_count_var)
        written_points = safe_int(self.written_count_var)

        # Calculate points per question
        mcq_per_q = (mcq_points / self.mcq_available) if self.mcq_available > 0 and mcq_points > 0 else 0
        written_per_q = (written_points / self.written_available) if self.written_available > 0 and written_points > 0 else 0

        # Update MCQ label
        if mcq_points > 0:
            self.mcq_info_label.config(
                text=f"({self.mcq_available} questions × {mcq_per_q:.2f} points each)"
            )
        else:
            self.mcq_info_label.config(text=f"({self.mcq_available} MCQ questions available)")

        # Update Written label
        if written_points > 0:
            self.written_info_label.config(
                text=f"({self.written_available} questions × {written_per_q:.2f} points each)"
            )
        else:
            self.written_info_label.config(text=f"({self.written_available} written questions available)")

        # Validation
        if mcq_points == 0 and written_points == 0:
            self.status_var.set("⚠️ At least one section must have points")
            self.continue_btn.config(state=tk.DISABLED)
        else:
            total_points = mcq_points + written_points
            self.status_var.set(f"✓ Total exam worth: {total_points} points ({mcq_points} MCQ + {written_points} Written)")
            self.continue_btn.config(state=tk.NORMAL)
    
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
        total_q = template_info['total_questions']
        mcq_avail = template_info.get('mcq_questions_available', 0)
        written_avail = template_info.get('written_questions_available', 0)
        
        self.questions_var.set(f"{total_q} ({mcq_avail} MCQ + {written_avail} Written available)")
        self.status_var.set("Template loaded successfully ✓")
        
        # Store available counts for validation
        self.mcq_available = mcq_avail
        self.written_available = written_avail
        
        # Show configuration card
        self.create_config_card()
    
    def on_configure_sections(self):
        mcq_points = self.mcq_count_var.get()
        written_points = self.written_count_var.get()

        success, error = self.flow.set_question_counts(mcq_points, written_points)
        if not success:
            messagebox.showerror("Error", error)
            return

        # ❗ Destroy entire config frame so it leaves no empty space
        self.config_frame.destroy()

        # Recreate a new blank frame so layout remains consistent if needed later
        self.config_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.config_frame.pack_forget()

        # Make answer frame take its place with no gap
        self.answer_frame.pack_forget()
        self.answer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        self.show_answer_entry_ui()


    
    def show_answer_entry_ui(self):
        """Show the answer entry UI with two panels"""
        # Clear existing
        for widget in self.answer_frame.winfo_children():
            widget.destroy()
        
        # Create two-panel layout - IMPORTANT: Give it weight to expand
        panels_container = tk.Frame(self.answer_frame, bg=self.BG_COLOR)
        panels_container.pack(fill=tk.BOTH, expand=True, pady=0)
        
        # Configure grid weights so panels expand properly
        panels_container.grid_rowconfigure(0, weight=1)
        panels_container.grid_columnconfigure(0, weight=1)
        panels_container.grid_columnconfigure(1, weight=1)
        
        # MCQ Panel (Left) - Use grid instead of pack
        if self.flow.mcq_count > 0:
            self.create_mcq_panel_grid(panels_container, column=0)
        
        # Written Panel (Right) - Use grid instead of pack
        if self.flow.written_count > 0:
            col = 1 if self.flow.mcq_count > 0 else 0
            self.create_written_panel_grid(panels_container, column=col)
        
        # Control buttons
        self.create_control_buttons(self.answer_frame)
    
    def create_mcq_panel_grid(self, parent, column):
        """Create MCQ answer entry panel using grid layout"""
        mcq_panel = tk.Frame(parent, bg=self.MCQ_COLOR, relief="flat")
        mcq_panel.grid(row=0, column=column, sticky="nsew", padx=(0, 5 if column == 0 else 0))
        
        # Configure row weight so scrollable area expands
        mcq_panel.grid_rowconfigure(2, weight=10) # Row 2 is the scrollable area
        mcq_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header = tk.Frame(mcq_panel, bg="#1976d2")
        header.grid(row=0, column=0, sticky="ew")
        
        header_inner = tk.Frame(header, bg="#1976d2")
        header_inner.pack(fill=tk.X, padx=8, pady=6)
        
        tk.Label(header_inner, text="📝 Multiple Choice Questions", 
                font=("Segoe UI", 12, "bold"), bg="#1976d2", fg="white").pack(side=tk.LEFT)
        
        progress_label = tk.Label(header_inner, textvariable=self.mcq_progress_var,
                                 font=("Segoe UI", 11, "bold"), bg="#1976d2", fg="white")
        progress_label.pack(side=tk.RIGHT)
        
        tk.Label(header_inner, text=f" / {self.flow.mcq_count}",
                font=("Segoe UI", 11), bg="#1976d2", fg="white").pack(side=tk.RIGHT)
        
        # Tip
        tip_frame = tk.Frame(mcq_panel, bg=self.MCQ_COLOR)
        tip_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        
        tk.Label(tip_frame, text="💡 Tip: Enter answers as A, B, C, or D. Multiple answers: A,B,C",
                font=("Segoe UI", 8), fg="#1565c0", bg=self.MCQ_COLOR).pack(anchor="w")
        
        # Scrollable area - THIS MUST EXPAND
        scroll_container = tk.Frame(mcq_panel, bg=self.MCQ_COLOR)
        scroll_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 2))
        
        # Configure scroll_container to expand
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)
        
        canvas = tk.Canvas(scroll_container, bg=self.MCQ_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.MCQ_COLOR)
        
        scrollable_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Make canvas window expand with canvas width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create MCQ entries
        self.create_mcq_entries(scrollable_frame)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Auto-fill button
        btn_frame = tk.Frame(mcq_panel, bg=self.MCQ_COLOR)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        ttk.Button(btn_frame, text="Auto Fill (A,B,C,D...)", 
                  command=self.on_auto_fill_mcq).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Clear MCQ", 
                  command=self.on_clear_mcq).pack(side=tk.LEFT, padx=(10, 0))
    
    def create_mcq_panel(self, parent):
        """Wrapper for backward compatibility"""
        self.create_mcq_panel_grid(parent, column=0)
    
    def create_written_panel_grid(self, parent, column):
        """Create written answer entry panel using grid layout"""
        written_panel = tk.Frame(parent, bg=self.WRITTEN_COLOR, relief="flat")
        written_panel.grid(row=0, column=column, sticky="nsew", padx=(5 if column > 0 else 0, 0))
        
        # Configure row weight so scrollable area expands
        written_panel.grid_rowconfigure(2, weight=10) # Row 2 is the scrollable area
        written_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header = tk.Frame(written_panel, bg="#f57c00")
        header.grid(row=0, column=0, sticky="ew")
        
        header_inner = tk.Frame(header, bg="#f57c00")
        header_inner.pack(fill=tk.X, padx=15, pady=12)
        
        tk.Label(header_inner, text="🔢 Written Answer Questions", 
                font=("Segoe UI", 12, "bold"), bg="#f57c00", fg="white").pack(side=tk.LEFT)
        
        progress_label = tk.Label(header_inner, textvariable=self.written_progress_var,
                                 font=("Segoe UI", 11, "bold"), bg="#f57c00", fg="white")
        progress_label.pack(side=tk.RIGHT)
        
        tk.Label(header_inner, text=f" / {self.flow.written_count}",
                font=("Segoe UI", 11), bg="#f57c00", fg="white").pack(side=tk.RIGHT)
        
        # Tip
        tip_frame = tk.Frame(written_panel, bg=self.WRITTEN_COLOR)
        tip_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        
        tk.Label(tip_frame, text="💡 Tip: Enter numeric answers (integers or decimals)",
                font=("Segoe UI", 8), fg="#e65100", bg=self.WRITTEN_COLOR).pack(anchor="w")
        
        # Scrollable area - THIS MUST EXPAND
        scroll_container = tk.Frame(written_panel, bg=self.WRITTEN_COLOR)
        scroll_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 5))  
        
        # Configure scroll_container to expand
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)
        
        canvas = tk.Canvas(scroll_container, bg=self.WRITTEN_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.WRITTEN_COLOR)
        
        scrollable_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Make canvas window expand with canvas width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create written entries
        self.create_written_entries(scrollable_frame)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Auto-fill button
        btn_frame = tk.Frame(written_panel, bg=self.WRITTEN_COLOR)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        ttk.Button(btn_frame, text="Fill All with 0", 
                  command=self.on_auto_fill_written).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Clear Written", 
                  command=self.on_clear_written).pack(side=tk.LEFT, padx=(10, 0))
    
    def create_written_panel(self, parent):
        """Wrapper for backward compatibility"""
        self.create_written_panel_grid(parent, column=1)
    
    def create_mcq_entries(self, parent):
        """Create MCQ entry fields in multiple columns (max 12 per column)"""
        self.mcq_entries = []

        max_per_col = 12
        total = self.flow.mcq_count
        columns = (total + max_per_col - 1) // max_per_col  # ceil division

        col_frames = []

        for col in range(columns):
            col_frame = tk.Frame(parent, bg=self.MCQ_COLOR)
            col_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
            col_frames.append(col_frame)

        q_index = 0
        for col in range(columns):
            for row in range(max_per_col):
                q_num = q_index + 1
                if q_num > total:
                    break

                row_frame = tk.Frame(col_frames[col], bg=self.MCQ_COLOR)
                row_frame.pack(fill=tk.X, pady=4)

                tk.Label(
                    row_frame,
                    text=f"Q{q_num}.",
                    width=5,
                    anchor="e",
                    font=("Segoe UI", 10, "bold"),
                    bg=self.MCQ_COLOR,
                    fg="#1565c0"
                ).pack(side=tk.LEFT, padx=(0, 6))

                entry = ttk.Entry(row_frame, width=10, font=("Segoe UI", 11), justify="center")
                entry.pack(side=tk.LEFT)

                self.mcq_entries.append(entry)

                entry.bind('<KeyRelease>', lambda e, q=q_num, ent=entry: self.on_mcq_answer_change(q, ent))
                entry.bind('<Return>', lambda e, q=q_num: self.on_mcq_enter_press(q))

                q_index += 1

    
    def create_written_entries(self, parent):
        """Create written entry fields with larger height area"""
        self.written_entries = []
        written_start = self.flow.mcq_count + 1

        for i in range(self.flow.written_count):
            q_num = written_start + i

            row_frame = tk.Frame(parent, bg=self.WRITTEN_COLOR)
            row_frame.pack(fill=tk.X, pady=4)

            tk.Label(
                row_frame,
                text=f"Q{q_num}.",
                width=5,
                anchor="e",
                font=("Segoe UI", 10, "bold"),
                bg=self.WRITTEN_COLOR,
                fg="#e65100"
            ).pack(side=tk.LEFT, padx=(0, 6))

            entry = ttk.Entry(row_frame, width=10, font=("Segoe UI", 11), justify="center")
            entry.pack(side=tk.LEFT)
            self.written_entries.append(entry)

            entry.bind('<KeyRelease>', lambda e, q=q_num, ent=entry: self.on_written_answer_change(q, ent))
            entry.bind('<Return>', lambda e, idx=i: self.on_written_enter_press(idx))
    
    def create_control_buttons(self, parent):
        """Create control buttons"""
        control_frame = tk.Frame(parent, bg=self.BG_COLOR)
        control_frame.pack(fill=tk.X, pady=(0, 0))
        
        ttk.Button(control_frame, text="Clear All", 
                  command=self.on_clear_all).pack(side=tk.LEFT)
        
        ttk.Button(control_frame, text="Cancel", 
                  command=self.root.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        
        self.save_btn = ttk.Button(control_frame, text="💾 Save Answer Key", 
                                   command=self.on_save, 
                                   state=DISABLED,
                                   style="Accent.TButton")
        self.save_btn.pack(side=tk.RIGHT)
    
    def on_mcq_answer_change(self, question_num, entry):
        """Handle MCQ answer input change"""
        answer_input = entry.get().strip().upper()
        
        if not answer_input:
            # Clear answer
            if str(question_num) in self.flow.mcq_answers:
                del self.flow.mcq_answers[str(question_num)]
            entry.config(style="TEntry")
        else:
            # Set answer (flow handles validation)
            success, error = self.flow.set_mcq_answer(question_num, answer_input)
            
            if success:
                entry.config(style="Valid.TEntry")
            else:
                entry.config(style="TEntry")
        
        # Update progress
        self.update_progress()
    
    def on_written_answer_change(self, question_num, entry):
        """Handle written answer input change"""
        answer_input = entry.get().strip()
        
        if not answer_input:
            # Clear answer
            if str(question_num) in self.flow.written_answers:
                del self.flow.written_answers[str(question_num)]
            entry.config(style="TEntry")
        else:
            # Set answer (flow handles validation)
            success, error = self.flow.set_written_answer(question_num, answer_input)
            
            if success:
                entry.config(style="Valid.TEntry")
            else:
                entry.config(style="TEntry")
        
        # Update progress
        self.update_progress()
    
    def on_mcq_enter_press(self, question_num):
        """Handle Enter key press in MCQ"""
        if question_num < self.flow.mcq_count and question_num < len(self.mcq_entries):
            self.mcq_entries[question_num].focus()
        elif self.written_entries:
            # Jump to first written entry
            self.written_entries[0].focus()
    
    def on_written_enter_press(self, index):
        """Handle Enter key press in written"""
        if index < len(self.written_entries) - 1:
            self.written_entries[index + 1].focus()
    
    def update_progress(self):
        """Update progress display"""
        progress = self.flow.get_progress()
        
        self.mcq_progress_var.set(str(progress['mcq']['answered']))
        self.written_progress_var.set(str(progress['written']['answered']))
        
        # Enable/disable save button
        self.save_btn.config(state=NORMAL if progress['overall']['is_complete'] else DISABLED)
        
        # Update status
        if progress['overall']['is_complete']:
            self.status_var.set("✓ All answers filled! Ready to save.")
        else:
            self.status_var.set(f"Progress: {progress['overall']['answered']}/{progress['overall']['total']} questions")
    
    def on_auto_fill_mcq(self):
        """Handle MCQ auto-fill button"""
        success, error = self.flow.auto_fill_mcq_pattern('sequential')
        
        if success:
            # Update all MCQ entries
            for i, entry in enumerate(self.mcq_entries):
                q_num = str(i + 1)
                if q_num in self.flow.mcq_answers:
                    entry.delete(0, tk.END)
                    entry.insert(0, ','.join(self.flow.mcq_answers[q_num]))
                    entry.config(style="Valid.TEntry")
            
            self.update_progress()
        else:
            messagebox.showerror("Error", error)
    
    def on_auto_fill_written(self):
        """Handle written auto-fill button"""
        success, error = self.flow.auto_fill_written_pattern(0)
        
        if success:
            # Update all written entries
            for i, entry in enumerate(self.written_entries):
                q_num = str(self.flow.mcq_count + i + 1)
                if q_num in self.flow.written_answers:
                    entry.delete(0, tk.END)
                    entry.insert(0, str(self.flow.written_answers[q_num]))
                    entry.config(style="Valid.TEntry")
            
            self.update_progress()
        else:
            messagebox.showerror("Error", error)
    
    def on_clear_mcq(self):
        """Handle clear MCQ button"""
        self.flow.mcq_answers = {}
        
        for entry in self.mcq_entries:
            entry.delete(0, tk.END)
            entry.config(style="TEntry")
        
        self.update_progress()
        
        if self.mcq_entries:
            self.mcq_entries[0].focus()
    
    def on_clear_written(self):
        """Handle clear written button"""
        self.flow.written_answers = {}
        
        for entry in self.written_entries:
            entry.delete(0, tk.END)
            entry.config(style="TEntry")
        
        self.update_progress()
        
        if self.written_entries:
            self.written_entries[0].focus()
    
    def on_clear_all(self):
        """Handle clear all button"""
        self.on_clear_mcq()
        self.on_clear_written()
    
    def on_save(self):
        """Handle save button"""
        # Validate
        valid, error, missing = self.flow.validate_answers()
        if not valid:
            messagebox.showerror("Error", error)
            return
        
        # Prompt for exam name
        exam_name = simpledialog.askstring("Exam Name", 
                                          "Enter exam name:",
                                          initialvalue="Exam")
        
        if not exam_name:
            return
        
        # Save
        success, error, saved_path = self.flow.save_answer_key(exam_name=exam_name)
        
        if success:
            msg = f"Answer key saved successfully!\n\n"
            msg += f"File: {os.path.basename(saved_path)}\n"
            msg += f"MCQ Questions: {self.flow.mcq_count}\n"
            msg += f"Written Questions: {self.flow.written_count}\n"
            msg += f"Total: {self.flow.mcq_count + self.flow.written_count}"
            
            messagebox.showinfo("Success", msg)
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