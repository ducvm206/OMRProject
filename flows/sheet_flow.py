"""
Sheet Generation Flow
Business logic for creating answer sheets and extracting templates
Updated for MCQ + Written questions and combined generation
"""
import os
import sys
import json
import datetime

# At top of file (already exists)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_ROOT = os.path.join(PROJECT_ROOT, "files")

BLANK_SHEETS_DIR = os.path.join(FILES_ROOT, "blank_sheets")
TEMPLATES_DIR = os.path.join(FILES_ROOT, "template")
ANSWER_KEYS_DIR = os.path.join(FILES_ROOT, "answer_keys")

if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

from utils.db_operations import get_db_operations
from utils.file_utils import ensure_directory, to_relative_path, sanitize_filename
from utils.validation import validate_number_of_questions, validate_filename


class SheetGenerationFlow:
    """Handles answer sheet generation and template extraction workflow"""
    
    def __init__(self):
        """Initialize the flow"""
        self.db_ops = get_db_operations()
        
        # Configuration
        self.num_mcq_questions = 40
        self.num_written_questions = 0
        self.include_student_id = True
        self.include_key = True  # New: Include KEY area
        self.include_class_info = True
        self.include_timestamp = False
        self.output_directory = "blank_sheets"
        self.filename = None
        
        # Generated outputs
        self.current_pdf_path = None
        self.current_template_json = None
        self.current_sheet_id = None
        self.current_template_id = None
    
    def configure_sheet(self, num_mcq_questions=None, num_written_questions=None, 
                       include_student_id=None, include_key=None,  # Added include_key
                       include_class_info=None, include_timestamp=None):
        """
        Configure sheet parameters
        
        Args:
            num_mcq_questions: Number of MCQ questions
            num_written_questions: Number of written answer questions
            include_student_id: Include student ID field
            include_key: Include KEY area (new parameter)
            include_class_info: Include class information
            include_timestamp: Include timestamp
            
        Returns:
            Tuple of (success, error_message)
        """
        if num_mcq_questions is not None:
            valid, error, parsed = validate_number_of_questions(num_mcq_questions)
            if not valid:
                return False, error
            self.num_mcq_questions = parsed
        
        if num_written_questions is not None:
            valid, error, parsed = validate_number_of_questions(num_written_questions)
            if not valid:
                return False, error
            self.num_written_questions = parsed
        
        if include_student_id is not None:
            self.include_student_id = bool(include_student_id)
        
        if include_key is not None:  # New: Handle include_key
            self.include_key = bool(include_key)
        
        if include_class_info is not None:
            self.include_class_info = bool(include_class_info)
        
        if include_timestamp is not None:
            self.include_timestamp = bool(include_timestamp)
        
        return True, None
    
    def set_output_location(self, directory, filename=None):
        """
        Ensure directory maps correctly to files/* subfolders
        """
        valid_dirs = {
            "blank_sheets": BLANK_SHEETS_DIR,
            "template": TEMPLATES_DIR,
            "answer_keys": ANSWER_KEYS_DIR,
        }

        if directory not in valid_dirs:
            return False, f"Invalid directory '{directory}'. Must be one of: {list(valid_dirs.keys())}"

        self.output_directory = valid_dirs[directory]

        if filename:
            valid, error = validate_filename(filename)
            if not valid:
                return False, error

            filename = sanitize_filename(filename)
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

        self.filename = filename
        return True, None
    
    def generate_sheet(self):
        """
        Generate answer sheet PDF with proper MCQ and written question sections
        using the new designer API.
        
        Returns:
            Tuple of (success, error_message, pdf_path)
        """
        try:
            from core.sheet_maker import AnswerSheetDesigner
            
            # Ensure destination exists in the proper files/* directory
            if not ensure_directory(self.output_directory):
                return False, f"Failed to create directory: {self.output_directory}", None

            # Auto filename if not given
            if not self.filename:
                if self.num_written_questions > 0:
                    self.filename = f"answer_sheet_{self.num_mcq_questions}mcq_{self.num_written_questions}written.pdf"
                else:
                    self.filename = f"answer_sheet_{self.num_mcq_questions}_questions.pdf"

            output_path = os.path.join(self.output_directory, self.filename)
            
            # Create designer
            designer = AnswerSheetDesigner()
            
            # Configure (for student ID, KEY, class info, timestamp)
            designer.set_config(
                include_student_id=self.include_student_id,
                include_key=self.include_key,  # Pass include_key to designer
                include_class_info=self.include_class_info,
                include_timestamp=self.include_timestamp
            )
            
            # Call the new designer API directly
            total_quick_boxes = self.num_written_questions  # assume written questions map to quick number boxes
            designer.create_answer_sheet(
                self.num_mcq_questions,
                output_path,
                format='pdf',
                quick_number_boxes=total_quick_boxes
            )
            
            self.current_pdf_path = output_path
            
            # Save to database
            if self.db_ops.is_connected():
                try:
                    sheet_name = os.path.splitext(self.filename)[0]
                    
                    # Build notes with all configuration info
                    notes_parts = [
                        f"Generated with {self.num_mcq_questions} MCQ + {self.num_written_questions} written questions"
                    ]
                    if not self.include_student_id:
                        notes_parts.append("No Student ID")
                    if not self.include_key:
                        notes_parts.append("No KEY area")
                    if not self.include_class_info:
                        notes_parts.append("No class info")
                    
                    self.current_sheet_id = self.db_ops.save_sheet(
                        file_path=to_relative_path(output_path).replace("\\", "/"),
                        name=sheet_name,
                        notes=" | ".join(notes_parts)
                    )
                    
                    if self.current_sheet_id:
                        print(f"[FLOW] Sheet saved to database (ID: {self.current_sheet_id})")
                    else:
                        print(f"[FLOW] Warning: Failed to save sheet to database")
                        
                except Exception as e:
                    print(f"[FLOW] Database save failed: {e}")
            
            return True, None, output_path
        
        except ImportError as e:
            return False, f"Failed to import sheet_maker: {e}", None
        except Exception as e:
            return False, f"Failed to generate sheet: {e}", None

    
    def extract_template(self, pdf_path=None, dpi=300, show_visualization=True):
        """
        Extract template from generated PDF using the complete template extraction
        
        Args:
            pdf_path: Path to PDF (uses current_pdf_path if None)
            dpi: DPI for image conversion
            show_visualization: Show detection visualizations
            
        Returns:
            Tuple of (success, error_message, template_json_path)
        """
        if pdf_path is None:
            pdf_path = self.current_pdf_path
        
        if not pdf_path or not os.path.exists(pdf_path):
            return False, "No PDF available for extraction", None
        
        try:
            json_path = None
            
            # Option 1: Complete template extraction
            try:
                from core.template_extraction.template_extraction import process_pdf_complete_template
                print("[FLOW] Using complete template extraction")
                json_path = process_pdf_complete_template(
                    pdf_path=pdf_path,
                    dpi=dpi,
                    keep_png=False,
                    show_visualization=show_visualization
                )
            except ImportError as e:
                print(f"[FLOW] Complete template extraction not available: {e}")
                # Option 2: Basic bubble extraction
                try:
                    from core.template_extraction.bubble_extraction import process_pdf_answer_sheet
                    print("[FLOW] Using basic bubble extraction")
                    json_path = process_pdf_answer_sheet(
                        pdf_path=pdf_path,
                        dpi=dpi,
                        keep_png=False,
                        show_visualization=show_visualization
                    )
                except ImportError as e2:
                    print(f"[FLOW] Bubble extraction not available: {e2}")
                    return False, f"Template extraction modules not found: {e2}", None
            
            if not json_path:
                return False, "Template extraction failed - no JSON output", None
            
            # Move JSON file into /files/template
            ensure_directory(TEMPLATES_DIR)

            new_json_path = os.path.join(
                TEMPLATES_DIR,
                sanitize_filename(os.path.basename(json_path))
            )

            os.replace(json_path, new_json_path)
            self.current_template_json = new_json_path
            json_path = new_json_path
            
            # Save template to database
            if self.db_ops.is_connected() and self.current_sheet_id:
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    mcq_questions, written_questions = self._analyze_template_questions(template_data)
                    final_mcq = self.num_mcq_questions
                    final_written = self.num_written_questions
                    has_student_id = self._check_student_id_presence(template_data)
                    has_key = self._check_key_presence(template_data)
                    
                    # FIXED: Store has_key in template_data metadata instead of separate DB column
                    if 'metadata' not in template_data:
                        template_data['metadata'] = {}
                    template_data['metadata']['has_key'] = has_key
                    
                    template_name = f"Template_{os.path.splitext(self.filename)[0]}"
                    
                    # FIXED: Removed has_key parameter - not in DB schema
                    self.current_template_id = self.db_ops.save_template(
                        sheet_id=self.current_sheet_id,
                        name=template_name,
                        json_path=to_relative_path(json_path).replace("\\", "/"),
                        template_data=template_data,  # Contains has_key in metadata
                        multiple_choice_questions=final_mcq,
                        written_answer_questions=final_written,
                        has_student_id=has_student_id
                    )
                    
                    if self.current_template_id:
                        print(f"[FLOW] Template saved to database (ID: {self.current_template_id})")
                    else:
                        print(f"[FLOW] Warning: Failed to save template to database")
                        
                except Exception as e:
                    print(f"[FLOW] Database save failed: {e}")
            
            return True, None, json_path
            
        except Exception as e:
            return False, f"Failed to extract template: {e}", None
    
    def _analyze_template_questions(self, template_data):
        mcq_questions = 0
        written_questions = 0
        
        if any(key.startswith('page_') for key in template_data.keys()):
            for page_key, page_data in template_data.items():
                if page_key.startswith('page_'):
                    bubble_data = page_data.get('bubble_answers', {})
                    if bubble_data and 'questions_detected' in bubble_data:
                        mcq_questions += bubble_data['questions_detected']
                    elif 'questions' in page_data:
                        mcq_questions += len(page_data.get('questions', {}))
                    
                    quick_data = page_data.get('quick_answers', {})
                    if quick_data and 'total_questions' in quick_data:
                        written_questions += quick_data['total_questions']
        else:
            if 'questions' in template_data:
                mcq_questions = len(template_data.get('questions', {}))
            elif 'total_questions' in template_data:
                mcq_questions = template_data.get('total_questions', 0)
        
        if self.num_written_questions > 0:
            written_questions = self.num_written_questions
        if mcq_questions < self.num_mcq_questions:
            mcq_questions = self.num_mcq_questions
        
        return mcq_questions, written_questions
    
    def _check_student_id_presence(self, template_data):
        if any(key.startswith('page_') for key in template_data.keys()):
            for page_key, page_data in template_data.items():
                if page_key.startswith('page_'):
                    bubble_data = page_data.get('bubble_answers', {})
                    if bubble_data and bubble_data.get('student_id'):
                        return True
        elif 'student_id' in template_data:
            return True
        return False
    
    def _check_key_presence(self, template_data):
        """Check if KEY area is present in template data"""
        if any(key.startswith('page_') for key in template_data.keys()):
            for page_key, page_data in template_data.items():
                if page_key.startswith('page_'):
                    if 'key_area' in page_data or 'key_bubbles' in page_data:
                        return True
                    # Also check for key markers or key section
                    for field_key in page_data.keys():
                        if 'key' in field_key.lower():
                            return True
        elif 'key_area' in template_data or 'key_bubbles' in template_data:
            return True
        return False
    
    def generate_and_extract(self, show_visualization=True):
        success, error, pdf_path = self.generate_sheet()
        if not success:
            return False, error, None, None
        
        success, error, template_path = self.extract_template(show_visualization=show_visualization)
        if not success:
            return False, error, pdf_path, None
        
        return True, None, pdf_path, template_path
    
    def get_generation_info(self):
        return {
            'num_mcq_questions': self.num_mcq_questions,
            'num_written_questions': self.num_written_questions,
            'include_student_id': self.include_student_id,
            'include_key': self.include_key,  # Added include_key
            'include_class_info': self.include_class_info,
            'include_timestamp': self.include_timestamp,
            'pdf_path': self.current_pdf_path,
            'template_json_path': self.current_template_json,
            'sheet_id': self.current_sheet_id,
            'template_id': self.current_template_id
        }
    
    def reset(self):
        self.num_mcq_questions = 40
        self.num_written_questions = 0
        self.include_student_id = True
        self.include_key = True  # Reset include_key
        self.include_class_info = True
        self.include_timestamp = False
        self.output_directory = "blank_sheets"
        self.filename = None
        self.current_pdf_path = None
        self.current_template_json = None
        self.current_sheet_id = None
        self.current_template_id = None


def generate_sheet_quick(num_mcq_questions=40, num_written_questions=0, 
                         include_student_id=True, include_key=True,  # Added parameters
                         output_dir="blank_sheets"):
    flow = SheetGenerationFlow()
    success, error = flow.configure_sheet(
        num_mcq_questions=num_mcq_questions, 
        num_written_questions=num_written_questions,
        include_student_id=include_student_id,
        include_key=include_key
    )
    if not success:
        return False, error, None
    success, error = flow.set_output_location(output_dir)
    if not success:
        return False, error, None
    return flow.generate_sheet()


def generate_sheet_with_template(num_mcq_questions=40, num_written_questions=0,
                                 include_student_id=True, include_key=True,  # Added parameters
                                 output_dir="blank_sheets", template_dir="template", 
                                 show_viz=True):
    flow = SheetGenerationFlow()
    success, error = flow.configure_sheet(
        num_mcq_questions=num_mcq_questions, 
        num_written_questions=num_written_questions,
        include_student_id=include_student_id,
        include_key=include_key
    )
    if not success:
        return False, error, None, None
    success, error = flow.set_output_location(output_dir)
    if not success:
        return False, error, None, None
    return flow.generate_and_extract(show_visualization=show_viz)