"""
Sheet Generation UI
Pure UI components for sheet generation and template extraction
Updated for MCQ + Written questions and combined generation
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, StringVar, BooleanVar, NORMAL, DISABLED
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.file_utils import select_directory, get_project_root
from flows.sheet_flow import SheetGenerationFlow


class SheetGenerationUI:
    """UI for sheet generation and template extraction"""
    
    def __init__(self, root):
        self.root = root
        self.flow = SheetGenerationFlow()
        
        # UI State
        self.mcq_questions_var = StringVar(value="40")
        self.written_questions_var = StringVar(value="0")
        self.student_id_var = BooleanVar(value=True)
        self.key_var = BooleanVar(value=True)  # New: KEY area toggle
        self.class_info_var = BooleanVar(value=True)
        self.timestamp_var = BooleanVar(value=False)
        self.output_dir_var = StringVar(value="blank_sheets")
        self.filename_var = StringVar(value="answer_sheet_40_questions.pdf")
        self.status_var = StringVar(value="Ready to generate")
        self.auto_extract_var = BooleanVar(value=True)
        
        self.current_preview_image = None
        
        self.setup_window()
        self.create_ui()
    
    def setup_window(self):
        self.root.title("Answer Sheet Generator & Template Extractor")
        self.root.geometry("1500x1000")
        self.root.resizable(True, True)
        style = ttk.Style()
        style.theme_use('clam')
        self.BG_COLOR = "#f5f5f5"
        self.CARD_COLOR = "#ffffff"
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabel", background=self.BG_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.CARD_COLOR, relief="flat")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background=self.CARD_COLOR, font=("Segoe UI", 10))
        style.configure("TEntry", relief="flat", padding=5)
    
    def create_ui(self):
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        left_panel = tk.Frame(paned, bg=self.BG_COLOR, width=450)
        paned.add(left_panel, weight=0)
        right_panel = tk.Frame(paned, bg=self.BG_COLOR)
        paned.add(right_panel, weight=1)
        
        self.create_left_panel(left_panel)
        self.create_right_panel(right_panel)
    
    def create_left_panel(self, parent):
        content = tk.Frame(parent, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(content, text="📋 Sheet Generator & Template Extractor",
                font=("Segoe UI", 15, "bold"), bg=self.BG_COLOR, fg="#333").pack(pady=(0, 20))
        
        self.create_config_card(content)
        self.create_options_card(content)
        self.create_output_card(content)
        self.create_buttons(content)
        self.create_status(content)
    
    def create_config_card(self, parent):
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 15))
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(inner, text="🔧 Sheet Settings",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
        
        # MCQ
        mcq_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        mcq_frame.pack(fill=tk.X, pady=8)
        tk.Label(mcq_frame, text="MCQ Questions:", font=("Segoe UI", 10), bg=self.CARD_COLOR).pack(side=tk.LEFT)
        vcmd = (self.root.register(self.validate_number_input), '%d', '%P')
        ttk.Entry(mcq_frame, textvariable=self.mcq_questions_var, width=15,
                  validate="key", validatecommand=vcmd).pack(side=tk.LEFT, padx=(10,0))
        
        # Written
        written_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        written_frame.pack(fill=tk.X, pady=8)
        tk.Label(written_frame, text="Written Questions:", font=("Segoe UI", 10), bg=self.CARD_COLOR).pack(side=tk.LEFT)
        ttk.Entry(written_frame, textvariable=self.written_questions_var, width=15,
                  validate="key", validatecommand=vcmd).pack(side=tk.LEFT, padx=(10,0))
        
        self.mcq_questions_var.trace("w", self.update_filename_preview)
        self.written_questions_var.trace("w", self.update_filename_preview)
    
    def create_options_card(self, parent):
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0,15))
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(inner, text="⚙️ Additional Options",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0,15))
        
        # Create a grid layout for checkboxes
        options_grid = tk.Frame(inner, bg=self.CARD_COLOR)
        options_grid.pack(fill=tk.X, pady=5)
        
        # Left column
        left_col = tk.Frame(options_grid, bg=self.CARD_COLOR)
        left_col.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        ttk.Checkbutton(left_col, text="Include Student ID Field", variable=self.student_id_var).pack(anchor=tk.W, pady=5)
        ttk.Checkbutton(left_col, text="Include KEY Area", variable=self.key_var).pack(anchor=tk.W, pady=5)
        
        # Right column
        right_col = tk.Frame(options_grid, bg=self.CARD_COLOR)
        right_col.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        ttk.Checkbutton(right_col, text="Include Class Information", variable=self.class_info_var).pack(anchor=tk.W, pady=5)
        ttk.Checkbutton(right_col, text="Include Timestamp", variable=self.timestamp_var).pack(anchor=tk.W, pady=5)
        
        # Auto-extract on bottom
        ttk.Checkbutton(inner, text="Auto-extract template after generation", 
                       variable=self.auto_extract_var).pack(anchor=tk.W, pady=(15, 5))
    
    def create_output_card(self, parent):
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0,15))
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=20)
        tk.Label(inner, text="💾 Output Settings", font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0,15))
        
        dir_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        dir_frame.pack(fill=tk.X, pady=8)
        tk.Label(dir_frame, text="Directory:", font=("Segoe UI", 10), bg=self.CARD_COLOR).pack(side=tk.LEFT)
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=20).pack(side=tk.LEFT, padx=(10,5), fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="📁", command=self.on_browse_directory, width=3).pack(side=tk.LEFT)
        
        file_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        file_frame.pack(fill=tk.X, pady=8)
        tk.Label(file_frame, text="Filename:", font=("Segoe UI", 10), bg=self.CARD_COLOR).pack(side=tk.LEFT)
        ttk.Entry(file_frame, textvariable=self.filename_var, width=20).pack(side=tk.LEFT, padx=(10,5), fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Auto", command=self.auto_generate_filename, width=5).pack(side=tk.LEFT)
    
    def create_buttons(self, parent):
        frame = tk.Frame(parent, bg=self.BG_COLOR)
        frame.pack(fill=tk.X, pady=(20,15))
        ttk.Button(frame, text="Reset", command=self.on_reset).pack(side=tk.LEFT, padx=(0,10))
        self.generate_btn = ttk.Button(frame, text="🚀 Generate Sheet & Template", command=self.on_generate, style="Accent.TButton")
        self.generate_btn.pack(side=tk.RIGHT)
    
    def create_status(self, parent):
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0,10))
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=15)
        tk.Label(inner, textvariable=self.status_var, font=("Segoe UI", 9), bg=self.CARD_COLOR, fg="#666").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(inner, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(8,0))
        tk.Label(parent, text="One-click generation: Sheet + Template extraction",
                 font=("Segoe UI", 9), bg=self.BG_COLOR, fg="#999").pack(side=tk.BOTTOM, pady=(15,0))
    
    def create_right_panel(self, parent):
        content = tk.Frame(parent, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(content, text="👁️ Live Preview", font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333").pack(pady=(0,15))
        preview_card = tk.Frame(content, bg=self.CARD_COLOR)
        preview_card.pack(fill=tk.BOTH, expand=True)
        self.preview_frame = tk.Frame(preview_card, bg="#f0f0f0", relief="flat")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.show_preview_placeholder()
    
    def show_preview_placeholder(self):
        for w in self.preview_frame.winfo_children(): w.destroy()
        tk.Label(self.preview_frame, text="📄\n\nGenerate an answer sheet\nto see preview",
                 font=("Segoe UI", 12), bg="#f5f5f5", fg="#999", justify=tk.CENTER).pack(expand=True)
    
    def validate_number_input(self, action, value):
        return value.isdigit() or value == "" if action=='1' else True
    
    def update_filename_preview(self, *args):
        try:
            mcq = self.mcq_questions_var.get()
            written = self.written_questions_var.get()
            if mcq.isdigit() and written.isdigit():
                # Create a descriptive filename based on settings
                parts = []
                if int(written) > 0:
                    parts.append(f"{mcq}mcq_{written}written")
                else:
                    parts.append(f"{mcq}mcq")
                
                # Add flags for missing sections
                if not self.student_id_var.get():
                    parts.append("no_id")
                if not self.key_var.get():
                    parts.append("no_key")
                
                filename = f"answer_sheet_{'_'.join(parts)}.pdf"
                self.filename_var.set(filename)
        except: pass
    
    def auto_generate_filename(self): 
        self.update_filename_preview()
    
    def on_browse_directory(self):
        directory = select_directory(title="Select Output Directory", initial_dir=get_project_root(), return_relative=False)
        if directory: 
            # Convert to relative path if it's within the project
            if directory.startswith(get_project_root()):
                rel_path = os.path.relpath(directory, get_project_root())
                if rel_path.startswith("files"):
                    directory = rel_path.split(os.sep)[-1] if os.sep in rel_path else rel_path
            
            self.output_dir_var.set(directory)
    
    def on_generate(self):
        # Configure sheet with all options
        success, error = self.flow.configure_sheet(
            num_mcq_questions=self.mcq_questions_var.get(),
            num_written_questions=self.written_questions_var.get(),
            include_student_id=self.student_id_var.get(),
            include_key=self.key_var.get(),  # Pass KEY setting
            include_class_info=self.class_info_var.get(),
            include_timestamp=self.timestamp_var.get()
        )
        if not success: 
            return messagebox.showerror("Error", error)
        
        success, error = self.flow.set_output_location(
            directory=self.output_dir_var.get(),
            filename=self.filename_var.get()
        )
        if not success: 
            return messagebox.showerror("Error", error)
        
        self.status_var.set("Generating answer sheet...")
        self.progress_bar.start()
        self.generate_btn.config(state=DISABLED)
        self.root.update_idletasks()
        
        if self.auto_extract_var.get():
            success, error, pdf_path, template_path = self.flow.generate_and_extract(show_visualization=True)
        else:
            success, error, pdf_path = self.flow.generate_sheet()
            template_path = None
        
        self.progress_bar.stop()
        self.generate_btn.config(state=NORMAL)
        
        if success:
            self.status_var.set("Success!")
            self.update_preview(pdf_path)
            msg = f"PDF saved as: {pdf_path}\n"
            if template_path: 
                msg += f"Template saved as: {template_path}\n"
            
            # Show configuration summary
            info = self.flow.get_generation_info()
            config_summary = []
            if not info['include_student_id']:
                config_summary.append("No Student ID")
            if not info['include_key']:
                config_summary.append("No KEY")
            if not info['include_class_info']:
                config_summary.append("No class info")
            
            if config_summary:
                msg += f"Configuration: {', '.join(config_summary)}\n"
            
            if info['sheet_id'] and info['template_id']: 
                msg += f"DB: Sheet #{info['sheet_id']} → Template #{info['template_id']}"
            
            messagebox.showinfo("Success", msg)
        else:
            self.status_var.set("Error during generation")
            messagebox.showerror("Error", f"Failed to create sheet:\n{error}")
    
    def on_reset(self):
        self.flow.reset()
        self.mcq_questions_var.set("40")
        self.written_questions_var.set("0")
        self.student_id_var.set(True)
        self.key_var.set(True)  # Reset KEY toggle
        self.class_info_var.set(True)
        self.timestamp_var.set(False)
        self.auto_extract_var.set(True)
        self.output_dir_var.set("blank_sheets")
        self.filename_var.set("answer_sheet_40_questions.pdf")
        self.status_var.set("Ready to generate")
        self.show_preview_placeholder()
    
    def update_preview(self, pdf_path):
        try:
            pdf_doc = fitz.open(pdf_path)
            page = pdf_doc[0]
            mat = fitz.Matrix(1.5,1.5)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            pdf_doc.close()
            self.display_image(pil_image)
        except Exception as e:
            self.show_preview_error(str(e))
    
    def display_image(self, pil_image):
        for w in self.preview_frame.winfo_children(): w.destroy()
        self.preview_frame.update_idletasks()
        fw = max(self.preview_frame.winfo_width()-40, 600)
        fh = max(self.preview_frame.winfo_height()-40, 800)
        scale = min((fw-60)/pil_image.width, (fh-60)/pil_image.height, 1.0)
        resized = pil_image.resize((int(pil_image.width*scale), int(pil_image.height*scale)), Image.Resampling.LANCZOS)
        self.current_preview_image = ImageTk.PhotoImage(resized)
        pf = tk.Frame(self.preview_frame, bg="white", relief="raised", bd=2)
        pf.pack(pady=20, padx=20)
        tk.Label(pf, image=self.current_preview_image, bg="white").pack(pady=10, padx=10)
    
    def show_preview_error(self, message):
        for w in self.preview_frame.winfo_children(): w.destroy()
        tk.Label(self.preview_frame, text=f"Preview unavailable\n{message}", font=("Segoe UI", 10),
                 bg="#f5f5f5", fg="#d32f2f", justify=tk.CENTER).pack(expand=True)
    
    def run(self): self.root.mainloop()


def create_sheet_ui():
    root = tk.Tk()
    ui = SheetGenerationUI(root)
    ui.run()


if __name__ == "__main__":
    create_sheet_ui()