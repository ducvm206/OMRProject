"""
Grading UI
Pure UI components for grading answer sheets
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, StringVar, IntVar, NORMAL, DISABLED
from PIL import Image, ImageTk
import cv2
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.file_utils import select_file, select_directory, get_project_root, create_temp_file, cleanup_temp_files
from flows.grading_flow import GradingFlow


class GradingUI:
    """UI for grading answer sheets"""
    
    def __init__(self, root):
        """
        Initialize UI
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.flow = GradingFlow()
        
        # UI State
        self.template_var = StringVar(value="Not loaded")
        self.key_var = StringVar(value="Not loaded")
        self.threshold_var = IntVar(value=50)
        self.mode_var = StringVar(value="single")
        
        # Batch state
        self.current_batch_index = 0
        self.temp_files = []
        
        # Image display
        self.current_image = None
        self.canvas_scale = 1.0
        
        # Setup UI
        self.setup_window()
        self.create_ui()
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("Grade Answer Sheets")
        self.root.geometry("1400x850")
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
    
    def create_ui(self):
        """Create main UI components"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create paned window
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left panel
        left_panel = tk.Frame(paned, bg=self.BG_COLOR, width=500)
        paned.add(left_panel, weight=0)
        
        # Right panel
        right_panel = tk.Frame(paned, bg=self.BG_COLOR)
        paned.add(right_panel, weight=1)
        
        # Create panels
        self.create_left_panel(left_panel)
        self.create_right_panel(right_panel)
        
        # Handle cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_left_panel(self, parent):
        """Create left control panel"""
        content = tk.Frame(parent, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(content, text="📊 Grade Answer Sheets",
                font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333").pack(pady=(0, 20))
        
        # Configuration card
        self.create_config_card(content)
        
        # Mode card
        self.create_mode_card(content)
        
        # Results area
        self.create_results_area(content)
    
    def create_config_card(self, parent):
        """Create configuration card"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        tk.Label(inner, text="⚙️ Configuration",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        # Template
        template_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        template_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(template_frame, text="Template:", font=("Segoe UI", 9, "bold"),
                bg=self.CARD_COLOR).pack(side=tk.LEFT)
        tk.Label(template_frame, textvariable=self.template_var,
                font=("Segoe UI", 9), bg=self.CARD_COLOR, fg="#666").pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(template_frame, text="📂", command=self.on_load_template, width=3).pack(side=tk.LEFT)
        
        # Answer Key
        key_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        key_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(key_frame, text="Answer Key:", font=("Segoe UI", 9, "bold"),
                bg=self.CARD_COLOR).pack(side=tk.LEFT)
        tk.Label(key_frame, textvariable=self.key_var,
                font=("Segoe UI", 9), bg=self.CARD_COLOR, fg="#666").pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(key_frame, text="📂", command=self.on_load_key, width=3).pack(side=tk.LEFT)
        
        # Threshold
        tk.Label(inner, text="Detection Threshold:",
                font=("Segoe UI", 9, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(10, 5))
        
        threshold_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        threshold_frame.pack(fill=tk.X)
        
        ttk.Scale(threshold_frame, from_=20, to=90, variable=self.threshold_var,
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.threshold_label = tk.Label(threshold_frame, text=f"{self.threshold_var.get()}%",
                                       bg=self.CARD_COLOR, width=5)
        self.threshold_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.threshold_var.trace("w", self.update_threshold_label)
    
    def create_mode_card(self, parent):
        """Create mode selection card"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        tk.Label(inner, text="📋 Grading Mode",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        ttk.Radiobutton(inner, text="Single sheet", variable=self.mode_var,
                       value="single").pack(anchor="w", pady=3)
        ttk.Radiobutton(inner, text="Batch (folder)", variable=self.mode_var,
                       value="batch").pack(anchor="w", pady=3)
        
        ttk.Button(inner, text="🚀 Start Grading", command=self.on_grade,
                  style="Accent.TButton").pack(pady=(15, 0))
    
    def create_results_area(self, parent):
        """Create results display area"""
        card = tk.Frame(parent, bg=self.CARD_COLOR)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(card, bg=self.CARD_COLOR)
        inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        tk.Label(inner, text="📈 Results",
                font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        # Results text
        self.results_text = tk.Text(inner, height=20, wrap=tk.WORD,
                                   font=("Courier New", 9), bg="#fafafa", relief=tk.FLAT)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.results_text.insert("1.0", "Results will appear here after grading...")
        self.results_text.config(state=tk.DISABLED)
        
        # Navigation for batch mode
        self.nav_frame = tk.Frame(inner, bg=self.CARD_COLOR)
        
        self.nav_label = tk.Label(self.nav_frame, text="Sheet 1 of 1", bg=self.CARD_COLOR,
                                 font=("Segoe UI", 9, "bold"))
        self.nav_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.prev_btn = ttk.Button(self.nav_frame, text="← Prev", command=self.on_prev_sheet, width=8)
        self.prev_btn.pack(side=tk.LEFT, padx=2)
        
        self.next_btn = ttk.Button(self.nav_frame, text="Next →", command=self.on_next_sheet, width=8)
        self.next_btn.pack(side=tk.LEFT, padx=2)
    
    def create_right_panel(self, parent):
        """Create right preview panel"""
        content = tk.Frame(parent, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(content, text="👁️ Answer Sheet Preview",
                font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333").pack(pady=(0, 15))
        
        # Image canvas
        image_card = tk.Frame(content, bg=self.CARD_COLOR)
        image_card.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(image_card, bg="#f0f0f0", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.current_image = None
        
        # Placeholder
        self.canvas.create_text(400, 300,
                               text="Answer sheet preview will\nappear here after grading",
                               font=("Segoe UI", 12), fill="gray", justify=tk.CENTER)
    
    def update_threshold_label(self, *args):
        """Update threshold label"""
        self.threshold_label.config(text=f"{self.threshold_var.get()}%")
    
    def on_load_template(self):
        """Handle load template button"""
        template_dir = os.path.join(get_project_root(), 'template')
        
        path = select_file(
            title="Select Template JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initial_dir=template_dir
        )
        
        if not path:
            return
        
        success, error, template_info = self.flow.load_template(path)
        
        if success:
            self.template_var.set(template_info['name'])
        else:
            messagebox.showerror("Error", f"Failed to load template:\n{error}")
    
    def on_load_key(self):
        """Handle load answer key button"""
        key_dir = os.path.join(get_project_root(), 'answer_keys')
        
        path = select_file(
            title="Select Answer Key JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initial_dir=key_dir
        )
        
        if not path:
            return
        
        success, error, key_info = self.flow.load_answer_key(path)
        
        if success:
            self.key_var.set(key_info['name'])
        else:
            messagebox.showerror("Error", f"Failed to load answer key:\n{error}")
    
    def on_grade(self):
        """Handle start grading button"""
        config = self.flow.get_configuration()
        
        if not config['template_loaded']:
            messagebox.showerror("Error", "Please load template first")
            return
        
        if not config['key_loaded']:
            messagebox.showerror("Error", "Please load answer key first")
            return
        
        # Set threshold
        self.flow.set_threshold(self.threshold_var.get())
        
        if self.mode_var.get() == "single":
            self.grade_single()
        else:
            self.grade_batch()
    
    def grade_single(self):
        """Grade single sheet"""
        image_path = select_file(
            title="Select Filled Answer Sheet",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")]
        )
        
        if not image_path:
            return
        
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", "Processing answer sheet...\n")
        self.results_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
        success, error, result = self.flow.grade_single_sheet(image_path)
        
        if success:
            self.display_single_result(result)
            self.nav_frame.pack_forget()
            
            # Display the processed image with colored bubble outlines
            processed_image = self.flow.get_processed_image()
            if processed_image is not None:
                self._display_image_on_canvas(processed_image)
            else:
                print("[UI] Warning: No processed image available")
        else:
            messagebox.showerror("Error", f"Grading failed:\n{error}")
    
    def grade_batch(self):
        """Grade batch of sheets"""
        folder_path = select_directory(
            title="Select Folder with Answer Sheets"
        )
        
        if not folder_path:
            return
        
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", "Processing batch...\n")
        self.results_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
        success, error, results = self.flow.grade_batch(folder_path)
        
        if success:
            batch_results, summary = results
            self.current_batch_index = 0
            self.display_batch_result(0)
            self.nav_frame.pack(pady=(10, 0))
            
            messagebox.showinfo("Batch Complete",
                f"Batch grading complete!\n\n"
                f"• {summary['total_sheets']} sheets graded\n"
                f"• Average score: {summary['avg_score']:.1f}%\n"
                f"• Use navigation to view results")
        else:
            messagebox.showerror("Error", f"Batch grading failed:\n{error}")
    
    def display_single_result(self, result):
        """Display single grading result"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        
        # Header
        self.results_text.insert(tk.END, "╔" + "═" * 48 + "╗\n", "header")
        self.results_text.insert(tk.END, "GRADING RESULTS\n", "header")
        self.results_text.insert(tk.END, "╚" + "═" * 48 + "╝\n\n", "header")
        
        # Student ID
        self.results_text.insert(tk.END, f"Student ID: ", "label")
        self.results_text.insert(tk.END, f"{result['student_id']}\n\n", "value")
        
        # Score
        self.results_text.insert(tk.END, f"Score: ", "label")
        self.results_text.insert(tk.END, f"{result['correct']}/{result['total_questions']}\n", "score")
        
        self.results_text.insert(tk.END, f"Percentage: ", "label")
        self.results_text.insert(tk.END, f"{result['percentage']:.1f}%\n\n", "score")
        
        # Details
        self.results_text.insert(tk.END, f"✓ Correct: ", "label")
        self.results_text.insert(tk.END, f"{result['correct']}\n", "correct")
        
        self.results_text.insert(tk.END, f"✗ Wrong: ", "label")
        self.results_text.insert(tk.END, f"{result['wrong']}\n", "wrong")
        
        self.results_text.insert(tk.END, f"○ Blank: ", "label")
        self.results_text.insert(tk.END, f"{result['blank']}\n", "blank")
        
        # Configure tags
        self.results_text.tag_config("header", font=("Courier New", 9, "bold"))
        self.results_text.tag_config("label", font=("Courier New", 9, "bold"))
        self.results_text.tag_config("value", font=("Courier New", 9))
        self.results_text.tag_config("score", font=("Courier New", 10, "bold"), foreground="blue")
        self.results_text.tag_config("correct", foreground="green")
        self.results_text.tag_config("wrong", foreground="red")
        self.results_text.tag_config("blank", foreground="orange")
        
        self.results_text.config(state=tk.DISABLED)
    
    def _display_image_on_canvas(self, image_array):
        """
        Display image array on canvas (expects RGB format)
        
        Args:
            image_array: NumPy array in RGB format
        """
        if image_array is None:
            print("[UI] Cannot display None image")
            return
        
        try:
            # Image is already in RGB format from the flow
            pil_image = Image.fromarray(image_array.astype('uint8'))
            
            # Get canvas dimensions
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Use defaults if canvas not ready
            if canvas_width < 10 or canvas_height < 10:
                canvas_width = 800
                canvas_height = 600
            
            # Calculate scaling to fit canvas (with padding)
            img_width, img_height = pil_image.size
            scale_x = (canvas_width - 40) / img_width
            scale_y = (canvas_height - 40) / img_height
            self.canvas_scale = min(scale_x, scale_y, 1.0)  # Don't scale up
            
            # Resize image
            new_width = int(img_width * self.canvas_scale)
            new_height = int(img_height * self.canvas_scale)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_image = ImageTk.PhotoImage(pil_image)
            
            # Clear canvas and display
            self.canvas.delete("all")
            x = canvas_width // 2
            y = canvas_height // 2
            self.canvas.create_image(x, y, image=self.current_image, anchor=tk.CENTER)
            
            print(f"[UI] Image displayed: {new_width}x{new_height}")
            
        except Exception as e:
            print(f"[UI] Error displaying image: {e}")
            import traceback
            traceback.print_exc()
            self.canvas.delete("all")
            self.canvas.create_text(400, 300,
                                   text=f"Error displaying image:\n{str(e)[:50]}",
                                   font=("Segoe UI", 10), fill="red", justify=tk.CENTER)
    
    def display_batch_result(self, index):
        """Display batch result at index"""
        batch_results = self.flow.get_batch_results()
        
        if not batch_results or index >= len(batch_results):
            return
        
        result = batch_results[index]
        
        # Update navigation
        self.nav_label.config(text=f"Sheet {index + 1} of {len(batch_results)}")
        self.prev_btn.config(state=NORMAL if index > 0 else DISABLED)
        self.next_btn.config(state=NORMAL if index < len(batch_results) - 1 else DISABLED)
        
        # Display result text
        self.display_single_result(result)
        
        # Get and display the processed image for this sheet
        processed_image = self.flow.get_processed_image_for_sheet(index)
        if processed_image is not None:
            self._display_image_on_canvas(processed_image)
        else:
            print(f"[UI] Warning: No processed image for sheet {index}")
    
    def on_prev_sheet(self):
        """Handle previous button"""
        if self.current_batch_index > 0:
            self.current_batch_index -= 1
            self.display_batch_result(self.current_batch_index)
    
    def on_next_sheet(self):
        """Handle next button"""
        batch_results = self.flow.get_batch_results()
        if self.current_batch_index < len(batch_results) - 1:
            self.current_batch_index += 1
            self.display_batch_result(self.current_batch_index)
    
    def on_close(self):
        """Handle window close"""
        cleanup_temp_files(self.temp_files)
        self.root.destroy()
    
    def run(self):
        """Run the UI"""
        self.root.mainloop()


def create_grading_ui():
    """Create and run grading UI"""
    root = tk.Tk()
    ui = GradingUI(root)
    ui.run()


if __name__ == "__main__":
    create_grading_ui()