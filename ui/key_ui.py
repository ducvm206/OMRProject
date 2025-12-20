"""
Answer Key Creation UI - Multiple Keys Support
Pure UI components for creating multiple answer keys (A-E) for an exam
Now with extraction from filled answer sheets
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, StringVar, IntVar, NORMAL, DISABLED, BooleanVar, Toplevel

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.file_utils import select_file, get_project_root, select_directory
from flows.key_flow import AnswerKeyFlow


class ExtractionDialog:
    """Dialog for extracting keys from filled answer sheets"""
    
    def __init__(self, parent, flow, key_letters):
        self.parent = parent
        self.flow = flow
        self.key_letters = key_letters
        
        # Create dialog
        self.dialog = Toplevel(parent)
        self.dialog.title("Extract Keys from Filled Sheets")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg="#f5f5f5")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + (parent.winfo_width() - 800) // 2,
            parent.winfo_rooty() + (parent.winfo_height() - 600) // 2
        ))
        
        # Store sheet paths
        self.sheet_paths = {}
        self.threshold_var = IntVar(value=50)
        self.extract_mode_var = StringVar(value="single")
        
        self.create_ui()
    
    def create_ui(self):
        """Create extraction UI"""
        main_frame = tk.Frame(self.dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_frame, text="📸 Extract Keys from Answer Sheets", 
                        font=("Segoe UI", 14, "bold"), bg="#f5f5f5", fg="#333")
        title.pack(anchor="w", pady=(0, 15))
        
        # Info text
        info_text = ("This feature extracts answers from filled answer sheets to create answer keys.\n"
                     "Use this when you have master answer sheets already filled with correct answers.")
        tk.Label(main_frame, text=info_text, font=("Segoe UI", 9), 
                bg="#f5f5f5", fg="#666", justify="left", wraplength=700).pack(anchor="w", pady=(0, 20))
        
        # Mode selection
        mode_frame = tk.Frame(main_frame, bg="#e8f5e8")
        mode_frame.pack(fill=tk.X, pady=(0, 20))
        
        mode_inner = tk.Frame(mode_frame, bg="#e8f5e8")
        mode_inner.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(mode_inner, text="Extraction Mode:", 
                font=("Segoe UI", 10, "bold"), bg="#e8f5e8").pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Radiobutton(mode_inner, text="Single Sheet → Single Key", 
                       variable=self.extract_mode_var, value="single", 
                       style="TRadiobutton").pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(mode_inner, text="Multiple Sheets → Multiple Keys", 
                       variable=self.extract_mode_var, value="batch",
                       style="TRadiobutton").pack(side=tk.LEFT, padx=10)
        
        # Single extraction mode frame
        self.single_frame = tk.Frame(main_frame, bg="#f5f5f5")
        self.single_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Key selection for single mode
        key_sel_frame = tk.Frame(self.single_frame, bg="#f5f5f5")
        key_sel_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(key_sel_frame, text="Target Key:", 
                font=("Segoe UI", 10), bg="#f5f5f5", width=12, anchor="w").pack(side=tk.LEFT)
        
        self.single_key_var = StringVar(value=self.key_letters[0])
        key_dropdown = ttk.Combobox(key_sel_frame, textvariable=self.single_key_var,
                                    values=self.key_letters, state="readonly", width=10)
        key_dropdown.pack(side=tk.LEFT)
        
        # Sheet selection for single mode
        sheet_sel_frame = tk.Frame(self.single_frame, bg="#f5f5f5")
        sheet_sel_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(sheet_sel_frame, text="Sheet Image:", 
                font=("Segoe UI", 10), bg="#f5f5f5", width=12, anchor="w").pack(side=tk.LEFT)
        
        self.single_sheet_path = tk.StringVar(value="")
        sheet_entry = ttk.Entry(sheet_sel_frame, textvariable=self.single_sheet_path, width=40)
        sheet_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(sheet_sel_frame, text="Browse...", 
                  command=lambda: self.browse_sheet_file(self.single_sheet_path)).pack(side=tk.LEFT)
        
        # Batch extraction mode frame (initially hidden)
        self.batch_frame = tk.Frame(main_frame, bg="#f5f5f5")
        
        # Create batch grid
        batch_inner = tk.Frame(self.batch_frame, bg="#f5f5f5")
        batch_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Header
        tk.Label(batch_inner, text="Assign sheets to keys:", 
                font=("Segoe UI", 10, "bold"), bg="#f5f5f5").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # Create rows for each key
        self.batch_entries = {}
        for i, key in enumerate(self.key_letters):
            row = i + 1
            
            # Key label
            tk.Label(batch_inner, text=f"Key {key}:", 
                    font=("Segoe UI", 10), bg="#f5f5f5", width=8, anchor="w").grid(row=row, column=0, sticky="w", pady=5)
            
            # Path entry
            path_var = tk.StringVar(value="")
            entry = ttk.Entry(batch_inner, textvariable=path_var, width=35)
            entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
            
            # Browse button
            ttk.Button(batch_inner, text="Browse...", 
                      command=lambda k=key, v=path_var: self.browse_sheet_file(v)).grid(row=row, column=2, sticky="w", pady=5)
            
            self.batch_entries[key] = path_var
        
        batch_inner.grid_columnconfigure(1, weight=1)
        
        # Parameters frame
        params_frame = tk.Frame(main_frame, bg="#e3f2fd")
        params_frame.pack(fill=tk.X, pady=(20, 10))
        
        params_inner = tk.Frame(params_frame, bg="#e3f2fd")
        params_inner.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(params_inner, text="Extraction Parameters:", 
                font=("Segoe UI", 10, "bold"), bg="#e3f2fd").pack(side=tk.LEFT, padx=(0, 15))
        
        # Threshold slider
        tk.Label(params_inner, text="Detection Threshold:", 
                font=("Segoe UI", 9), bg="#e3f2fd").pack(side=tk.LEFT)
        
        threshold_frame = tk.Frame(params_inner, bg="#e3f2fd")
        threshold_frame.pack(side=tk.LEFT, padx=(5, 0))
        
        threshold_slider = ttk.Scale(threshold_frame, from_=10, to=90, 
                                     variable=self.threshold_var, orient="horizontal", length=200)
        threshold_slider.pack(side=tk.LEFT, padx=5)
        
        self.threshold_label = tk.Label(threshold_frame, text=f"{self.threshold_var.get()}%", 
                                       font=("Segoe UI", 9), bg="#e3f2fd", width=5)
        self.threshold_label.pack(side=tk.LEFT)
        
        # Update threshold label
        def update_threshold_label(*args):
            self.threshold_label.config(text=f"{self.threshold_var.get()}%")
        
        self.threshold_var.trace("w", update_threshold_label)
        
        # Debug checkbox
        self.debug_var = BooleanVar(value=False)
        debug_check = ttk.Checkbutton(params_inner, text="Show Debug Visualization", 
                                      variable=self.debug_var, style="TCheckbutton")
        debug_check.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Control buttons
        button_frame = tk.Frame(main_frame, bg="#f5f5f5")
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="Cancel", 
                  command=self.dialog.destroy).pack(side=tk.LEFT)
        
        ttk.Button(button_frame, text="Start Extraction", 
                  command=self.start_extraction,
                  style="Accent.TButton").pack(side=tk.RIGHT)
        
        # Update mode display
        self.update_mode_display()
        self.extract_mode_var.trace("w", lambda *args: self.update_mode_display())
    
    def update_mode_display(self):
        """Update UI based on selected mode"""
        mode = self.extract_mode_var.get()
        
        if mode == "single":
            self.single_frame.pack(fill=tk.X, pady=(0, 10))
            self.batch_frame.pack_forget()
        else:
            self.single_frame.pack_forget()
            self.batch_frame.pack(fill=tk.X, pady=(0, 10))
    
    def browse_sheet_file(self, path_var):
        """Browse for sheet image file"""
        initial_dir = os.path.join(get_project_root(), 'filled_sheets')
        
        if not os.path.exists(initial_dir):
            initial_dir = get_project_root()
        
        sheet_path = select_file(
            title="Select Filled Answer Sheet",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")],
            initial_dir=initial_dir,
            return_relative=False
        )
        
        if sheet_path:
            path_var.set(sheet_path)
    
    def start_extraction(self):
        """Start the extraction process"""
        mode = self.extract_mode_var.get()
        threshold = self.threshold_var.get()
        debug = self.debug_var.get()
        
        try:
            if mode == "single":
                # Single sheet extraction
                target_key = self.single_key_var.get()
                sheet_path = self.single_sheet_path.get()
                
                if not sheet_path or not os.path.exists(sheet_path):
                    messagebox.showerror("Error", f"Sheet image not found:\n{sheet_path}")
                    return
                
                # Show progress
                progress_window = tk.Toplevel(self.dialog)
                progress_window.title("Extracting...")
                progress_window.geometry("400x150")
                progress_window.configure(bg="#f5f5f5")
                progress_window.transient(self.dialog)
                progress_window.grab_set()
                
                # Center progress window
                progress_window.geometry("+%d+%d" % (
                    self.dialog.winfo_rootx() + (self.dialog.winfo_width() - 400) // 2,
                    self.dialog.winfo_rooty() + (self.dialog.winfo_height() - 150) // 2
                ))
                
                tk.Label(progress_window, text="Extracting answers from sheet...", 
                        font=("Segoe UI", 11), bg="#f5f5f5").pack(pady=20)
                
                tk.Label(progress_window, text=f"Target: Key {target_key}", 
                        font=("Segoe UI", 10), bg="#f5f5f5").pack()
                
                tk.Label(progress_window, text=f"Sheet: {os.path.basename(sheet_path)}", 
                        font=("Segoe UI", 9), bg="#f5f5f5", fg="#666").pack(pady=(5, 0))
                
                progress_var = tk.StringVar(value="0%")
                progress_label = tk.Label(progress_window, textvariable=progress_var, 
                                         font=("Segoe UI", 10), bg="#f5f5f5")
                progress_label.pack(pady=10)
                
                # Update UI
                progress_window.update()
                
                # Perform extraction
                success, error, result = self.flow.extract_key_from_filled_sheet(
                    sheet_image_path=sheet_path,
                    target_key_letter=target_key,
                    threshold_percent=threshold,
                    debug=debug
                )
                
                progress_window.destroy()
                
                if success:
                    # Show results
                    mcq_extracted = result['mcq_results']['extracted']
                    written_extracted = result['written_results']['extracted']
                    mcq_total = result['mcq_results']['total_expected']
                    written_total = result['written_results']['total_expected']
                    
                    messagebox.showinfo("Extraction Complete", 
                                       f"✓ Key {target_key} extracted successfully!\n\n"
                                       f"MCQ Answers: {mcq_extracted}/{mcq_total}\n"
                                       f"Written Answers: {written_extracted}/{written_total}\n"
                                       f"Success Rate: {result['mcq_results']['success_rate']:.1f}% (MCQ), "
                                       f"{result['written_results']['success_rate']:.1f}% (Written)")
                    
                    self.dialog.destroy()
                    return True
                else:
                    messagebox.showerror("Extraction Failed", f"Failed to extract answers:\n{error}")
                    return False
                    
            else:
                # Batch extraction
                sheet_dict = {}
                missing_keys = []
                
                for key, path_var in self.batch_entries.items():
                    path = path_var.get()
                    if path and os.path.exists(path):
                        sheet_dict[key] = path
                    else:
                        missing_keys.append(key)
                
                if not sheet_dict:
                    messagebox.showerror("Error", "No valid sheet images selected")
                    return
                
                if missing_keys:
                    response = messagebox.askyesno("Missing Sheets", 
                                                  f"Sheets not selected for keys: {', '.join(missing_keys)}\n"
                                                  "Continue with available sheets only?")
                    if not response:
                        return
                
                # Show batch progress
                progress_window = tk.Toplevel(self.dialog)
                progress_window.title("Batch Extracting...")
                progress_window.geometry("400x200")
                progress_window.configure(bg="#f5f5f5")
                progress_window.transient(self.dialog)
                progress_window.grab_set()
                
                # Center progress window
                progress_window.geometry("+%d+%d" % (
                    self.dialog.winfo_rootx() + (self.dialog.winfo_width() - 400) // 2,
                    self.dialog.winfo_rooty() + (self.dialog.winfo_height() - 200) // 2
                ))
                
                tk.Label(progress_window, text="Batch extracting answers...", 
                        font=("Segoe UI", 11), bg="#f5f5f5").pack(pady=15)
                
                tk.Label(progress_window, text=f"Processing {len(sheet_dict)} sheet(s)", 
                        font=("Segoe UI", 10), bg="#f5f5f5").pack()
                
                # Progress text
                self.batch_progress_text = tk.Text(progress_window, height=6, width=45, 
                                                  font=("Consolas", 9), bg="#f5f5f5")
                self.batch_progress_text.pack(pady=10, padx=10)
                
                # Update UI
                progress_window.update()
                
                # Perform batch extraction
                def update_progress(text):
                    self.batch_progress_text.insert(tk.END, text + "\n")
                    self.batch_progress_text.see(tk.END)
                    progress_window.update()
                
                success, error, results = self.flow.extract_all_keys_from_sheets(
                    sheet_images_dict=sheet_dict,
                    threshold_percent=threshold,
                    debug=debug
                )
                
                progress_window.destroy()
                
                if results:
                    # Show batch results
                    success_count = len(results)
                    total_count = len(sheet_dict)
                    
                    result_text = f"✓ Batch extraction complete!\n\n"
                    result_text += f"Successfully extracted: {success_count}/{total_count} keys\n\n"
                    
                    for key, result in results.items():
                        mcq = result['mcq_results']
                        written = result['written_results']
                        result_text += f"Key {key}: {mcq['extracted']}/{mcq['total_expected']} MCQ, " \
                                      f"{written['extracted']}/{written['total_expected']} Written\n"
                    
                    messagebox.showinfo("Batch Extraction Complete", result_text)
                    self.dialog.destroy()
                    return True
                else:
                    messagebox.showerror("Batch Extraction Failed", 
                                        f"Failed to extract answers:\n{error}")
                    return False
                    
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error:\n{str(e)}")
            import traceback
            traceback.print_exc()
            return False


class AnswerKeyUI:
    """UI for creating multiple answer keys (A-E) for an exam"""
    
    def __init__(self, root):
        """Initialize UI"""
        self.root = root
        self.flow = AnswerKeyFlow()
        
        # UI State
        self.exam_name_var = StringVar(value="")
        self.num_keys_var = IntVar(value=1)
        self.mcq_points_var = IntVar(value=0)
        self.written_points_var = IntVar(value=0)
        self.template_var = StringVar(value="No template loaded")
        self.current_key_var = StringVar(value="A")
        self.status_var = StringVar(value="Ready")
        
        # Entry widgets for current key - changed to store checkbox variables
        self.mcq_checkboxes = []  # List of tuples: (q_num, {'A': var, 'B': var, 'C': var, 'D': var})
        self.written_entries = []
        
        # Colors
        self.BG_COLOR = "#f5f5f5"
        self.CARD_COLOR = "#ffffff"
        self.MCQ_COLOR = "#e3f2fd"
        self.WRITTEN_COLOR = "#fff3e0"
        self.KEY_SELECTOR_COLOR = "#f3e5f5"
        self.EXTRACTION_COLOR = "#e8f5e9"
        self.BUTTON_COLORS = {
            'A': "#4CAF50",  # Green
            'B': "#2196F3",  # Blue
            'C': "#FF9800",  # Orange
            'D': "#F44336",  # Red
            'random': "#9C27B0",  # Purple
            'extract': "#0097A7"  # Teal for extraction
        }
        
        self.setup_window()
        self.create_checkbox_images()  # Create custom checkbox images
        self.create_ui()
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("Answer Key Creator - Multiple Keys (A-E)")
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        width = int(screen_width * 0.9)
        height = int(screen_height * 0.9)
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.minsize(1400, 800)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabel", background=self.BG_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.CARD_COLOR, relief="flat")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Valid.TEntry", fieldbackground="#d4edda", relief="flat")
        style.configure("TEntry", relief="flat", padding=5)
        style.configure("Extraction.TButton", background=self.BUTTON_COLORS['extract'], 
                       foreground="white", font=("Segoe UI", 10, "bold"))
    
    def create_checkbox_images(self):
        """Create custom images for larger checkboxes"""
        # Create blank images
        self.unchecked_img = tk.PhotoImage(width=16, height=16)
        self.checked_img = tk.PhotoImage(width=16, height=16)
        
        # Draw unchecked box (black border, MCQ_COLOR inside)
        for x in range(16):
            for y in range(16):
                if x < 2 or x > 13 or y < 2 or y > 13:
                    self.unchecked_img.put("#000000", (x, y))  # Black border
                else:
                    self.unchecked_img.put("#ffffff", (x, y))  # Inside color
        
        # Draw checked box (black border, white inside with check mark)
        for x in range(16):
            for y in range(16):
                if x < 2 or x > 13 or y < 2 or y > 13:
                    self.checked_img.put("#000000", (x, y))  # Black border
                else:
                    self.checked_img.put("#ffffff", (x, y))  # White inside
        
        # Draw check mark (X shape)
        for i in range(4, 12):
            self.checked_img.put("#000000", (i, i))       # \
            self.checked_img.put("#000000", (i, 15 - i))  # /
    
    def create_ui(self):
        """Create main UI"""
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Title
        title = tk.Label(main_container, text="Answer Key Creator - Multiple Keys", 
                        font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333")
        title.pack(pady=(0, 20))
        
        # Step 1: Configuration Card
        self.create_configuration_card(main_container)
        
        # Step 2: Key Selection & Entry (hidden initially)
        self.key_entry_frame = tk.Frame(main_container, bg=self.BG_COLOR)
        self.key_entry_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Status bar
        self.create_status_bar(main_container)
    
    def create_configuration_card(self, parent):
        """Create initial configuration card"""
        config_card = tk.Frame(parent, bg=self.CARD_COLOR, relief="flat")
        config_card.pack(fill=tk.X, pady=(0, 20))
        
        config_inner = tk.Frame(config_card, bg=self.CARD_COLOR)
        config_inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        # Step 1: Template
        step1_frame = tk.Frame(config_inner, bg=self.CARD_COLOR)
        step1_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(step1_frame, text="Step 1: Load Template", 
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 10))
        
        template_display = tk.Frame(step1_frame, bg=self.CARD_COLOR)
        template_display.pack(fill=tk.X)
        
        tk.Label(template_display, text="Template:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR).pack(side=tk.LEFT)
        tk.Label(template_display, textvariable=self.template_var, 
                font=("Segoe UI", 9), bg=self.CARD_COLOR).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(step1_frame, text="📂 Load Template", 
                  command=self.on_load_template).pack(anchor="w", pady=(10, 0))
        
        # Step 2: Exam Configuration
        step2_frame = tk.Frame(config_inner, bg=self.CARD_COLOR)
        step2_frame.pack(fill=tk.X, pady=(20, 0))
        
        tk.Label(step2_frame, text="Step 2: Configure Exam", 
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 10))
        
        # Exam name
        name_frame = tk.Frame(step2_frame, bg=self.CARD_COLOR)
        name_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(name_frame, text="Exam Name:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR, width=15, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.exam_name_var, width=30).pack(side=tk.LEFT, padx=(0, 10))
        
        # Number of keys
        keys_frame = tk.Frame(step2_frame, bg=self.CARD_COLOR)
        keys_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(keys_frame, text="Number of Keys:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR, width=15, anchor="w").pack(side=tk.LEFT)
        ttk.Spinbox(keys_frame, from_=1, to=5, textvariable=self.num_keys_var, width=5).pack(side=tk.LEFT)
        tk.Label(keys_frame, text="(1-5, e.g., Key A, Key B, etc.)", 
                font=("Segoe UI", 8), bg=self.CARD_COLOR, fg="#666").pack(side=tk.LEFT, padx=(10, 0))
        
        # MCQ max points
        mcq_frame = tk.Frame(step2_frame, bg=self.CARD_COLOR)
        mcq_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(mcq_frame, text="MCQ Max Points:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR, width=15, anchor="w").pack(side=tk.LEFT)
        ttk.Spinbox(mcq_frame, from_=0, to=1000, textvariable=self.mcq_points_var, width=10).pack(side=tk.LEFT)
        tk.Label(mcq_frame, text="(0 = skip MCQ section)", 
                font=("Segoe UI", 8), bg=self.CARD_COLOR, fg="#666").pack(side=tk.LEFT, padx=(10, 0))
        
        # Written max points
        written_frame = tk.Frame(step2_frame, bg=self.CARD_COLOR)
        written_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(written_frame, text="Written Max Points:", 
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR, width=15, anchor="w").pack(side=tk.LEFT)
        ttk.Spinbox(written_frame, from_=0, to=1000, textvariable=self.written_points_var, width=10).pack(side=tk.LEFT)
        tk.Label(written_frame, text="(0 = skip written section)", 
                font=("Segoe UI", 8), bg=self.CARD_COLOR, fg="#666").pack(side=tk.LEFT, padx=(10, 0))
        
        # Start button
        start_frame = tk.Frame(step2_frame, bg=self.CARD_COLOR)
        start_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.start_btn = ttk.Button(start_frame, text="▶ Start Answer Entry", 
                                   command=self.on_start_entry,
                                   style="Accent.TButton",
                                   state=DISABLED)
        self.start_btn.pack(anchor="w")
        
        self.config_card = config_card
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = tk.Frame(parent, bg=self.BG_COLOR)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(status_frame, textvariable=self.status_var, 
                font=("Segoe UI", 9), foreground="#666", bg=self.BG_COLOR).pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Exit", 
                  command=self.root.destroy).pack(side=tk.RIGHT)
    
    def on_load_template(self):
        """Load template"""
        template_dir = os.path.join(get_project_root(), 'template')
        
        template_path = select_file(
            title="Select Template JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initial_dir=template_dir,
            return_relative=True
        )
        
        if not template_path:
            return
        
        success, error, template_info = self.flow.load_template(template_path)
        
        if not success:
            messagebox.showerror("Error", f"Failed to load template:\n{error}")
            return
        
        self.template_var.set(template_info['name'])
        self.status_var.set(f"✓ Template loaded: {template_info['mcq_questions_available']} MCQ + "
                           f"{template_info['written_questions_available']} Written questions")
        self.start_btn.config(state=NORMAL)
    
    def on_start_entry(self):
        """Start answer entry after configuration"""
        exam_name = self.exam_name_var.get()
        num_keys = self.num_keys_var.get()
        mcq_points = self.mcq_points_var.get()
        written_points = self.written_points_var.get()
        
        # Validate
        if not exam_name.strip():
            messagebox.showerror("Error", "Exam name cannot be empty")
            return
        
        # Configure exam
        success, error = self.flow.configure_exam(exam_name, num_keys, mcq_points, written_points)
        
        if not success:
            messagebox.showerror("Error", f"Configuration error:\n{error}")
            return
        
        # Hide config card and show answer entry
        self.config_card.pack_forget()
        self.show_answer_entry_ui()
        
        # Enable save button
        self.save_btn.config(state=NORMAL)
    
    def show_answer_entry_ui(self):
        """Show answer entry interface"""
        # Clear existing
        for widget in self.key_entry_frame.winfo_children():
            widget.destroy()
        
        # Container with key selector and answer panels
        container = tk.Frame(self.key_entry_frame, bg=self.BG_COLOR)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Quick fill buttons (if MCQ exists)
        if self.flow.mcq_count > 0:
            self.create_quick_fill_buttons(container)
        
        # Key selector bar at top
        self.create_key_selector_bar(container)
        
        # Answer entry panels (MCQ + Written)
        panels_container = tk.Frame(container, bg=self.BG_COLOR)
        panels_container.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        panels_container.grid_rowconfigure(0, weight=1)
        panels_container.grid_columnconfigure(0, weight=1)
        panels_container.grid_columnconfigure(1, weight=1)
        
        # MCQ Panel
        if self.flow.mcq_count > 0:
            self.create_mcq_panel(panels_container, column=0)
        
        # Written Panel
        if self.flow.written_count > 0:
            col = 1 if self.flow.mcq_count > 0 else 0
            self.create_written_panel(panels_container, column=col)
        
        # Control buttons
        self.create_control_buttons(container)
    
    def create_quick_fill_buttons(self, parent):
        """Create quick fill buttons for batch MCQ answer setting"""
        quick_fill_frame = tk.Frame(parent, bg="#e8f5e8")
        quick_fill_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        quick_fill_inner = tk.Frame(quick_fill_frame, bg="#e8f5e8")
        quick_fill_inner.pack(fill=tk.X, padx=15, pady=8)
        
        # Left side: Quick fill buttons
        left_frame = tk.Frame(quick_fill_inner, bg="#e8f5e8")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(left_frame, text="Quick Fill MCQ Answers:", 
                font=("Segoe UI", 10, "bold"), bg="#e8f5e8").pack(side=tk.LEFT, padx=(0, 15))
        
        # Button styles
        self.quick_fill_buttons = {}
        
        # All A button (Green)
        btn_a = tk.Button(left_frame, text="Set All A", font=("Segoe UI", 9, "bold"),
                         bg=self.BUTTON_COLORS['A'], fg="white", relief="flat",
                         command=lambda: self.on_quick_fill('all_A', "all A"))
        btn_a.pack(side=tk.LEFT, padx=5, ipadx=15, ipady=5)
        self.quick_fill_buttons['all_A'] = btn_a
        
        # All B button (Blue)
        btn_b = tk.Button(left_frame, text="Set All B", font=("Segoe UI", 9, "bold"),
                         bg=self.BUTTON_COLORS['B'], fg="white", relief="flat",
                         command=lambda: self.on_quick_fill('all_B', "all B"))
        btn_b.pack(side=tk.LEFT, padx=5, ipadx=15, ipady=5)
        self.quick_fill_buttons['all_B'] = btn_b
        
        # All C button (Orange)
        btn_c = tk.Button(left_frame, text="Set All C", font=("Segoe UI", 9, "bold"),
                         bg=self.BUTTON_COLORS['C'], fg="white", relief="flat",
                         command=lambda: self.on_quick_fill('all_C', "all C"))
        btn_c.pack(side=tk.LEFT, padx=5, ipadx=15, ipady=5)
        self.quick_fill_buttons['all_C'] = btn_c
        
        # All D button (Red)
        btn_d = tk.Button(left_frame, text="Set All D", font=("Segoe UI", 9, "bold"),
                         bg=self.BUTTON_COLORS['D'], fg="white", relief="flat",
                         command=lambda: self.on_quick_fill('all_D', "all D"))
        btn_d.pack(side=tk.LEFT, padx=5, ipadx=15, ipady=5)
        self.quick_fill_buttons['all_D'] = btn_d
        
        # Random button (Purple)
        btn_random = tk.Button(left_frame, text="Set Random", font=("Segoe UI", 9, "bold"),
                              bg=self.BUTTON_COLORS['random'], fg="white", relief="flat",
                              command=lambda: self.on_quick_fill('random', "random"))
        btn_random.pack(side=tk.LEFT, padx=5, ipadx=15, ipady=5)
        self.quick_fill_buttons['random'] = btn_random
        
        # Apply to dropdown
        tk.Label(left_frame, text="Apply to:", 
                font=("Segoe UI", 9), bg="#e8f5e8").pack(side=tk.LEFT, padx=(15, 5))
        
        self.apply_to_var = StringVar(value="current")
        apply_to_dropdown = ttk.Combobox(left_frame, textvariable=self.apply_to_var,
                                        values=["current key only", "all keys"],
                                        state="readonly", width=15)
        apply_to_dropdown.pack(side=tk.LEFT)
        
        # Right side: Extraction button
        right_frame = tk.Frame(quick_fill_inner, bg="#e8f5e8")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Extraction button
        extract_btn = tk.Button(right_frame, text="📸 Extract from Sheet", 
                               font=("Segoe UI", 10, "bold"),
                               bg=self.BUTTON_COLORS['extract'], fg="white", 
                               relief="flat", padx=20,
                               command=self.on_extract_from_sheet)
        extract_btn.pack(side=tk.RIGHT, ipadx=10, ipady=5)
        
        # Help text
        help_text = "💡 Quick fill sets all MCQ answers. Use Extract to get answers from filled sheets."
        tk.Label(quick_fill_inner, text=help_text,
                font=("Segoe UI", 8), fg="#2e7d32", bg="#e8f5e8").pack(side=tk.BOTTOM, anchor="w", pady=(5, 0))
    
    def on_extract_from_sheet(self):
        """Open extraction dialog"""
        # Check if template is loaded
        if not self.flow.current_template:
            messagebox.showerror("Error", "Please load a template first")
            return
        
        # Get available key letters
        key_letters = list(self.flow.answer_keys.keys())
        
        if not key_letters:
            messagebox.showerror("Error", "No keys configured")
            return
        
        # Open extraction dialog
        ExtractionDialog(self.root, self.flow, key_letters)
    
    def create_key_selector_bar(self, parent):
        """Create key selector bar"""
        selector_frame = tk.Frame(parent, bg=self.KEY_SELECTOR_COLOR)
        selector_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        selector_inner = tk.Frame(selector_frame, bg=self.KEY_SELECTOR_COLOR)
        selector_inner.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(selector_inner, text="Select Key to Edit:", 
                font=("Segoe UI", 10, "bold"), bg=self.KEY_SELECTOR_COLOR).pack(side=tk.LEFT, padx=(0, 15))
        
        # Key buttons
        key_letters = ['A', 'B', 'C', 'D', 'E']
        self.key_buttons = {}
        
        for i in range(self.flow.num_keys):
            letter = key_letters[i]
            btn = ttk.Button(selector_inner, text=f"Key {letter}", 
                           command=lambda l=letter: self.on_switch_key(l),
                           width=10)
            btn.pack(side=tk.LEFT, padx=5)
            self.key_buttons[letter] = btn
        
        # Current key indicator
        self.key_indicator = tk.Label(selector_inner, text=f"Currently editing: Key A", 
                                     font=("Segoe UI", 10, "bold"), bg=self.KEY_SELECTOR_COLOR, 
                                     fg="#6a1b9a")
        self.key_indicator.pack(side=tk.LEFT, padx=(20, 0))
        
        # Progress indicator
        self.progress_label = tk.Label(selector_inner, text="0% complete", 
                                      font=("Segoe UI", 9), bg=self.KEY_SELECTOR_COLOR, fg="#666")
        self.progress_label.pack(side=tk.RIGHT, padx=(20, 0))
    
    def on_switch_key(self, key_letter):
        """Switch to a different key"""
        success, error = self.flow.switch_key(key_letter)
        
        if not success:
            messagebox.showerror("Error", error)
            return
        
        # Update UI
        self.current_key_var.set(key_letter)
        self.key_indicator.config(text=f"Currently editing: Key {key_letter}")
        
        # Reload entry fields with current key's answers
        self.reload_answer_entries()
        
        # Update progress
        self.update_progress()
    
    def on_quick_fill(self, pattern, display_name):
        """Handle quick fill button click"""
        apply_to = self.apply_to_var.get()
        
        if apply_to == "current key only":
            success, error, count_set = self.flow.set_all_mcq_answers(pattern)
            
            if success:
                self.status_var.set(f"✓ Set {count_set} MCQ answers to {display_name} for current key")
                self.reload_answer_entries()
                self.update_progress()
            else:
                messagebox.showerror("Error", f"Failed to set answers: {error}")
        else:
            # Apply to all keys
            result = messagebox.askyesno("Apply to All Keys", 
                                         f"Set all MCQ answers to {display_name} for ALL {self.flow.num_keys} keys?\n"
                                         "This will overwrite existing MCQ answers for all keys.")
            
            if result:
                success, error, results = self.flow.set_all_mcq_answers_all_keys(pattern)
                
                if success:
                    total_set = 0
                    success_keys = []
                    for letter, result_info in results.items():
                        if result_info['success']:
                            total_set += result_info['count_set']
                            success_keys.append(letter)
                    
                    self.status_var.set(f"✓ Set {total_set} MCQ answers to {display_name} for keys: {', '.join(success_keys)}")
                    
                    # Reload current key's entries
                    if self.flow.current_key_letter in success_keys:
                        self.reload_answer_entries()
                    
                    self.update_progress()
                else:
                    messagebox.showerror("Error", f"Failed to set answers: {error}")
    
    def create_mcq_panel(self, parent, column):
        """Create MCQ entry panel with custom checkbox images"""
        mcq_panel = tk.Frame(parent, bg=self.MCQ_COLOR, relief="flat")
        mcq_panel.grid(row=0, column=column, sticky="nsew", padx=(0, 5 if column == 0 else 0))
        
        mcq_panel.grid_rowconfigure(2, weight=1)
        mcq_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header = tk.Frame(mcq_panel, bg="#1976d2")
        header.grid(row=0, column=0, sticky="ew")
        
        header_inner = tk.Frame(header, bg="#1976d2")
        header_inner.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(header_inner, text="📝 Multiple Choice", 
                font=("Segoe UI", 12, "bold"), bg="#1976d2", fg="white").pack(side=tk.LEFT)
        
        # Tip
        tip_frame = tk.Frame(mcq_panel, bg=self.MCQ_COLOR)
        tip_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        
        tk.Label(tip_frame, text="💡 Click letters to select correct answer(s) - multiple allowed",
                font=("Segoe UI", 8), fg="#1565c0", bg=self.MCQ_COLOR).pack(anchor="w")
        
        # Scrollable area
        scroll_container = tk.Frame(mcq_panel, bg=self.MCQ_COLOR)
        scroll_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 10))
        
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)
        
        canvas = tk.Canvas(scroll_container, bg=self.MCQ_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.MCQ_COLOR)
        
        scrollable_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create MCQ checkboxes
        self.mcq_checkboxes = []
        total = self.flow.mcq_count
        columns = 2  # Always 2 columns
        questions_per_col = (total + 1) // 2  # Left column gets extra if odd
        
        col_frames = []
        for col in range(columns):
            col_frame = tk.Frame(scrollable_frame, bg=self.MCQ_COLOR)
            col_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15)
            col_frames.append(col_frame)
        
        q_index = 0
        colors = {'A': '#4CAF50', 'B': '#2196F3', 'C': '#FF9800', 'D': '#F44336'}

        for col in range(columns):
            col_frame = tk.Frame(scrollable_frame, bg=self.MCQ_COLOR)
            col_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15)
            col_frames.append(col_frame)

        q_index = 0
        for col in range(columns):
            # Calculate how many questions in this column
            if col == 0:
                # First column gets ceil(N/2)
                questions_in_this_col = (total + 1) // 2
            else:
                # Second column gets floor(N/2)
                questions_in_this_col = total // 2
            
            for row in range(questions_in_this_col):
                q_num = q_index + 1
                if q_num > total:
                    break
                
                # Create frame for this question
                q_frame = tk.Frame(col_frames[col], bg=self.MCQ_COLOR)
                q_frame.pack(fill=tk.X, pady=6)
                
                # Question number label
                tk.Label(q_frame, text=f"Q{q_num}.", width=5, anchor="e",
                        font=("Segoe UI", 11, "bold"), bg=self.MCQ_COLOR, fg="#1565c0").pack(side=tk.LEFT, padx=(0, 8))
                
                # Create checkbox variables for A, B, C, D
                checkbox_vars = {
                    'A': BooleanVar(value=False),
                    'B': BooleanVar(value=False),
                    'C': BooleanVar(value=False),
                    'D': BooleanVar(value=False)
                }
                
                # Create checkboxes
                cb_frame = tk.Frame(q_frame, bg=self.MCQ_COLOR)
                cb_frame.pack(side=tk.LEFT, padx=5)
                
                for letter in ['A', 'B', 'C', 'D']:
                    # Create custom checkbox with images
                    checkbox = tk.Checkbutton(cb_frame, variable=checkbox_vars[letter],
                                            bg=self.MCQ_COLOR,
                                            indicatoron=False,  # Use images instead of default indicator
                                            image=self.unchecked_img,
                                            selectimage=self.checked_img,
                                            compound="right",  # Put text to the right of image
                                            activebackground=self.MCQ_COLOR,
                                            borderwidth=0,
                                            highlightthickness=0,
                                            command=lambda q=q_num, cv=checkbox_vars: self.on_mcq_checkbox_change(q, cv))
                    checkbox.config(text=letter, 
                                font=("Segoe UI", 12, "bold"), 
                                fg=colors[letter],
                                anchor="w")
                    checkbox.pack(side=tk.LEFT, padx=(0, 8))
                    
                    # Store checkbox widget for later updates
                    checkbox_vars[letter].widget = checkbox
                
                # Store checkbox variables for this question
                self.mcq_checkboxes.append((q_num, checkbox_vars))
                
                q_index += 1
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
    
    def create_written_panel(self, parent, column):
        """Create written answer entry panel"""
        written_panel = tk.Frame(parent, bg=self.WRITTEN_COLOR, relief="flat")
        written_panel.grid(row=0, column=column, sticky="nsew", padx=(5 if column > 0 else 0, 0))
        
        written_panel.grid_rowconfigure(2, weight=1)
        written_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header = tk.Frame(written_panel, bg="#f57c00")
        header.grid(row=0, column=0, sticky="ew")
        
        header_inner = tk.Frame(header, bg="#f57c00")
        header_inner.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(header_inner, text="🔢 Written Answers", 
                font=("Segoe UI", 12, "bold"), bg="#f57c00", fg="white").pack(side=tk.LEFT)
        
        # Tip
        tip_frame = tk.Frame(written_panel, bg=self.WRITTEN_COLOR)
        tip_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        
        tk.Label(tip_frame, text="💡 Enter numeric answers (integers or decimals)",
                font=("Segoe UI", 8), fg="#e65100", bg=self.WRITTEN_COLOR).pack(anchor="w")
        
        # Scrollable area
        scroll_container = tk.Frame(written_panel, bg=self.WRITTEN_COLOR)
        scroll_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 10))
        
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)
        
        canvas = tk.Canvas(scroll_container, bg=self.WRITTEN_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.WRITTEN_COLOR)
        
        scrollable_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create written entries
        self.written_entries = []
        written_start = self.flow.mcq_count + 1
        
        for i in range(self.flow.written_count):
            q_num = written_start + i
            
            row_frame = tk.Frame(scrollable_frame, bg=self.WRITTEN_COLOR)
            row_frame.pack(fill=tk.X, pady=4)
            
            tk.Label(row_frame, text=f"Q{q_num}.", width=5, anchor="e",
                    font=("Segoe UI", 10, "bold"), bg=self.WRITTEN_COLOR, fg="#e65100").pack(side=tk.LEFT, padx=(0, 6))
            
            entry = ttk.Entry(row_frame, width=10, font=("Segoe UI", 11), justify="center")
            entry.pack(side=tk.LEFT)
            self.written_entries.append((q_num, entry))
            
            entry.bind('<KeyRelease>', lambda e, q=q_num, ent=entry: self.on_written_answer_change(q, ent))
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
    
    def on_mcq_checkbox_change(self, question_num, checkbox_vars):
        """Handle MCQ checkbox change"""
        # Get selected answers
        selected_answers = [letter for letter, var in checkbox_vars.items() if var.get()]
        
        if not selected_answers:
            # Clear answer if no checkboxes are selected
            current_key = self.flow.answer_keys[self.flow.current_key_letter]
            if str(question_num) in current_key.mcq_answers:
                del current_key.mcq_answers[str(question_num)]
        else:
            # Convert selected answers to comma-separated string
            answer_input = ','.join(sorted(selected_answers))
            success, error = self.flow.set_mcq_answer(question_num, answer_input)
            
            if not success:
                # Revert checkbox state
                for letter, var in checkbox_vars.items():
                    var.set(letter in selected_answers)
        
        self.update_progress()
    
    def on_written_answer_change(self, question_num, entry):
        """Handle written answer change"""
        answer_input = entry.get().strip()
        
        if not answer_input:
            # Get current key object
            current_key = self.flow.answer_keys[self.flow.current_key_letter]
            if str(question_num) in current_key.written_answers:
                del current_key.written_answers[str(question_num)]
            entry.config(style="TEntry")
        else:
            success, error = self.flow.set_written_answer(question_num, answer_input)
            
            if success:
                entry.config(style="Valid.TEntry")
            else:
                entry.config(style="TEntry")
        
        self.update_progress()
    
    def reload_answer_entries(self):
        """Reload entry fields when switching keys"""
        # Get current key object
        current_key = self.flow.answer_keys[self.flow.current_key_letter]
        
        # Reload MCQ checkboxes
        for q_num, checkbox_vars in self.mcq_checkboxes:
            answers = current_key.mcq_answers.get(str(q_num), [])
            for letter, var in checkbox_vars.items():
                var.set(letter in answers)
        
        # Reload written entries
        for q_num, entry in self.written_entries:
            entry.delete(0, tk.END)
            if str(q_num) in current_key.written_answers:
                entry.insert(0, str(current_key.written_answers[str(q_num)]))
                entry.config(style="Valid.TEntry")
            else:
                entry.config(style="TEntry")
    
    def update_progress(self):
        """Update progress display"""
        # Overall progress across all keys
        all_progress = self.flow.get_all_keys_progress()
        
        total_answered = 0
        total_expected = 0
        
        for letter, progress in all_progress.items():
            total_answered += progress['overall']['answered']
            total_expected += progress['overall']['total']
        
        percentage = (total_answered / total_expected * 100) if total_expected > 0 else 0
        
        self.progress_label.config(text=f"{percentage:.0f}% complete ({total_answered}/{total_expected})")
        
        # Current key completion
        current_progress = self.flow.get_current_key_progress()
        
        if current_progress['overall']['is_complete']:
            self.status_var.set(f"✓ Key {self.flow.current_key_letter} complete")
        else:
            self.status_var.set(f"Key {self.flow.current_key_letter}: "
                              f"{current_progress['overall']['answered']}/{current_progress['overall']['total']} answered")
    
    def create_control_buttons(self, parent):
        """Create control buttons"""
        control_frame = tk.Frame(parent, bg=self.BG_COLOR)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Back to Config", 
                  command=self.show_configuration).pack(side=tk.LEFT)
        
        ttk.Button(control_frame, text="Cancel", 
                  command=self.root.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        
        self.save_btn = ttk.Button(control_frame, text="💾 Save All Keys", 
                                  command=self.on_save,
                                  state=DISABLED,
                                  style="Accent.TButton")
        self.save_btn.pack(side=tk.RIGHT)
    
    def show_configuration(self):
        """Show configuration panel again"""
        for widget in self.key_entry_frame.winfo_children():
            widget.destroy()
        
        self.config_card.pack(fill=tk.X, pady=(0, 20))
    
    def on_save(self):
        """Save all keys"""
        # Validate all keys complete
        valid, error, progress = self.flow.validate_all_keys()
        
        if not valid:
            messagebox.showerror("Error", f"Cannot save:\n{error}")
            return
        
        # Save
        success, error, result_dict = self.flow.save_exam_answer_keys()  # Changed from saved_path to result_dict
        
        if success:
            msg = f"✓ Answer keys saved successfully!\n\n"
            msg += f"File: {os.path.basename(result_dict['file_path'])}\n"  # Access file_path from result_dict
            msg += f"Exam: {self.flow.exam_name}\n"
            msg += f"Keys: {', '.join(self.flow.answer_keys.keys())}\n"
            msg += f"Questions: {self.flow.mcq_count + self.flow.written_count}"
            
            # Add exam ID if available
            if result_dict.get('exam_id'):
                msg += f"\nExam ID: {result_dict['exam_id']}"
            
            messagebox.showinfo("Success", msg)
            self.root.destroy()
        else:
            messagebox.showerror("Error", f"Failed to save:\n{error}")


def create_answer_key_ui():
    """Create and run answer key UI"""
    root = tk.Tk()
    ui = AnswerKeyUI(root)
    ui.run()


def run():
    """Run the UI"""
    root = tk.Tk()
    ui = AnswerKeyUI(root)
    ui.root.mainloop()


if __name__ == "__main__":
    run()