import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, StringVar, IntVar, BooleanVar
from PIL import Image, ImageTk, ImageDraw
import fitz  # PyMuPDF
import io
import cv2
import numpy as np
import json
import datetime

# Fix project root path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"[DEBUG] Project root: {PROJECT_ROOT}")
print(f"[DEBUG] sys.path: {sys.path[:3]}")

def get_parent_window():
    """Get reference to parent window if launched from home screen"""
    if not tk._default_root:
        return None
    
    for widget in tk._default_root.winfo_children():
        if isinstance(widget, tk.Tk):
            title = widget.title()
            if "Answer Sheet Grading System" in title:
                return widget
    return None

def create_integrated_gui():
    """Integrated GUI for sheet generation and template extraction with DB support"""
    
    # Global variables
    current_preview_image = None
    current_pdf_path = None
    current_template_json = None
    current_sheet_id = None
    db = None
    
    # Initialize database
    try:
        from core.database import GradingDatabase
        db = GradingDatabase()
        print("[DB] Database initialized successfully")
    except Exception as e:
        print(f"[DB] Warning: Could not initialize database: {e}")
        db = None
    
    def generate_sheet():
        nonlocal current_preview_image, current_pdf_path, current_template_json, current_sheet_id
        try:
            from core.sheet_maker import AnswerSheetDesigner
            
            # Get values from UI
            try:
                num_questions = int(questions_var.get())
                if num_questions <= 0:
                    messagebox.showerror("Error", "Number of questions must be positive")
                    return
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number for questions")
                return
            
            # Get output directory and filename
            output_dir = output_dir_var.get()
            filename = filename_var.get().strip()
            
            if not filename:
                messagebox.showerror("Error", "Please enter a filename")
                return
            
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Clean filename
            import re
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            # Update status
            status_var.set("Generating answer sheet...")
            progress_bar.start()
            root.update_idletasks()
            
            # Create designer and generate PDF
            designer = AnswerSheetDesigner()
            designer.set_config(
                include_student_id=student_id_var.get(),
                include_class_info=class_info_var.get(),
                include_timestamp=timestamp_var.get()
            )
            
            designer.create_answer_sheet(
                total_questions=num_questions,
                output_path=output_path,
                format='pdf',
                use_preset=True
            )
            
            progress_bar.stop()
            current_pdf_path = output_path
            status_var.set(f"Success! Created: {filename}")
            
            # Show PDF preview first
            update_preview_with_pdf(output_path)
            
            # Enable extract button
            extract_btn.config(state=tk.NORMAL)
            
            # Save to database (sheets table)
            if db:
                try:
                    # Save sheet to database
                    sheet_id = db.save_sheet(
                        image_path=output_path,
                        template_id=None,  # No template yet
                        num_questions=num_questions,
                        settings={
                            'student_id': student_id_var.get(),
                            'class_info': class_info_var.get(),
                            'timestamp': timestamp_var.get(),
                            'generated_at': datetime.datetime.now().isoformat()
                        }
                    )
                    current_sheet_id = sheet_id
                    print(f"[DB] Sheet saved with ID: {sheet_id}")
                    
                except Exception as e:
                    print(f"[DB] Failed to save sheet: {e}")
            
            messagebox.showinfo("Success", 
                f"Answer sheet created successfully!\n\n"
                f"Saved as: {output_path}\n\n"
                f"Click 'Extract Template' to detect bubbles and create template JSON.")
            
        except ImportError as e:
            progress_bar.stop()
            messagebox.showerror("Error", f"Failed to import sheet_maker: {e}")
            status_var.set("Error: Module not found")
        except Exception as e:
            progress_bar.stop()
            messagebox.showerror("Error", f"Failed to create answer sheet: {e}")
            status_var.set("Error during generation")
    
    def extract_template():
        nonlocal current_preview_image, current_template_json, current_sheet_id
        
        if not current_pdf_path or not os.path.exists(current_pdf_path):
            messagebox.showerror("Error", "No PDF to extract from. Generate a sheet first.")
            return
        
        try:
            from core.bubble_extraction import process_pdf_answer_sheet
            
            status_var.set("Extracting template...")
            progress_bar.start()
            root.update_idletasks()
            
            # Process PDF with visualization enabled
            json_path = process_pdf_answer_sheet(
                pdf_path=current_pdf_path,
                dpi=300,
                keep_png=False,
                show_visualization=True
            )
            
            progress_bar.stop()
            
            if json_path:
                current_template_json = json_path
                status_var.set(f"Template extracted: {os.path.basename(json_path)}")
                
                # Save template to database and link to sheet
                if db and current_sheet_id:
                    try:
                        # Read template to extract metadata
                        with open(json_path, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                        
                        # Extract template metadata
                        page_data = template_data.get('page_1', {})
                        num_questions = page_data.get('total_questions', 0)
                        if not num_questions:
                            num_questions = len(page_data.get('questions', []))
                        
                        # Get student ID info
                        has_student_id = bool(page_data.get('student_id', {}).get('digit_columns'))
                        
                        # Save template to database
                        template_id = db.save_template(
                            name=f"Template_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            json_path=json_path,
                            sheet_id=current_sheet_id,  # Link to the sheet
                            total_questions=num_questions,
                            has_student_id=has_student_id,
                            metadata={
                                'extraction_method': 'bubble_detection',
                                'source_pdf': current_pdf_path,
                                'extracted_at': datetime.datetime.now().isoformat()
                            }
                        )
                        
                        print(f"[DB] Template saved with ID: {template_id}")
                        
                        # Update sheet to mark as template
                        try:
                            db.update_sheet(sheet_id=current_sheet_id, updates={'is_template': True})
                            print(f"[DB] Sheet {current_sheet_id} marked as template")
                        except Exception as update_e:
                            print(f"[DB] Failed to update sheet: {update_e}")
                        
                        # Show success message with DB info
                        messagebox.showinfo("Success", 
                            f"Template extracted successfully!\n\n"
                            f"JSON saved as: {json_path}\n"
                            f"Database: Sheet #{current_sheet_id} → Template #{template_id}\n\n"
                            f"Detection visualizations were shown in separate windows.")
                        
                    except Exception as e:
                        print(f"[DB] Failed to save template: {e}")
                        # Show success but warn about DB
                        messagebox.showwarning("Success (DB Warning)", 
                            f"Template extracted but database save failed:\n{e}\n\n"
                            f"JSON saved as: {json_path}")
                else:
                    # No database connection
                    messagebox.showinfo("Success", 
                        f"Template extracted successfully!\n\n"
                        f"JSON saved as: {json_path}\n\n"
                        f"Detection visualizations were shown in separate windows.")
                        
            else:
                status_var.set("Failed to extract template")
                messagebox.showerror("Error", "Failed to extract template from PDF")
                
        except ImportError as e:
            progress_bar.stop()
            messagebox.showerror("Error", 
                f"Failed to import bubble_extraction module:\n{e}\n\n"
                f"Make sure core/bubble_extraction.py exists.")
            status_var.set("Error: Module not found")
        except Exception as e:
            progress_bar.stop()
            messagebox.showerror("Error", f"Failed to extract template: {e}")
            status_var.set("Error during extraction")
    
    def update_preview_with_pdf(pdf_path):
        """Update preview frame with PDF"""
        nonlocal current_preview_image
        
        try:
            # Clear previous preview
            for widget in preview_frame.winfo_children():
                widget.destroy()
            
            pdf_image = convert_pdf_to_image(pdf_path)
            if pdf_image:
                display_pdf_image(pdf_image, is_detection=False)
            else:
                show_preview_error("Could not generate preview")
                
        except Exception as e:
            print(f"Preview update error: {e}")
            show_preview_error(str(e))
    
    def convert_pdf_to_image(pdf_path, page_number=0):
        """Convert PDF page to PIL Image"""
        try:
            pdf_document = fitz.open(pdf_path)
            
            if page_number < len(pdf_document):
                page = pdf_document[page_number]
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                pil_image = Image.open(io.BytesIO(img_data))
                pdf_document.close()
                return pil_image
            else:
                pdf_document.close()
                return None
                
        except Exception as e:
            print(f"PDF to image conversion error: {e}")
            return None
    
    def display_pdf_image(pil_image, is_detection=False):
        """Display PIL Image in preview frame"""
        nonlocal current_preview_image
        
        try:
            preview_frame.update_idletasks()
            frame_width = preview_frame.winfo_width() - 40
            frame_height = preview_frame.winfo_height() - 40
            
            if frame_width < 10:
                frame_width = 400
                frame_height = 550
            
            # Calculate scaling
            img_width, img_height = pil_image.size
            scale_x = (frame_width - 60) / img_width
            scale_y = (frame_height - 60) / img_height
            scale = min(scale_x, scale_y, 1.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            current_preview_image = ImageTk.PhotoImage(resized_image)
            
            # Paper frame
            paper_frame = tk.Frame(preview_frame, bg="white", relief="raised", bd=2)
            paper_frame.pack(pady=20, padx=20)
            
            image_label = tk.Label(paper_frame, image=current_preview_image, bg="white")
            image_label.pack(pady=10, padx=10)
            
            # Status label
            if is_detection:
                status_text = "✓ Detection Complete"
                bg_color = "#e3f2fd"
                fg_color = "#1976d2"
                
                # Legend
                legend_frame = tk.Frame(preview_frame, bg="#f5f5f5")
                legend_frame.pack(side=tk.BOTTOM, pady=10, fill=tk.X)
                
                tk.Label(legend_frame, text="Legend:", font=("Segoe UI", 9, "bold"),
                        bg="#f5f5f5").pack(side=tk.LEFT, padx=10)
                tk.Label(legend_frame, text="🟦 Questions", font=("Segoe UI", 9),
                        bg="#f5f5f5", fg="blue").pack(side=tk.LEFT, padx=5)
                tk.Label(legend_frame, text="🟩 Bubbles (A,B,C,D)", font=("Segoe UI", 9),
                        bg="#f5f5f5", fg="green").pack(side=tk.LEFT, padx=5)
                tk.Label(legend_frame, text="🟦 ID Region", font=("Segoe UI", 9),
                        bg="#f5f5f5", fg="cyan").pack(side=tk.LEFT, padx=5)
                tk.Label(legend_frame, text="🟪 ID Bubbles", font=("Segoe UI", 9),
                        bg="#f5f5f5", fg="magenta").pack(side=tk.LEFT, padx=5)
            else:
                status_text = "✓ PDF Generated"
                bg_color = "#e8f5e9"
                fg_color = "#2e7d32"
            
            watermark_label = tk.Label(preview_frame, text=status_text,
                                     font=("Segoe UI", 9, "bold"),
                                     bg=bg_color, fg=fg_color,
                                     relief="flat", padx=10, pady=5)
            watermark_label.pack(side=tk.BOTTOM, pady=5)
            
        except Exception as e:
            print(f"Image display error: {e}")
            show_preview_error("Display error")
    
    def show_preview_error(message):
        """Show error message in preview frame"""
        error_label = tk.Label(preview_frame, 
                             text=f"Preview unavailable\n{message}",
                             font=("Segoe UI", 10), bg="#f5f5f5", 
                             fg="#d32f2f", justify=tk.CENTER)
        error_label.pack(expand=True)
    
    def browse_output_location():
        """Choose output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            output_dir_var.set(directory)
    
    def reset_defaults():
        """Reset all fields"""
        nonlocal current_pdf_path, current_template_json, current_sheet_id
        
        questions_var.set("40")
        student_id_var.set(True)
        class_info_var.set(True)
        timestamp_var.set(False)
        output_dir_var.set("blank_sheets")
        filename_var.set("answer_sheet_40_questions.pdf")
        status_var.set("Ready to generate")
        
        current_pdf_path = None
        current_template_json = None
        current_sheet_id = None
        extract_btn.config(state=tk.DISABLED)
        
        # Clear preview
        for widget in preview_frame.winfo_children():
            widget.destroy()
        
        placeholder_label = tk.Label(preview_frame,
                                   text="📄\n\nGenerate an answer sheet\nto see preview",
                                   font=("Segoe UI", 12), bg="#f5f5f5",
                                   fg="#999", justify=tk.CENTER)
        placeholder_label.pack(expand=True)
    
    def validate_number_input(action, value_if_allowed):
        """Validate number input"""
        if action == '1':
            if value_if_allowed == "" or value_if_allowed.isdigit():
                return True
            else:
                return False
        return True
    
    def update_filename_preview(*args):
        """Update filename based on questions"""
        try:
            num_questions = questions_var.get()
            if num_questions.isdigit():
                suggested_name = f"answer_sheet_{num_questions}_questions.pdf"
                filename_var.set(suggested_name)
        except:
            pass
    
    def show_database_status():
        """Show database connection status"""
        if db:
            try:
                cursor = db.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sheets'")
                result = cursor.fetchone()
                if result:
                    status_text = "✅ Database connected"
                else:
                    status_text = "⚠️ Database not initialized"
            except:
                status_text = "⚠️ Database status unknown"
        else:
            status_text = "❌ Database not available"
        
        messagebox.showinfo("Database Status", status_text)
    
    # Create main window
    root = tk.Tk()
    root.title("Answer Sheet Generator & Template Extractor")
    root.geometry("1200x800")
    root.resizable(True, True)
    
    # Configure style
    style = ttk.Style()
    style.theme_use('clam')
    
    BG_COLOR = "#f5f5f5"
    CARD_COLOR = "#ffffff"
    
    style.configure("TFrame", background=BG_COLOR)
    style.configure("TLabel", background=BG_COLOR, font=("Segoe UI", 10))
    style.configure("Card.TFrame", background=CARD_COLOR, relief="flat")
    style.configure("TButton", font=("Segoe UI", 10), padding=8)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
    style.configure("TCheckbutton", background=CARD_COLOR, font=("Segoe UI", 10))
    style.configure("TEntry", relief="flat", padding=5)
    
    # Main container
    main_container = tk.Frame(root, bg=BG_COLOR)
    main_container.pack(fill=tk.BOTH, expand=True)
    
    paned_window = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Left frame
    left_frame = tk.Frame(paned_window, bg=BG_COLOR, width=450)
    paned_window.add(left_frame, weight=0)
    
    # Right frame
    right_frame = tk.Frame(paned_window, bg=BG_COLOR)
    paned_window.add(right_frame, weight=1)
    
    # ===== LEFT FRAME =====
    left_content = tk.Frame(left_frame, bg=BG_COLOR)
    left_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Title
    title_label = tk.Label(left_content, 
                          text="📋 Sheet Generator & Template Extractor",
                          font=("Segoe UI", 15, "bold"), bg=BG_COLOR, fg="#333")
    title_label.pack(pady=(0, 20))
    
    # Database status button
    db_button = tk.Button(left_content, text="📊 Database Status", 
                         command=show_database_status, font=("Segoe UI", 9),
                         bg="#e3f2fd", relief="flat", padx=10, pady=5)
    db_button.pack(anchor=tk.NE, pady=(0, 10))
    
    # Configuration Card
    config_card = tk.Frame(left_content, bg=CARD_COLOR)
    config_card.pack(fill=tk.X, pady=(0, 15))
    
    config_inner = tk.Frame(config_card, bg=CARD_COLOR)
    config_inner.pack(fill=tk.BOTH, padx=20, pady=20)
    
    tk.Label(config_inner, text="🔧 Sheet Settings",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
    
    # Number of Questions
    questions_frame = tk.Frame(config_inner, bg=CARD_COLOR)
    questions_frame.pack(fill=tk.X, pady=8)
    
    tk.Label(questions_frame, text="Number of Questions:",
            font=("Segoe UI", 10), bg=CARD_COLOR).pack(side=tk.LEFT)
    questions_var = StringVar(value="40")
    questions_var.trace("w", update_filename_preview)
    vcmd = (root.register(validate_number_input), '%d', '%P')
    questions_entry = ttk.Entry(questions_frame, textvariable=questions_var,
                               width=15, validate="key", validatecommand=vcmd)
    questions_entry.pack(side=tk.LEFT, padx=(10, 0))
    
    # Options Card
    options_card = tk.Frame(left_content, bg=CARD_COLOR)
    options_card.pack(fill=tk.X, pady=(0, 15))
    
    options_inner = tk.Frame(options_card, bg=CARD_COLOR)
    options_inner.pack(fill=tk.BOTH, padx=20, pady=20)
    
    tk.Label(options_inner, text="⚙️ Additional Options",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
    
    student_id_var = BooleanVar(value=True)
    class_info_var = BooleanVar(value=True)
    timestamp_var = BooleanVar(value=False)
    
    ttk.Checkbutton(options_inner, text="Include Student ID Field",
                   variable=student_id_var).pack(anchor=tk.W, pady=5)
    ttk.Checkbutton(options_inner, text="Include Class Information",
                   variable=class_info_var).pack(anchor=tk.W, pady=5)
    ttk.Checkbutton(options_inner, text="Include Timestamp",
                   variable=timestamp_var).pack(anchor=tk.W, pady=5)
    
    # Output Card
    output_card = tk.Frame(left_content, bg=CARD_COLOR)
    output_card.pack(fill=tk.X, pady=(0, 15))
    
    output_inner = tk.Frame(output_card, bg=CARD_COLOR)
    output_inner.pack(fill=tk.BOTH, padx=20, pady=20)
    
    tk.Label(output_inner, text="💾 Output Settings",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
    
    # Directory
    dir_frame = tk.Frame(output_inner, bg=CARD_COLOR)
    dir_frame.pack(fill=tk.X, pady=8)
    
    tk.Label(dir_frame, text="Directory:", font=("Segoe UI", 10),
            bg=CARD_COLOR).pack(side=tk.LEFT)
    output_dir_var = StringVar(value="blank_sheets")
    dir_entry = ttk.Entry(dir_frame, textvariable=output_dir_var, width=20)
    dir_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
    ttk.Button(dir_frame, text="📁", command=browse_output_location,
              width=3).pack(side=tk.LEFT)
    
    # Filename
    filename_frame = tk.Frame(output_inner, bg=CARD_COLOR)
    filename_frame.pack(fill=tk.X, pady=8)
    
    tk.Label(filename_frame, text="Filename:", font=("Segoe UI", 10),
            bg=CARD_COLOR).pack(side=tk.LEFT)
    filename_var = StringVar(value="answer_sheet_40_questions.pdf")
    filename_entry = ttk.Entry(filename_frame, textvariable=filename_var, width=20)
    filename_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
    
    def auto_generate_filename():
        try:
            num_questions = questions_var.get()
            if num_questions.isdigit():
                suggested_name = f"answer_sheet_{num_questions}_questions.pdf"
                filename_var.set(suggested_name)
        except:
            pass
    
    ttk.Button(filename_frame, text="Auto", command=auto_generate_filename,
              width=5).pack(side=tk.LEFT)
    
    # Buttons Frame
    buttons_frame = tk.Frame(left_content, bg=BG_COLOR)
    buttons_frame.pack(fill=tk.X, pady=(20, 15))
    
    ttk.Button(buttons_frame, text="Reset",
              command=reset_defaults).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Button(buttons_frame, text="🚀 Generate Sheet",
              command=generate_sheet, style="Accent.TButton").pack(side=tk.RIGHT)
    
    # Extract button
    extract_frame = tk.Frame(left_content, bg=BG_COLOR)
    extract_frame.pack(fill=tk.X, pady=(0, 15))
    
    extract_btn = ttk.Button(extract_frame, text="🔍 Extract Template (Detect Bubbles)",
                            command=extract_template, state=tk.DISABLED)
    extract_btn.pack(fill=tk.X)
    
    tk.Label(extract_frame, text="Generate a sheet first, then extract template",
            font=("Segoe UI", 8), bg=BG_COLOR, fg="#999").pack(pady=(5, 0))
    
    # Status Card
    status_card = tk.Frame(left_content, bg=CARD_COLOR)
    status_card.pack(fill=tk.X, pady=(0, 10))
    
    status_inner = tk.Frame(status_card, bg=CARD_COLOR)
    status_inner.pack(fill=tk.BOTH, padx=20, pady=15)
    
    status_var = StringVar(value="Ready to generate")
    status_label = tk.Label(status_inner, textvariable=status_var,
                          font=("Segoe UI", 9), bg=CARD_COLOR, fg="#666")
    status_label.pack(anchor=tk.W)
    
    progress_bar = ttk.Progressbar(status_inner, mode='indeterminate')
    progress_bar.pack(fill=tk.X, pady=(8, 0))
    
    # Back to main menu and footer
    footer_frame = tk.Frame(left_content, bg=BG_COLOR)
    footer_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)
    
    # Back to main menu button
    def back_to_menu():
        parent = get_parent_window()
        if parent:
            root.destroy()
            parent.deiconify()
        else:
            if messagebox.askyesno("Exit", "Close Sheet Generator?"):
                root.destroy()
    
    ttk.Button(footer_frame, text="⬅ Main Menu", 
              command=back_to_menu).pack(side=tk.LEFT)
    
    footer_label = tk.Label(footer_frame,
                          text="Step 1: Generate → Step 2: Extract Template",
                          font=("Segoe UI", 9), bg=BG_COLOR, fg="#999")
    footer_label.pack(side=tk.RIGHT)
    
    # ===== RIGHT FRAME =====
    right_content = tk.Frame(right_frame, bg=BG_COLOR)
    right_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    preview_title = tk.Label(right_content, text="👁️ Live Preview",
                           font=("Segoe UI", 16, "bold"), bg=BG_COLOR, fg="#333")
    preview_title.pack(pady=(0, 15))
    
    preview_card = tk.Frame(right_content, bg=CARD_COLOR)
    preview_card.pack(fill=tk.BOTH, expand=True)
    
    preview_frame = tk.Frame(preview_card, bg="#f5f5f5", relief="flat")
    preview_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    preview_frame.pack_propagate(False)
    
    # Initialize
    reset_defaults()
    
    root.mainloop()

# Backward compatibility
def create_sheet_gui():
    """Alias for backward compatibility"""
    create_integrated_gui()

def create_sheet(num_questions=40):
    """Original function for backward compatibility"""
    try:
        from core.sheet_maker import AnswerSheetDesigner
        
        try:
            num_questions = int(num_questions)
            if num_questions <= 0:
                print("[ERROR] Number must be positive. Using 40 questions.")
                num_questions = 40
        except (ValueError, TypeError):
            print("[ERROR] Invalid number. Using 40 questions.")
            num_questions = 40
        
        output_dir = "blank_sheets"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"answer_sheet_{num_questions}_questions.pdf")
        
        print(f"\nCreating {num_questions}-question answer sheet...")
        
        designer = AnswerSheetDesigner()
        designer.set_config(include_student_id=True)
        designer.create_answer_sheet(
            total_questions=num_questions,
            output_path=output_path,
            format='pdf',
            use_preset=True
        )
        
        print(f"\n[SUCCESS] Blank sheet created: {output_path}")
        return output_path
        
    except ImportError as e:
        print(f"[ERROR] Failed to import sheet_maker: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create blank sheet: {e}")
        return None

if __name__ == "__main__":
    create_integrated_gui()