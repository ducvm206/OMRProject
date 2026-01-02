import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from dataclasses import dataclass

# Import from flows
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flows.analysis_flow import ExamAnalyzer, ExamStats

@dataclass
class UIExamData:
    """Container for exam data in UI"""
    exam_id: int
    exam_name: str
    key_count: int
    graded_count: int

class ExamAnalysisUI:
    """UI for exam analysis and visualization"""
    
    def __init__(self, parent_frame: tk.Frame, db_path: str = "grading_system.db"):
        self.parent = parent_frame
        self.db_path = db_path
        self.analyzer = ExamAnalyzer(db_path)
        
        self.current_exam_id = None
        self.current_exam_stats = {}
        self.figures = []
        
        # Styling
        self.BG_COLOR = "#f5f5f5"
        self.CARD_COLOR = "#ffffff"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface with consistent styling"""
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabel", background=self.BG_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.CARD_COLOR, relief="flat")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        
        # Main container with custom background
        main_container = tk.Frame(self.parent, bg=self.BG_COLOR)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_container, bg=self.BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(header_frame, text="📊 Exam Analytics Dashboard", 
                 font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg="#333").pack(side="left")
        
        # Exam selection card
        selection_card = tk.Frame(main_container, bg=self.CARD_COLOR)
        selection_card.pack(fill="x", pady=(0, 15))
        
        inner_selection = tk.Frame(selection_card, bg=self.CARD_COLOR)
        inner_selection.pack(fill="both", padx=20, pady=15)
        
        tk.Label(inner_selection, text="📋 Exam Selection",
                 font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        # Selection controls
        control_frame = tk.Frame(inner_selection, bg=self.CARD_COLOR)
        control_frame.pack(fill="x", pady=5)
        
        tk.Label(control_frame, text="Select Exam:", font=("Segoe UI", 9, "bold"),
                bg=self.CARD_COLOR).grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        self.exam_var = tk.StringVar()
        self.exam_combo = ttk.Combobox(control_frame, textvariable=self.exam_var, width=60,
                                      font=("Segoe UI", 9))
        self.exam_combo.grid(row=0, column=1, padx=(0, 10))
        self.exam_combo.bind("<<ComboboxSelected>>", self.on_exam_selected)
        
        ttk.Button(control_frame, text="🔄 Refresh", 
                  command=self.load_exams, style="Accent.TButton").grid(row=0, column=2)
        
        # Histogram controls card
        controls_card = tk.Frame(main_container, bg=self.CARD_COLOR)
        controls_card.pack(fill="x", pady=(0, 15))
        
        inner_controls = tk.Frame(controls_card, bg=self.CARD_COLOR)
        inner_controls.pack(fill="both", padx=20, pady=15)
        
        tk.Label(inner_controls, text="⚙️ Visualization Controls",
                 font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        # Bins control
        bins_frame = tk.Frame(inner_controls, bg=self.CARD_COLOR)
        bins_frame.pack(fill="x", pady=5)
        
        tk.Label(bins_frame, text="Score Histogram Bins:", font=("Segoe UI", 9, "bold"),
                bg=self.CARD_COLOR).pack(side="left", padx=(0, 10))
        
        self.bins_var = tk.IntVar(value=10)
        bins_spinbox = ttk.Spinbox(bins_frame, from_=5, to=50, 
                                   textvariable=self.bins_var, width=10,
                                   font=("Segoe UI", 9))
        bins_spinbox.pack(side="left", padx=(0, 10))
        
        ttk.Button(bins_frame, text="📈 Update Histograms", 
                  command=self.update_histograms, style="Accent.TButton").pack(side="left")
        
        # Create a paned window for figures and stats
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, pady=(0, 15))
        
        # Left panel for figures
        figures_panel = tk.Frame(paned, bg=self.BG_COLOR)
        paned.add(figures_panel, weight=2)
        
        # Right panel for statistics
        stats_panel = tk.Frame(paned, bg=self.BG_COLOR)
        paned.add(stats_panel, weight=1)
        
        # Figures area
        figures_card = tk.Frame(figures_panel, bg=self.CARD_COLOR)
        figures_card.pack(fill="both", expand=True)
        
        inner_figures = tk.Frame(figures_card, bg=self.CARD_COLOR)
        inner_figures.pack(fill="both", expand=True, padx=20, pady=15)
        
        tk.Label(inner_figures, text="📊 Visualizations",
                 font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        self.figures_frame = tk.Frame(inner_figures, bg=self.CARD_COLOR)
        self.figures_frame.pack(fill="both", expand=True)
        
        # Placeholder for figures
        self.figures_placeholder = tk.Label(self.figures_frame, 
                                           text="Select an exam to view visualizations\n\n"
                                                "• Score distribution histograms\n"
                                                "• Per-key comparisons\n"
                                                "• Question analysis",
                                           font=("Segoe UI", 11), bg=self.CARD_COLOR, 
                                           fg="#666", justify=tk.CENTER)
        self.figures_placeholder.pack(expand=True)
        
        # Statistics area
        stats_card = tk.Frame(stats_panel, bg=self.CARD_COLOR)
        stats_card.pack(fill="both", expand=True)
        
        inner_stats = tk.Frame(stats_card, bg=self.CARD_COLOR)
        inner_stats.pack(fill="both", expand=True, padx=20, pady=15)
        
        tk.Label(inner_stats, text="📈 Exam Statistics",
                 font=("Segoe UI", 11, "bold"), bg=self.CARD_COLOR).pack(anchor="w", pady=(0, 10))
        
        # Text area for statistics with scrollbar
        text_frame = tk.Frame(inner_stats, bg=self.CARD_COLOR)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.stats_text = tk.Text(text_frame, height=20, wrap=tk.WORD,
                                 font=("Courier New", 10), bg="#fafafa", relief=tk.FLAT,
                                 yscrollcommand=scrollbar.set)
        self.stats_text.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=self.stats_text.yview)
        
        # Add placeholder text
        self.stats_text.insert("1.0", "Statistics will appear here after selecting an exam...\n\n")
        self.stats_text.insert(tk.END, "Available statistics:\n")
        self.stats_text.insert(tk.END, "• Overall exam statistics\n")
        self.stats_text.insert(tk.END, "• Per-key performance\n")
        self.stats_text.insert(tk.END, "• Score distributions\n")
        self.stats_text.insert(tk.END, "• Percentile analysis\n")
        self.stats_text.insert(tk.END, "• Standard deviation\n")
        self.stats_text.config(state="disabled")
        
        # Initial load
        self.load_exams()
        
    def load_exams(self):
        """Load exams from database"""
        try:
            exams = self.analyzer.get_exams()
            
            exam_names = []
            self.exam_data = {}
            
            for exam in exams:
                exam_obj = UIExamData(
                    exam_id=exam['id'],
                    exam_name=exam['name'],
                    key_count=exam['key_count'],
                    graded_count=exam['graded_count']
                )
                display_name = f"{exam['name']} (ID: {exam['id']}, Keys: {exam['key_count']}, Graded: {exam['graded_count']})"
                exam_names.append(display_name)
                self.exam_data[display_name] = exam_obj
            
            self.exam_combo['values'] = exam_names
            
            if exam_names:
                self.exam_combo.current(0)
                self.on_exam_selected()
                
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load exams: {str(e)}")
    
    def on_exam_selected(self, event=None):
        """Handle exam selection"""
        selected_display = self.exam_var.get()
        if selected_display in self.exam_data:
            exam_data = self.exam_data[selected_display]
            self.current_exam_id = exam_data.exam_id
            self.analyze_exam()
    
    def analyze_exam(self):
        """Perform analysis on selected exam"""
        if self.current_exam_id is None:
            return
        
        try:
            # Calculate statistics
            self.current_exam_stats = self.analyzer.calculate_exam_stats(self.current_exam_id)
            
            # Create histograms
            self.update_histograms()
            
            # Update statistics display
            self.update_stats_display()
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Failed to analyze exam: {str(e)}")
    
    def update_histograms(self):
        """Update the histograms with current settings"""
        if self.current_exam_id is None:
            return
        
        # Remove placeholder
        self.figures_placeholder.pack_forget()
        
        # Clear existing figures
        for widget in self.figures_frame.winfo_children():
            widget.destroy()
        
        self.figures.clear()
        
        # Get bins from UI
        bins = self.bins_var.get()
        
        try:
            # Create comparison histograms
            figures = self.analyzer.create_comparison_histograms(self.current_exam_id, bins)
            
            if not figures:
                tk.Label(self.figures_frame, 
                         text="📊 No data available for this exam\n\n"
                              "Please ensure the exam has been graded and\n"
                              "contains student answer sheets.",
                         font=("Segoe UI", 11), bg=self.CARD_COLOR, 
                         fg="#666", justify=tk.CENTER).pack(expand=True)
                return
            
            # Create notebook for tabbed display
            notebook = ttk.Notebook(self.figures_frame)
            notebook.pack(fill="both", expand=True)
            
            # Style notebook
            style = ttk.Style()
            style.configure("TNotebook", background=self.BG_COLOR)
            style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[10, 5])
            
            # Add a tab for each key + overall
            for key_label, fig in figures:
                tab_frame = tk.Frame(notebook, bg=self.CARD_COLOR)
                notebook.add(tab_frame, text=f"Key {key_label}" if key_label != "Overall" else "📊 Overall")
                
                # Create canvas for matplotlib figure
                canvas = FigureCanvasTkAgg(fig, master=tab_frame)
                canvas.draw()
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.pack(fill="both", expand=True)
                
                # Store reference to prevent garbage collection
                self.figures.append((fig, canvas))
            
        except Exception as e:
            messagebox.showerror("Visualization Error", 
                               f"Failed to create histograms: {str(e)}")
            # Restore placeholder
            self.figures_placeholder.pack(expand=True)
    
    def update_stats_display(self):
        """Update statistics text display"""
        self.stats_text.config(state="normal")
        self.stats_text.delete(1.0, tk.END)
        
        if not self.current_exam_stats:
            self.stats_text.insert(tk.END, "No statistics available.")
            self.stats_text.config(state="disabled")
            return
        
        # Format statistics
        stats_text = "=" * 60 + "\n"
        stats_text += "EXAM STATISTICS SUMMARY\n"
        stats_text += "=" * 60 + "\n\n"
        
        # Overall statistics
        if 'Overall' in self.current_exam_stats:
            overall = self.current_exam_stats['Overall']
            stats_text += f"{'OVERALL STATISTICS':^60}\n"
            stats_text += "-" * 60 + "\n"
            stats_text += f"Total Students: {overall.total_students}\n"
            stats_text += f"Highest Score:  {overall.highest_score:.2f}\n"
            stats_text += f"Lowest Score:   {overall.lowest_score:.2f}\n"
            stats_text += f"Average Score:  {overall.average_score:.2f}\n"
            stats_text += f"Median Score:   {overall.median_score:.2f}\n"
            stats_text += "\n"
        
        # Per-key statistics
        stats_text += f"{'PER-KEY STATISTICS':^60}\n"
        stats_text += "-" * 60 + "\n"
        
        # Sort keys (A, B, C, ... then Overall)
        sorted_keys = sorted([k for k in self.current_exam_stats.keys() if k != 'Overall'])
        if 'Overall' in self.current_exam_stats:
            sorted_keys.append('Overall')
        
        for key_label in sorted_keys:
            stats = self.current_exam_stats[key_label]
            
            stats_text += f"\n[Key {key_label}]\n"
            stats_text += f"  Students:     {stats.total_students}\n"
            stats_text += f"  Highest:      {stats.highest_score:.2f}\n"
            stats_text += f"  Lowest:       {stats.lowest_score:.2f}\n"
            stats_text += f"  Average:      {stats.average_score:.2f}\n"
            stats_text += f"  Median:       {stats.median_score:.2f}\n"
        
        # Additional analysis
        stats_text += "\n" + "=" * 60 + "\n"
        stats_text += "ADDITIONAL ANALYSIS\n"
        stats_text += "=" * 60 + "\n\n"
        
        # Get score distribution
        scores_by_key = self.analyzer.get_student_scores(self.current_exam_id)
        
        if 'Overall' in scores_by_key and scores_by_key['Overall']:
            all_scores = scores_by_key['Overall']
            
            # Score ranges
            stats_text += "Score Distribution:\n"
            stats_text += f"  Total Scores: {len(all_scores)}\n"
            stats_text += f"  Score Range:  {min(all_scores):.2f} - {max(all_scores):.2f}\n"
            
            # Standard deviation
            std_dev = np.std(all_scores)
            stats_text += f"  Std Dev:      {std_dev:.2f}\n"
            
            # Percentiles
            for pct in [25, 50, 75, 90]:
                percentile = np.percentile(all_scores, pct)
                stats_text += f"  {pct}th Percentile: {percentile:.2f}\n"
        
        self.stats_text.insert(tk.END, stats_text)
        
        # Apply text styling
        self.stats_text.tag_add("header", "1.0", "1.60")
        self.stats_text.tag_add("header", "3.0", "3.60")
        self.stats_text.tag_add("header", f"{len(stats_text.splitlines())-2}.0", f"{len(stats_text.splitlines())-2}.60")
        
        self.stats_text.tag_config("header", font=("Courier New", 10, "bold"))
        
        self.stats_text.config(state="disabled")
    
    def cleanup(self):
        """Clean up resources"""
        for fig, canvas in self.figures:
            plt.close(fig)
        self.analyzer.close()


def main():
    """Main function for standalone testing"""
    root = tk.Tk()
    root.title("📈 Exam Analysis System")
    root.geometry("1400x900")
    
    # Set window icon (optional)
    # root.iconbitmap('icon.ico')
    
    # Create main frame with styling
    main_frame = tk.Frame(root, bg="#f5f5f5")
    main_frame.pack(fill="both", expand=True)
    
    # Create analysis UI
    analysis_ui = ExamAnalysisUI(main_frame)
    
    def on_closing():
        analysis_ui.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()