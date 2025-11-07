"""
extraction.py - Combined Answer and Student ID Extraction (FIXED)

Fixed: Filters out square alignment markers from student ID detection
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime


class Bubble:
    """Class to represent a single bubble in the answer sheet"""
    
    def __init__(self, label, x, y, radius):
        self.label = label
        self.question_number = None
        self.x = x
        self.y = y
        self.radius = radius
        self.filled = False
        self.fill_percentage = 0.0
    
    def scale(self, scale_x, scale_y):
        """Scale bubble coordinates"""
        scale_avg = (scale_x + scale_y) / 2
        return Bubble(
            label=self.label,
            x=int(self.x * scale_x),
            y=int(self.y * scale_y),
            radius=int(self.radius * scale_avg)
        )
    
    def __repr__(self):
        filled_str = "Filled" if self.filled else "Empty"
        return f"Bubble({self.label}, ({self.x}, {self.y}), r={self.radius}, {filled_str})"


class Question:
    """Class to represent a question with multiple bubbles"""
    
    def __init__(self, question_number, bubbles, bounding_box=None):
        self.question_number = question_number
        self.bubbles = bubbles
        self.bounding_box = bounding_box
        
        for bubble in self.bubbles:
            bubble.question_number = question_number
    
    def get_filled_bubbles(self):
        """Get list of filled bubbles"""
        return [bubble for bubble in self.bubbles if bubble.filled]
    
    def get_answer(self):
        """Get the answer(s) for this question"""
        return [bubble.label for bubble in self.bubbles if bubble.filled]
    
    def scale(self, scale_x, scale_y):
        """Scale question and all its bubbles"""
        scaled_bubbles = [bubble.scale(scale_x, scale_y) for bubble in self.bubbles]
        
        scaled_bbox = None
        if self.bounding_box:
            scale_avg = (scale_x + scale_y) / 2
            scaled_bbox = {
                'x_min': int(self.bounding_box['x_min'] * scale_x),
                'x_max': int(self.bounding_box['x_max'] * scale_x),
                'y_min': int(self.bounding_box['y_min'] * scale_y),
                'y_max': int(self.bounding_box['y_max'] * scale_y),
                'avg_radius': int(self.bounding_box['avg_radius'] * scale_avg)
            }
        
        return Question(self.question_number, scaled_bubbles, scaled_bbox)
    
    def __repr__(self):
        answer = self.get_answer()
        answer_str = ', '.join(answer) if answer else 'No answer'
        return f"Question {self.question_number}: {answer_str}"


class BubbleTemplate:
    """Class to store and manage bubble template data"""
    
    def __init__(self, json_path):
        """Load template from JSON file"""
        self.json_path = json_path
        self.template_data = self.load_template(json_path)
        self.questions = self.extract_questions()
        self.id_template = self.extract_id_template()
        self.template_width = None
        self.template_height = None
        
        if self.questions:
            first_page_data = self.get_page_data(1)
            if first_page_data:
                self.template_width = first_page_data['image_dimensions']['width']
                self.template_height = first_page_data['image_dimensions']['height']
    
    def load_template(self, json_path):
        """Load template from JSON file"""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Template not found: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        print(f"[LOADED] Template: {json_path}")
        print(f"  Total pages: {template_data['metadata']['total_pages']}")
        print(f"  Total questions: {template_data['metadata']['total_questions']}")
        
        return template_data
    
    def get_page_data(self, page_num):
        """Get data for a specific page"""
        page_key = f"page_{page_num}"
        return self.template_data.get(page_key)
    
    def extract_questions(self):
        """Extract all questions from template into Question objects"""
        questions = []
        
        for page_key in sorted(self.template_data.keys()):
            if page_key.startswith('page_'):
                page_data = self.template_data[page_key]
                
                for question_data in page_data['questions']:
                    bubbles = []
                    for bubble_data in question_data['bubbles']:
                        bubble = Bubble(
                            label=bubble_data['label'],
                            x=bubble_data['x'],
                            y=bubble_data['y'],
                            radius=bubble_data['radius']
                        )
                        bubbles.append(bubble)
                    
                    question = Question(
                        question_number=question_data['question_number'],
                        bubbles=bubbles,
                        bounding_box=question_data['bounding_box']
                    )
                    questions.append(question)
        
        return questions
    
    def extract_id_template(self):
        """Extract student ID template from first page - FIXED to filter square markers"""
        page_data = self.template_data.get('page_1')
        if not page_data:
            return None
        
        id_data = page_data.get('student_id')
        if not id_data:
            print("[INFO] No student_id found in template")
            return None
        
        template_width = page_data['image_dimensions']['width']
        template_height = page_data['image_dimensions']['height']
        
        # FIX: Filter out columns that are actually square markers
        # Square markers typically have only 1 bubble or have 'marker' in some field
        valid_columns = []
        for column in id_data['digit_columns']:
            # Skip if column has only 1 bubble (likely a square marker)
            if len(column['bubbles']) <= 1:
                print(f"[FILTERED] Skipping column at position {column['digit_position']} - only {len(column['bubbles'])} bubble(s)")
                continue
            
            # Skip if all bubbles have the same digit (not a valid ID column)
            unique_digits = set(b['digit'] for b in column['bubbles'])
            if len(unique_digits) <= 1:
                print(f"[FILTERED] Skipping column at position {column['digit_position']} - not enough unique digits")
                continue
            
            # Skip if bubbles don't represent digits 0-9
            if not all(isinstance(b['digit'], int) and 0 <= b['digit'] <= 9 for b in column['bubbles']):
                print(f"[FILTERED] Skipping column at position {column['digit_position']} - invalid digit values")
                continue
            
            valid_columns.append(column)
        
        if not valid_columns:
            print("[WARNING] No valid ID columns found after filtering")
            return None
        
        id_template = {
            'template_width': template_width,
            'template_height': template_height,
            'total_digits': len(valid_columns),  # Use actual valid column count
            'digit_columns': valid_columns
        }
        
        print(f"[INFO] ID Template: {id_template['total_digits']} valid digit columns (filtered from {len(id_data['digit_columns'])} total)")
        
        return id_template


class AnswerSheetExtractor:
    """Class to extract both answers and student ID from scanned answer sheets"""
    
    def __init__(self, template):
        """Initialize extractor with template"""
        self.template = template
    
    def scale_questions(self, target_width, target_height):
        """Scale all template questions to match target image dimensions"""
        if not self.template.template_width or not self.template.template_height:
            print("Error: Template dimensions not available")
            return []
        
        scale_x = target_width / self.template.template_width
        scale_y = target_height / self.template.template_height
        
        print(f"\nScale factors: X={scale_x:.3f}, Y={scale_y:.3f}")
        
        scaled_questions = []
        for question in self.template.questions:
            scaled_q = question.scale(scale_x, scale_y)
            scaled_questions.append(scaled_q)
        
        return scaled_questions
    
    def scale_id_template(self, target_width, target_height):
        """Scale ID template coordinates to match target image"""
        if not self.template.id_template:
            return None
        
        template_width = self.template.id_template['template_width']
        template_height = self.template.id_template['template_height']
        
        scale_x = target_width / template_width
        scale_y = target_height / template_height
        scale_avg = (scale_x + scale_y) / 2
        
        scaled_template = {
            'total_digits': self.template.id_template['total_digits'],
            'digit_columns': []
        }
        
        for column in self.template.id_template['digit_columns']:
            scaled_column = {
                'digit_position': column['digit_position'],
                'bubbles': []
            }
            
            for bubble in column['bubbles']:
                scaled_bubble = {
                    'digit': bubble['digit'],
                    'x': int(bubble['x'] * scale_x),
                    'y': int(bubble['y'] * scale_y),
                    'radius': int(bubble['radius'] * scale_avg)
                }
                scaled_column['bubbles'].append(scaled_bubble)
            
            scaled_template['digit_columns'].append(scaled_column)
        
        return scaled_template
    
    def check_bubble_filled(self, image, bubble, threshold_percent=50):
        """Check if a bubble is filled"""
        x = bubble.x if hasattr(bubble, 'x') else bubble['x']
        y = bubble.y if hasattr(bubble, 'y') else bubble['y']
        radius = bubble.radius if hasattr(bubble, 'radius') else bubble['radius']
        
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (x, y), radius, 255, -1)
        
        bubble_region = cv2.bitwise_and(image, image, mask=mask)
        circle_pixels = cv2.countNonZero(mask)
        
        _, thresh = cv2.threshold(bubble_region, 127, 255, cv2.THRESH_BINARY_INV)
        dark_pixels = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
        
        if circle_pixels == 0:
            return False, 0.0
        
        filled_percent = (dark_pixels / circle_pixels) * 100
        is_filled = filled_percent >= threshold_percent
        
        return is_filled, filled_percent
    
    def extract_answers(self, image, gray, questions, threshold_percent=50):
        """Extract answers from questions"""
        print("\n" + "="*70)
        print("EXTRACTING ANSWERS")
        print("="*70)
        
        for question in questions:
            for bubble in question.bubbles:
                is_filled, filled_percent = self.check_bubble_filled(
                    gray, bubble, threshold_percent
                )
                bubble.filled = is_filled
                bubble.fill_percentage = filled_percent
        
        # Print summary
        for question in questions[:5]:  # Show first 5
            answer = question.get_answer()
            answer_str = ', '.join(answer) if answer else 'No answer'
            print(f"Question {question.question_number}: {answer_str}")
        
        if len(questions) > 5:
            print(f"... and {len(questions) - 5} more questions")
        
        return questions
    
    def extract_student_id(self, gray, scaled_id_template, threshold_percent=50):
        """Extract student ID"""
        print("\n" + "="*70)
        print("EXTRACTING STUDENT ID")
        print("="*70)
        
        if not scaled_id_template:
            print("[INFO] No ID template available")
            return None
        
        student_id = []
        id_confidence = []
        digit_details = []
        
        for column in scaled_id_template['digit_columns']:
            digit_pos = column['digit_position']
            filled_digits = []
            
            for bubble in column['bubbles']:
                digit = bubble['digit']
                is_filled, fill_percent = self.check_bubble_filled(
                    gray, bubble, threshold_percent
                )
                
                if is_filled:
                    filled_digits.append({
                        'digit': digit,
                        'confidence': fill_percent
                    })
            
            # Determine selected digit
            if len(filled_digits) == 0:
                student_id.append(None)
                id_confidence.append(0.0)
                digit_details.append({
                    'position': digit_pos,
                    'digit': None,
                    'confidence': 0.0,
                    'status': 'blank'
                })
            elif len(filled_digits) == 1:
                digit = filled_digits[0]['digit']
                confidence = filled_digits[0]['confidence']
                student_id.append(digit)
                id_confidence.append(confidence)
                digit_details.append({
                    'position': digit_pos,
                    'digit': digit,
                    'confidence': confidence,
                    'status': 'valid'
                })
            else:
                best = max(filled_digits, key=lambda d: d['confidence'])
                digit = best['digit']
                confidence = best['confidence']
                student_id.append(digit)
                id_confidence.append(confidence)
                digit_details.append({
                    'position': digit_pos,
                    'digit': digit,
                    'confidence': confidence,
                    'status': 'conflict',
                    'conflicting_digits': [d['digit'] for d in filled_digits]
                })
        
        # Build ID string
        if all(d is not None for d in student_id):
            id_string = ''.join(str(d) for d in student_id)
            is_valid = True
        else:
            id_string = ''.join(str(d) if d is not None else '_' for d in student_id)
            is_valid = False
        
        avg_confidence = np.mean(id_confidence) if id_confidence else 0.0
        
        result = {
            'student_id': id_string,
            'is_valid': is_valid,
            'average_confidence': avg_confidence,
            'digit_details': digit_details
        }
        
        print(f"Student ID: {id_string}")
        print(f"Valid: {is_valid}")
        print(f"Confidence: {avg_confidence:.1f}%")
        
        return result
    
    def visualize_extraction(self, image, questions, id_result, scaled_id_template):
        """Visualize both answer and ID extraction"""
        output = image.copy()
        
        # Draw answer bubbles
        for question in questions:
            for bubble in question.bubbles:
                x = bubble.x
                y = bubble.y
                radius = bubble.radius
                
                color = (0, 255, 0) if bubble.filled else (0, 0, 255)
                thickness = 3 if bubble.filled else 2
                
                cv2.circle(output, (x, y), radius, color, thickness)
                cv2.putText(output, bubble.label, (x - 5, y - radius - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw ID bubbles if available
        if id_result and scaled_id_template:
            status_map = {d['position']: d for d in id_result['digit_details']}
            
            for column in scaled_id_template['digit_columns']:
                digit_pos = column['digit_position']
                status = status_map.get(digit_pos, {})
                selected_digit = status.get('digit')
                
                for bubble in column['bubbles']:
                    x = bubble['x']
                    y = bubble['y']
                    radius = bubble['radius']
                    digit = bubble['digit']
                    
                    if digit == selected_digit:
                        if status.get('status') == 'conflict':
                            color = (0, 165, 255)  # Orange
                            thickness = 3
                        else:
                            color = (255, 0, 255)  # Magenta
                            thickness = 3
                    else:
                        color = (128, 0, 128)  # Purple
                        thickness = 1
                    
                    cv2.circle(output, (x, y), radius, color, thickness)
            
            # Add ID text
            id_text = f"ID: {id_result['student_id']}"
            cv2.putText(output, id_text, (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3)
        
        # Resize if needed
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('Answer & ID Extraction', output)
        print("\n[VISUALIZATION]")
        print("  GREEN = Filled answer bubble")
        print("  RED = Empty answer bubble")
        print("  MAGENTA = Selected ID digit")
        print("\nPress any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def extract_complete(self, image_path, threshold_percent=50, debug=True):
        """
        Extract both answers and student ID from filled answer sheet
        
        Args:
            image_path: Path to filled answer sheet image
            threshold_percent: Threshold for bubble detection
            debug: If True, show visualization
            
        Returns:
            Dictionary with complete extraction data
        """
        print("\n" + "="*70)
        print("COMPLETE ANSWER SHEET EXTRACTION")
        print("="*70)
        print(f"Image: {image_path}")
        print(f"Threshold: {threshold_percent}%")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] Could not load image: {image_path}")
            return None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        target_height, target_width = image.shape[:2]
        
        print(f"Dimensions: {target_width}x{target_height}")
        
        # Scale questions
        scaled_questions = self.scale_questions(target_width, target_height)
        print(f"[SUCCESS] Scaled {len(scaled_questions)} questions")
        
        # Extract answers
        questions = self.extract_answers(image, gray, scaled_questions, threshold_percent)
        
        # Scale and extract ID
        scaled_id_template = self.scale_id_template(target_width, target_height)
        id_result = self.extract_student_id(gray, scaled_id_template, threshold_percent)
        
        # Compile results
        result = {
            'metadata': {
                'source_image': image_path,
                'extracted_at': datetime.now().isoformat(),
                'template_used': self.template.json_path,
                'threshold_percent': threshold_percent,
                'total_questions': len(questions)
            },
            'student_id': id_result,
            'answers': {}
        }
        
        # Add answer data
        for question in questions:
            q_num = question.question_number
            bubbles_data = []
            
            for bubble in question.bubbles:
                bubbles_data.append({
                    'label': bubble.label,
                    'filled': bubble.filled,
                    'fill_percentage': round(bubble.fill_percentage, 2)
                })
            
            result['answers'][str(q_num)] = {
                'question_number': q_num,
                'selected_answers': question.get_answer(),
                'bubbles': bubbles_data
            }
        
        # Visualization
        if debug:
            self.visualize_extraction(image, questions, id_result, scaled_id_template)
        
        return result


def save_extraction_to_json(result, output_dir='scanned_answers'):
    """
    Save extraction data to JSON with format: answers_XXq_StudentID.json
    
    Args:
        result: Dictionary with extraction results
        output_dir: Directory to save JSON
        
    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Build filename
    num_questions = result['metadata']['total_questions']
    student_id = result['student_id']['student_id'] if result['student_id'] else 'NOID'
    student_id = student_id.replace('_', 'X')  # Replace blanks with X
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"answers_{num_questions}q_{student_id}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Save to JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] Extraction saved to: {json_path}")
    
    return json_path


def main():
    """Example usage"""
    
    print("="*70)
    print("COMPLETE ANSWER SHEET EXTRACTION SYSTEM")
    print("="*70)
    
    template_path = 'template/answer_sheet_10q.json'
    answer_sheet = 'filled_sheet.png'
    
    if not os.path.exists(template_path):
        print(f"[ERROR] Template not found: {template_path}")
        return
    
    if not os.path.exists(answer_sheet):
        print(f"[ERROR] Answer sheet not found: {answer_sheet}")
        return
    
    # Load template
    template = BubbleTemplate(template_path)
    
    # Extract both answers and ID
    extractor = AnswerSheetExtractor(template)
    result = extractor.extract_complete(
        answer_sheet,
        threshold_percent=50,
        debug=True
    )
    
    if result:
        # Save to JSON
        json_path = save_extraction_to_json(result)
        
        print("\n" + "="*70)
        print("EXTRACTION COMPLETE")
        print("="*70)
        if result['student_id']:
            print(f"Student ID: {result['student_id']['student_id']}")
        print(f"Questions answered: {len(result['answers'])}")
        print(f"Saved to: {json_path}")


if __name__ == "__main__":
    main()