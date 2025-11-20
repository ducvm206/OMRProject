"""
File utilities module
Handles file operations, path conversions, and file dialogs
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog
import tempfile

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_project_root():
    """Get project root directory"""
    return PROJECT_ROOT


def to_relative_path(absolute_path):
    """
    Convert absolute path to relative path from project root
    
    Args:
        absolute_path: Absolute file path
        
    Returns:
        Relative path from project root
    """
    try:
        return os.path.relpath(absolute_path, PROJECT_ROOT)
    except ValueError:
        # If paths are on different drives (Windows), return absolute path
        return absolute_path


def to_absolute_path(relative_path):
    """
    Convert relative path to absolute path from project root
    
    Args:
        relative_path: Relative file path from project root
        
    Returns:
        Absolute file path
    """
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(PROJECT_ROOT, relative_path)


def ensure_directory(directory):
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory: Directory path to ensure exists
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create directory {directory}: {e}")
        return False


def select_file(title, filetypes, initial_dir=None, return_relative=True):
    """
    Open file picker dialog and return file path (non-blocking)
    
    Args:
        title: Dialog title
        filetypes: List of tuples (description, pattern)
        initial_dir: Initial directory to open
        return_relative: If True, return relative path from project root
        
    Returns:
        Selected file path or None if cancelled
    """
    # Use tkinter's built-in dialog directly (it's already non-blocking)
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    start_dir = initial_dir or os.getcwd()
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes,
        initialdir=start_dir
    )
    root.destroy()
    
    if file_path:
        return to_relative_path(file_path) if return_relative else file_path
    return None


def select_files(title, filetypes, initial_dir=None, return_relative=True):
    """
    Open file picker dialog for multiple files
    
    Args:
        title: Dialog title
        filetypes: List of tuples (description, pattern)
        initial_dir: Initial directory to open
        return_relative: If True, return relative paths from project root
        
    Returns:
        List of selected file paths or empty list if cancelled
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    start_dir = initial_dir or os.getcwd()
    selected = filedialog.askopenfilenames(
        title=title,
        filetypes=filetypes,
        initialdir=start_dir
    )
    root.destroy()
    
    if return_relative:
        return [to_relative_path(f) for f in selected]
    return list(selected)


def select_directory(title, initial_dir=None, return_relative=True):
    """
    Open directory picker dialog
    
    Args:
        title: Dialog title
        initial_dir: Initial directory to open
        return_relative: If True, return relative path from project root
        
    Returns:
        Selected directory path or None if cancelled
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    start_dir = initial_dir or os.getcwd()
    dir_path = filedialog.askdirectory(
        title=title,
        initialdir=start_dir
    )
    root.destroy()
    
    if dir_path:
        return to_relative_path(dir_path) if return_relative else dir_path
    return None


def save_file_dialog(title, defaultextension, filetypes, initialfile=None, 
                     initialdir=None, return_relative=True):
    """
    Open save file dialog
    
    Args:
        title: Dialog title
        defaultextension: Default file extension (e.g., ".json")
        filetypes: List of tuples (description, pattern)
        initialfile: Default filename
        initialdir: Initial directory to open
        return_relative: If True, return relative path from project root
        
    Returns:
        Selected file path or None if cancelled
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    start_dir = initialdir or os.getcwd()
    file_path = filedialog.asksaveasfilename(
        title=title,
        defaultextension=defaultextension,
        filetypes=filetypes,
        initialfile=initialfile,
        initialdir=start_dir
    )
    root.destroy()
    
    if file_path:
        # Ensure extension
        if not file_path.lower().endswith(defaultextension):
            file_path += defaultextension
        
        return to_relative_path(file_path) if return_relative else file_path
    return None


def create_temp_file(suffix='.tmp', prefix='temp_', directory=None):
    """
    Create a temporary file
    
    Args:
        suffix: File suffix/extension
        prefix: File prefix
        directory: Directory to create temp file in
        
    Returns:
        Path to temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        prefix=prefix,
        dir=directory
    )
    temp_file.close()
    return temp_file.name


def cleanup_temp_files(file_list):
    """
    Clean up temporary files
    
    Args:
        file_list: List of file paths to delete
    """
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"[WARNING] Failed to delete temp file {file_path}: {e}")


def sanitize_filename(filename):
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters for Windows/Unix filesystems
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def get_file_extension(filename):
    """
    Get file extension
    
    Args:
        filename: Filename or path
        
    Returns:
        File extension including the dot (e.g., ".pdf")
    """
    return os.path.splitext(filename)[1]


def get_filename_without_extension(filename):
    """
    Get filename without extension
    
    Args:
        filename: Filename or path
        
    Returns:
        Filename without extension
    """
    return os.path.splitext(os.path.basename(filename))[0]


def list_files_in_directory(directory, extensions=None, recursive=False):
    """
    List files in directory, optionally filtered by extension
    
    Args:
        directory: Directory path
        extensions: List of extensions to filter (e.g., ['.pdf', '.json'])
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    files = []
    
    try:
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if extensions is None or get_file_extension(filename) in extensions:
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    if extensions is None or get_file_extension(filename) in extensions:
                        files.append(filepath)
    except Exception as e:
        print(f"[ERROR] Failed to list files in {directory}: {e}")
    
    return files


def file_exists(filepath):
    """
    Check if file exists
    
    Args:
        filepath: File path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return os.path.isfile(filepath)


def get_file_size(filepath):
    """
    Get file size in bytes
    
    Args:
        filepath: File path
        
    Returns:
        File size in bytes or 0 if file doesn't exist
    """
    try:
        return os.path.getsize(filepath)
    except:
        return 0


def get_file_modified_time(filepath):
    """
    Get file last modified time
    
    Args:
        filepath: File path
        
    Returns:
        Modified time as datetime object or None if error
    """
    try:
        import datetime
        timestamp = os.path.getmtime(filepath)
        return datetime.datetime.fromtimestamp(timestamp)
    except:
        return None