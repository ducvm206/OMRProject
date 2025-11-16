import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from datetime import datetime
from pymongo import MongoClient
import threading
from pathlib import Path

# Import core modules
from core import sheet_maker, bubble_extraction, answer_key, extraction, grading

class GradingSystemUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automatic Answer Sheet Grading System")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # MongoDB connection
        self.db = None
        self.connect_db()
        
        # Project paths
        self.PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        
        # Color scheme
        self.colors = {
            'primary': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'danger': '#F44336',
            'bg': '#F5F5F5',
            'card': '#FFFFFF',
            'text': '#212121',
            'text_light': '#757575'
        }
        
        # Configure styles
        self.setup_styles()
        
        # Create main UI
        self.create_ui()
        
    def connect_db(self):
        """Connect to MongoDB"""
        try:
            client = MongoClient('mongodb://localhost:27017/')
            self.db = client['grading_system']
            print("✅ Connected to MongoDB")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            messagebox.showerror("Database Error", 
                "Failed to connect to MongoDB.\nPlease ensure MongoDB is running.")
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure('Primary.TButton', 
            background=self.colors['primary'],
            foreground='white',
            padding=10,
            font=('Segoe UI', 10))
        
        style.configure('Success.TButton',
            background=self.colors['success'],
            foreground='white',
            padding=10,
            font=('Segoe UI', 10))
        
        # Configure frame styles
        style.configure('Card.TFrame',
            background=self.colors['card'],
            relief='flat')
        
        # Configure label styles
        style.configure('Title.TLabel',
            background=self.colors['card'],
            foreground=self.colors['text'],
            font=('Segoe UI', 16, 'bold'))
        
        style.configure('Subtitle.TLabel',
            background=self.colors['card'],
            foreground=self.colors['text_light'],
            font=('Segoe UI', 10))
    
    def create_ui(self):
        """Create main UI layout"""
        # Header
        self.create_header()
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left panel - Navigation
        self.create_navigation(main_container)
        
        # Right panel - Content
        self.content_frame = ttk.Frame(main_container)
        self.content_frame.pack(side='left', fill='both', expand=True, padx=(20, 0))
        
        # Show dashboard by default
        self.show_dashboard()
    
    def create_header(self):
        """Create header section"""
        header = tk.Frame(self.root, bg=self.colors['primary'], height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        title = tk.Label(header, 
            text="📝 Answer Sheet Grading System",
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 20, 'bold'))
        title.pack(pady=20, padx=30, anchor='w')
    
    def create_navigation(self, parent):
        """Create navigation panel"""
        nav_frame = ttk.Frame(parent, width=250)
        nav_frame.pack(side='left', fill='y')
        nav_frame.pack_propagate(False)
        
        nav_items = [
            ("🏠 Dashboard", self.show_dashboard),
            ("📄 Create Sheet", self.show_create_sheet),
            ("📊 Extract Template", self.show_extract_template),
            ("🔑 Create Answer Key", self.show_create_key),
            ("✏️ Grade Single Sheet", self.show_grade_single),
            ("📚 Batch Grading", self.show_batch_grading),
            ("👨‍🎓 Students", self.show_students),
            ("📈 Reports", self.show_reports),
            ("⚙️ Settings", self.show_settings)
        ]
        
        for text, command in nav_items:
            btn = tk.Button(nav_frame,
                text=text,
                command=command,
                bg='white',
                fg=self.colors['text'],
                font=('Segoe UI', 11),
                anchor='w',
                padx=20,
                pady=15,
                relief='flat',
                cursor='hand2')
            btn.pack(fill='x', pady=2)
            
            # Hover effects
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=self.colors['bg']))
            btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='white'))
    
    def clear_content(self):
        """Clear content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def create_card(self, parent, title):
        """Create a card widget"""
        card = ttk.Frame(parent, style='Card.TFrame', relief='solid', borderwidth=1)
        card.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(card, text=title, style='Title.TLabel')
        title_label.pack(pady=(20, 10), padx=20, anchor='w')
        
        # Content frame
        content = ttk.Frame(card, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        return card, content
    
    # ===== VIEW METHODS =====
    
    def show_dashboard(self):
        """Show dashboard view"""
        self.clear_content()
        
        # Welcome message
        welcome = ttk.Label(self.content_frame,
            text="Welcome to Answer Sheet Grading System",
            style='Title.TLabel')
        welcome.pack(pady=20)
        
        # Stats container
        stats_container = ttk.Frame(self.content_frame)
        stats_container.pack(fill='x', pady=20)
        
        # Get statistics from DB
        stats = self.get_dashboard_stats()
        
        # Create stat cards
        stat_items = [
            ("📄 Templates", stats['templates'], self.colors['primary']),
            ("🔑 Answer Keys", stats['answer_keys'], self.colors['success']),
            ("👨‍🎓 Students", stats['students'], self.colors['warning']),
            ("📝 Submissions", stats['submissions'], self.colors['danger'])
        ]
        
        for i, (title, value, color) in enumerate(stat_items):
            stat_card = tk.Frame(stats_container, bg=color, relief='solid', borderwidth=0)
            stat_card.grid(row=0, column=i, padx=10, pady=10, sticky='ew')
            stats_container.grid_columnconfigure(i, weight=1)
            
            tk.Label(stat_card,
                text=title,
                bg=color,
                fg='white',
                font=('Segoe UI', 12)).pack(pady=(20, 5))
            
            tk.Label(stat_card,
                text=str(value),
                bg=color,
                fg='white',
                font=('Segoe UI', 28, 'bold')).pack(pady=(5, 20))
        
        # Recent activity
        card, content = self.create_card(self.content_frame, "Recent Activity")
        
        # Activity list
        activity_list = ttk.Treeview(content,
            columns=('Type', 'Name', 'Date'),
            show='headings',
            height=10)
        
        activity_list.heading('Type', text='Type')
        activity_list.heading('Name', text='Name')
        activity_list.heading('Date', text='Date')
        
        activity_list.column('Type', width=150)
        activity_list.column('Name', width=300)
        activity_list.column('Date', width=200)
        
        # Get recent activity
        recent = self.get_recent_activity()
        for item in recent:
            activity_list.insert('', 'end', values=item)
        
        activity_list.pack(fill='both', expand=True)
    
    def show_create_sheet(self):
        """Show create sheet view"""
        self.clear_content()
        
        card, content = self.create_card(self.content_frame, "Create Blank Answer Sheet")
        
        # Form
        form_frame = ttk.Frame(content)
        form_frame.pack(fill='x', pady=20)
        
        # Number of questions
        ttk.Label(form_frame, text="Number of Questions:").grid(row=0, column=0, sticky='w', pady=10)
        questions_var = tk.StringVar(value="40")
        questions_entry = ttk.Entry(form_frame, textvariable=questions_var, width=30)
        questions_entry.grid(row=0, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Output filename
        ttk.Label(form_frame, text="Output Filename:").grid(row=1, column=0, sticky='w', pady=10)
        filename_var = tk.StringVar(value="answer_sheet.pdf")
        filename_entry = ttk.Entry(form_frame, textvariable=filename_var, width=30)
        filename_entry.grid(row=1, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Student ID option
        include_id_var = tk.BooleanVar(value=True)
        id_check = ttk.Checkbutton(form_frame,
            text="Include Student ID bubbles",
            variable=include_id_var)
        id_check.grid(row=2, column=0, columnspan=2, sticky='w', pady=10)
        
        # Output log
        log_label = ttk.Label(content, text="Output:")
        log_label.pack(anchor='w', pady=(20, 5))
        
        log_text = scrolledtext.ScrolledText(content, height=10, wrap='word')
        log_text.pack(fill='both', expand=True)
        
        # Create button
        def create_sheet():
            try:
                num_questions = int(questions_var.get())
                output_path = filename_var.get()
                
                log_text.insert('end', f"Creating {num_questions}-question answer sheet...\n")
                log_text.see('end')
                
                # Create designer
                from core.sheet_maker import AnswerSheetDesigner
                designer = AnswerSheetDesigner()
                designer.set_config(include_student_id=include_id_var.get())
                
                # Generate PDF
                designer.create_answer_sheet(
                    total_questions=num_questions,
                    output_path=output_path,
                    format='pdf',
                    use_preset=True
                )
                
                log_text.insert('end', f"✅ Success! Saved to: {output_path}\n")
                log_text.see('end')
                
                messagebox.showinfo("Success", f"Answer sheet created: {output_path}")
                
            except Exception as e:
                log_text.insert('end', f"❌ Error: {str(e)}\n")
                log_text.see('end')
                messagebox.showerror("Error", str(e))
        
        create_btn = ttk.Button(content,
            text="Create Answer Sheet",
            command=create_sheet,
            style='Primary.TButton')
        create_btn.pack(pady=20)
    
    def show_extract_template(self):
        """Show extract template view"""
        self.clear_content()
        
        card, content = self.create_card(self.content_frame, "Extract Bubble Template")
        
        # Form
        form_frame = ttk.Frame(content)
        form_frame.pack(fill='x', pady=20)
        
        # PDF file selection
        ttk.Label(form_frame, text="Template PDF:").grid(row=0, column=0, sticky='w', pady=10)
        pdf_var = tk.StringVar()
        pdf_entry = ttk.Entry(form_frame, textvariable=pdf_var, width=40)
        pdf_entry.grid(row=0, column=1, sticky='w', pady=10, padx=(10, 0))
        
        def browse_pdf():
            filename = filedialog.askopenfilename(
                title="Select Template PDF",
                filetypes=[("PDF files", "*.pdf")])
            if filename:
                pdf_var.set(filename)
        
        browse_btn = ttk.Button(form_frame, text="Browse", command=browse_pdf)
        browse_btn.grid(row=0, column=2, pady=10, padx=(10, 0))
        
        # DPI setting
        ttk.Label(form_frame, text="DPI:").grid(row=1, column=0, sticky='w', pady=10)
        dpi_var = tk.StringVar(value="300")
        dpi_combo = ttk.Combobox(form_frame, textvariable=dpi_var, width=15, values=["150", "300", "600"])
        dpi_combo.grid(row=1, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Show visualization
        show_viz_var = tk.BooleanVar(value=True)
        viz_check = ttk.Checkbutton(form_frame,
            text="Show visualization",
            variable=show_viz_var)
        viz_check.grid(row=2, column=0, columnspan=2, sticky='w', pady=10)
        
        # Output log
        log_text = scrolledtext.ScrolledText(content, height=15, wrap='word')
        log_text.pack(fill='both', expand=True, pady=(20, 0))
        
        # Extract button
        def extract_template():
            pdf_path = pdf_var.get()
            if not pdf_path or not os.path.exists(pdf_path):
                messagebox.showerror("Error", "Please select a valid PDF file")
                return
            
            try:
                log_text.insert('end', f"Processing: {pdf_path}\n")
                log_text.see('end')
                
                from core.bubble_extraction import process_pdf_answer_sheet
                
                json_path = process_pdf_answer_sheet(
                    pdf_path=pdf_path,
                    dpi=int(dpi_var.get()),
                    keep_png=False,
                    show_visualization=show_viz_var.get()
                )
                
                if json_path:
                    log_text.insert('end', f"✅ Template saved: {json_path}\n")
                    log_text.see('end')
                    
                    # Save to database
                    self.save_template_to_db(json_path, pdf_path)
                    
                    messagebox.showinfo("Success", f"Template extracted: {json_path}")
                else:
                    log_text.insert('end', "❌ Extraction failed\n")
                    log_text.see('end')
                    
            except Exception as e:
                log_text.insert('end', f"❌ Error: {str(e)}\n")
                log_text.see('end')
                messagebox.showerror("Error", str(e))
        
        extract_btn = ttk.Button(content,
            text="Extract Template",
            command=extract_template,
            style='Success.TButton')
        extract_btn.pack(pady=20)
    
    def show_create_key(self):
        """Show create answer key view"""
        self.clear_content()
        
        card, content = self.create_card(self.content_frame, "Create Answer Key")
        
        # Template selection
        form_frame = ttk.Frame(content)
        form_frame.pack(fill='x', pady=20)
        
        ttk.Label(form_frame, text="Select Template:").grid(row=0, column=0, sticky='w', pady=10)
        
        # Get templates from DB
        templates = list(self.db.templates.find({'status': 'active'}))
        template_names = [t['name'] for t in templates]
        
        template_var = tk.StringVar()
        template_combo = ttk.Combobox(form_frame, textvariable=template_var, width=40, values=template_names)
        template_combo.grid(row=0, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Method selection
        ttk.Label(form_frame, text="Method:").grid(row=1, column=0, sticky='w', pady=10)
        method_var = tk.StringVar(value="manual")
        
        ttk.Radiobutton(form_frame,
            text="Manual entry",
            variable=method_var,
            value="manual").grid(row=1, column=1, sticky='w', pady=5, padx=(10, 0))
        
        ttk.Radiobutton(form_frame,
            text="Scan master sheet",
            variable=method_var,
            value="scan").grid(row=2, column=1, sticky='w', pady=5, padx=(10, 0))
        
        # Output log
        log_text = scrolledtext.ScrolledText(content, height=15, wrap='word')
        log_text.pack(fill='both', expand=True, pady=(20, 0))
        
        # Create button
        def create_key():
            template_name = template_var.get()
            if not template_name:
                messagebox.showerror("Error", "Please select a template")
                return
            
            # Find template
            template = next((t for t in templates if t['name'] == template_name), None)
            if not template:
                messagebox.showerror("Error", "Template not found")
                return
            
            try:
                log_text.insert('end', f"Creating answer key for: {template_name}\n")
                log_text.see('end')
                
                # Implementation depends on method
                if method_var.get() == "manual":
                    # Open manual entry dialog
                    self.open_manual_key_entry(template, log_text)
                else:
                    # Scan master sheet
                    master_path = filedialog.askopenfilename(
                        title="Select Master Answer Sheet",
                        filetypes=[("Image files", "*.png *.jpg *.jpeg")])
                    
                    if master_path:
                        self.create_key_from_scan(template, master_path, log_text)
                
            except Exception as e:
                log_text.insert('end', f"❌ Error: {str(e)}\n")
                log_text.see('end')
                messagebox.showerror("Error", str(e))
        
        create_btn = ttk.Button(content,
            text="Create Answer Key",
            command=create_key,
            style='Primary.TButton')
        create_btn.pack(pady=20)
    
    def show_grade_single(self):
        """Show grade single sheet view"""
        self.clear_content()
        
        card, content = self.create_card(self.content_frame, "Grade Single Answer Sheet")
        
        # Form
        form_frame = ttk.Frame(content)
        form_frame.pack(fill='x', pady=20)
        
        # Template selection
        ttk.Label(form_frame, text="Template:").grid(row=0, column=0, sticky='w', pady=10)
        templates = list(self.db.templates.find({'status': 'active'}))
        template_names = [t['name'] for t in templates]
        template_var = tk.StringVar()
        template_combo = ttk.Combobox(form_frame, textvariable=template_var, width=35, values=template_names)
        template_combo.grid(row=0, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Answer key selection
        ttk.Label(form_frame, text="Answer Key:").grid(row=1, column=0, sticky='w', pady=10)
        keys = list(self.db.answer_keys.find({'status': 'active'}))
        key_names = [k['name'] for k in keys]
        key_var = tk.StringVar()
        key_combo = ttk.Combobox(form_frame, textvariable=key_var, width=35, values=key_names)
        key_combo.grid(row=1, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Image selection
        ttk.Label(form_frame, text="Answer Sheet:").grid(row=2, column=0, sticky='w', pady=10)
        image_var = tk.StringVar()
        image_entry = ttk.Entry(form_frame, textvariable=image_var, width=35)
        image_entry.grid(row=2, column=1, sticky='w', pady=10, padx=(10, 0))
        
        def browse_image():
            filename = filedialog.askopenfilename(
                title="Select Answer Sheet",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
            if filename:
                image_var.set(filename)
        
        browse_btn = ttk.Button(form_frame, text="Browse", command=browse_image)
        browse_btn.grid(row=2, column=2, pady=10, padx=(10, 0))
        
        # Threshold
        ttk.Label(form_frame, text="Threshold (%):").grid(row=3, column=0, sticky='w', pady=10)
        threshold_var = tk.StringVar(value="50")
        threshold_spin = ttk.Spinbox(form_frame, from_=20, to=90, textvariable=threshold_var, width=10)
        threshold_spin.grid(row=3, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Results frame
        results_frame = ttk.LabelFrame(content, text="Results", padding=10)
        results_frame.pack(fill='both', expand=True, pady=20)
        
        results_text = scrolledtext.ScrolledText(results_frame, height=15, wrap='word')
        results_text.pack(fill='both', expand=True)
        
        # Grade button
        def grade_sheet():
            # Validate inputs
            if not all([template_var.get(), key_var.get(), image_var.get()]):
                messagebox.showerror("Error", "Please fill all fields")
                return
            
            try:
                results_text.insert('end', "Starting grading process...\n")
                results_text.see('end')
                
                # Find template and key
                template = next((t for t in templates if t['name'] == template_var.get()), None)
                answer_key = next((k for k in keys if k['name'] == key_var.get()), None)
                
                if not template or not answer_key:
                    messagebox.showerror("Error", "Template or key not found")
                    return
                
                # Grade the sheet
                result = self.grade_single_sheet(
                    template['json_path'],
                    answer_key,
                    image_var.get(),
                    int(threshold_var.get()),
                    results_text
                )
                
                if result:
                    results_text.insert('end', "\n✅ Grading complete!\n")
                    results_text.insert('end', f"Student ID: {result.get('student_id', 'N/A')}\n")
                    results_text.insert('end', f"Score: {result['score']}/{result['max_score']}\n")
                    results_text.insert('end', f"Percentage: {result['percentage']:.2f}%\n")
                    results_text.insert('end', f"Grade: {result['letter_grade']}\n")
                    results_text.see('end')
                    
                    messagebox.showinfo("Success", "Grading completed successfully!")
                
            except Exception as e:
                results_text.insert('end', f"\n❌ Error: {str(e)}\n")
                results_text.see('end')
                messagebox.showerror("Error", str(e))
        
        grade_btn = ttk.Button(content,
            text="Grade Answer Sheet",
            command=grade_sheet,
            style='Success.TButton')
        grade_btn.pack(pady=10)
    
    def show_batch_grading(self):
        """Show batch grading view"""
        self.clear_content()
        
        card, content = self.create_card(self.content_frame, "Batch Grading")
        
        # Form
        form_frame = ttk.Frame(content)
        form_frame.pack(fill='x', pady=20)
        
        # Template selection
        ttk.Label(form_frame, text="Template:").grid(row=0, column=0, sticky='w', pady=10)
        templates = list(self.db.templates.find({'status': 'active'}))
        template_names = [t['name'] for t in templates]
        template_var = tk.StringVar()
        template_combo = ttk.Combobox(form_frame, textvariable=template_var, width=35, values=template_names)
        template_combo.grid(row=0, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Answer key selection
        ttk.Label(form_frame, text="Answer Key:").grid(row=1, column=0, sticky='w', pady=10)
        keys = list(self.db.answer_keys.find({'status': 'active'}))
        key_names = [k['name'] for k in keys]
        key_var = tk.StringVar()
        key_combo = ttk.Combobox(form_frame, textvariable=key_var, width=35, values=key_names)
        key_combo.grid(row=1, column=1, sticky='w', pady=10, padx=(10, 0))
        
        # Folder selection
        ttk.Label(form_frame, text="Images Folder:").grid(row=2, column=0, sticky='w', pady=10)
        folder_var = tk.StringVar()
        folder_entry = ttk.Entry(form_frame, textvariable=folder_var, width=35)
        folder_entry.grid(row=2, column=1, sticky='w', pady=10, padx=(10, 0))
        
        def browse_folder():
            folder = filedialog.askdirectory(title="Select Folder with Answer Sheets")
            if folder:
                folder_var.set(folder)
        
        browse_btn = ttk.Button(form_frame, text="Browse", command=browse_folder)
        browse_btn.grid(row=2, column=2, pady=10, padx=(10, 0))
        
        # Progress frame
        progress_frame = ttk.LabelFrame(content, text="Progress", padding=10)
        progress_frame.pack(fill='both', expand=True, pady=20)
        
        progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        progress_bar.pack(fill='x', pady=10)
        
        status_label = ttk.Label(progress_frame, text="Ready")
        status_label.pack()
        
        results_text = scrolledtext.ScrolledText(progress_frame, height=12, wrap='word')
        results_text.pack(fill='both', expand=True, pady=10)
        
        # Start button
        def start_batch():
            # Validate
            if not all([template_var.get(), key_var.get(), folder_var.get()]):
                messagebox.showerror("Error", "Please fill all fields")
                return
            
            # Find template and key
            template = next((t for t in templates if t['name'] == template_var.get()), None)
            answer_key = next((k for k in keys if k['name'] == key_var.get()), None)
            
            if not template or not answer_key:
                messagebox.showerror("Error", "Template or key not found")
                return
            
            # Run in thread
            def batch_worker():
                self.process_batch_grading(
                    template['json_path'],
                    answer_key,
                    folder_var.get(),
                    progress_bar,
                    status_label,
                    results_text
                )
            
            thread = threading.Thread(target=batch_worker, daemon=True)
            thread.start()
        
        start_btn = ttk.Button(content,
            text="Start Batch Grading",
            command=start_batch,
            style='Success.TButton')
        start_btn.pack(pady=10)
    
    def show_students(self):
        """Show students management view"""
        self.clear_content()
        
        card, content = self.create_card(self.content_frame, "Students Management")
        
        # Toolbar
        toolbar = ttk.Frame(content)
        toolbar.pack(fill='x', pady=(0, 10))
        
        ttk.Button(toolbar, text="+ Add Student", command=self.add_student_dialog).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Import CSV", command=self.import_students_csv).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Refresh", command=lambda: self.show_students()).pack(side='left', padx=5)
        
        # Search
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side='right', padx=5)
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)