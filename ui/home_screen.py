"""
Home Screen - Main Dashboard
Entry point for the Answer Sheet Grading System
Updated for new schema with exams table
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.screen_manager import ScreenManager
from utils import get_db_operations


class HomeScreen:
    """Main dashboard/home screen for the grading system"""
    
    def __init__(self, root, screen_manager=None):
        """
        Initialize home screen
        
        Args:
            root: Tkinter root window
            screen_manager: ScreenManager instance for navigation
        """
        self.root = root
        self.screen_manager = screen_manager or ScreenManager(root)
        self.db_ops = get_db_operations()
        
        # Setup window
        self.setup_window()
        self.create_ui()
        self.check_database()
    
    def setup_window(self):
        """Configure main window"""
        self.root.title("Answer Sheet Grading System - Home")
        self.root.geometry("900x700")
        
        # Configure style
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
        
        # Colors
        self.BG_COLOR = "#f5f5f5"
        self.CARD_COLOR = "#ffffff"
        self.ACCENT_COLOR = "#0078d4"
        
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabel", background=self.BG_COLOR, font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground="#333")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 12), foreground="#666")
        style.configure("TButton", font=("Segoe UI", 10), padding=10)
        style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), padding=15)
        
        self.root.configure(bg=self.BG_COLOR)
    
    def create_ui(self):
        """Create main user interface"""
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container with scrollbar
        main_canvas = tk.Canvas(self.root, bg=self.BG_COLOR, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        main_container = tk.Frame(main_canvas, bg=self.BG_COLOR)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")
        
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        main_canvas.create_window((0, 0), window=main_container, anchor="nw")
        
        # Bind scroll region update
        def configure_scroll_region(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        
        main_container.bind("<Configure>", configure_scroll_region)
        
        # Header
        self.create_header(main_container)
        
        # Main action cards
        self.create_action_cards(main_container)
        
        # Quick Actions section
        self.create_quick_actions(main_container)
        
        # Statistics section
        self.create_statistics_section(main_container)
        
        # Recent Activity section
        self.create_recent_activity(main_container)
        
        # Footer
        self.create_footer(main_container)
    
    def create_header(self, parent):
        """Create application header"""
        header_frame = tk.Frame(parent, bg=self.BG_COLOR)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title
        title_label = ttk.Label(header_frame, 
                               text="📋 Answer Sheet Grading System",
                               style="Title.TLabel")
        title_label.pack()
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame,
                                  text="Create, manage, and grade multiple-choice and written answer sheets",
                                  style="Subtitle.TLabel")
        subtitle_label.pack(pady=(5, 0))
        
        # Database status
        self.db_status_label = tk.Label(header_frame,
                                       font=("Segoe UI", 9),
                                       bg=self.BG_COLOR,
                                       fg="#666")
        self.db_status_label.pack(pady=(5, 0))
        self.update_db_status()
    
    def create_action_cards(self, parent):
        """Create main action cards"""
        cards_frame = tk.Frame(parent, bg=self.BG_COLOR)
        cards_frame.pack(fill=tk.BOTH, pady=(0, 20))
        
        # Create grid of cards
        actions = [
            {
                'title': '📄 Sheets & Templates',
                'description': 'Create blank answer sheets\nand extract templates',
                'command': self.open_sheet_creator,
                'color': '#e3f2fd',
                'icon': '📄'
            },
            {
                'title': '📝 Exams & Answer Keys',
                'description': 'Create exams and answer keys\nwith multiple versions (A-E)',
                'command': self.open_exam_manager,
                'color': '#f3e5f5',
                'icon': '📝'
            },
            {
                'title': '📊 Grade Sheets',
                'description': 'Grade filled answer sheets\nand view detailed results',
                'command': self.open_grading,
                'color': '#e8f5e9',
                'icon': '📊'
            },
            {
                'title': '📈 Analytics',
                'description': 'View statistics and\nperformance analytics',
                'command': self.open_analytics,
                'color': '#fff3e0',
                'icon': '📈'
            }
        ]
        
        # Create 2x2 grid
        for i in range(2):  # rows
            for j in range(2):  # columns
                idx = i * 2 + j
                if idx < len(actions):
                    self.create_action_card(cards_frame, actions[idx], row=i, col=j)
        
        # Configure grid weights
        for col in range(2):
            cards_frame.grid_columnconfigure(col, weight=1)
        cards_frame.grid_rowconfigure(0, weight=1)
        cards_frame.grid_rowconfigure(1, weight=1)
    
    def create_action_card(self, parent, action, row, col):
        """Create a single action card"""
        card = tk.Frame(parent, bg=action['color'], relief="solid", borderwidth=1)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Card content
        content = tk.Frame(card, bg=action['color'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Icon
        icon_label = tk.Label(content,
                             text=action['icon'],
                             font=("Segoe UI", 24),
                             bg=action['color'],
                             fg="#555")
        icon_label.pack(pady=(0, 10))
        
        # Title
        title_label = tk.Label(content,
                              text=action['title'],
                              font=("Segoe UI", 14, "bold"),
                              bg=action['color'],
                              fg="#333")
        title_label.pack(pady=(0, 8))
        
        # Description
        desc_label = tk.Label(content,
                             text=action['description'],
                             font=("Segoe UI", 10),
                             bg=action['color'],
                             fg="#666",
                             justify=tk.CENTER)
        desc_label.pack(pady=(0, 15))
        
        # Button
        btn = ttk.Button(content,
                        text="Open",
                        command=action['command'],
                        style="Action.TButton")
        btn.pack()
        
        # Hover effects
        def on_enter(e):
            card.configure(relief="raised", borderwidth=2)
        
        def on_leave(e):
            card.configure(relief="solid", borderwidth=1)
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        content.bind("<Enter>", on_enter)
        content.bind("<Leave>", on_leave)
    
    def create_quick_actions(self, parent):
        """Create quick action buttons"""
        quick_frame = tk.Frame(parent, bg=self.BG_COLOR)
        quick_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(quick_frame,
                text="Quick Actions",
                font=("Segoe UI", 12, "bold"),
                bg=self.BG_COLOR,
                fg="#333").pack(anchor="w", pady=(0, 10))
        
        actions_frame = tk.Frame(quick_frame, bg=self.BG_COLOR)
        actions_frame.pack(fill=tk.X)
        
        quick_actions = [
            ("Import Exam", "📥", self.import_exam),
            ("Export Results", "📤", self.export_results),
            ("View Students", "👥", self.view_students),
            ("Database Info", "🗄️", self.show_database_info)
        ]
        
        for i, (text, icon, command) in enumerate(quick_actions):
            btn = tk.Button(actions_frame,
                          text=f"{icon} {text}",
                          font=("Segoe UI", 10),
                          bg=self.CARD_COLOR,
                          fg="#333",
                          relief="solid",
                          borderwidth=1,
                          padx=15,
                          pady=8,
                          command=command)
            btn.pack(side=tk.LEFT, padx=(0, 10))
    
    def create_statistics_section(self, parent):
        """Create statistics section"""
        stats_frame = tk.Frame(parent, bg=self.CARD_COLOR, relief="solid", borderwidth=1)
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        stats_inner = tk.Frame(stats_frame, bg=self.CARD_COLOR)
        stats_inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        # Title
        tk.Label(stats_inner,
                text="📈 System Statistics",
                font=("Segoe UI", 12, "bold"),
                bg=self.CARD_COLOR,
                fg="#333").pack(anchor="w", pady=(0, 15))
        
        # Stats grid
        stats_grid = tk.Frame(stats_inner, bg=self.CARD_COLOR)
        stats_grid.pack(fill=tk.X)
        
        # Get statistics from database
        stats = self.get_statistics()
        
        stat_items = [
            ('Exams', stats['exams'], '📝'),
            ('Answer Keys', stats['answer_keys'], '🔑'),
            ('Templates', stats['templates'], '📋'),
            ('Students', stats['students'], '👥'),
            ('Graded', stats['graded_sheets'], '✓'),
            ('Avg Score', stats['avg_score'], '📊')
        ]
        
        for i, (label, value, icon) in enumerate(stat_items):
            stat_card = tk.Frame(stats_grid, bg="#f8f9fa", relief="flat")
            stat_card.grid(row=0, column=i, padx=5, sticky="ew")
            stats_grid.grid_columnconfigure(i, weight=1)
            
            # Icon and value
            tk.Label(stat_card,
                    text=f"{icon} {value}",
                    font=("Segoe UI", 14, "bold"),
                    bg="#f8f9fa",
                    fg=self.ACCENT_COLOR).pack(pady=(10, 5))
            
            # Label
            tk.Label(stat_card,
                    text=label,
                    font=("Segoe UI", 9),
                    bg="#f8f9fa",
                    fg="#666").pack(pady=(0, 10))
    
    def create_recent_activity(self, parent):
        """Create recent activity section"""
        activity_frame = tk.Frame(parent, bg=self.CARD_COLOR, relief="solid", borderwidth=1)
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        activity_inner = tk.Frame(activity_frame, bg=self.CARD_COLOR)
        activity_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Title with refresh button
        title_frame = tk.Frame(activity_inner, bg=self.CARD_COLOR)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(title_frame,
                text="🕐 Recent Grading Activity",
                font=("Segoe UI", 12, "bold"),
                bg=self.CARD_COLOR,
                fg="#333").pack(side=tk.LEFT)
        
        refresh_btn = tk.Button(title_frame,
                               text="⟳ Refresh",
                               font=("Segoe UI", 9),
                               bg=self.CARD_COLOR,
                               fg="#0078d4",
                               relief="flat",
                               command=self.refresh_activity)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Activity list with scrollbar
        list_frame = tk.Frame(activity_inner, bg=self.CARD_COLOR)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create listbox with scrollbar
        listbox_scrollbar = ttk.Scrollbar(list_frame)
        listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.activity_listbox = tk.Listbox(list_frame,
                                          font=("Courier New", 10),
                                          bg="white",
                                          relief="flat",
                                          yscrollcommand=listbox_scrollbar.set,
                                          height=8)
        self.activity_listbox.pack(fill=tk.BOTH, expand=True)
        listbox_scrollbar.config(command=self.activity_listbox.yview)
        
        # Load recent activity
        self.load_recent_activity()
    
    def create_footer(self, parent):
        """Create footer with tools and info"""
        footer_frame = tk.Frame(parent, bg=self.BG_COLOR)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(20, 0))
        
        # Left side - Status
        left_frame = tk.Frame(footer_frame, bg=self.BG_COLOR)
        left_frame.pack(side=tk.LEFT)
        
        self.status_label = tk.Label(left_frame,
                                    font=("Segoe UI", 9),
                                    bg=self.BG_COLOR,
                                    fg="#666")
        self.status_label.pack()
        self.update_status()
        
        # Right side - Info
        right_frame = tk.Frame(footer_frame, bg=self.BG_COLOR)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame,
                  text="❓ Help",
                  command=self.show_help,
                  width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(right_frame,
                  text="ℹ️ About",
                  command=self.show_about,
                  width=8).pack(side=tk.LEFT, padx=5)
    
    def update_db_status(self):
        """Update database status display"""
        if self.db_ops.is_connected():
            self.db_status_label.config(text="✓ Database Connected", fg="#28a745")
        else:
            self.db_status_label.config(text="✗ Database Not Connected", fg="#dc3545")
    
    def update_status(self):
        """Update status label"""
        import datetime
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        if self.db_ops.is_connected():
            try:
                cursor = self.db_ops.db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM graded_sheets")
                count = cursor.fetchone()[0]
                self.status_label.config(text=f"Last updated: {timestamp} | Total graded: {count}")
            except:
                self.status_label.config(text=f"Last updated: {timestamp}")
        else:
            self.status_label.config(text=f"Last updated: {timestamp} | Database not connected")
    
    def check_database(self):
        """Check database connectivity on startup"""
        if not self.db_ops.is_connected():
            messagebox.showwarning(
                "Database Warning",
                "Database connection could not be established.\n\n"
                "Some features may not work properly.\n"
                "Please run: python database/init_db.py"
            )
    
    def get_statistics(self):
        """Get statistics from database"""
        stats = {
            'exams': 0,
            'answer_keys': 0,
            'templates': 0,
            'students': 0,
            'graded_sheets': 0,
            'avg_score': '0%'
        }
        
        if self.db_ops.is_connected():
            try:
                cursor = self.db_ops.db.conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM exams")
                stats['exams'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM answer_keys")
                stats['answer_keys'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM templates")
                stats['templates'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM students")
                stats['students'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM graded_sheets")
                stats['graded_sheets'] = cursor.fetchone()[0]
                
                # Get average score
                cursor.execute("SELECT AVG(percentage) FROM graded_sheets WHERE percentage > 0")
                avg_result = cursor.fetchone()[0]
                if avg_result:
                    stats['avg_score'] = f"{avg_result:.1f}%"
                else:
                    stats['avg_score'] = "N/A"
                
            except Exception as e:
                print(f"[HOME] Error getting statistics: {e}")
        
        return stats
    
    def load_recent_activity(self):
        """Load recent activity into listbox"""
        self.activity_listbox.delete(0, tk.END)
        
        if not self.db_ops.is_connected():
            self.activity_listbox.insert(0, "Database not connected")
            return
        
        try:
            # Get recent grades from database
            recent_grades = self.db_ops.get_recent_grades(limit=15)
            
            if not recent_grades:
                self.activity_listbox.insert(0, "No grading activity yet")
                return
            
            for grade in recent_grades:
                # Format the display
                timestamp = grade['graded_at'][:19] if grade['graded_at'] else "Unknown"
                student_id = grade['student_id']
                score = grade['score']
                max_score = grade['max_score']
                percentage = grade['percentage'] if grade['percentage'] else 0
                key_label = grade.get('key_label', '?')
                exam_name = grade.get('exam_name_full', grade.get('exam_name', 'Unknown'))
                
                # Truncate long exam names
                if len(exam_name) > 25:
                    exam_name = exam_name[:22] + "..."
                
                display_text = f"{timestamp} | {student_id:8s} | {score:4.1f}/{max_score:4.1f} ({percentage:5.1f}%) | Key {key_label} | {exam_name}"
                self.activity_listbox.insert(tk.END, display_text)
            
            # Add header
            self.activity_listbox.insert(0, "Timestamp             | Student  | Score     | Key | Exam")
            self.activity_listbox.insert(1, "-" * 70)
            
        except Exception as e:
            print(f"[HOME] Error loading recent activity: {e}")
            self.activity_listbox.insert(0, f"Error loading activity: {e}")
    
    def refresh_activity(self):
        """Refresh recent activity list"""
        self.load_recent_activity()
        self.update_status()
    
    def open_sheet_creator(self):
        """Open sheet creation screen"""
        self.screen_manager.open_screen('sheet')
    
    def open_exam_manager(self):
        """Open exam and answer key management screen"""
        # Check if we have a proper exam manager screen, fallback to key creator
        try:
            self.screen_manager.open_screen('exam')
        except:
            self.screen_manager.open_screen('key')
    
    def open_grading(self):
        """Open grading screen"""
        self.screen_manager.open_screen('grading')
    
    def open_analytics(self):
        """Open analytics screen"""
        self.show_detailed_statistics()
    
    def import_exam(self):
        """Import exam from file"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Exam JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            # TODO: Implement exam import with template selection
            messagebox.showinfo("Import Exam", f"Selected: {file_path}\n\nThis feature will be implemented soon.")
    
    def export_results(self):
        """Export grading results"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            # TODO: Implement export functionality
            messagebox.showinfo("Export Results", f"Export to: {file_path}\n\nThis feature will be implemented soon.")
    
    def view_students(self):
        """View student list"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        try:
            students = self.db_ops.list_students() if hasattr(self.db_ops, 'list_students') else []
            
            if not students:
                messagebox.showinfo("Students", "No students found in database.")
                return
            
            # Create student list window
            student_window = tk.Toplevel(self.root)
            student_window.title("Student List")
            student_window.geometry("600x400")
            
            # Create listbox with scrollbar
            frame = tk.Frame(student_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(frame,
                                font=("Courier New", 10),
                                yscrollcommand=scrollbar.set,
                                height=20)
            listbox.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Add students to list
            listbox.insert(0, "Student ID       | Exams | Total Score | Avg %")
            listbox.insert(1, "-" * 60)
            
            for student in students:
                student_id = student['student_id']
                total_exams = student.get('total_exams', 0)
                total_score = student.get('total_score', 0)
                avg_percentage = student.get('avg_percentage', 0)
                
                display_text = f"{student_id:15s} | {total_exams:5d} | {total_score:10.1f} | {avg_percentage:6.1f}%"
                listbox.insert(tk.END, display_text)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load students: {e}")
    
    def show_database_info(self):
        """Show database information"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        info_window = tk.Toplevel(self.root)
        info_window.title("Database Information")
        info_window.geometry("600x500")
        info_window.transient(self.root)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(info_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tables tab
        tables_tab = ttk.Frame(notebook)
        notebook.add(tables_tab, text="Tables")
        
        tables_text = tk.Text(tables_tab, wrap=tk.WORD, font=("Courier New", 9))
        tables_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Views tab
        views_tab = ttk.Frame(notebook)
        notebook.add(views_tab, text="Views")
        
        views_text = tk.Text(views_tab, wrap=tk.WORD, font=("Courier New", 9))
        views_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        try:
            cursor = self.db_ops.db.conn.cursor()
            
            # Tables information
            tables_text.insert(tk.END, "DATABASE TABLES\n")
            tables_text.insert(tk.END, "=" * 50 + "\n\n")
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                tables_text.insert(tk.END, f"{table_name:20s} {count:>10,} records\n")
                
                # Show columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                for col in columns[:3]:  # Show first 3 columns
                    tables_text.insert(tk.END, f"    {col[1]:15s} {col[2]:10s}\n")
                if len(columns) > 3:
                    tables_text.insert(tk.END, f"    ... and {len(columns) - 3} more columns\n")
                tables_text.insert(tk.END, "\n")
            
            # Views information
            views_text.insert(tk.END, "DATABASE VIEWS\n")
            views_text.insert(tk.END, "=" * 50 + "\n\n")
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view'
                ORDER BY name
            """)
            
            views = cursor.fetchall()
            
            if views:
                for view in views:
                    view_name = view[0]
                    views_text.insert(tk.END, f"✓ {view_name}\n")
            else:
                views_text.insert(tk.END, "No views defined\n")
            
        except Exception as e:
            tables_text.insert(tk.END, f"\nError: {e}")
            views_text.insert(tk.END, f"\nError: {e}")
        
        tables_text.config(state=tk.DISABLED)
        views_text.config(state=tk.DISABLED)
    
    def show_detailed_statistics(self):
        """Show detailed statistics window"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Detailed Statistics")
        stats_window.geometry("800x600")
        stats_window.transient(self.root)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Overview tab
        overview_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        
        overview_text = tk.Text(overview_tab, wrap=tk.WORD, font=("Courier New", 9))
        overview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Exams tab
        exams_tab = ttk.Frame(notebook)
        notebook.add(exams_tab, text="Exams")
        
        exams_text = tk.Text(exams_tab, wrap=tk.WORD, font=("Courier New", 9))
        exams_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        try:
            cursor = self.db_ops.db.conn.cursor()
            
            # Overview tab
            overview_text.insert(tk.END, "SYSTEM OVERVIEW\n")
            overview_text.insert(tk.END, "=" * 60 + "\n\n")
            
            # Get all stats
            cursor.execute("SELECT COUNT(*) FROM exams")
            exam_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM answer_keys")
            key_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM templates")
            template_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM students")
            student_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM graded_sheets")
            graded_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(percentage) FROM graded_sheets WHERE percentage > 0")
            avg_percentage = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(score), SUM(max_score) FROM graded_sheets")
            total_scores = cursor.fetchone()
            total_score = total_scores[0] or 0
            total_max = total_scores[1] or 0
            
            # Display overview
            overview_text.insert(tk.END, f"Total Exams:            {exam_count:>10}\n")
            overview_text.insert(tk.END, f"Total Answer Keys:      {key_count:>10}\n")
            overview_text.insert(tk.END, f"Total Templates:        {template_count:>10}\n")
            overview_text.insert(tk.END, f"Total Students:         {student_count:>10}\n")
            overview_text.insert(tk.END, f"Total Graded Sheets:    {graded_count:>10}\n")
            overview_text.insert(tk.END, f"Average Score:          {avg_percentage:>9.1f}%\n")
            overview_text.insert(tk.END, f"Total Points Scored:    {total_score:>10.1f} / {total_max:10.1f}\n")
            overview_text.insert(tk.END, f"Overall Percentage:     {(total_score/total_max*100 if total_max>0 else 0):>9.1f}%\n")
            
            # Exams tab
            exams_text.insert(tk.END, "EXAM SUMMARY\n")
            exams_text.insert(tk.END, "=" * 80 + "\n\n")
            
            # Get exam summary from view
            cursor.execute("SELECT * FROM exam_summary ORDER BY exam_name")
            exam_summaries = cursor.fetchall()
            
            if exam_summaries:
                for exam in exam_summaries:
                    exam_name = exam['exam_name']
                    total_students = exam['total_students'] or 0
                    avg_score = exam['avg_score'] or 0
                    avg_percentage = exam['avg_percentage'] or 0
                    
                    exams_text.insert(tk.END, f"{exam_name[:30]:30s} | Students: {total_students:3d} | "
                                            f"Avg Score: {avg_score:5.1f} | Avg %: {avg_percentage:5.1f}%\n")
            else:
                exams_text.insert(tk.END, "No exams found\n")
            
        except Exception as e:
            overview_text.insert(tk.END, f"\nError: {e}")
            exams_text.insert(tk.END, f"\nError: {e}")
        
        overview_text.config(state=tk.DISABLED)
        exams_text.config(state=tk.DISABLED)
    
    def show_help(self):
        """Show help information"""
        help_text = """
