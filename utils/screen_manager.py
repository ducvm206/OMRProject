"""
Screen Manager
Handles navigation between different screens in the application
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox
import subprocess

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class ScreenManager:
    """Manages screen transitions and window state"""
    
    def __init__(self, root):
        """
        Initialize screen manager
        
        Args:
            root: Main Tkinter root window
        """
        self.root = root
        self.current_screen = None
        self.screen_history = []
        
    def open_screen(self, screen_name):
        """
        Open a screen in a new window (independent)
        
        Args:
            screen_name: Name of screen to open ('key', 'sheet', 'grading')
        """
        try:
            if screen_name == 'key':
                self._open_key_screen()
            elif screen_name == 'sheet':
                self._open_sheet_screen()
            elif screen_name == 'grading':
                self._open_grading_screen()
            else:
                messagebox.showerror("Error", f"Unknown screen: {screen_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {screen_name} screen:\n{e}")
    
    def _open_key_screen(self):
        """Open answer key creation in new window"""
        try:
            # Import and create in new window
            from ui.key_ui import AnswerKeyUI
            
            new_window = tk.Toplevel(self.root)
            key_ui = AnswerKeyUI(new_window)
            
            # Don't call run() - window is already managed by Toplevel
            print("[SCREEN] Answer key window opened")
            
        except Exception as e:
            print(f"[SCREEN] Error opening key screen: {e}")
            raise
    
    def _open_sheet_screen(self):
        """Open sheet generation in new window"""
        try:
            from ui.sheet_ui import SheetGenerationUI
            
            new_window = tk.Toplevel(self.root)
            sheet_ui = SheetGenerationUI(new_window)
            
            print("[SCREEN] Sheet generation window opened")
            
        except Exception as e:
            print(f"[SCREEN] Error opening sheet screen: {e}")
            raise
    
    def _open_grading_screen(self):
        """Open grading in new window"""
        try:
            from ui.grading_ui import GradingUI
            
            new_window = tk.Toplevel(self.root)
            grading_ui = GradingUI(new_window)
            
            print("[SCREEN] Grading window opened")
            
        except Exception as e:
            print(f"[SCREEN] Error opening grading screen: {e}")
            raise
    
    def go_back(self):
        """Go back to previous screen"""
        if self.screen_history:
            previous_screen = self.screen_history.pop()
            self.switch_to(previous_screen, add_to_history=False)
        else:
            messagebox.showinfo("Info", "Already at home screen")
    
    def switch_to(self, screen_name, add_to_history=True):
        """
        Switch to a different screen (replaces current)
        
        Args:
            screen_name: Name of screen to switch to
            add_to_history: Whether to add current screen to history
        """
        if add_to_history and self.current_screen:
            self.screen_history.append(self.current_screen)
        
        # Clear current window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Load new screen
        if screen_name == 'home':
            self._load_home_screen()
        elif screen_name == 'key':
            self._load_key_screen()
        elif screen_name == 'sheet':
            self._load_sheet_screen()
        elif screen_name == 'grading':
            self._load_grading_screen()
        
        self.current_screen = screen_name
    
    def _load_home_screen(self):
        """Load home screen into main window"""
        from ui.home_screen import HomeScreen
        home = HomeScreen(self.root, self)
    
    def _load_key_screen(self):
        """Load answer key screen into main window"""
        from ui.key_ui import AnswerKeyUI
        key_ui = AnswerKeyUI(self.root)
    
    def _load_sheet_screen(self):
        """Load sheet generation screen into main window"""
        from ui.sheet_ui import SheetGenerationUI
        sheet_ui = SheetGenerationUI(self.root)
    
    def _load_grading_screen(self):
        """Load grading screen into main window"""
        from ui.grading_ui import GradingUI
        grading_ui = GradingUI(self.root)


class WindowManager:
    """Manages independent windows for each screen"""
    
    @staticmethod
    def open_independent_window(screen_type):
        """
        Open a screen in completely independent window (subprocess)
        
        Args:
            screen_type: 'key', 'sheet', or 'grading'
        """
        script_map = {
            'key': 'ui/key_ui.py',
            'sheet': 'ui/sheet_ui.py',
            'grading': 'ui/grading_ui.py'
        }
        
        if screen_type not in script_map:
            messagebox.showerror("Error", f"Unknown screen type: {screen_type}")
            return
        
        script_path = os.path.join(PROJECT_ROOT, script_map[screen_type])
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return
        
        try:
            # Launch as separate process
            subprocess.Popen([sys.executable, script_path])
            print(f"[WINDOW] Launched independent {screen_type} window")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch window:\n{e}")


def create_back_button(parent, screen_manager, **kwargs):
    """
    Create a back button for navigation
    
    Args:
        parent: Parent widget
        screen_manager: ScreenManager instance
        **kwargs: Additional button arguments
        
    Returns:
        Button widget
    """
    from tkinter import ttk
    
    btn = ttk.Button(parent, text="← Back to Home", 
                    command=lambda: screen_manager.switch_to('home'),
                    **kwargs)
    return btn


def add_navigation_bar(parent, screen_manager, current_screen):
    """
    Add navigation bar to a screen
    
    Args:
        parent: Parent widget
        screen_manager: ScreenManager instance
        current_screen: Name of current screen
    """
    from tkinter import ttk
    
    nav_frame = ttk.Frame(parent)
    nav_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
    
    # Back button
    ttk.Button(nav_frame, text="← Back to Home",
              command=lambda: screen_manager.switch_to('home')).pack(side=tk.LEFT)
    
    # Current screen indicator
    ttk.Label(nav_frame, text=f"Current: {current_screen.title()}",
             font=("Segoe UI", 9)).pack(side=tk.RIGHT)