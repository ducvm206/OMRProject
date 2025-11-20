"""
Sheet Generation UI
Pure UI components for sheet generation and template extraction
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
        """
        Initialize UI
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.flow = SheetGenerationFlow()
        
        # UI State
        self.questions_var = StringVar(value="40")
        self.student_id_var = BooleanVar(value=True)
        self.class_info_var = BooleanVar(value=True)
        self.timestamp_var = BooleanVar(value=False)
        self.output_dir_var = StringVar(value="blank_sheets")
        self.filename_var = StringVar(value="answer_sheet_40_questions.pdf")
        self.status_var = StringVar(value="Ready to generate")
        
        # State
        self.current_preview_image = None
        self.extract_enabled = False
        
        # Setup UI
        self.setup_window()
        self.create_ui()
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("Answer Sheet Generator & Template Extractor")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Configure style
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
        """Create main UI components"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create paned window for left/right split
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left panel (controls)
        left_panel = tk.Frame(paned, bg=self.BG_COLOR, width=450)
        paned.add(left_panel, weight=0)
        
        # Right panel (preview)
        right_panel = tk.Frame(paned, bg=self.BG_COLOR)
        paned.add(right_panel, weight=1)
        
        # Create left panel content
        self.create_left_panel(left_panel)
        
        # Create right panel content
        self.create_right_panel(right_panel)
    
    def create_left_panel(self, parent):
        """Create left control panel"""
        content = tk.Frame(parent, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(content, text="📋 Sheet Generator & Template Extractor",
                font=("Segoe UI", 15, "bold"), bg=self.BG_COLOR, fg="#333").pack(pady=(0, 20))
        
        # Configuration card
        self.create_config_card(content)
        
        # Options card
        self.create_options_card(content)
        
        # Output card
        self.create_output_card(content)
        
        # Buttons
        self.create_buttons(content)
        
        # Status
        self.create_status(content)
    
    def create_config_card(self, parent):
        """Create configuration card"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(inner, text="🔧 Sheet Settings",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
        
        # Number of questions
        q_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        q_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(q_frame, text="Number of Questions:",
                font=("Segoe UI", 10), bg=self.CARD_COLOR).pack(side=tk.LEFT)
        
        vcmd = (self.root.register(self.validate_number_input), '%d', '%P')
        q_entry = ttk.Entry(q_frame, textvariable=self.questions_var,
                           width=15, validate="key", validatecommand=vcmd)
        q_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Bind to update filename
        self.questions_var.trace("w", self.update_filename_preview)
    
    def create_options_card(self, parent):
        """Create options card"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(inner, text="⚙️ Additional Options",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
        
        ttk.Checkbutton(inner, text="Include Student ID Field",
                       variable=self.student_id_var).pack(anchor=tk.W, pady=5)
        ttk.Checkbutton(inner, text="Include Class Information",
                       variable=self.class_info_var).pack(anchor=tk.W, pady=5)
        ttk.Checkbutton(inner, text="Include Timestamp",
                       variable=self.timestamp_var).pack(anchor=tk.W, pady=5)
    
    def create_output_card(self, parent):
        """Create output settings card"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=20)
        
        tk.Label(inner, text="💾 Output Settings",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
        
        # Directory
        dir_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        dir_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(dir_frame, text="Directory:", font=("Segoe UI", 10),
                bg=self.CARD_COLOR).pack(side=tk.LEFT)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=20)
        dir_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="📁", command=self.on_browse_directory,
                  width=3).pack(side=tk.LEFT)
        
        # Filename
        file_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        file_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(file_frame, text="Filename:", font=("Segoe UI", 10),
                bg=self.CARD_COLOR).pack(side=tk.LEFT)
        file_entry = ttk.Entry(file_frame, textvariable=self.filename_var, width=20)
        file_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Auto", command=self.auto_generate_filename,
                  width=5).pack(side=tk.LEFT)
    
    def create_buttons(self, parent):
        """Create action buttons"""
        button_frame = tk.Frame(parent, bg=self.BG_COLOR)
        button_frame.pack(fill=tk.X, pady=(20, 15))
        
        ttk.Button(button_frame, text="Reset",
                  command=self.on_reset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🚀 Generate Sheet",
                  command=self.on_generate, style="Accent.TButton").pack(side=tk.RIGHT)
        
        # Extract button
        extract_frame = tk.Frame(parent, bg=self.BG_COLOR)
        extract_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.extract_btn = ttk.Button(extract_frame, text="🔍 Extract Template (Detect Bubbles)",
                                      command=self.on_extract, state=DISABLED)
        self.extract_btn.pack(fill=tk.X)
        
        tk.Label(extract_frame, text="Generate a sheet first, then extract template",
                font=("Segoe UI", 8), bg=self.BG_COLOR, fg="#999").pack(pady=(5, 0))
    
    def create_status(self, parent):
        """Create status bar"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 10))
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        status_label = tk.Label(inner, textvariable=self.status_var,
                              font=("Segoe UI", 9), bg=self.CARD_COLOR, fg="#666")
        status_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(inner, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))
        
        # Footer
        footer_label = tk.Label(parent,
                              text="Step 1: Generate → Step 2: Extract Template",
                              font=("Segoe UI", 9), bg=self.BG_COLOR, fg="#999")
        footer_label.pack(side=tk.BOTTOM, pady=(15, 0))
    
    def create_right_panel(self, parent):
        """Create right preview panel"""
        content = tk.Frame(parent, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(content, text="👁️ Live Preview",
                font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333").pack(pady=(0, 15))
        
        # Preview card
        preview_card = tk.Frame(content, bg=self.CARD_COLOR)
        preview_card.pack(fill=tk.BOTH, expand=True)
        
        self.preview_frame = tk.Frame(preview_card, bg="#f0f0f0", relief="flat")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Show placeholder
        self.show_preview_placeholder()
    
    def show_preview_placeholder(self):
        """Show placeholder in preview"""
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        placeholder = tk.Label(self.preview_frame,
                             text="📄\n\nGenerate an answer sheet\nto see preview",
                             font=("Segoe UI", 12), bg="#f5f5f5",
                             fg="#999", justify=tk.CENTER)
        placeholder.pack(expand=True)
    
    def validate_number_input(self, action, value):
        """Validate number input"""
        if action == '1':
            return value == "" or value.isdigit()
        return True
    
    def update_filename_preview(self, *args):
        """Update filename based on questions"""
        try:
            num = self.questions_var.get()
            if num.isdigit():
                self.filename_var.set(f"answer_sheet_{num}_questions.pdf")
        except:
            pass
    
    def auto_generate_filename(self):
        """Auto-generate filename"""
        self.update_filename_preview()
    
    def on_browse_directory(self):
        """Handle browse directory button"""
        directory = select_directory(
            title="Select Output Directory",
            initial_dir=get_project_root(),
            return_relative=False
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def on_generate(self):
        """Handle generate button"""
        # Configure flow
        success, error = self.flow.configure_sheet(
            num_questions=self.questions_var.get(),
            include_student_id=self.student_id_var.get(),
            include_class_info=self.class_info_var.get(),
            include_timestamp=self.timestamp_var.get()
        )
        
        if not success:
            messagebox.showerror("Error", error)
            return
        
        success, error = self.flow.set_output_location(
            directory=self.output_dir_var.get(),
            filename=self.filename_var.get()
        )
        
        if not success:
            messagebox.showerror("Error", error)
            return
        
        # Generate
        self.status_var.set("Generating answer sheet...")
        self.progress_bar.start()
        self.root.update_idletasks()
        
        success, error, pdf_path = self.flow.generate_sheet()
        
        self.progress_bar.stop()
        
        if success:
            self.status_var.set(f"Success! Created: {os.path.basename(pdf_path)}")
            self.extract_enabled = True
            self.extract_btn.config(state=NORMAL)
            
            # Show preview
            self.update_preview(pdf_path)
            
            messagebox.showinfo("Success",
                f"Answer sheet created successfully!\n\n"
                f"Saved as: {pdf_path}\n\n"
                f"Click 'Extract Template' to detect bubbles.")
        else:
            self.status_var.set("Error during generation")
            messagebox.showerror("Error", f"Failed to create sheet:\n{error}")
    
    def on_extract(self):
        """Handle extract button"""
        if not self.flow.current_pdf_path:
            messagebox.showerror("Error", "No PDF to extract from")
            return
        
        self.status_var.set("Extracting template...")
        self.progress_bar.start()
        self.root.update_idletasks()
        
        success, error, template_path = self.flow.extract_template(show_visualization=True)
        
        self.progress_bar.stop()
        
        if success:
            self.status_var.set(f"Template extracted: {os.path.basename(template_path)}")
            
            info = self.flow.get_generation_info()
            
            msg = f"Template extracted successfully!\n\n"
            msg += f"JSON saved as: {template_path}\n"
            
            if info['sheet_id'] and info['template_id']:
                msg += f"\nDatabase: Sheet #{info['sheet_id']} → Template #{info['template_id']}"
            
            msg += "\n\nDetection visualizations were shown in separate windows."
            
            messagebox.showinfo("Success", msg)
        else:
            self.status_var.set("Failed to extract template")
            messagebox.showerror("Error", f"Failed to extract template:\n{error}")
    
    def on_reset(self):
        """Handle reset button"""
        self.flow.reset()
        
        self.questions_var.set("40")
        self.student_id_var.set(True)
        self.class_info_var.set(True)
        self.timestamp_var.set(False)
        self.output_dir_var.set("blank_sheets")
        self.filename_var.set("answer_sheet_40_questions.pdf")
        self.status_var.set("Ready to generate")
        
        self.extract_enabled = False
        self.extract_btn.config(state=DISABLED)
        
        self.show_preview_placeholder()
    
    def update_preview(self, pdf_path):
        """Update preview with PDF"""
        try:
            # Convert PDF to image
            pdf_doc = fitz.open(pdf_path)
            page = pdf_doc[0]
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            pdf_doc.close()
            
            # Display image
            self.display_image(pil_image)
            
        except Exception as e:
            print(f"[UI] Preview error: {e}")
            self.show_preview_error(str(e))
    
    def display_image(self, pil_image):
        """Display PIL image in preview"""
        try:
            # Clear preview
            for widget in self.preview_frame.winfo_children():
                widget.destroy()
            
            # Calculate scaling
            self.preview_frame.update_idletasks()
            frame_width = self.preview_frame.winfo_width() - 40
            frame_height = self.preview_frame.winfo_height() - 40
            
            if frame_width < 10:
                frame_width = 600
                frame_height = 800
            
            img_width, img_height = pil_image.size
            scale = min((frame_width - 60) / img_width, (frame_height - 60) / img_height, 1.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            resized = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.current_preview_image = ImageTk.PhotoImage(resized)
            
            # Paper frame
            paper_frame = tk.Frame(self.preview_frame, bg="white", relief="raised", bd=2)
            paper_frame.pack(pady=20, padx=20)
            
            image_label = tk.Label(paper_frame, image=self.current_preview_image, bg="white")
            image_label.pack(pady=10, padx=10)
            
            # Status label
            watermark = tk.Label(self.preview_frame, text="✓ PDF Generated",
                               font=("Segoe UI", 9, "bold"),
                               bg="#e8f5e9", fg="#2e7d32",
                               relief="flat", padx=10, pady=5)
            watermark.pack(side=tk.BOTTOM, pady=5)
            
        except Exception as e:
            print(f"[UI] Display error: {e}")
            self.show_preview_error(str(e))
    
    def show_preview_error(self, message):
        """Show error in preview"""
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        error_label = tk.Label(self.preview_frame,
                             text=f"Preview unavailable\n{message}",
                             font=("Segoe UI", 10), bg="#f5f5f5",
                             fg="#d32f2f", justify=tk.CENTER)
        error_label.pack(expand=True)
    
    def run(self):
        """Run the UI"""
        self.root.mainloop()


def create_sheet_ui():
    """Create and run sheet generation UI"""
    root = tk.Tk()
    ui = SheetGenerationUI(root)
    ui.run()


if __name__ == "__main__":
    create_sheet_ui()