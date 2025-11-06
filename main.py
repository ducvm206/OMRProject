"""
ui.py - Graphical User Interface for Answer Sheet Processing System

A simple and intuitive UI for the complete workflow:
1. Create blank templates
2. Extract bubble positions
3. Create answer keys
4. Scan answer sheets
5. Grade answers
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading


class AnswerSheetUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Answer Sheet Processing System")
        self.root.geometry("900x700")
        
        # Variables to store file paths
        self.template_pdf = tk.StringVar()
        self.template_json = tk.StringVar()
        self.answer_key_json = tk.StringVar()
        self.filled_sheet = tk.StringVar()
        self.scanned_answers_json = tk.StringVar()
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        """Create the main UI layout"""
        
        # Title
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text="Answer Sheet Processing System",
            font=("Arial", 18, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Complete workflow from template creation to grading",
            font=("Arial", 10)
        )
        subtitle_label.pack()
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Create Template
        self.tab_create = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_create, text="1. Create Template")
        self.create_template_tab()
        
        # Tab 2: Extract Bubbles
        self.tab_extract = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_extract, text="2. Extract Bubbles")
        self.create_extract_tab()
        
        # Tab 3: Create Answer Key
        self.tab_key = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_key, text="3. Answer Key")
        self.create_key_tab()
        
        # Tab 4: Scan Answer Sheet
        self.tab_scan = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_scan, text="4. Scan Answers")
        self.create_scan_tab()
        
        # Tab 5: Grade
        self.tab_grade = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_grade, text="5. Grade")
        self.create_grade_tab()
        
        # Output console at bottom
        console_frame = ttk.LabelFrame(self.root, text="Output Console", padding="5")
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.console = scrolledtext.ScrolledText(
            console_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", 9)
        )
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Clear console button
        clear_btn = ttk.Button(console_frame, text="Clear Console", command=self.clear_console)
        clear_btn.pack(pady=5)
    
    def create_template_tab(self):
        """Tab 1: Create blank template"""
        frame = ttk.Frame(self.tab_create, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        ttk.Label(
            frame,
            text="Create a blank answer sheet template (PDF)",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            frame,
            text="This will generate a PDF with bubble questions that can be printed and filled.",
            wraplength=600
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Number of questions
        q_frame = ttk.Frame(frame)
        q_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(q_frame, text="Number of questions:", width=20).pack(side=tk.LEFT)
        self.num_questions = ttk.Spinbox(q_frame, from_=1, to=200, width=10)
        self.num_questions.set(40)
        self.num_questions.pack(side=tk.LEFT, padx=5)
        
        # Output path
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="Save as:", width=20).pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=self.template_pdf, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="Browse...", command=self.browse_save_pdf).pack(side=tk.LEFT)
        
        # Create button
        ttk.Button(
            frame,
            text="Create Template PDF",
            command=self.create_template,
            style="Accent.TButton"
        ).pack(pady=20)
        
        # Status
        self.template_status = ttk.Label(frame, text="", foreground="green")
        self.template_status.pack()
    
    def create_extract_tab(self):
        """Tab 2: Extract bubble positions"""
        frame = ttk.Frame(self.tab_extract, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="Extract Bubble Positions from PDF",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            frame,
            text="This will detect all bubbles and save their positions to a JSON template file.",
            wraplength=600
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # PDF input
        pdf_frame = ttk.Frame(frame)
        pdf_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(pdf_frame, text="Template PDF:", width=20).pack(side=tk.LEFT)
        ttk.Entry(pdf_frame, textvariable=self.template_pdf, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(pdf_frame, text="Browse...", command=self.browse_template_pdf).pack(side=tk.LEFT)
        
        # DPI setting
        dpi_frame = ttk.Frame(frame)
        dpi_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dpi_frame, text="DPI (quality):", width=20).pack(side=tk.LEFT)
        self.dpi = ttk.Combobox(dpi_frame, values=[150, 200, 300], width=10)
        self.dpi.set(300)
        self.dpi.pack(side=tk.LEFT, padx=5)
        ttk.Label(dpi_frame, text="(300 = high quality, 150 = faster)").pack(side=tk.LEFT, padx=5)
        
        # Visualization option
        self.show_visualization = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Show visualization (recommended for first time)",
            variable=self.show_visualization
        ).pack(anchor=tk.W, pady=10)
        
        # Extract button
        ttk.Button(
            frame,
            text="Extract Bubble Positions",
            command=self.extract_bubbles,
            style="Accent.TButton"
        ).pack(pady=20)
        
        # Status
        self.extract_status = ttk.Label(frame, text="", foreground="green")
        self.extract_status.pack()
    
    def create_key_tab(self):
        """Tab 3: Create answer key"""
        frame = ttk.Frame(self.tab_key, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="Create Answer Key",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            frame,
            text="Create an answer key by entering answers manually or scanning a master sheet.",
            wraplength=600
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Template JSON input
        json_frame = ttk.Frame(frame)
        json_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(json_frame, text="Template JSON:", width=20).pack(side=tk.LEFT)
        ttk.Entry(json_frame, textvariable=self.template_json, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(json_frame, text="Browse...", command=self.browse_template_json).pack(side=tk.LEFT)
        
        # Method selection
        ttk.Label(frame, text="Creation method:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(20, 5))
        
        self.key_method = tk.StringVar(value="manual")
        
        ttk.Radiobutton(
            frame,
            text="Manual entry (type answers in console)",
            variable=self.key_method,
            value="manual"
        ).pack(anchor=tk.W, padx=20)
        
        ttk.Radiobutton(
            frame,
            text="Scan master answer sheet",
            variable=self.key_method,
            value="scan"
        ).pack(anchor=tk.W, padx=20)
        
        # Master sheet path (for scan method)
        master_frame = ttk.Frame(frame)
        master_frame.pack(fill=tk.X, pady=10, padx=20)
        
        ttk.Label(master_frame, text="Master sheet:", width=15).pack(side=tk.LEFT)
        self.master_sheet = tk.StringVar()
        ttk.Entry(master_frame, textvariable=self.master_sheet, width=35).pack(side=tk.LEFT, padx=5)
        ttk.Button(master_frame, text="Browse...", command=self.browse_master_sheet).pack(side=tk.LEFT)
        
        # Create button
        ttk.Button(
            frame,
            text="Create Answer Key",
            command=self.create_answer_key,
            style="Accent.TButton"
        ).pack(pady=20)
        
        # Status
        self.key_status = ttk.Label(frame, text="", foreground="green")
        self.key_status.pack()
    
    def create_scan_tab(self):
        """Tab 4: Scan answer sheet"""
        frame = ttk.Frame(self.tab_scan, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="Scan Filled Answer Sheet",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            frame,
            text="Scan a student's filled answer sheet and extract their answers.",
            wraplength=600
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Template JSON
        json_frame = ttk.Frame(frame)
        json_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(json_frame, text="Template JSON:", width=20).pack(side=tk.LEFT)
        ttk.Entry(json_frame, textvariable=self.template_json, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(json_frame, text="Browse...", command=self.browse_template_json).pack(side=tk.LEFT)
        
        # Filled sheet
        sheet_frame = ttk.Frame(frame)
        sheet_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sheet_frame, text="Filled answer sheet:", width=20).pack(side=tk.LEFT)
        ttk.Entry(sheet_frame, textvariable=self.filled_sheet, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(sheet_frame, text="Browse...", command=self.browse_filled_sheet).pack(side=tk.LEFT)
        
        # Threshold
        threshold_frame = ttk.Frame(frame)
        threshold_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(threshold_frame, text="Detection threshold:", width=20).pack(side=tk.LEFT)
        self.threshold = ttk.Scale(threshold_frame, from_=20, to=80, orient=tk.HORIZONTAL, length=200)
        self.threshold.set(50)
        self.threshold.pack(side=tk.LEFT, padx=5)
        self.threshold_label = ttk.Label(threshold_frame, text="50%")
        self.threshold_label.pack(side=tk.LEFT, padx=5)
        self.threshold.configure(command=lambda v: self.threshold_label.config(text=f"{int(float(v))}%"))
        
        # Visualization
        self.show_scan_viz = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Show visualization",
            variable=self.show_scan_viz
        ).pack(anchor=tk.W, pady=10)
        
        # Scan button
        ttk.Button(
            frame,
            text="Scan Answer Sheet",
            command=self.scan_answers,
            style="Accent.TButton"
        ).pack(pady=20)
        
        # Status
        self.scan_status = ttk.Label(frame, text="", foreground="green")
        self.scan_status.pack()
    
    def create_grade_tab(self):
        """Tab 5: Grade answers"""
        frame = ttk.Frame(self.tab_grade, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="Grade Answer Sheet",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            frame,
            text="Compare scanned answers with the answer key and generate a grade report.",
            wraplength=600
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Answer key
        key_frame = ttk.Frame(frame)
        key_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(key_frame, text="Answer key JSON:", width=20).pack(side=tk.LEFT)
        ttk.Entry(key_frame, textvariable=self.answer_key_json, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(key_frame, text="Browse...", command=self.browse_answer_key).pack(side=tk.LEFT)
        
        # Scanned answers
        answers_frame = ttk.Frame(frame)
        answers_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(answers_frame, text="Scanned answers:", width=20).pack(side=tk.LEFT)
        ttk.Entry(answers_frame, textvariable=self.scanned_answers_json, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(answers_frame, text="Browse...", command=self.browse_scanned_answers).pack(side=tk.LEFT)
        
        # Max points
        points_frame = ttk.Frame(frame)
        points_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(points_frame, text="Maximum points:", width=20).pack(side=tk.LEFT)
        self.max_points = ttk.Entry(points_frame, width=10)
        self.max_points.insert(0, "100")
        self.max_points.pack(side=tk.LEFT, padx=5)
        ttk.Label(points_frame, text="(leave empty to use 1 point per question)").pack(side=tk.LEFT, padx=5)
        
        # Partial credit
        self.partial_credit = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Enable partial credit for multiple-answer questions",
            variable=self.partial_credit
        ).pack(anchor=tk.W, pady=10)
        
        # Grade button
        ttk.Button(
            frame,
            text="Grade Answer Sheet",
            command=self.grade_answers,
            style="Accent.TButton"
        ).pack(pady=20)
        
        # Status
        self.grade_status = ttk.Label(frame, text="", foreground="green")
        self.grade_status.pack()
    
    # Browse functions
    def browse_save_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            self.template_pdf.set(path)
    
    def browse_template_pdf(self):
        path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            self.template_pdf.set(path)
    
    def browse_template_json(self):
        path = filedialog.askopenfilename(
            initialdir="template",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.template_json.set(path)
    
    def browse_master_sheet(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if path:
            self.master_sheet.set(path)
    
    def browse_filled_sheet(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if path:
            self.filled_sheet.set(path)
    
    def browse_answer_key(self):
        path = filedialog.askopenfilename(
            initialdir="answer_keys",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.answer_key_json.set(path)
    
    def browse_scanned_answers(self):
        path = filedialog.askopenfilename(
            initialdir="scanned_answers",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.scanned_answers_json.set(path)
    
    # Console functions
    def log(self, message):
        """Add message to console"""
        self.console.configure(state=tk.NORMAL)
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.configure(state=tk.DISABLED)
        self.root.update()
    
    def clear_console(self):
        """Clear the console"""
        self.console.configure(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.configure(state=tk.DISABLED)
    
    # Action functions
    def create_template(self):
        """Create blank template PDF"""
        try:
            from core.sheet_maker import AnswerSheetDesigner
            
            num_q = int(self.num_questions.get())
            output = self.template_pdf.get()
            
            if not output:
                messagebox.showerror("Error", "Please specify output path")
                return
            
            self.log(f"Creating template with {num_q} questions...")
            
            designer = AnswerSheetDesigner()
            designer.set_config(include_student_id=False)
            designer.create_answer_sheet(num_q, output, format='pdf')
            
            self.log(f"✓ Template created: {output}")
            self.template_status.config(text=f"✓ Created: {os.path.basename(output)}")
            messagebox.showinfo("Success", f"Template created successfully!\n{output}")
            
        except Exception as e:
            self.log(f"✗ Error: {e}")
            messagebox.showerror("Error", str(e))
    
    def extract_bubbles(self):
        """Extract bubble positions from PDF"""
        try:
            from core.bubble_extraction import process_pdf_answer_sheet
            
            pdf_path = self.template_pdf.get()
            if not pdf_path or not os.path.exists(pdf_path):
                messagebox.showerror("Error", "Please select a valid PDF file")
                return
            
            dpi = int(self.dpi.get())
            show_viz = self.show_visualization.get()
            
            self.log(f"Extracting bubbles from: {pdf_path}")
            self.log(f"DPI: {dpi}, Visualization: {show_viz}")
            
            json_path = process_pdf_answer_sheet(
                pdf_path=pdf_path,
                dpi=dpi,
                keep_png=False,
                show_visualization=show_viz
            )
            
            if json_path:
                self.template_json.set(json_path)
                self.log(f"✓ Template saved: {json_path}")
                self.extract_status.config(text=f"✓ Saved: {os.path.basename(json_path)}")
                messagebox.showinfo("Success", f"Bubbles extracted!\n{json_path}")
            
        except Exception as e:
            self.log(f"✗ Error: {e}")
            messagebox.showerror("Error", str(e))
    
    def create_answer_key(self):
        """Create answer key"""
        try:
            from core.answer_key import load_template_info, create_answer_key_manual, create_answer_key_from_scan
            
            template_path = self.template_json.get()
            if not template_path or not os.path.exists(template_path):
                messagebox.showerror("Error", "Please select a valid template JSON")
                return
            
            self.log("Loading template...")
            template_info = load_template_info(template_path)
            
            method = self.key_method.get()
            
            if method == "manual":
                messagebox.showinfo(
                    "Manual Entry",
                    "Please enter answers in the console window.\n"
                    "The UI may appear frozen - check the console!"
                )
                self.log("\n--- MANUAL ANSWER KEY ENTRY ---")
                answer_key, key_json = create_answer_key_manual(template_info)
                
            else:  # scan
                master = self.master_sheet.get()
                if not master or not os.path.exists(master):
                    messagebox.showerror("Error", "Please select a master answer sheet")
                    return
                
                self.log(f"Scanning master sheet: {master}")
                answer_key, key_json = create_answer_key_from_scan(template_info, master)
            
            if key_json:
                self.answer_key_json.set(key_json)
                self.log(f"✓ Answer key created: {key_json}")
                self.key_status.config(text=f"✓ Created: {os.path.basename(key_json)}")
                messagebox.showinfo("Success", f"Answer key created!\n{key_json}")
            
        except Exception as e:
            self.log(f"✗ Error: {e}")
            messagebox.showerror("Error", str(e))
    
    def scan_answers(self):
        """Scan filled answer sheet"""
        try:
            from core.answer_extraction import BubbleTemplate, AnswerExtractor, save_answers_to_json
            
            template_path = self.template_json.get()
            sheet_path = self.filled_sheet.get()
            
            if not template_path or not os.path.exists(template_path):
                messagebox.showerror("Error", "Please select a valid template JSON")
                return
            
            if not sheet_path or not os.path.exists(sheet_path):
                messagebox.showerror("Error", "Please select a filled answer sheet")
                return
            
            threshold = int(self.threshold.get())
            show_viz = self.show_scan_viz.get()
            
            self.log(f"Scanning: {sheet_path}")
            self.log(f"Threshold: {threshold}%")
            
            template = BubbleTemplate(template_path)
            extractor = AnswerExtractor(template)
            
            questions = extractor.extract_answers(
                sheet_path,
                threshold_percent=threshold,
                debug=show_viz
            )
            
            if questions:
                answers_json = save_answers_to_json(
                    questions=questions,
                    source_image_path=sheet_path,
                    template_path=template_path,
                    threshold_percent=threshold
                )
                
                self.scanned_answers_json.set(answers_json)
                self.log(f"✓ Answers saved: {answers_json}")
                self.scan_status.config(text=f"✓ Saved: {os.path.basename(answers_json)}")
                messagebox.showinfo("Success", f"Answers scanned!\n{answers_json}")
            
        except Exception as e:
            self.log(f"✗ Error: {e}")
            messagebox.showerror("Error", str(e))
    
    def grade_answers(self):
        """Grade the answer sheet"""
        try:
            from core.grading import load_answer_key, load_scanned_answers, grade_answers
            from core.grading import print_grading_summary, save_grade_report
            
            key_path = self.answer_key_json.get()
            answers_path = self.scanned_answers_json.get()
            
            if not key_path or not os.path.exists(key_path):
                messagebox.showerror("Error", "Please select an answer key")
                return
            
            if not answers_path or not os.path.exists(answers_path):
                messagebox.showerror("Error", "Please select scanned answers")
                return
            
            self.log("Loading data...")
            answer_key_data = load_answer_key(key_path)
            scanned_answers_data = load_scanned_answers(answers_path)
            
            # Get max points
            max_pts_str = self.max_points.get().strip()
            max_pts = float(max_pts_str) if max_pts_str else None
            
            partial = self.partial_credit.get()
            
            self.log(f"Grading with max points: {max_pts or 'auto'}")
            self.log(f"Partial credit: {partial}")
            
            results = grade_answers(
                answer_key_data,
                scanned_answers_data,
                max_points=max_pts,
                partial_credit=partial
            )
            
            # Display results
            self.log("\n=== GRADING RESULTS ===")
            self.log(f"Score: {results['score']:.2f} / {results['max_points']:.2f}")
            self.log(f"Percentage: {results['percentage']:.2f}%")
            self.log(f"Correct: {results['correct']}")
            self.log(f"Incorrect: {results['incorrect']}")
            self.log(f"Blank: {results['blank']}")
            
            # Save report
            report_json = save_grade_report(results, key_path, answers_path)
            self.log(f"✓ Report saved: {report_json}")
            
            self.grade_status.config(
                text=f"✓ Score: {results['score']:.2f}/{results['max_points']:.2f} ({results['percentage']:.2f}%)"
            )
            
            messagebox.showinfo(
                "Grading Complete",
                f"Score: {results['score']:.2f} / {results['max_points']:.2f}\n"
                f"Percentage: {results['percentage']:.2f}%\n\n"
                f"Report saved to:\n{report_json}"
            )
            
        except Exception as e:
            self.log(f"✗ Error: {e}")
            messagebox.showerror("Error", str(e))


def main():
    """Main function to run the UI"""
    root = tk.Tk()
    
    # Try to apply a theme
    try:
        style = ttk.Style()
        style.theme_use('clam')  # You can try: 'clam', 'alt', 'default', 'classic'
    except:
        pass
    
    app = AnswerSheetUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()