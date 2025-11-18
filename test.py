import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, StringVar, IntVar, BooleanVar, NORMAL, DISABLED
from PIL import Image, ImageTk, ImageDraw
import json
import tempfile
import cv2
import numpy as np
import datetime

# Fix project root path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"[DEBUG] Project root: {PROJECT_ROOT}")

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

def to_relative_path(absolute_path):
    """Convert absolute path to relative path from project root"""
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        return absolute_path

def grade_sheet_gui(template_json=None, key_json=None):
    """Main GUI for grading answer sheets with database integration"""
    
    # Initialize database
    db = None
    try:
        from core.database import GradingDatabase
        db = GradingDatabase()
        print("[DB] Database initialized successfully")
    except Exception as e:
        print(f"[DB] Warning: Could not initialize database: {e}")
    
    # Main window
    root = tk.Tk()
    root.title("Grade Answer Sheets")
    root.geometry("1400x850")
    root.resizable(True, True)
    
    # Configure modern style
    style = ttk.Style()
    style.theme_use('clam')
    
    BG_COLOR = "#f5f5f5"
    CARD_COLOR = "#ffffff"
    ACCENT_COLOR = "#0078d4"
    
    style.configure("TFrame", background=BG_COLOR)
    style.configure("TLabel", background=BG_COLOR, font=("Segoe UI", 10))
    style.configure("Title.TLabel", background=BG_COLOR, font=("Segoe UI", 16, "bold"))
    style.configure("Card.TFrame", background=CARD_COLOR, relief="flat")
    style.configure("TButton", font=("Segoe UI", 10), padding=8)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
    
    # Global state
    current_template = template_json
    current_key = key_json
    grading_mode = StringVar(value="single")
    threshold_var = IntVar(value=50)
    
    # Batch grading state
    batch_results = []
    current_batch_index = 0
    temp_overlay_files = []
    
    # Main container
    main_container = tk.Frame(root, bg=BG_COLOR)
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Create paned window
    paned = tk.PanedWindow(main_container, orient=tk.HORIZONTAL, bg=BG_COLOR, 
                           sashwidth=5, sashrelief=tk.RAISED)
    paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # LEFT PANEL
    left_panel = tk.Frame(paned, bg=BG_COLOR, width=500)
    paned.add(left_panel, minsize=400)
    
    # RIGHT PANEL
    right_panel = tk.Frame(paned, bg=BG_COLOR)
    paned.add(right_panel, minsize=600)
    
    # === LEFT PANEL CONTENT ===
    left_content = tk.Frame(left_panel, bg=BG_COLOR)
    left_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Title
    tk.Label(left_content, text="📊 Grade Answer Sheets",
            font=("Segoe UI", 16, "bold"), bg=BG_COLOR, fg="#333").pack(pady=(0, 20))
    
    # Configuration card
    config_card = tk.Frame(left_content, bg=CARD_COLOR)
    config_card.pack(fill=tk.X, pady=(0, 15))
    
    config_inner = tk.Frame(config_card, bg=CARD_COLOR)
    config_inner.pack(fill=tk.BOTH, padx=20, pady=15)
    
    tk.Label(config_inner, text="⚙️ Configuration",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR).pack(anchor="w", pady=(0, 10))
    
    # Template
    template_frame = tk.Frame(config_inner, bg=CARD_COLOR)
    template_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(template_frame, text="Template:", font=("Segoe UI", 9, "bold"),
            bg=CARD_COLOR).pack(side=tk.LEFT)
    
    template_label = tk.Label(template_frame, 
                             text=os.path.basename(current_template) if current_template else "Not loaded",
                             font=("Segoe UI", 9), bg=CARD_COLOR, fg="#666")
    template_label.pack(side=tk.LEFT, padx=(5, 5))
    
    def load_template():
        nonlocal current_template
        template_dir = os.path.join(PROJECT_ROOT, 'template')
        if not os.path.exists(template_dir):
            template_dir = PROJECT_ROOT
        
        path = filedialog.askopenfilename(
            title="Select Template JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=template_dir
        )
        if path:
            current_template = path
            template_label.config(text=os.path.basename(path))
    
    ttk.Button(template_frame, text="📂", command=load_template, width=3).pack(side=tk.LEFT)
    
    # Answer Key
    key_frame = tk.Frame(config_inner, bg=CARD_COLOR)
    key_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(key_frame, text="Answer Key:", font=("Segoe UI", 9, "bold"),
            bg=CARD_COLOR).pack(side=tk.LEFT)
    
    key_label = tk.Label(key_frame,
                        text=os.path.basename(current_key) if current_key else "Not loaded",
                        font=("Segoe UI", 9), bg=CARD_COLOR, fg="#666")
    key_label.pack(side=tk.LEFT, padx=(5, 5))
    
    def load_key():
        nonlocal current_key
        key_dir = os.path.join(PROJECT_ROOT, 'answer_keys')
        if not os.path.exists(key_dir):
            key_dir = PROJECT_ROOT
        
        path = filedialog.askopenfilename(
            title="Select Answer Key JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=key_dir
        )
        if path:
            current_key = path
            key_label.config(text=os.path.basename(path))
    
    ttk.Button(key_frame, text="📂", command=load_key, width=3).pack(side=tk.LEFT)
    
    # Mode selection card
    mode_card = tk.Frame(left_content, bg=CARD_COLOR)
    mode_card.pack(fill=tk.X, pady=(0, 15))
    
    mode_inner = tk.Frame(mode_card, bg=CARD_COLOR)
    mode_inner.pack(fill=tk.BOTH, padx=20, pady=15)
    
    tk.Label(mode_inner, text="📋 Grading Mode",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR).pack(anchor="w", pady=(0, 10))
    
    ttk.Radiobutton(mode_inner, text="Single sheet", variable=grading_mode,
                   value="single").pack(anchor="w", pady=3)
    ttk.Radiobutton(mode_inner, text="Batch (folder)", variable=grading_mode,
                   value="batch").pack(anchor="w", pady=3)
    
    # Threshold
    tk.Label(mode_inner, text="Detection Threshold:",
            font=("Segoe UI", 9, "bold"), bg=CARD_COLOR).pack(anchor="w", pady=(10, 5))
    
    threshold_frame = tk.Frame(mode_inner, bg=CARD_COLOR)
    threshold_frame.pack(fill=tk.X)
    
    ttk.Scale(threshold_frame, from_=20, to=90, variable=threshold_var,
             orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    threshold_label = tk.Label(threshold_frame, text=f"{threshold_var.get()}%",
                              bg=CARD_COLOR, width=5)
    threshold_label.pack(side=tk.RIGHT, padx=(5, 0))
    
    def update_threshold(*args):
        threshold_label.config(text=f"{threshold_var.get()}%")
    
    threshold_var.trace("w", update_threshold)
    
    # Grade button
    def start_grading():
        if not current_template or not current_key:
            messagebox.showerror("Error", "Please load template and answer key first")
            return
        
        if grading_mode.get() == "single":
            grade_single_sheet()
        else:
            grade_batch_sheets()
    
    ttk.Button(mode_inner, text="🚀 Start Grading", command=start_grading,
              style="Accent.TButton").pack(pady=(15, 0))
    
    # Results card
    results_card = tk.Frame(left_content, bg=CARD_COLOR)
    results_card.pack(fill=tk.BOTH, expand=True)
    
    results_inner = tk.Frame(results_card, bg=CARD_COLOR)
    results_inner.pack(fill=tk.BOTH, padx=20, pady=15)
    
    tk.Label(results_inner, text="📈 Results",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR).pack(anchor="w", pady=(0, 10))
    
    # Results text area
    results_text = tk.Text(results_inner, height=20, wrap=tk.WORD,
                          font=("Courier New", 9), bg="#fafafa", relief=tk.FLAT)
    results_text.pack(fill=tk.BOTH, expand=True)
    results_text.insert("1.0", "Results will appear here after grading...")
    results_text.config(state=tk.DISABLED)
    
    # Navigation for batch mode
    nav_frame = tk.Frame(results_inner, bg=CARD_COLOR)
    
    nav_label = tk.Label(nav_frame, text="Sheet 1 of 1", bg=CARD_COLOR,
                        font=("Segoe UI", 9, "bold"))
    nav_label.pack(side=tk.LEFT, padx=(0, 10))
    
    def prev_sheet():
        nonlocal current_batch_index
        if current_batch_index > 0:
            current_batch_index -= 1
            display_batch_result(current_batch_index)
    
    def next_sheet():
        nonlocal current_batch_index
        if current_batch_index < len(batch_results) - 1:
            current_batch_index += 1
            display_batch_result(current_batch_index)
    
    prev_btn = ttk.Button(nav_frame, text="← Prev", command=prev_sheet, width=8)
    prev_btn.pack(side=tk.LEFT, padx=2)
    
    next_btn = ttk.Button(nav_frame, text="Next →", command=next_sheet, width=8)
    next_btn.pack(side=tk.LEFT, padx=2)
    
    # Footer with back button
    footer_frame = tk.Frame(left_content, bg=BG_COLOR)
    footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
    
    # Back to main menu button
    def back_to_menu():
        parent = get_parent_window()
        cleanup_temp_files()  # Clean up temp overlay files
        if parent:
            root.destroy()
            parent.deiconify()
        else:
            if messagebox.askyesno("Exit", "Close Grading System?"):
                root.destroy()
    
    ttk.Button(footer_frame, text="⬅ Main Menu", 
              command=back_to_menu).pack(side=tk.LEFT)
    
    # === RIGHT PANEL CONTENT ===
    right_content = tk.Frame(right_panel, bg=BG_COLOR)
    right_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    tk.Label(right_content, text="👁️ Answer Sheet Preview",
            font=("Segoe UI", 16, "bold"), bg=BG_COLOR, fg="#333").pack(pady=(0, 15))
    
    # Image canvas
    image_card = tk.Frame(right_content, bg=CARD_COLOR)
    image_card.pack(fill=tk.BOTH, expand=True)
    
    canvas = tk.Canvas(image_card, bg="#f0f0f0", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    
    canvas_image = {"img": None}

    def display_image_with_overlay(image_path, grade_data):
        """Create and display overlay image with colored bubbles"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise Exception("Failed to load image")
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width = img_rgb.shape[:2]
            
            # Get extraction result
            extraction = grade_data.get('extraction_result', {})
            answers_data = extraction.get('answers', {})
            
            # Load answer key
            with open(current_key, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
            correct_answers = key_data.get('answer_key', {})
            
            # Get grade results
            grade_results = grade_data.get('grade_results', {})
            details = grade_results.get('details', [])
            
            # Create correctness map
            correctness_map = {}
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict):
                        q_num = str(detail.get('question_number'))
                        is_correct = detail.get('is_correct', False)
                        if not is_correct and 'status' in detail:
                            is_correct = detail.get('status') == 'correct'
                        correctness_map[q_num] = is_correct
            elif isinstance(details, dict):
                for q_num, detail_info in details.items():
                    if isinstance(detail_info, dict):
                        is_correct = detail_info.get('is_correct', False)
                        if not is_correct and 'status' in detail_info:
                            is_correct = detail_info.get('status') == 'correct'
                        correctness_map[str(q_num)] = is_correct
            
            # Load template
            from core.extraction import BubbleTemplate
            template = BubbleTemplate(current_template)
            
            # Calculate scale factors
            template_width = template.template_width
            template_height = template.template_height
            scale_x = width / template_width
            scale_y = height / template_height
            scale_avg = (scale_x + scale_y) / 2
            
            # Draw answer bubbles
            for question in template.questions:
                q_num = str(question.question_number)
                is_correct = correctness_map.get(q_num, False)
                q_data = answers_data.get(q_num, {})
                selected = q_data.get('selected_answers', [])
                
                for bubble in question.bubbles:
                    if bubble.label in selected:
                        color = (0, 255, 0) if is_correct else (255, 0, 0)
                        x = int(bubble.x * scale_x)
                        y = int(bubble.y * scale_y)
                        radius = int(bubble.radius * scale_avg)
                        cv2.circle(img_rgb, (x, y), radius, color, 3)
            
            # Draw student ID bubbles
            student_id_data = extraction.get('student_id', {})
            if student_id_data and isinstance(student_id_data, dict):
                digit_details = student_id_data.get('digit_details', [])
                
                if template.id_template:
                    selected_positions = {d['position']: d['digit'] for d in digit_details if d.get('digit') is not None}
                    
                    for column in template.id_template['digit_columns']:
                        pos = column['digit_position']
                        selected_digit = selected_positions.get(pos)
                        
                        for bubble in column['bubbles']:
                            x = int(bubble['x'] * scale_x)
                            y = int(bubble['y'] * scale_y)
                            radius = int(bubble['radius'] * scale_avg)
                            digit = bubble['digit']
                            
                            if digit == selected_digit:
                                cv2.circle(img_rgb, (x, y), radius, (255, 0, 255), 3)
            
            # Convert to PIL Image
            pil_img = Image.fromarray(img_rgb)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            pil_img.save(temp_file.name)
            temp_file.close()
            temp_overlay_files.append(temp_file.name)
            
            # Display in canvas
            display_image_on_canvas(temp_file.name)
            
        except Exception as e:
            print(f"[ERROR] Error creating overlay: {e}")
            import traceback
            traceback.print_exc()
            try:
                display_image_on_canvas(image_path)
            except Exception as e2:
                print(f"[ERROR] Fallback also failed: {e2}")
                canvas.delete("all")
                canvas.create_text(400, 300, 
                                 text=f"Error displaying image:\n{str(e)[:50]}",
                                 font=("Segoe UI", 10), fill="red", justify=tk.CENTER)
    
    def display_image_on_canvas(image_path):
        """Display image on canvas"""
        try:
            img = Image.open(image_path)
            
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            if canvas_width < 10:
                canvas_width = 600
                canvas_height = 800
            
            # Scale image
            img_width, img_height = img.size
            scale_x = (canvas_width - 40) / img_width
            scale_y = (canvas_height - 40) / img_height
            scale = min(scale_x, scale_y, 1.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            canvas_image["img"] = ImageTk.PhotoImage(img_resized)
            
            # Display
            canvas.delete("all")
            x = canvas_width // 2
            y = canvas_height // 2
            canvas.create_image(x, y, image=canvas_image["img"])
            
        except Exception as e:
            print(f"Error displaying image: {e}")
            canvas.delete("all")
            canvas.create_text(300, 400, text="Error loading image",
                             font=("Segoe UI", 12), fill="red")
    
    def grade_single_sheet():
        """Grade a single answer sheet"""
        image_path = filedialog.askopenfilename(
            title="Select Filled Answer Sheet",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")],
            initialdir=PROJECT_ROOT
        )
        
        if not image_path:
            return
        
        try:
            from core.extraction import BubbleTemplate, AnswerSheetExtractor
            from core.grading import load_answer_key, grade_answers
            
            # Update results
            results_text.config(state=tk.NORMAL)
            results_text.delete("1.0", tk.END)
            results_text.insert("1.0", "Processing answer sheet...\n")
            results_text.config(state=tk.DISABLED)
            root.update_idletasks()
            
            # Extract
            template = BubbleTemplate(current_template)
            extractor = AnswerSheetExtractor(template)
            
            result = extractor.extract_complete(
                image_path,
                threshold_percent=threshold_var.get(),
                debug=False
            )
            
            if not result:
                messagebox.showerror("Error", "Failed to extract answers")
                return
            
            # Grade
            answer_key_data = load_answer_key(current_key)
            scanned_answers_data = {
                'metadata': result.get('metadata', {}),
                'answers': result.get('answers', {})
            }
            
            grade_results = grade_answers(answer_key_data, scanned_answers_data)
            
            if not isinstance(grade_results, dict):
                messagebox.showerror("Error", f"Unexpected grading result format: {type(grade_results)}")
                return
            
            # Extract student ID
            student_id = "N/A"
            sid = result.get('student_id')
            if isinstance(sid, dict):
                student_id = sid.get('student_id', 'N/A')
            elif isinstance(sid, str):
                student_id = sid
            
            # Extract grade data
            try:
                total_q = grade_results.get('total_questions', 0)
                correct = grade_results.get('correct', 0)
                wrong = grade_results.get('wrong', 0)
                blank = grade_results.get('blank', 0)
                percentage = grade_results.get('percentage', 0.0)
                
                if 'summary' in grade_results and isinstance(grade_results.get('summary'), dict):
                    summary = grade_results['summary']
                    total_q = summary.get('total_questions', total_q)
                    correct = summary.get('correct', correct)
                    wrong = summary.get('wrong', wrong)
                    blank = summary.get('blank', blank)
                    percentage = summary.get('percentage', percentage)
                
                if total_q == 0:
                    total_q = correct + wrong + blank
                if percentage == 0.0 and total_q > 0:
                    percentage = (correct / total_q) * 100
                    
            except Exception as e:
                print(f"[ERROR] Failed to extract grade data: {e}")
                messagebox.showerror("Error", f"Failed to parse grading results: {e}")
                return
            
            # Display results
            results_text.config(state=tk.NORMAL)
            results_text.delete("1.0", tk.END)
            
            results_text.insert(tk.END, "╔" + "═" * 48 + "╗\n", "header")
            results_text.insert(tk.END, "GRADING RESULTS\n", "header")
            results_text.insert(tk.END, "╚" + "═" * 48 + "╝\n\n", "header")
            
            results_text.insert(tk.END, f"Student ID: ", "label")
            results_text.insert(tk.END, f"{student_id}\n\n", "value")
            
            results_text.insert(tk.END, f"Score: ", "label")
            score_text = f"{correct}/{total_q}"
            results_text.insert(tk.END, f"{score_text}\n", "score")
            
            results_text.insert(tk.END, f"Percentage: ", "label")
            results_text.insert(tk.END, f"{percentage:.1f}%\n\n", "score")
            
            results_text.insert(tk.END, f"✓ Correct: ", "label")
            results_text.insert(tk.END, f"{correct}\n", "correct")
            
            results_text.insert(tk.END, f"✗ Wrong: ", "label")
            results_text.insert(tk.END, f"{wrong}\n", "wrong")
            
            results_text.insert(tk.END, f"○ Blank: ", "label")
            results_text.insert(tk.END, f"{blank}\n\n", "blank")
            
            # Show wrong answers
            details = grade_results.get('details', [])
            wrong_questions = []
            
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict):
                        is_correct = detail.get('is_correct', True)
                        if not is_correct and 'status' in detail:
                            is_correct = detail.get('status') == 'correct'
                        if not is_correct:
                            wrong_questions.append(detail)
            elif isinstance(details, dict):
                for q_num, detail_info in details.items():
                    if isinstance(detail_info, dict):
                        is_correct = detail_info.get('is_correct', True)
                        if not is_correct and 'status' in detail_info:
                            is_correct = detail_info.get('status') == 'correct'
                        if not is_correct:
                            detail_copy = detail_info.copy()
                            detail_copy['question_number'] = q_num
                            wrong_questions.append(detail_copy)
            
            if wrong_questions:
                results_text.insert(tk.END, "Wrong Answers:\n", "label")
                for detail in wrong_questions[:10]:
                    q_num = detail.get('question_number', '?')
                    student_ans = detail.get('student_answer') or detail.get('student_answers', [])
                    correct_ans = detail.get('correct_answer') or detail.get('correct_answers', [])
                    
                    if isinstance(student_ans, list):
                        student_ans_str = ', '.join(str(a) for a in student_ans) if student_ans else 'Blank'
                    else:
                        student_ans_str = str(student_ans) if student_ans else 'Blank'
                    
                    if isinstance(correct_ans, list):
                        correct_ans_str = ', '.join(str(a) for a in correct_ans) if correct_ans else '?'
                    else:
                        correct_ans_str = str(correct_ans) if correct_ans else '?'
                    
                    results_text.insert(tk.END, f"  Q{q_num}: {student_ans_str} → {correct_ans_str}\n", "wrong")
                
                if len(wrong_questions) > 10:
                    results_text.insert(tk.END, f"  ... and {len(wrong_questions) - 10} more\n", "wrong")
            
            # Configure tags
            results_text.tag_config("header", font=("Courier New", 9, "bold"))
            results_text.tag_config("label", font=("Courier New", 9, "bold"))
            results_text.tag_config("value", font=("Courier New", 9))
            results_text.tag_config("score", font=("Courier New", 10, "bold"), foreground="blue")
            results_text.tag_config("correct", foreground="green")
            results_text.tag_config("wrong", foreground="red")
            results_text.tag_config("blank", foreground="orange")
            
            results_text.config(state=tk.DISABLED)
            
            # Hide navigation
            nav_frame.pack_forget()
            
            # Display overlay image
            grade_data = {
                'extraction_result': result,
                'grade_results': grade_results
            }
            display_image_with_overlay(image_path, grade_data)
            
            # Log to database
            if db:
                try:
                    template_info = db.get_template_by_json_path(current_template)
                    answer_key_info = db.get_answer_key_by_file_path(current_key)
                    
                    if template_info and answer_key_info:
                        template_id = template_info['id']
                        answer_key_id = answer_key_info['id']
                        
                        session_id = db.create_grading_session(
                            name=f"Single Grade {datetime.datetime.now().strftime('%H:%M:%S')}",
                            template_id=template_id,
                            answer_key_id=answer_key_id,
                            is_batch=False,
                            total_sheets=1
                        )
                        
                        graded_sheet_id = db.save_graded_sheet(
                            session_id=session_id,
                            sheet_image_path=image_path,
                            student_id=student_id,
                            score=correct,
                            total_questions=total_q,
                            percentage=percentage,
                            correct_count=correct,
                            wrong_count=wrong,
                            blank_count=blank,
                            threshold_used=threshold_var.get(),
                            extraction_json=json.dumps(result)
                        )
                        
                        if graded_sheet_id and details:
                            for detail in details:
                                if isinstance(detail, dict):
                                    q_num = detail.get('question_number')
                                    student_answer = detail.get('student_answer') or detail.get('student_answers', [])
                                    correct_answer = detail.get('correct_answer') or detail.get('correct_answers', [])
                                    is_correct = detail.get('is_correct', False)
                                    
                                    if isinstance(student_answer, list):
                                        student_answer_str = ','.join(str(a) for a in student_answer)
                                    else:
                                        student_answer_str = str(student_answer)
                                    
                                    if isinstance(correct_answer, list):
                                        correct_answer_str = ','.join(str(a) for a in correct_answer)
                                    else:
                                        correct_answer_str = str(correct_answer)
                                    
                                    db.save_question_result(
                                        graded_sheet_id=graded_sheet_id,
                                        question_number=q_num,
                                        student_answer=student_answer_str,
                                        correct_answer=correct_answer_str,
                                        is_correct=is_correct
                                    )
                        
                        print(f"[DB] Grading session saved: session_id={session_id}, graded_sheet_id={graded_sheet_id}")
                    else:
                        print(f"[DB] Could not find template or answer key in database")
                            
                except Exception as e:
                    print(f"[DB] Failed to log grading session: {e}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Grading failed:\n{str(e)}")
        
    def grade_batch_sheets():
        """Grade batch of answer sheets"""
        nonlocal batch_results, current_batch_index
        
        folder_path = filedialog.askdirectory(
            title="Select Folder with Answer Sheets",
            initialdir=PROJECT_ROOT
        )
        
        if not folder_path:
            return
        
        try:
            from core.extraction import BubbleTemplate, AnswerSheetExtractor
            from core.grading import load_answer_key, grade_answers
            import glob
            
            # Get all images
            patterns = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']
            image_files = []
            for pattern in patterns:
                image_files.extend(glob.glob(os.path.join(folder_path, pattern)))
            
            if not image_files:
                messagebox.showerror("Error", "No image files found in folder")
                return
            
            # Update results
            results_text.config(state=tk.NORMAL)
            results_text.delete("1.0", tk.END)
            results_text.insert("1.0", f"Processing {len(image_files)} sheets...\n\n")
            results_text.config(state=tk.DISABLED)
            root.update_idletasks()
            
            # Process each sheet
            batch_results = []
            
            for i, img_path in enumerate(image_files):
                try:
                    # Update progress
                    results_text.config(state=tk.NORMAL)
                    results_text.insert(tk.END, f"Processing {i+1}/{len(image_files)}: {os.path.basename(img_path)}... ")
                    results_text.config(state=tk.DISABLED)
                    root.update_idletasks()
                    
                    # Extract and grade
                    from core.extraction import BubbleTemplate, AnswerSheetExtractor
                    template = BubbleTemplate(current_template)
                    extractor = AnswerSheetExtractor(template)
                    
                    result = extractor.extract_complete(img_path, threshold_percent=threshold_var.get(), debug=False)
                    
                    if result:
                        answer_key_data = load_answer_key(current_key)
                        scanned_answers_data = {
                            'metadata': result.get('metadata', {}),
                            'answers': result.get('answers', {})
                        }
                        
                        grade_results = grade_answers(answer_key_data, scanned_answers_data)
                        
                        student_id = "N/A"
                        sid = result.get('student_id')
                        if isinstance(sid, dict):
                            student_id = sid.get('student_id', 'N/A')
                        elif isinstance(sid, str):
                            student_id = sid
                        
                        # Extract grade data
                        total_q = grade_results.get('total_questions', 0)
                        correct = grade_results.get('correct', 0)
                        wrong = grade_results.get('wrong', 0)
                        blank = grade_results.get('blank', 0)
                        percentage = grade_results.get('percentage', 0.0)
                        
                        if 'summary' in grade_results and isinstance(grade_results.get('summary'), dict):
                            summary = grade_results['summary']
                            total_q = summary.get('total_questions', total_q)
                            correct = summary.get('correct', correct)
                            wrong = summary.get('wrong', wrong)
                            blank = summary.get('blank', blank)
                            percentage = summary.get('percentage', percentage)
                        
                        if total_q == 0:
                            total_q = correct + wrong + blank
                        if percentage == 0.0 and total_q > 0:
                            percentage = (correct / total_q) * 100
                        
                        batch_results.append({
                            'image_path': img_path,
                            'student_id': student_id,
                            'extraction_result': result,
                            'grade_results': grade_results,
                            'score': correct,
                            'total_questions': total_q,
                            'percentage': percentage,
                            'correct': correct,
                            'wrong': wrong,
                            'blank': blank
                        })
                        
                        # Log to database
                        if db:
                            try:
                                template_info = db.get_template_by_json_path(to_relative_path(current_template))
                                answer_key_info = db.get_answer_key_by_file_path(to_relative_path(current_key))
                                
                                if template_info and answer_key_info:
                                    template_id = template_info['id']
                                    answer_key_id = answer_key_info['id']
                                    
                                    session_id = db.create_grading_session(
                                        name=f"Batch Sheet {i+1} - {datetime.datetime.now().strftime('%H:%M:%S')}",
                                        template_id=template_id,
                                        answer_key_id=answer_key_id,
                                        is_batch=True,
                                        total_sheets=len(image_files)
                                    )
                                    
                                    if session_id:
                                        graded_sheet_id = db.save_graded_sheet(
                                            session_id=session_id,
                                            sheet_image_path=img_path,
                                            student_id=student_id,
                                            score=correct,
                                            total_questions=total_q,
                                            percentage=percentage,
                                            correct_count=correct,
                                            wrong_count=wrong,
                                            blank_count=blank,
                                            threshold_used=threshold_var.get(),
                                            extraction_json=json.dumps(result)
                                        )
                                        
                                        print(f"[DB] Batch sheet {i+1} saved: session_id={session_id}, graded_sheet_id={graded_sheet_id}")
                                    else:
                                        print(f"[DB] Failed to create session for batch sheet {i+1}")
                                else:
                                    print(f"[DB] Could not find template or answer key for batch sheet {i+1}")
                                    
                            except Exception as e:
                                print(f"[DB] Failed to log batch sheet {i+1}: {e}")
                        
                        # Update progress
                        results_text.config(state=tk.NORMAL)
                        results_text.insert(tk.END, f"✓ {correct}/{total_q} ({percentage:.1f}%)\n")
                        results_text.config(state=tk.DISABLED)
                        root.update_idletasks()
                        
                    else:
                        results_text.config(state=tk.NORMAL)
                        results_text.insert(tk.END, "✗ Failed\n")
                        results_text.config(state=tk.DISABLED)
                        root.update_idletasks()
                
                except Exception as e:
                    print(f"Error processing {img_path}: {e}")
                    results_text.config(state=tk.NORMAL)
                    results_text.insert(tk.END, f"✗ Error: {str(e)[:50]}...\n")
                    results_text.config(state=tk.DISABLED)
                    root.update_idletasks()
            
            # Show results
            if batch_results:
                current_batch_index = 0
                display_batch_result(0)
                
                # Show navigation
                nav_frame.pack(pady=(10, 0))
                
                # Show summary
                total_sheets = len(batch_results)
                avg_score = sum(item['percentage'] for item in batch_results) / total_sheets
                messagebox.showinfo("Batch Complete", 
                                f"Batch grading complete!\n\n"
                                f"• {total_sheets} sheets graded\n"
                                f"• Average score: {avg_score:.1f}%\n"
                                f"• Use navigation to view individual results")
            else:
                messagebox.showerror("Error", "No sheets were successfully graded")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Batch grading failed:\n{str(e)}")
    
    def display_batch_result(index):
        """Display result for a specific batch item"""
        if not batch_results or index >= len(batch_results):
            return
        
        item = batch_results[index]
        grade_results = item['grade_results']
        student_id = item['student_id']
        
        # Update navigation label
        nav_label.config(text=f"Sheet {index + 1} of {len(batch_results)}")
        
        # Update prev/next buttons
        prev_btn.config(state=NORMAL if index > 0 else DISABLED)
        next_btn.config(state=NORMAL if index < len(batch_results) - 1 else DISABLED)
        
        # Display results
        results_text.config(state=tk.NORMAL)
        results_text.delete("1.0", tk.END)
        
        results_text.insert(tk.END, "╔" + "═" * 48 + "╗\n", "header")
        results_text.insert(tk.END, f"SHEET {index + 1}/{len(batch_results)}\n", "header")
        results_text.insert(tk.END, "╚" + "═" * 48 + "╝\n\n", "header")
        
        results_text.insert(tk.END, f"Student ID: ", "label")
        results_text.insert(tk.END, f"{student_id}\n\n", "value")
        
        # Handle grade results
        try:
            total_q = grade_results.get('total_questions', 0)
            correct = grade_results.get('correct', 0)
            wrong = grade_results.get('wrong', 0)
            blank = grade_results.get('blank', 0)
            percentage = grade_results.get('percentage', 0.0)
            
            if 'summary' in grade_results and isinstance(grade_results.get('summary'), dict):
                summary = grade_results['summary']
                total_q = summary.get('total_questions', total_q)
                correct = summary.get('correct', correct)
                wrong = summary.get('wrong', wrong)
                blank = summary.get('blank', blank)
                percentage = summary.get('percentage', percentage)
            
            if total_q == 0:
                total_q = correct + wrong + blank
            if percentage == 0.0 and total_q > 0:
                percentage = (correct / total_q) * 100
        except Exception as e:
            print(f"[ERROR] Failed to extract grade data for batch item: {e}")
            return
        
        results_text.insert(tk.END, f"Score: ", "label")
        score_text = f"{correct}/{total_q}"
        results_text.insert(tk.END, f"{score_text}\n", "score")
        
        results_text.insert(tk.END, f"Percentage: ", "label")
        results_text.insert(tk.END, f"{percentage:.1f}%\n\n", "score")
        
        results_text.insert(tk.END, f"✓ Correct: ", "label")
        results_text.insert(tk.END, f"{correct}\n", "correct")
        
        results_text.insert(tk.END, f"✗ Wrong: ", "label")
        results_text.insert(tk.END, f"{wrong}\n", "wrong")
        
        results_text.insert(tk.END, f"○ Blank: ", "label")
        results_text.insert(tk.END, f"{blank}\n\n", "blank")
        
        # Show wrong answers
        details = grade_results.get('details', [])
        wrong_questions = []
        
        if isinstance(details, list):
            for detail in details:
                if isinstance(detail, dict):
                    is_correct = detail.get('is_correct', True)
                    if not is_correct and 'status' in detail:
                        is_correct = detail.get('status') == 'correct'
                    if not is_correct:
                        wrong_questions.append(detail)
        elif isinstance(details, dict):
            for q_num, detail_info in details.items():
                if isinstance(detail_info, dict):
                    is_correct = detail_info.get('is_correct', True)
                    if not is_correct and 'status' in detail_info:
                        is_correct = detail_info.get('status') == 'correct'
                    if not is_correct:
                        detail_copy = detail_info.copy()
                        detail_copy['question_number'] = q_num
                        wrong_questions.append(detail_copy)
        
        if wrong_questions:
            results_text.insert(tk.END, "Wrong Answers:\n", "label")
            for detail in wrong_questions[:10]:
                q_num = detail.get('question_number', '?')
                student_ans = detail.get('student_answer') or detail.get('student_answers', [])
                correct_ans = detail.get('correct_answer') or detail.get('correct_answers', [])
                
                if isinstance(student_ans, list):
                    student_ans_str = ', '.join(str(a) for a in student_ans) if student_ans else 'Blank'
                else:
                    student_ans_str = str(student_ans) if student_ans else 'Blank'
                
                if isinstance(correct_ans, list):
                    correct_ans_str = ', '.join(str(a) for a in correct_ans) if correct_ans else '?'
                else:
                    correct_ans_str = str(correct_ans) if correct_ans else '?'
                
                results_text.insert(tk.END, f"  Q{q_num}: {student_ans_str} → {correct_ans_str}\n", "wrong")
            
            if len(wrong_questions) > 10:
                results_text.insert(tk.END, f"  ... and {len(wrong_questions) - 10} more\n", "wrong")
        
        # Configure tags
        results_text.tag_config("header", font=("Courier New", 9, "bold"))
        results_text.tag_config("label", font=("Courier New", 9, "bold"))
        results_text.tag_config("value", font=("Courier New", 9))
        results_text.tag_config("score", font=("Courier New", 10, "bold"), foreground="blue")
        results_text.tag_config("correct", foreground="green")
        results_text.tag_config("wrong", foreground="red")
        results_text.tag_config("blank", foreground="orange")
        
        results_text.config(state=tk.DISABLED)
        
        # Display overlay image
        display_image_with_overlay(item['image_path'], item)
    
    def cleanup_temp_files():
        """Clean up temporary overlay files"""
        for temp_file in temp_overlay_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        temp_overlay_files.clear()
    
    def on_closing():
        """Handle window close event"""
        cleanup_temp_files()
        root.destroy()
    
    # Set close handler
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Show placeholder in canvas
    canvas.create_text(400, 300, 
                      text="Answer sheet preview will\nappear here after grading",
                      font=("Segoe UI", 12), fill="gray", justify=tk.CENTER)
    
    return root

if __name__ == "__main__":
    root = grade_sheet_gui()
    root.mainloop()