import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# Fix project root path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def create_home_screen():
    """Main menu screen for the Answer Sheet Grading System"""
    
    root = tk.Tk()
    root.title("Answer Sheet Grading System - Main Menu")
    root.geometry("900x750")
    root.resizable(True, True)
    
    # Configure modern style (matching other screens)
    style = ttk.Style()
    style.theme_use('clam')
    
    # Color scheme (consistent with other screens)
    BG_COLOR = "#f5f5f5"
    CARD_COLOR = "#ffffff"
    ACCENT_COLOR = "#0078d4"
    SUCCESS_COLOR = "#28a745"
    
    style.configure("TFrame", background=BG_COLOR)
    style.configure("TLabel", background=BG_COLOR, font=("Segoe UI", 10))
    style.configure("Title.TLabel", background=BG_COLOR, font=("Segoe UI", 16, "bold"))
    style.configure("Subtitle.TLabel", background=BG_COLOR, font=("Segoe UI", 11, "bold"))
    style.configure("Card.TFrame", background=CARD_COLOR, relief="flat")
    style.configure("TButton", font=("Segoe UI", 10), padding=8)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
    style.configure("MenuButton.TButton", font=("Segoe UI", 11, "bold"), padding=12)
    
    root.configure(bg=BG_COLOR)
    
    # Main container
    main_container = tk.Frame(root, bg=BG_COLOR)
    main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title section
    title_label = tk.Label(
        main_container,
        text="📋 Answer Sheet Grading System",
        font=("Segoe UI", 16, "bold"),
        bg=BG_COLOR,
        fg="#333"
    )
    title_label.pack(pady=(0, 30))
    
    # Main features card
    main_card = tk.Frame(main_container, bg=CARD_COLOR, relief="flat")
    main_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    
    main_inner = tk.Frame(main_card, bg=CARD_COLOR)
    main_inner.pack(fill=tk.BOTH, padx=20, pady=20)
    
    tk.Label(main_inner, text="✨ Main Features",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 20))
    
    # Menu functions
    def open_create_sheet():
        try:
            root.withdraw()
            from flows.create_sheet import create_integrated_gui
            create_integrated_gui()
            root.deiconify()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Sheet Creator:\n{e}")
            root.deiconify()
    
    def open_create_key():
        try:
            root.withdraw()
            from flows.create_key import create_key
            create_key()
            root.deiconify()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Key Creator:\n{e}")
            root.deiconify()
    
    def open_grade_sheet():
        try:
            root.withdraw()
            from flows.grade_sheet import grade_sheet_gui
            grade_window = grade_sheet_gui()
            grade_window.mainloop()
            root.deiconify()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Grading:\n{e}")
            root.deiconify()
    
    def open_database_viewer():
        messagebox.showinfo("Coming Soon", 
            "Database viewer feature is under development!\n\n"
            "This will allow you to:\n"
            "• Browse grading history\n"
            "• View student statistics\n"
            "• Analyze question difficulty\n"
            "• Export reports")
    
    def open_settings():
        messagebox.showinfo("Settings", 
            "Settings panel coming soon!\n\n"
            "Future features:\n"
            "• Default configurations\n"
            "• Theme preferences\n"
            "• Export settings\n"
            "• Database management")
    
    def show_about():
        about_text = """Answer Sheet Grading System
Version 1.0

A comprehensive tool for creating, managing, and grading 
multiple-choice answer sheets.

Features:
• Generate custom answer sheets (PDF)
• Extract templates automatically
• Create answer keys manually or by scanning
• Grade single sheets or batch folders
• Store results in SQLite database
• Detailed question-level analysis

Database: grading_system.db
Templates: template/
Answer Keys: answer_keys/
Filled Sheets: filled_sheets/

Developed with Python + Tkinter + OpenCV"""
        
        messagebox.showinfo("About", about_text)
    
    # Create Sheet button
    sheet_frame = tk.Frame(main_inner, bg=CARD_COLOR)
    sheet_frame.pack(fill=tk.X, pady=(0, 15))
    
    tk.Label(sheet_frame, text="📄", font=("Segoe UI", 24), bg=CARD_COLOR).pack(side=tk.LEFT, padx=(0, 15))
    
    sheet_text_frame = tk.Frame(sheet_frame, bg=CARD_COLOR)
    sheet_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    tk.Label(sheet_text_frame, text="Create Answer Sheet",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333", anchor="w").pack(fill=tk.X)
    tk.Label(sheet_text_frame, text="Generate blank answer sheets and extract templates",
            font=("Segoe UI", 9), bg=CARD_COLOR, fg="#666", anchor="w").pack(fill=tk.X)
    
    ttk.Button(sheet_frame, text="Open", command=open_create_sheet,
              style="MenuButton.TButton", width=12).pack(side=tk.RIGHT, padx=(15, 0))
    
    ttk.Separator(main_inner, orient='horizontal').pack(fill=tk.X, pady=15)
    
    # Create Key button
    key_frame = tk.Frame(main_inner, bg=CARD_COLOR)
    key_frame.pack(fill=tk.X, pady=(0, 15))
    
    tk.Label(key_frame, text="🔑", font=("Segoe UI", 24), bg=CARD_COLOR).pack(side=tk.LEFT, padx=(0, 15))
    
    key_text_frame = tk.Frame(key_frame, bg=CARD_COLOR)
    key_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    tk.Label(key_text_frame, text="Create Answer Key",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333", anchor="w").pack(fill=tk.X)
    tk.Label(key_text_frame, text="Create answer keys manually or by scanning master sheets",
            font=("Segoe UI", 9), bg=CARD_COLOR, fg="#666", anchor="w").pack(fill=tk.X)
    
    ttk.Button(key_frame, text="Open", command=open_create_key,
              style="MenuButton.TButton", width=12).pack(side=tk.RIGHT, padx=(15, 0))
    
    ttk.Separator(main_inner, orient='horizontal').pack(fill=tk.X, pady=15)
    
    # Grade Sheets button
    grade_frame = tk.Frame(main_inner, bg=CARD_COLOR)
    grade_frame.pack(fill=tk.X, pady=(0, 15))
    
    tk.Label(grade_frame, text="📊", font=("Segoe UI", 24), bg=CARD_COLOR).pack(side=tk.LEFT, padx=(0, 15))
    
    grade_text_frame = tk.Frame(grade_frame, bg=CARD_COLOR)
    grade_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    tk.Label(grade_text_frame, text="Grade Answer Sheets",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333", anchor="w").pack(fill=tk.X)
    tk.Label(grade_text_frame, text="Grade single sheets or batch process entire folders",
            font=("Segoe UI", 9), bg=CARD_COLOR, fg="#666", anchor="w").pack(fill=tk.X)
    
    ttk.Button(grade_frame, text="Open", command=open_grade_sheet,
              style="MenuButton.TButton", width=12).pack(side=tk.RIGHT, padx=(15, 0))
    
    # Additional tools card
    tools_card = tk.Frame(main_container, bg=CARD_COLOR, relief="flat")
    tools_card.pack(fill=tk.X, pady=(0, 15))
    
    tools_inner = tk.Frame(tools_card, bg=CARD_COLOR)
    tools_inner.pack(fill=tk.BOTH, padx=20, pady=20)
    
    tk.Label(tools_inner, text="🔧 Additional Tools",
            font=("Segoe UI", 11, "bold"), bg=CARD_COLOR, fg="#333").pack(anchor="w", pady=(0, 15))
    
    # Tools buttons in a row
    tools_buttons_frame = tk.Frame(tools_inner, bg=CARD_COLOR)
    tools_buttons_frame.pack(fill=tk.X)
    
    # Database viewer button
    db_btn_frame = tk.Frame(tools_buttons_frame, bg=CARD_COLOR)
    db_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    
    ttk.Button(db_btn_frame, text="💾 View Database", command=open_database_viewer,
              width=20).pack(fill=tk.X, pady=2)
    tk.Label(db_btn_frame, text="Browse history & stats",
            font=("Segoe UI", 8), bg=CARD_COLOR, fg="#999").pack()
    
    # Settings button
    settings_btn_frame = tk.Frame(tools_buttons_frame, bg=CARD_COLOR)
    settings_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
    
    ttk.Button(settings_btn_frame, text="⚙️ Settings", command=open_settings,
              width=20).pack(fill=tk.X, pady=2)
    tk.Label(settings_btn_frame, text="Configure preferences",
            font=("Segoe UI", 8), bg=CARD_COLOR, fg="#999").pack()
    
    # About button
    about_btn_frame = tk.Frame(tools_buttons_frame, bg=CARD_COLOR)
    about_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
    
    ttk.Button(about_btn_frame, text="ℹ️ About", command=show_about,
              width=20).pack(fill=tk.X, pady=2)
    tk.Label(about_btn_frame, text="System information",
            font=("Segoe UI", 8), bg=CARD_COLOR, fg="#999").pack()
    
    # Status card
    status_card = tk.Frame(main_container, bg=CARD_COLOR, relief="flat")
    status_card.pack(fill=tk.X)
    
    status_inner = tk.Frame(status_card, bg=CARD_COLOR)
    status_inner.pack(fill=tk.BOTH, padx=20, pady=15)
    
    # Database status
    db_status_label = tk.Label(
        status_inner,
        text="",
        font=("Segoe UI", 9),
        bg=CARD_COLOR,
        fg="#666"
    )
    db_status_label.pack(side=tk.LEFT)
    
    # Check database connection
    def check_database():
        try:
            from core.database import GradingDatabase
            db = GradingDatabase()
            # Test connection by trying a simple query
            cursor = db.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sheets'")
            result = cursor.fetchone()
            if result:
                db_status_label.config(text="✅ Database connected", fg="green")
            else:
                db_status_label.config(text="⚠️ Database not initialized", fg="orange")
            db.close()
        except Exception as e:
            db_status_label.config(text="❌ Database unavailable", fg="red")
    
    root.after(500, check_database)
    
    # Version label
    version_label = tk.Label(
        status_inner,
        text="v1.0",
        font=("Segoe UI", 8),
        bg=CARD_COLOR,
        fg="#999"
    )
    version_label.pack(side=tk.RIGHT, padx=(0, 10))
    
    # Exit button
    exit_btn = ttk.Button(
        status_inner,
        text="Exit",
        command=root.quit,
        width=10
    )
    exit_btn.pack(side=tk.RIGHT)
    
    return root

if __name__ == "__main__":
    root = create_home_screen()
    root.mainloop()