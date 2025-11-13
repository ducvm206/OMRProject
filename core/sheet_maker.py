import cv2
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from PIL import Image, ImageDraw, ImageFont

class AnswerSheetDesigner:
    def __init__(self, lato_font_path=None):
        """
        Initialize with optional Lato font path
        Args:
            lato_font_path: Dictionary with paths to Lato font files
                           {'regular': 'path/to/Lato-Regular.ttf',
                            'bold': 'path/to/Lato-Bold.ttf'}
        """
        self.lato_font_path = lato_font_path or {
            'regular': 'Lato-Regular.ttf',
            'bold': 'Lato-Bold.ttf'
        }
        
        self.design_config = {
            'page_size': 'Letter',
            'margins': {'top': 10, 'bottom': 50, 'left': 50, 'right': 50},
            'bubble_radius': 8,
            'questions_per_page': 40,
            'options_per_question': 4,
            'option_labels': ['A', 'B', 'C', 'D'],
            'columns': 3,
            'max_questions_per_column': 20,  # Maximum questions that fit in one column
            'bubble_spacing': 23,
            'row_spacing': 35,
            'question_number_width': 30,
            'font_size': 12,
            'show_question_numbers': True,
            'include_header': True,
            'include_instructions': False,
            'bubble_line_width': 2,
            'header_height': 80,
            'include_student_id': True,
            'student_id_digits': 8,
            'id_bubble_radius': 7,
            'id_bubble_spacing': 20,
            'id_row_spacing': 22,
            'id_marker_size': 10  # Size of corner markers
        }
        
        # Predefined presets
        self.presets = {
            10: {'columns': 2, 'max_questions_per_column': 15, 'questions_per_page': 30, 'row_spacing': 40},
            20: {'columns': 2, 'max_questions_per_column': 18, 'questions_per_page': 36, 'row_spacing': 35},
            30: {'columns': 3, 'max_questions_per_column': 18, 'questions_per_page': 54, 'row_spacing': 35},
            40: {'columns': 3, 'max_questions_per_column': 18, 'questions_per_page': 54, 'row_spacing': 35}
        }
        
        # Register Lato fonts for PDF
        self._register_lato_fonts()
        
    def _register_lato_fonts(self):
        """Register Lato fonts for ReportLab PDF generation"""
        try:
            pdfmetrics.registerFont(TTFont('Lato', self.lato_font_path['regular']))
            pdfmetrics.registerFont(TTFont('Lato-Bold', self.lato_font_path['bold']))
            self.pdf_font_registered = True
            print("Lato fonts registered successfully for PDF")
        except Exception as e:
            print(f"Warning: Could not register Lato fonts for PDF: {e}")
            print("Falling back to Helvetica")
            self.pdf_font_registered = False
    
    def apply_preset(self, total_questions):
        """Apply preset configuration based on number of questions"""
        # Find the closest preset
        preset_keys = sorted(self.presets.keys())
        for key in preset_keys:
            if total_questions <= key:
                preset = self.presets[key]
                self.set_config(**preset)
                print(f"Applied preset for {key} questions")
                return
        
        # If more than max preset, use the largest
        preset = self.presets[preset_keys[-1]]
        self.set_config(**preset)
        print(f"Applied preset for {preset_keys[-1]} questions")
        
    def set_config(self, **kwargs):
        """Update design configuration"""
        for key, value in kwargs.items():
            if key in self.design_config:
                self.design_config[key] = value
    
    def create_answer_sheet(self, total_questions, output_path, format='pdf', use_preset=True):
        """Create a complete answer sheet design"""
        
        # Apply preset if enabled
        if use_preset:
            self.apply_preset(total_questions)
        
        if format.lower() == 'pdf':
            self._create_pdf_sheet(total_questions, output_path)
        else:
            self._create_image_sheet(total_questions, output_path, format)
        
        print(f"Answer sheet created: {output_path}")
    
    def _create_pdf_sheet(self, total_questions, output_path):
        """Create PDF answer sheet with Lato font"""
        if self.design_config['page_size'].upper() == 'LETTER':
            page_width, page_height = letter
        else:
            page_width, page_height = A4
        
        c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
        
        questions_per_page = self.design_config['questions_per_page']
        total_pages = (total_questions + questions_per_page - 1) // questions_per_page
        
        for page in range(total_pages):
            if page > 0:
                c.showPage()
            
            self._draw_pdf_header(c, page_width, page_height, page + 1, total_pages)
            self._draw_pdf_questions(c, page_width, page_height, page, total_questions)
            
            # Draw Student ID section on first page
            if page == 0 and self.design_config['include_student_id']:
                self._draw_pdf_student_id(c, page_width, page_height)
        
        c.save()
    
    def _draw_pdf_header(self, c, page_width, page_height, current_page, total_pages):
        """Draw compact header section on PDF with Lato font"""
        margins = self.design_config['margins']
        
        font_bold = "Lato-Bold" if self.pdf_font_registered else "Helvetica-Bold"
        font_regular = "Lato" if self.pdf_font_registered else "Helvetica"
        
        if self.design_config['include_header']:
            c.setFont(font_bold, 14)
            c.drawString(margins['left'], page_height - margins['top'] - 10, "ANSWER SHEET")
            
            c.setFont(font_regular, 9)
            c.drawString(page_width - margins['right'] - 40, page_height - margins['top'] - 10, 
                        f"Page {current_page}/{total_pages}")
            
            c.setFont(font_regular, 9)
            info_y = page_height - margins['top'] - 30
            c.drawString(margins['left'], info_y, "Name: ____________________________")
            c.drawString(margins['left'] + 180, info_y, "Date: ______________")
            
            if self.design_config['include_instructions']:
                c.setFont(font_regular, 7)
                c.drawString(margins['left'], info_y - 15, "Use #2 pencil • Fill circles completely")
    
    def _draw_pdf_student_id(self, c, page_width, page_height):
        """Draw Student ID block in bottom right with corner markers"""
        margins = self.design_config['margins']
        font_bold = "Lato-Bold" if self.pdf_font_registered else "Helvetica-Bold"
        font_regular = "Lato" if self.pdf_font_registered else "Helvetica"
        
        num_digits = self.design_config['student_id_digits']
        id_bubble_radius = self.design_config['id_bubble_radius']
        id_bubble_spacing = self.design_config['id_bubble_spacing']
        id_row_spacing = self.design_config['id_row_spacing']
        marker_size = self.design_config['id_marker_size']
        
        # Calculate dimensions
        id_section_width = num_digits * id_bubble_spacing + 40
        id_section_height = 10 * id_row_spacing + 50
        
        # Position in bottom right corner
        start_x = page_width - margins['right'] - id_section_width - 25
        start_y = margins['bottom'] + id_section_height - 20
        
        # Draw title
        c.setFont(font_bold, 10)
        c.drawString(start_x + 10, start_y + 25, "STUDENT ID")
        
        # Draw column headers (digit positions)
        c.setFont(font_regular, 7)
        for col in range(num_digits):
            col_x = start_x + 20 + col * id_bubble_spacing
            c.drawString(col_x - 2, start_y, str(col + 1))
        
        # Draw rows (0-9) with numbers inside bubbles
        for row in range(10):
            row_y = start_y - 15 - row * id_row_spacing
            
            # Draw bubbles for each column with digit inside
            for col in range(num_digits):
                bubble_x = start_x + 20 + col * id_bubble_spacing
                bubble_y = row_y
                
                # Draw hollow bubble
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillColorRGB(1, 1, 1)
                c.circle(bubble_x, bubble_y, id_bubble_radius, stroke=1, fill=0)
                
                # Draw number inside bubble
                c.setFillColorRGB(0, 0, 0)
                c.setFont(font_bold, 8)
                digit_str = str(row)
                text_width = c.stringWidth(digit_str, font_bold, 8)
                text_x = bubble_x - text_width / 2
                text_y = bubble_y - 3
                c.drawString(text_x, text_y, digit_str)
        
        # Calculate border box coordinates
        box_x1 = start_x + 5
        box_y1 = start_y - 15 - 9 * id_row_spacing - 15
        box_x2 = start_x + id_section_width - 20
        box_y2 = start_y + 20
    
        
        # Draw BLACK SQUARE MARKERS at four corners
        c.setFillColorRGB(0, 0, 0)
        
        # Top-left marker
        c.rect(box_x1 - marker_size/2, box_y2 - marker_size/2, marker_size, marker_size, stroke=0, fill=1)
        
        # Top-right marker
        c.rect(box_x2 - marker_size/2, box_y2 - marker_size/2, marker_size, marker_size, stroke=0, fill=1)
        
        # Bottom-left marker
        c.rect(box_x1 - marker_size/2, box_y1 - marker_size/2, marker_size, marker_size, stroke=0, fill=1)
        
        # Bottom-right marker
        c.rect(box_x2 - marker_size/2, box_y1 - marker_size/2, marker_size, marker_size, stroke=0, fill=1)
    
    def _draw_pdf_questions(self, c, page_width, page_height, current_page, total_questions):
        """Draw questions and bubbles on PDF with Lato font - Fill columns sequentially"""
        margins = self.design_config['margins']
        questions_per_page = self.design_config['questions_per_page']
        columns = self.design_config['columns']
        max_per_column = self.design_config['max_questions_per_column']
        
        font_bold = "Lato-Bold" if self.pdf_font_registered else "Helvetica-Bold"
        font_regular = "Lato" if self.pdf_font_registered else "Helvetica"
        
        start_question = current_page * questions_per_page
        end_question = min(start_question + questions_per_page, total_questions)
        questions_this_page = end_question - start_question
        
        # Calculate layout - NO compression for ID section
        content_width = page_width - margins['left'] - margins['right']
        content_height = page_height - margins['top'] - margins['bottom'] - self.design_config['header_height']
        
        column_width = content_width / columns
        row_spacing = self.design_config['row_spacing']
        bubble_radius = self.design_config['bubble_radius']
        bubble_spacing = self.design_config['bubble_spacing']
        question_number_width = self.design_config['question_number_width']
        
        # Start questions
        start_y = page_height - margins['top'] - self.design_config['header_height']
        
        # Render questions column by column (fill first column completely before moving to next)
        question_index = 0
        for col in range(columns):
            col_x = margins['left'] + col * column_width
            
            # Determine how many questions in this column
            remaining_questions = questions_this_page - question_index
            questions_in_column = min(max_per_column, remaining_questions)
            
            for row in range(questions_in_column):
                question_num = start_question + question_index + 1
                if question_num > end_question:
                    break
                
                # Calculate vertical position
                row_y = start_y - row * row_spacing
                
                # Draw question number
                if self.design_config['show_question_numbers']:
                    c.setFont(font_bold, self.design_config['font_size'])
                    c.drawString(col_x, row_y - 6, f"{question_num}")
                
                # Draw hollow bubbles with letters inside
                bubble_start_x = col_x + question_number_width
                for i, option in enumerate(self.design_config['option_labels']):
                    bubble_x = bubble_start_x + i * bubble_spacing
                    bubble_y = row_y - 2
                    
                    # Draw hollow bubble circle
                    c.setStrokeColorRGB(0, 0, 0)
                    c.setFillColorRGB(1, 1, 1)
                    c.circle(bubble_x, bubble_y, bubble_radius, stroke=1, fill=0)
                    
                    # Draw black letter inside hollow bubble
                    c.setFillColorRGB(0, 0, 0)
                    c.setFont(font_bold, self.design_config['font_size'] - 1)
                    
                    # Center the letter in the bubble
                    text_width = c.stringWidth(option, font_bold, self.design_config['font_size'] - 1)
                    text_x = bubble_x - text_width / 2
                    text_y = bubble_y - (self.design_config['font_size'] - 1) / 3
                    
                    c.drawString(text_x, text_y, option)
                
                question_index += 1
    
    def _create_image_sheet(self, total_questions, output_path, format='png'):
        """Create image-based answer sheet (PNG/JPG) with Lato font"""
        # Determine image size based on page size
        if self.design_config['page_size'].upper() == 'LETTER':
            width, height = 612, 792
        else:
            width, height = 595, 842
        
        # Scale up for better resolution
        scale = 2
        width *= scale
        height *= scale
        
        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        # Convert to PIL for better text rendering
        pil_image = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_image)
        
        # Load Lato fonts
        try:
            font_large = ImageFont.truetype(self.lato_font_path['bold'], 14 * scale)
            font_medium = ImageFont.truetype(self.lato_font_path['regular'], 12 * scale)
            font_bold = ImageFont.truetype(self.lato_font_path['bold'], 11 * scale)
            font_small = ImageFont.truetype(self.lato_font_path['regular'], 9 * scale)
            font_tiny = ImageFont.truetype(self.lato_font_path['bold'], 8 * scale)
            print("Lato fonts loaded successfully for image")
        except Exception as e:
            print(f"Warning: Could not load Lato fonts for image: {e}")
            try:
                font_large = ImageFont.truetype("arial.ttf", 14 * scale)
                font_medium = ImageFont.truetype("arial.ttf", 12 * scale)
                font_bold = ImageFont.truetype("arialbd.ttf", 11 * scale)
                font_small = ImageFont.truetype("arial.ttf", 9 * scale)
                font_tiny = ImageFont.truetype("arialbd.ttf", 8 * scale)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_bold = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_tiny = ImageFont.load_default()
        
        # Draw compact header
        self._draw_image_header(draw, width, height, scale, font_large, font_small)
        
        # Draw questions
        self._draw_image_questions(draw, width, height, total_questions, scale, font_medium, font_bold)
        
        # Draw Student ID section
        if self.design_config['include_student_id']:
            self._draw_image_student_id(draw, width, height, scale, font_bold, font_small, font_tiny)
        
        # Convert back to OpenCV format and save
        if format.lower() == 'jpg':
            output_path = output_path.replace('.png', '.jpg')
            pil_image.save(output_path, 'JPEG', quality=95)
        else:
            output_path = output_path.replace('.jpg', '.png')
            pil_image.save(output_path, 'PNG')
    
    def _draw_image_header(self, draw, width, height, scale, font_large, font_small):
        """Draw compact header on image"""
        margins = self.design_config['margins']
        
        if self.design_config['include_header']:
            header_y = height - margins['top'] * scale - 10 * scale
            draw.text((margins['left'] * scale, header_y), 
                     "ANSWER SHEET", fill=(0, 0, 0), font=font_large)
            
            info_y = header_y - 20 * scale
            draw.text((margins['left'] * scale, info_y), 
                     "Name: _________________", fill=(0, 0, 0), font=font_small)
            draw.text((margins['left'] * scale + 180 * scale, info_y), 
                     "Date: ______", fill=(0, 0, 0), font=font_small)
    
    def _draw_image_student_id(self, draw, width, height, scale, font_bold, font_small, font_tiny):
        """Draw Student ID block in bottom right with corner markers"""
        margins = self.design_config['margins']
        
        num_digits = self.design_config['student_id_digits']
        id_bubble_radius = self.design_config['id_bubble_radius'] * scale
        id_bubble_spacing = self.design_config['id_bubble_spacing'] * scale
        id_row_spacing = self.design_config['id_row_spacing'] * scale
        marker_size = self.design_config['id_marker_size'] * scale
        
        # Calculate dimensions
        id_section_width = num_digits * id_bubble_spacing + 40 * scale
        id_section_height = 10 * id_row_spacing + 50 * scale
        
        # Position in bottom right corner
        start_x = width - margins['right'] * scale - id_section_width
        start_y = margins['bottom'] * scale + id_section_height - 20 * scale
        
        # Draw title
        draw.text((start_x + 10 * scale, start_y + 15 * scale), 
                 "STUDENT ID", fill=(0, 0, 0), font=font_bold)
        
        # Draw column headers
        for col in range(num_digits):
            col_x = start_x + 20 * scale + col * id_bubble_spacing
            draw.text((col_x - 2 * scale, start_y), 
                     str(col + 1), fill=(0, 0, 0), font=font_small)
        
        # Draw rows (0-9) with numbers inside bubbles
        for row in range(10):
            row_y = start_y - 15 * scale - row * id_row_spacing
            
            for col in range(num_digits):
                bubble_x = start_x + 20 * scale + col * id_bubble_spacing
                bubble_y = row_y
                
                # Draw hollow bubble
                draw.ellipse([
                    bubble_x - id_bubble_radius, bubble_y - id_bubble_radius,
                    bubble_x + id_bubble_radius, bubble_y + id_bubble_radius
                ], outline=(0, 0, 0), fill=(255, 255, 255), width=self.design_config['bubble_line_width'])
                
                # Draw number inside bubble
                digit_str = str(row)
                bbox = draw.textbbox((0, 0), digit_str, font=font_tiny)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                text_x = bubble_x - text_width / 2
                text_y = bubble_y - text_height / 2
                
                draw.text((text_x, text_y), digit_str, fill=(0, 0, 0), font=font_tiny)
        
        # Calculate border box coordinates
        box_x1 = start_x + 5 * scale
        box_y1 = start_y - 15 * scale - 9 * id_row_spacing - 15 * scale
        box_x2 = start_x + id_section_width - 5 * scale
        box_y2 = start_y + 20 * scale
        
        # Draw border around ID section
        draw.rectangle([box_x1, box_y1, box_x2, box_y2], 
                      outline=(0, 0, 0), width=0)
        
        # Draw BLACK SQUARE MARKERS at four corners
        # Top-left marker
        draw.rectangle([box_x1 - marker_size/2, box_y2 - marker_size/2,
                       box_x1 + marker_size/2, box_y2 + marker_size/2],
                      fill=(0, 0, 0))
        
        # Top-right marker
        draw.rectangle([box_x2 - marker_size/2, box_y2 - marker_size/2,
                       box_x2 + marker_size/2, box_y2 + marker_size/2],
                      fill=(0, 0, 0))
        
        # Bottom-left marker
        draw.rectangle([box_x1 - marker_size/2, box_y1 - marker_size/2,
                       box_x1 + marker_size/2, box_y1 + marker_size/2],
                      fill=(0, 0, 0))
        
        # Bottom-right marker
        draw.rectangle([box_x2 - marker_size/2, box_y1 - marker_size/2,
                       box_x2 + marker_size/2, box_y1 + marker_size/2],
                      fill=(0, 0, 0))
    
    def _draw_image_questions(self, draw, width, height, total_questions, scale, font_medium, font_bold):
        """Draw questions on image - NO compression for ID"""
        margins = self.design_config['margins']
        questions_per_page = self.design_config['questions_per_page']
        columns = self.design_config['columns']
        
        # Full width for questions - NO space reserved for ID
        content_width = width - (margins['left'] + margins['right']) * scale
        content_height = height - (margins['top'] + margins['bottom']) * scale
        
        # Layout parameters
        row_spacing = self.design_config['row_spacing'] * scale
        bubble_radius = self.design_config['bubble_radius'] * scale
        bubble_spacing = self.design_config['bubble_spacing'] * scale
        question_number_width = self.design_config['question_number_width'] * scale
        line_width = self.design_config['bubble_line_width']
        
        column_width = content_width / columns
        
        for page in range((total_questions + questions_per_page - 1) // questions_per_page):
            start_question = page * questions_per_page
            end_question = min(start_question + questions_per_page, total_questions)
            questions_this_page = end_question - start_question
            
            # Calculate questions per column
            questions_per_column = (questions_this_page + columns - 1) // columns
            
            # Start questions
            start_y = height - margins['top'] * scale - self.design_config['header_height'] * scale
            
            for col in range(columns):
                col_x = margins['left'] * scale + col * column_width
                
                for row in range(questions_per_column):
                    question_num = start_question + col * questions_per_column + row + 1
                    if question_num > end_question:
                        break
                    
                    # Calculate vertical position
                    row_y = start_y - row * row_spacing
                    
                    # Draw question number
                    if self.design_config['show_question_numbers']:
                        draw.text((col_x, row_y), f"{question_num}.", 
                                 fill=(0, 0, 0), font=font_medium)
                    
                    # Draw hollow bubbles with letters inside
                    bubble_start_x = col_x + question_number_width
                    for i, option in enumerate(self.design_config['option_labels']):
                        bubble_x = bubble_start_x + i * bubble_spacing
                        bubble_y = row_y - 2 * scale
                        
                        # Draw hollow bubble
                        draw.ellipse([
                            bubble_x - bubble_radius, bubble_y - bubble_radius,
                            bubble_x + bubble_radius, bubble_y + bubble_radius
                        ], outline=(0, 0, 0), fill=(255, 255, 255), width=line_width)
                        
                        # Draw black letter inside hollow bubble
                        bbox = draw.textbbox((0, 0), option, font=font_bold)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        text_x = bubble_x - text_width / 2
                        text_y = bubble_y - text_height / 2
                        
                        draw.text((text_x, text_y), option, fill=(0, 0, 0), font=font_bold)
    
    def preview_design(self, num_questions=10):
        """Create a small preview of the design"""
        temp_path = "preview.png"
        self.create_answer_sheet(num_questions, temp_path, format='png')
        
        # Display the preview
        preview = cv2.imread(temp_path)
        if preview is not None:
            # Resize for display
            height, width = preview.shape[:2]
            scale = min(800 / width, 600 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            preview_resized = cv2.resize(preview, (new_width, new_height))
            
            cv2.imshow('Answer Sheet Preview', preview_resized)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


# Example usage
if __name__ == "__main__":
    designer = AnswerSheetDesigner(lato_font_path={
        'regular': 'Lato-Regular.ttf',
        'bold': 'Lato-Bold.ttf'
    })
    
    # Test different presets
    print("\n=== Testing Presets ===")
    
    # 10 questions preset
    designer.create_answer_sheet(32, 'answer_sheet_15.pdf', format='pdf')

    