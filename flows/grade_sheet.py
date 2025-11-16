import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, StringVar, IntVar, BooleanVar, NORMAL, DISABLED
from PIL import Image, ImageTk, ImageDraw
import json
import tempfile
import cv2
import numpy as np

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def to_relative_path(absolute_path):
    """Convert absolute path to relative path from project root"""
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        return absolute_path

def grade_sheet_gui(template_json=None, key_json=None):
    """Main GUI for grading answer sheets"""
    
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
    temp_overlay_files = []  # Track temporary files for cleanup
    
    # Main container
    main_container = tk.Frame(root, bg=BG_COLOR)
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Create paned window (left: controls/results, right: image)
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
    
    ttk.Button(template_frame, text="📁", command=load_template, width=3).pack(side=tk.LEFT)
    
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
    
    ttk.Button(key_frame, text="📁", command=load_key, width=3).pack(side=tk.LEFT)
    
    # Mode selection card
    mode_card = tk.Frame(left_content, bg=CARD_COLOR)
    mode_card.pack(fill=tk.X, pady=(0, 15))
    
    mode_inner = tk.Frame(mode_card, bg=CARD_COLOR)
    mode_inner.pack(fill=tk.BOTH, padx=20, pady=15)
    
    tk.Label(mode_inner, text="📝 Grading Mode",
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
    
    # Navigation for batch mode (initially hidden)
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
            
            # Get extraction result and answer key for comparison
            extraction = grade_data.get('extraction_result', {})
            answers_data = extraction.get('answers', {})
            
            # Load answer key
            with open(current_key, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
            correct_answers = key_data.get('answer_key', {})
            
            # Get grade results to know which are correct/wrong
            grade_results = grade_data.get('grade_results', {})
            details = grade_results.get('details', [])
            
            print(f"[DEBUG] Details type: {type(details)}")
            print(f"[DEBUG] Details content: {details}")
            
            # Create lookup for correct/wrong by question number
            correctness_map = {}
            if isinstance(details, list):
                for i, detail in enumerate(details):
                    print(f"[DEBUG] Detail {i}: type={type(detail)}, value={detail}")
                    if isinstance(detail, dict):
                        q_num = str(detail.get('question_number'))
                        # Check both 'is_correct' and 'status' fields
                        is_correct = detail.get('is_correct', False)
                        if not is_correct and 'status' in detail:
                            is_correct = detail.get('status') == 'correct'
                        correctness_map[q_num] = is_correct
                        print(f"[DEBUG]   -> Q{q_num} is_correct={is_correct}")
                    elif isinstance(detail, (int, str)):
                        # Handle case where details is just a list of question numbers
                        q_num = str(detail)
                        correctness_map[q_num] = False  # Assume wrong if in details list
                        print(f"[DEBUG]   -> Q{q_num} assumed wrong (int/str in list)")
            elif isinstance(details, dict):
                # Handle case where details is a dict with question numbers as keys
                for q_num, detail_info in details.items():
                    print(f"[DEBUG] Detail for Q{q_num}: type={type(detail_info)}, value={detail_info}")
                    if isinstance(detail_info, dict):
                        # Check both 'is_correct' and 'status' fields
                        is_correct = detail_info.get('is_correct', False)
                        if not is_correct and 'status' in detail_info:
                            is_correct = detail_info.get('status') == 'correct'
                        correctness_map[str(q_num)] = is_correct
                        print(f"[DEBUG]   -> is_correct={is_correct}")
                    else:
                        correctness_map[str(q_num)] = bool(detail_info)
                        print(f"[DEBUG]   -> bool value={bool(detail_info)}")
            
            print(f"[DEBUG] Final correctness map: {correctness_map}")
            print(f"[DEBUG] Grade results keys: {grade_results.keys()}")
            
            # Load template to get bubble positions and scale factors
            from core.extraction import BubbleTemplate
            template = BubbleTemplate(current_template)
            
            # Calculate scale factors
            template_width = template.template_width
            template_height = template.template_height
            scale_x = width / template_width
            scale_y = height / template_height
            scale_avg = (scale_x + scale_y) / 2
            
            print(f"[DEBUG] Image size: {width}x{height}, Template size: {template_width}x{template_height}")
            print(f"[DEBUG] Scale factors: {scale_x:.3f}, {scale_y:.3f}")
            
            # Draw answer bubbles
            for question in template.questions:
                q_num = str(question.question_number)
                is_correct = correctness_map.get(q_num, False)
                
                # Get student's selected answers for this question
                q_data = answers_data.get(q_num, {})
                selected = q_data.get('selected_answers', [])
                
                print(f"[DEBUG] Q{q_num}: selected={selected}, correct={is_correct}")
                
                # Draw circles for each bubble that was filled
                for bubble in question.bubbles:
                    # Check if this specific bubble was filled
                    if bubble.label in selected:
                        # This bubble was filled - color based on question correctness
                        color = (0, 255, 0) if is_correct else (255, 0, 0)  # Green if correct, Red if wrong
                        
                        x = int(bubble.x * scale_x)
                        y = int(bubble.y * scale_y)
                        radius = int(bubble.radius * scale_avg)
                        
                        cv2.circle(img_rgb, (x, y), radius, color, 3)
            
            print(f"[DEBUG] Drew question overlays for {len(template.questions)} questions")
            
            # Draw student ID bubbles (purple)
            student_id_data = extraction.get('student_id', {})
            if student_id_data and isinstance(student_id_data, dict):
                digit_details = student_id_data.get('digit_details', [])
                
                if template.id_template:
                    # Get selected digits
                    selected_positions = {d['position']: d['digit'] for d in digit_details if d.get('digit') is not None}
                    
                    # Draw all ID bubbles (purple for selected)
                    for column in template.id_template['digit_columns']:
                        pos = column['digit_position']
                        selected_digit = selected_positions.get(pos)
                        
                        for bubble in column['bubbles']:
                            x = int(bubble['x'] * scale_x)
                            y = int(bubble['y'] * scale_y)
                            radius = int(bubble['radius'] * scale_avg)
                            digit = bubble['digit']
                            
                            if digit == selected_digit:
                                # Selected digit - purple/magenta
                                cv2.circle(img_rgb, (x, y), radius, (255, 0, 255), 3)
                    
                    print(f"[DEBUG] Drew ID overlays for {len(selected_positions)} digits")
            
            # Convert to PIL Image
            pil_img = Image.fromarray(img_rgb)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            pil_img.save(temp_file.name)
            temp_file.close()
            temp_overlay_files.append(temp_file.name)
            
            print(f"[DEBUG] Saved overlay to: {temp_file.name}")
            
            # Display in canvas
            display_image_on_canvas(temp_file.name)
            
        except Exception as e:
            print(f"[ERROR] Error creating overlay: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to original image
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
            
            # Get canvas size
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
        # Select image
        image_path = filedialog.askopenfilename(
            title="Select Filled Answer Sheet",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")],
            initialdir=PROJECT_ROOT
        )
        
        if not image_path:
            return
        
        try:
            from core.extraction import BubbleTemplate, AnswerSheetExtractor, save_extraction_to_json
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
            
            # Debug: Print grade results structure
            print(f"[DEBUG] Grade results type: {type(grade_results)}")
            print(f"[DEBUG] Grade results: {grade_results}")
            
            # Handle case where grade_answers returns non-dict
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
            
            # Display results
            results_text.config(state=tk.NORMAL)
            results_text.delete("1.0", tk.END)
            
            results_text.insert(tk.END, "═" * 50 + "\n", "header")
            results_text.insert(tk.END, "GRADING RESULTS\n", "header")
            results_text.insert(tk.END, "═" * 50 + "\n\n", "header")
            
            results_text.insert(tk.END, f"Student ID: ", "label")
            results_text.insert(tk.END, f"{student_id}\n\n", "value")
            
            # Handle different grade result formats safely
            try:
                # Try direct access first
                total_q = grade_results.get('total_questions', 0)
                correct = grade_results.get('correct', 0)
                wrong = grade_results.get('wrong', 0)
                blank = grade_results.get('blank', 0)
                percentage = grade_results.get('percentage', 0.0)
                
                # If using summary structure
                if 'summary' in grade_results and isinstance(grade_results.get('summary'), dict):
                    summary = grade_results['summary']
                    total_q = summary.get('total_questions', total_q)
                    correct = summary.get('correct', correct)
                    wrong = summary.get('wrong', wrong)
                    blank = summary.get('blank', blank)
                    percentage = summary.get('percentage', percentage)
                
                # Fallback calculations if values are missing
                if total_q == 0:
                    total_q = correct + wrong + blank
                if percentage == 0.0 and total_q > 0:
                    percentage = (correct / total_q) * 100
                
            except Exception as e:
                print(f"[ERROR] Failed to extract grade data: {e}")
                messagebox.showerror("Error", f"Failed to parse grading results: {e}")
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
            if isinstance(details, (list, dict)):
                # Extract wrong questions based on details structure
                wrong_questions = []
                
                if isinstance(details, list):
                    for detail in details:
                        if isinstance(detail, dict):
                            # Check both 'is_correct' and 'status'
                            is_correct = detail.get('is_correct', True)
                            if not is_correct and 'status' in detail:
                                is_correct = detail.get('status') == 'correct'
                            
                            if not is_correct:
                                wrong_questions.append(detail)
                
                elif isinstance(details, dict):
                    for q_num, detail_info in details.items():
                        if isinstance(detail_info, dict):
                            # Check both 'is_correct' and 'status'
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
                        
                        # Handle different field names
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
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Grading failed:\n{str(e)}")
    
    def grade_batch_sheets():
        """Grade batch of answer sheets"""
        nonlocal batch_results, current_batch_index
        
        # Select folder
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
            results_text.insert("1.0", f"Processing {len(image_files)} sheets...\n")
            results_text.config(state=tk.DISABLED)
            root.update_idletasks()
            
            # Process each sheet
            template = BubbleTemplate(current_template)
            extractor = AnswerSheetExtractor(template)
            answer_key_data = load_answer_key(current_key)
            
            batch_results = []
            
            for img_path in image_files:
                try:
                    result = extractor.extract_complete(img_path, threshold_percent=threshold_var.get(), debug=False)
                    
                    if result:
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
                        
                        batch_results.append({
                            'image_path': img_path,
                            'student_id': student_id,
                            'extraction_result': result,
                            'grade_results': grade_results
                        })
                except Exception as e:
                    print(f"Error processing {img_path}: {e}")
            
            if batch_results:
                current_batch_index = 0
                display_batch_result(0)
                
                # Show navigation
                nav_frame.pack(pady=(10, 0))
                
                messagebox.showinfo("Success", f"Batch grading complete!\n{len(batch_results)} sheets graded.")
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
        
        results_text.insert(tk.END, "═" * 50 + "\n", "header")
        results_text.insert(tk.END, f"SHEET {index + 1}/{len(batch_results)}\n", "header")
        results_text.insert(tk.END, "═" * 50 + "\n\n", "header")
        
        results_text.insert(tk.END, f"Student ID: ", "label")
        results_text.insert(tk.END, f"{student_id}\n\n", "value")
        
        # Handle different grade result formats safely
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
        if isinstance(details, (list, dict)):
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