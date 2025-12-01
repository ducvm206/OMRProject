"""
File utilities module
Handles file operations, path conversions, and file dialogs
"""

import os
import tkinter as tk
from tkinter import filedialog
import tempfile


# -------------------------------------------------
# Project root directories
# -------------------------------------------------

# root = project_root/utils/file_utils.py → go 2 levels up to project root
PROJECT_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_ROOT = os.path.join(PROJECT_BASE, "files")

BLANK_SHEETS_DIR = os.path.join(FILES_ROOT, "blank_sheets")
TEMPLATE_DIR = os.path.join(FILES_ROOT, "template")
ANSWER_KEYS_DIR = os.path.join(FILES_ROOT, "answer_keys")


def get_project_root():
    """Return the base files root directory"""
    return FILES_ROOT


# -------------------------------------------------
# Path Conversion
# -------------------------------------------------

def to_relative_path(absolute_path):
    """
    Convert absolute path to relative path from files/ root
    """
    try:
        return os.path.relpath(absolute_path, FILES_ROOT)
    except ValueError:
        return absolute_path  # Different drive (Windows)


def to_absolute_path(relative_path):
    """
    Convert relative path to absolute path from files/ root
    """
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(FILES_ROOT, relative_path)


# -------------------------------------------------
# Directory Management
# -------------------------------------------------

def ensure_directory(directory):
    """Ensure directory exists"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create directory {directory}: {e}")
        return False


# -------------------------------------------------
# File Dialog Helpers
# -------------------------------------------------

def _setup_tk_root():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def select_file(title, filetypes, initial_dir=None, return_relative=True):
    root = _setup_tk_root()
    start_dir = initial_dir or FILES_ROOT

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
    root = _setup_tk_root()
    start_dir = initial_dir or FILES_ROOT

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
    root = _setup_tk_root()
    start_dir = initial_dir or FILES_ROOT

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

    root = _setup_tk_root()
    start_dir = initialdir or FILES_ROOT

    file_path = filedialog.asksaveasfilename(
        title=title,
        defaultextension=defaultextension,
        filetypes=filetypes,
        initialfile=initialfile,
        initialdir=start_dir
    )
    root.destroy()

    if file_path:
        if not file_path.lower().endswith(defaultextension):
            file_path += defaultextension

        return to_relative_path(file_path) if return_relative else file_path
    return None


# -------------------------------------------------
# Temp Files
# -------------------------------------------------

def create_temp_file(suffix=".tmp", prefix="temp_", directory=None):
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        prefix=prefix,
        dir=directory or FILES_ROOT
    )
    temp_file.close()
    return temp_file.name


def cleanup_temp_files(file_list):
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"[WARNING] Failed to delete temp file {file_path}: {e}")


# -------------------------------------------------
# Filename Utilities
# -------------------------------------------------

def sanitize_filename(filename):
    import re
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def get_file_extension(filename):
    return os.path.splitext(filename)[1]


def get_filename_without_extension(filename):
    return os.path.splitext(os.path.basename(filename))[0]


# -------------------------------------------------
# Directory Listing
# -------------------------------------------------

def list_files_in_directory(directory, extensions=None, recursive=False):
    files = []
    directory = to_absolute_path(directory)

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


# -------------------------------------------------
# File Info
# -------------------------------------------------

def file_exists(filepath):
    return os.path.isfile(to_absolute_path(filepath))


def get_file_size(filepath):
    try:
        return os.path.getsize(to_absolute_path(filepath))
    except:
        return 0


def get_file_modified_time(filepath):
    try:
        import datetime
        timestamp = os.path.getmtime(to_absolute_path(filepath))
        return datetime.datetime.fromtimestamp(timestamp)
    except:
        return None
