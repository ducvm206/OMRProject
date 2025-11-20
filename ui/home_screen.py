"""
Home Screen - Main Dashboard
Entry point for the Answer Sheet Grading System
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
        
        # Don't resize if already set by app
        if not self.root.winfo_width() > 1:
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
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # Header
        self.create_header(main_container)
        
        # Main action cards
        self.create_action_cards(main_container)
        
        # Statistics section
        self.create_statistics_section(main_container)
        
        # Footer
        self.create_footer(main_container)
    
    def create_header(self, parent):
        """Create application header"""
        header_frame = tk.Frame(parent, bg=self.BG_COLOR)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Title
        title_label = ttk.Label(header_frame, 
                               text="📋 Answer Sheet Grading System",
                               style="Title.TLabel")
        title_label.pack()
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame,
                                  text="Create, manage, and grade multiple-choice answer sheets",
                                  style="Subtitle.TLabel")
        subtitle_label.pack(pady=(5, 0))
    
    def create_action_cards(self, parent):
        """Create main action cards"""
        cards_frame = tk.Frame(parent, bg=self.BG_COLOR)
        cards_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create grid of cards
        actions = [
            {
                'title': '📄 Create Answer Sheet',
                'description': 'Generate blank answer sheets\nand extract templates',
                'command': self.open_sheet_creator,
                'color': '#e3f2fd'
            },
            {
                'title': '🔑 Create Answer Key',
                'description': 'Define correct answers\nfor your exams',
                'command': self.open_key_creator,
                'color': '#f3e5f5'
            },
            {
                'title': '📊 Grade Sheets',
                'description': 'Grade filled answer sheets\nand view results',
                'command': self.open_grading,
                'color': '#e8f5e9'
            }
        ]
        
        for i, action in enumerate(actions):
            self.create_action_card(cards_frame, action, row=0, col=i)
    
    def create_action_card(self, parent, action, row, col):
        """Create a single action card"""
        card = tk.Frame(parent, bg=action['color'], relief="solid", borderwidth=1)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Configure grid weights
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        
        # Card content
        content = tk.Frame(card, bg=action['color'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(content, 
                              text=action['title'],
                              font=("Segoe UI", 14, "bold"),
                              bg=action['color'],
                              fg="#333")
        title_label.pack(pady=(0, 10))
        
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
    
    def create_statistics_section(self, parent):
        """Create statistics section"""
        stats_frame = tk.Frame(parent, bg=self.CARD_COLOR, relief="solid", borderwidth=1)
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        stats_inner = tk.Frame(stats_frame, bg=self.CARD_COLOR)
        stats_inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        # Title
        tk.Label(stats_inner,
                text="📈 Quick Statistics",
                font=("Segoe UI", 12, "bold"),
                bg=self.CARD_COLOR,
                fg="#333").pack(anchor="w", pady=(0, 10))
        
        # Stats grid
        stats_grid = tk.Frame(stats_inner, bg=self.CARD_COLOR)
        stats_grid.pack(fill=tk.X)
        
        # Get statistics from database
        stats = self.get_statistics()
        
        stat_items = [
            ('Templates', stats['templates'], '📋'),
            ('Answer Keys', stats['answer_keys'], '🔑'),
            ('Students', stats['students'], '👥'),
            ('Graded Sheets', stats['graded_sheets'], '✓')
        ]
        
        for i, (label, value, icon) in enumerate(stat_items):
            stat_card = tk.Frame(stats_grid, bg="#f8f9fa", relief="flat")
            stat_card.grid(row=0, column=i, padx=5, sticky="ew")
            stats_grid.grid_columnconfigure(i, weight=1)
            
            # Icon and value
            tk.Label(stat_card,
                    text=f"{icon} {value}",
                    font=("Segoe UI", 16, "bold"),
                    bg="#f8f9fa",
                    fg=self.ACCENT_COLOR).pack(pady=(10, 5))
            
            # Label
            tk.Label(stat_card,
                    text=label,
                    font=("Segoe UI", 9),
                    bg="#f8f9fa",
                    fg="#666").pack(pady=(0, 10))
    
    def create_footer(self, parent):
        """Create footer with tools and info"""
        footer_frame = tk.Frame(parent, bg=self.BG_COLOR)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Left side - Tools
        left_frame = tk.Frame(footer_frame, bg=self.BG_COLOR)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame,
                  text="🗄️ Database Info",
                  command=self.show_database_info).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(left_frame,
                  text="📊 View Statistics",
                  command=self.show_detailed_statistics).pack(side=tk.LEFT, padx=5)
        
        # Right side - Info
        right_frame = tk.Frame(footer_frame, bg=self.BG_COLOR)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame,
                  text="❓ Help",
                  command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(right_frame,
                  text="ℹ️ About",
                  command=self.show_about).pack(side=tk.LEFT, padx=5)
    
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
            'templates': 0,
            'answer_keys': 0,
            'students': 0,
            'graded_sheets': 0
        }
        
        if self.db_ops.is_connected():
            try:
                cursor = self.db_ops.db.conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM templates")
                stats['templates'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM answer_keys")
                stats['answer_keys'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM students")
                stats['students'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM graded_sheets")
                stats['graded_sheets'] = cursor.fetchone()[0]
                
            except Exception as e:
                print(f"[HOME] Error getting statistics: {e}")
        
        return stats
    
    def open_sheet_creator(self):
        """Open sheet creation screen"""
        self.screen_manager.open_screen('sheet')
    
    def open_key_creator(self):
        """Open answer key creation screen"""
        self.screen_manager.open_screen('key')
    
    def open_grading(self):
        """Open grading screen"""
        self.screen_manager.open_screen('grading')
    
    def show_database_info(self):
        """Show database information"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        info_window = tk.Toplevel(self.root)
        info_window.title("Database Information")
        info_window.geometry("500x400")
        info_window.transient(self.root)
        
        text = tk.Text(info_window, wrap=tk.WORD, font=("Courier New", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        try:
            cursor = self.db_ops.db.conn.cursor()
            
            text.insert(tk.END, "DATABASE INFORMATION\n")
            text.insert(tk.END, "=" * 50 + "\n\n")
            
            db_path = os.path.join(PROJECT_ROOT, 'grading_system.db')
            text.insert(tk.END, f"Location: {db_path}\n")
            
            if os.path.exists(db_path):
                size_mb = os.path.getsize(db_path) / (1024 * 1024)
                text.insert(tk.END, f"Size: {size_mb:.2f} MB\n\n")
            
            text.insert(tk.END, "TABLES\n")
            text.insert(tk.END, "-" * 50 + "\n")
            
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
                text.insert(tk.END, f"{table_name:20s} {count:>10,} records\n")
            
        except Exception as e:
            text.insert(tk.END, f"\nError: {e}")
        
        text.config(state=tk.DISABLED)
    
    def show_detailed_statistics(self):
        """Show detailed statistics window"""
        if not self.db_ops.is_connected():
            messagebox.showerror("Error", "Database not connected")
            return
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Detailed Statistics")
        stats_window.geometry("700x500")
        stats_window.transient(self.root)
        
        text = tk.Text(stats_window, wrap=tk.WORD, font=("Courier New", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        try:
            cursor = self.db_ops.db.conn.cursor()
            
            text.insert(tk.END, "DETAILED STATISTICS\n")
            text.insert(tk.END, "=" * 60 + "\n\n")
            
            # Recent activity
            text.insert(tk.END, "Recent Grading Activity:\n")
            text.insert(tk.END, "-" * 60 + "\n")
            
            cursor.execute("SELECT * FROM recent_grades LIMIT 10")
            recent = cursor.fetchall()
            
            if recent:
                for record in recent:
                    student_id = record['student_id']
                    percentage = record['percentage']
                    exam_name = record['exam_name'] if 'exam_name' in record.keys() else 'N/A'
                    text.insert(tk.END, f"{student_id:10s} {percentage:5.1f}% {exam_name}\n")
            else:
                text.insert(tk.END, "No grading activity yet.\n")
            
            # Student performance
            text.insert(tk.END, "\n\nTop Students:\n")
            text.insert(tk.END, "-" * 60 + "\n")
            
            cursor.execute("""
                SELECT student_id, avg_percentage, total_exams 
                FROM student_performance 
                ORDER BY avg_percentage DESC 
                LIMIT 10
            """)
            
            students = cursor.fetchall()
            
            if students:
                for student in students:
                    sid = student['student_id']
                    avg = student['avg_percentage'] or 0
                    exams = student['total_exams']
                    text.insert(tk.END, f"{sid:10s} {avg:5.1f}% ({exams} exams)\n")
            else:
                text.insert(tk.END, "No student data available.\n")
            
        except Exception as e:
            text.insert(tk.END, f"\nError: {e}")
        
        text.config(state=tk.DISABLED)
    
    def show_help(self):
        """Show help information"""
        help_text = """
ANSWER SHEET GRADING SYSTEM - QUICK HELP

GETTING STARTED:
1. Click "Create Answer Sheet" to generate blank sheets
2. Click "Create Answer Key" to define correct answers
3. Click "Grade Sheets" to grade filled answer sheets

TIPS:
• Use good quality scans (300 DPI recommended)
• Ensure sheets are well-lit and flat
• Use dark pencil or pen for filling bubbles

For detailed help, see the documentation.
        """
        messagebox.showinfo("Help", help_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = (
            "Answer Sheet Grading System\n"
            "Version 2.0\n\n"
            "A comprehensive system for creating, managing,\n"
            "and grading multiple-choice answer sheets.\n\n"
            "Built with Python, OpenCV, and Tkinter"
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