"""
Sheet Generation Flow
Business logic for creating answer sheets and extracting templates
"""
import os
import sys
import json
import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.db_operations import get_db_operations
from utils.file_utils import ensure_directory, to_relative_path, sanitize_filename
from utils.validation import validate_number_of_questions, validate_filename


class SheetGenerationFlow:
    """Handles answer sheet generation and template extraction workflow"""
    
    def __init__(self):
        """Initialize the flow"""
        self.db_ops = get_db_operations()
        
        # Configuration
        self.num_questions = 40
        self.include_student_id = True
        self.include_class_info = True
        self.include_timestamp = False
        self.output_directory = "blank_sheets"
        self.filename = None
        
        # Generated outputs
        self.current_pdf_path = None
        self.current_template_json = None
        self.current_sheet_id = None
        self.current_template_id = None
    
    def configure_sheet(self, num_questions=None, include_student_id=None, 
                       include_class_info=None, include_timestamp=None):
        """
        Configure sheet parameters
        
        Args:
            num_questions: Number of questions
            include_student_id: Include student ID field
            include_class_info: Include class information
            include_timestamp: Include timestamp
            
        Returns:
            Tuple of (success, error_message)
        """
        if num_questions is not None:
            valid, error, parsed = validate_number_of_questions(num_questions)
            if not valid:
                return False, error
            self.num_questions = parsed
        
        if include_student_id is not None:
            self.include_student_id = bool(include_student_id)
        
        if include_class_info is not None:
            self.include_class_info = bool(include_class_info)
        
        if include_timestamp is not None:
            self.include_timestamp = bool(include_timestamp)
        
        return True, None
    
    def set_output_location(self, directory, filename=None):
        """
        Set output location
        
        Args:
            directory: Output directory
            filename: Output filename (None for auto-generate)
            
        Returns:
            Tuple of (success, error_message)
        """
        if filename:
            valid, error = validate_filename(filename)
            if not valid:
                return False, error
            
            # Sanitize and ensure .pdf extension
            filename = sanitize_filename(filename)
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
        
        self.output_directory = directory
        self.filename = filename
        
        return True, None
    
    def generate_sheet(self):
        """
        Generate answer sheet PDF
        
        Returns:
            Tuple of (success, error_message, pdf_path)
        """
        try:
            from core.sheet_maker import AnswerSheetDesigner
            
            # Ensure output directory exists
            if not ensure_directory(self.output_directory):
                return False, f"Failed to create directory: {self.output_directory}", None
            
            # Generate filename if not provided
            if not self.filename:
                self.filename = f"answer_sheet_{self.num_questions}_questions.pdf"
            
            output_path = os.path.join(self.output_directory, self.filename)
            
            # Create designer and configure
            designer = AnswerSheetDesigner()
            designer.set_config(
                include_student_id=self.include_student_id,
                include_class_info=self.include_class_info,
                include_timestamp=self.include_timestamp
            )
            
            # Generate PDF
            designer.create_answer_sheet(
                total_questions=self.num_questions,
                output_path=output_path,
                format='pdf',
                use_preset=True
            )
            
            self.current_pdf_path = output_path
            
            # Save to database
            if self.db_ops.is_connected():
                try:
                    sheet_name = os.path.splitext(self.filename)[0]
                    self.current_sheet_id = self.db_ops.save_sheet(
                        file_path=to_relative_path(output_path),
                        name=sheet_name,
                        notes=f"Generated with {self.num_questions} questions"
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
        Extract template from generated PDF
        
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
            from core.bubble_extraction import process_pdf_answer_sheet
            
            # Process PDF to extract bubble positions
            json_path = process_pdf_answer_sheet(
                pdf_path=pdf_path,
                dpi=dpi,
                keep_png=False,
                show_visualization=show_visualization
            )
            
            if not json_path:
                return False, "Template extraction failed", None
            
            self.current_template_json = json_path
            
            # Save template to database
            if self.db_ops.is_connected() and self.current_sheet_id:
                try:
                    # Load template data
                    with open(json_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    # Extract metadata
                    page_data = template_data.get('page_1', {})
                    total_questions = page_data.get('total_questions', 0)
                    if not total_questions:
                        total_questions = len(page_data.get('questions', []))
                    
                    has_student_id = bool(page_data.get('student_id', {}).get('digit_columns'))
                    
                    # Generate template name
                    template_name = f"Template_{os.path.splitext(self.filename)[0]}"
                    
                    # Save to database
                    self.current_template_id = self.db_ops.save_template(
                        sheet_id=self.current_sheet_id,
                        name=template_name,
                        json_path=to_relative_path(json_path),
                        template_data=template_data,
                        total_questions=total_questions,
                        has_student_id=has_student_id
                    )
                    
                    if self.current_template_id:
                        print(f"[FLOW] Template saved to database (ID: {self.current_template_id})")
                    else:
                        print(f"[FLOW] Warning: Failed to save template to database")
                        
                except Exception as e:
                    print(f"[FLOW] Database save failed: {e}")
            
            return True, None, json_path
            
        except ImportError as e:
            return False, f"Failed to import bubble_extraction: {e}", None
        except Exception as e:
            return False, f"Failed to extract template: {e}", None
    
    def get_generation_info(self):
        """
        Get information about generated sheet
        
        Returns:
            Dictionary with generation info
        """
        return {
            'num_questions': self.num_questions,
            'include_student_id': self.include_student_id,
            'include_class_info': self.include_class_info,
            'include_timestamp': self.include_timestamp,
            'pdf_path': self.current_pdf_path,
            'template_json_path': self.current_template_json,
            'sheet_id': self.current_sheet_id,
            'template_id': self.current_template_id
        }
    
    def reset(self):
        """Reset flow to initial state"""
        self.num_questions = 40
        self.include_student_id = True
        self.include_class_info = True
        self.include_timestamp = False
        self.output_directory = "blank_sheets"
        self.filename = None
        self.current_pdf_path = None
        self.current_template_json = None
        self.current_sheet_id = None
        self.current_template_id = None


def generate_sheet_quick(num_questions=40, output_dir="blank_sheets"):
    """
    Quick function to generate a sheet programmatically
    
    Args:
        num_questions: Number of questions
        output_dir: Output directory
        
    Returns:
        Tuple of (success, error_message, pdf_path)
    """
    flow = SheetGenerationFlow()
    
    # Configure
    success, error = flow.configure_sheet(num_questions=num_questions)
    if not success:
        return False, error, None
    
    success, error = flow.set_output_location(output_dir)
    if not success:
        return False, error, None
    
    # Generate
    return flow.generate_sheet()


def generate_sheet_with_template(num_questions=40, output_dir="blank_sheets", 
                                 template_dir="template", show_viz=True):
    """
    Generate sheet and extract template in one go
    
    Args:
        num_questions: Number of questions
        output_dir: Output directory for PDF
        template_dir: Output directory for template JSON
        show_viz: Show detection visualizations
        
    Returns:
        Tuple of (success, error_message, pdf_path, template_path)
    """
    flow = SheetGenerationFlow()
    
    # Configure
    success, error = flow.configure_sheet(num_questions=num_questions)
    if not success:
        return False, error, None, None
    
    success, error = flow.set_output_location(output_dir)
    if not success:
        return False, error, None, None
    
    # Generate sheet
    success, error, pdf_path = flow.generate_sheet()
    if not success:
        return False, error, None, None
    
    # Extract template
    success, error, template_path = flow.extract_template(show_visualization=show_viz)
    if not success:
        return False, error, pdf_path, None
    
    return True, None, pdf_path, template_path