ANSWER SHEET GRADING SYSTEM - QUICK HELP

GETTING STARTED:
1. SHEETS & TEMPLATES: Create blank answer sheets and extract templates
2. EXAMS & ANSWER KEYS: Create exams with multiple answer keys (A-E)
3. GRADE SHEETS: Grade filled answer sheets automatically
4. ANALYTICS: View detailed statistics and performance data

FEATURES:
• Support for MCQ and written questions
• Multiple answer key versions per exam
• Student performance tracking
• Detailed analytics and reports

TIPS:
• Use good quality scans (300 DPI recommended)
• Ensure sheets are well-lit and flat
• Use dark pencil or pen for filling bubbles
• Keep answer keys organized by exam

For detailed documentation, see the docs/ folder.
        """
        messagebox.showinfo("Help", help_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = (
            "Answer Sheet Grading System\n"
            "Version 2.1 (New Schema)\n\n"
            "A comprehensive system for creating, managing,\n"
            "and grading multiple-choice and written answer sheets.\n\n"
            "Features:\n"
            "• Support for MCQ and written questions\n"
            "• Exam management with multiple keys (A-E)\n"
            "• Student performance tracking\n"
            "• Detailed analytics\n\n"
            "Built with Python, OpenCV, SQLite, and Tkinter"
        )
        messagebox.showinfo("About", about_text)


def create_home_screen(root=None, screen_manager=None):
    """
    Create and return home screen
    
    Args:
        root: Tkinter root window (creates new if None)
        screen_manager: ScreenManager instance
        
    Returns:
        HomeScreen instance
    """
    if root is None:
        root = tk.Tk()
    
    home = HomeScreen(root, screen_manager)
    return home


if __name__ == "__main__":
    # Standalone mode
    root = tk.Tk()
    home = create_home_screen(root)
    root.mainloop()