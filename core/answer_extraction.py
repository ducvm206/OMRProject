"""
answer_extraction.py - Extract answers from filled answer sheets

This module loads a JSON template and uses it to extract answers
from scanned/photographed answer sheets.
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
        self.question_number = None  # To be set when added to a question
        self.x = x
        self.y = y
        self.radius = radius
        self.filled = False  # To be determined during processing
        self.fill_percentage = 0.0  # Percentage of bubble that is filled
    
    def scale(self, scale_x, scale_y):
        """
        Scale bubble coordinates
        
        Args:
            scale_x: Horizontal scale factor
            scale_y: Vertical scale factor
            
        Returns:
            New scaled Bubble object
        """
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
        self.bubbles = bubbles  # List of Bubble objects
        self.bounding_box = bounding_box
        
        # Set question number for all bubbles
        for bubble in self.bubbles:
            bubble.question_number = question_number
    
    def get_filled_bubbles(self):
        """
        Get list of filled bubbles
        
        Returns:
            List of Bubble objects that are filled
        """
        return [bubble for bubble in self.bubbles if bubble.filled]
    
    def get_answer(self):
        """
        Get the answer(s) for this question
        
        Returns:
            List of labels (e.g., ['A'] or ['A', 'C'] if multiple filled)
        """
        return [bubble.label for bubble in self.bubbles if bubble.filled]
    
    def scale(self, scale_x, scale_y):
        """
        Scale question and all its bubbles
        
        Args:
            scale_x: Horizontal scale factor
            scale_y: Vertical scale factor
            
        Returns:
            New scaled Question object
        """
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
        """
        Load template from JSON file
        
        Args:
            json_path: Path to JSON template file
        """
        self.json_path = json_path
        self.template_data = self.load_template(json_path)
        self.questions = self.extract_questions()
        self.template_width = None
        self.template_height = None
        
        if self.questions:
            # Get template dimensions from first question's page
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
        """
        Extract all questions from template into Question objects
        
        Returns:
            List of Question objects
        """
        questions = []
        
        for page_key in sorted(self.template_data.keys()):
            if page_key.startswith('page_'):
                page_data = self.template_data[page_key]
                
                for question_data in page_data['questions']:
                    # Create Bubble objects
                    bubbles = []
                    for bubble_data in question_data['bubbles']:
                        bubble = Bubble(
                            label=bubble_data['label'],
                            x=bubble_data['x'],
                            y=bubble_data['y'],
                            radius=bubble_data['radius']
                        )
                        bubbles.append(bubble)
                    
                    # Create Question object
                    question = Question(
                        question_number=question_data['question_number'],
                        bubbles=bubbles,
                        bounding_box=question_data['bounding_box']
                    )
                    questions.append(question)
        
        return questions
    
    def print_debug_info(self):
        """Print debug information about loaded questions"""
        print("\n" + "="*70)
        print("DEBUG: LOADED TEMPLATE DATA")
        print("="*70)
        
        for question in self.questions[:5]:  # Show first 5
            print(f"\nQuestion {question.question_number}:")
            
            for bubble in question.bubbles:
                print(f"  Bubble {bubble.label} at ({bubble.x}, {bubble.y}), Radius = {bubble.radius}")
        
        if len(self.questions) > 5:
            print(f"\n  ... and {len(self.questions) - 5} more questions")


class AnswerExtractor:
    """Class to extract answers from scanned answer sheets"""
    
    def __init__(self, template):
        """
        Initialize answer extractor with template
        
        Args:
            template: BubbleTemplate object
        """
        self.template = template
    
    def scale_questions(self, target_width, target_height):
        """
        Scale all template questions to match target image dimensions
        
        Args:
            target_width: Width of target answer sheet image
            target_height: Height of target answer sheet image
            
        Returns:
            List of scaled Question objects
        """
        if not self.template.template_width or not self.template.template_height:
            print("Error: Template dimensions not available")
            return []
        
        # Calculate scaling factors
        scale_x = target_width / self.template.template_width
        scale_y = target_height / self.template.template_height
        
        #print(f"\nScale factors: X={scale_x:.3f}, Y={scale_y:.3f}")
        
        # Scale all questions
        scaled_questions = []
        for question in self.template.questions:
            scaled_q = question.scale(scale_x, scale_y)
            scaled_questions.append(scaled_q)
        
        return scaled_questions
    
    def check_bubble_filled(self, image, bubble, threshold_percent=50):
        """
        Check if a bubble is filled by analyzing pixel darkness
        
        Args:
            image: Grayscale image of answer sheet
            bubble: Bubble object
            threshold_percent: Percentage of dark pixels needed to consider filled (default: 50%)
            
        Returns:
            Tuple of (is_filled, fill_percentage)
        """
        x = bubble.x
        y = bubble.y
        radius = bubble.radius
        
        # Create a circular mask for the bubble
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (x, y), radius, 255, -1)  # Filled circle
        
        # Extract the circular region
        bubble_region = cv2.bitwise_and(image, image, mask=mask)
        
        # Count pixels inside the circle
        circle_pixels = cv2.countNonZero(mask)
        
        # Threshold the region to find dark pixels (filled marks)
        # Invert so filled bubbles (dark) become white
        _, thresh = cv2.threshold(bubble_region, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Count dark pixels in the bubble region
        dark_pixels = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
        
        # Calculate percentage of filled area
        if circle_pixels == 0:
            return False, 0.0
        
        filled_percent = (dark_pixels / circle_pixels) * 100
        
        # Check if filled percentage exceeds threshold
        is_filled = filled_percent >= threshold_percent
        
        return is_filled, filled_percent
    
    def visualize_bubbles(self, image, questions):
        """
        Draw circles on answer sheet to show detection results
        
        Args:
            image: Answer sheet image (color)
            questions: List of Question objects with filled status
        """
        output = image.copy()
        
        # Draw each question's bubbles
        for question in questions:
            for bubble in question.bubbles:
                x = bubble.x
                y = bubble.y
                radius = bubble.radius
                label = bubble.label
                
                # Color based on fill status: Green if filled, Red if empty
                color = (0, 255, 0) if bubble.filled else (0, 0, 255)  # Green : Red
                thickness = 3 if bubble.filled else 2
                
                # Draw circle
                cv2.circle(output, (x, y), radius, color, thickness)
                
                # Add label
                text_color = (0, 255, 0) if bubble.filled else (0, 0, 255)
                cv2.putText(
                    output,
                    label,
                    (x - 5, y - radius - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    text_color,
                    1
                )
        
        # Resize if too large
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('Bubble Fill Detection', output)
        print("\n[DEBUG] Showing bubble fill detection results")
        print("  Green circles = Filled bubbles")
        print("  Red circles = Empty bubbles")
        print("Press any key to close the window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def extract_answers(self, image_path, threshold_percent=50, debug=True):
        """
        Extract answers from a filled answer sheet
        
        Args:
            image_path: Path to filled answer sheet image
            threshold_percent: Percentage of dark pixels to consider bubble filled (default: 50%)
            debug: If True, show visualization
            
        Returns:
            List of Question objects with filled status updated
        """
        print("\n" + "="*70)
        print("ANSWER EXTRACTION")
        print("="*70)
        
        # Load the answer sheet
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load image at {image_path}")
            return None
        
        # Convert to grayscale for bubble detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        target_height, target_width = image.shape[:2]
        
        print(f"\nAnswer sheet dimensions: {target_width}x{target_height}")
        print(f"Template dimensions: {self.template.template_width}x{self.template.template_height}")
        print(f"Fill threshold: {threshold_percent}%")
        
        # Scale all questions to match answer sheet dimensions
        scaled_questions = self.scale_questions(target_width, target_height)
        
        print(f"\n[SUCCESS] Scaled {len(scaled_questions)} questions to match answer sheet")
        
        # Check each bubble for fill status
        print("\n" + "="*70)
        print("DEBUG: BUBBLE FILL DETECTION")
        print("="*70)
        
        for question in scaled_questions:
            print(f"\nQuestion {question.question_number}:")
            
            for bubble in question.bubbles:
                # Check if bubble is filled
                is_filled, filled_percent = self.check_bubble_filled(
                    gray, bubble, threshold_percent
                )
                
                # Update bubble object
                bubble.filled = is_filled
                bubble.fill_percentage = filled_percent
                
                # Debug print
                filled_str = "True" if is_filled else "False"
                print(f"  Bubble {bubble.label} at ({bubble.x}, {bubble.y}), "
                      f"Radius = {bubble.radius}, Filled = {filled_str} ({filled_percent:.1f}%)")
        
        # Visualize results
        if debug:
            self.visualize_bubbles(image, scaled_questions)
        
        # Print summary
        print("\n" + "="*70)
        print("DETECTED ANSWERS SUMMARY")
        print("="*70)
        for question in scaled_questions:
            answer = question.get_answer()
            if answer:
                answer_str = ", ".join(answer)
                print(f"Question {question.question_number}: {answer_str}")
            else:
                print(f"Question {question.question_number}: No answer detected")
        
        return scaled_questions


def save_answers_to_json(questions, source_image_path, template_path, threshold_percent, output_dir='scanned_answers'):
    """
    Save extracted answers to JSON file
    
    Args:
        questions: List of Question objects with filled status
        source_image_path: Path to the scanned answer sheet
        template_path: Path to the template JSON used
        threshold_percent: Threshold percentage used for detection
        output_dir: Directory to save the answers JSON
        
    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare answers data
    answers_data = {
        'metadata': {
            'source_image': source_image_path,
            'template_used': template_path,
            'scanned_at': datetime.now().isoformat(),
            'total_questions': len(questions)
        },
        'answers': {}
    }
    
    # Extract answers from each question
    for question in questions:
        q_num = question.question_number
        
        # Get all bubbles data
        bubbles_data = []
        for bubble in question.bubbles:
            bubbles_data.append({
                'label': bubble.label,
                'filled': bubble.filled,
                'fill_percentage': round(bubble.fill_percentage, 2),
                'position': {
                    'x': bubble.x,
                    'y': bubble.y,
                    'radius': bubble.radius
                }
            })
        
        # Get the selected answer(s)
        selected_answers = question.get_answer()
        
        answers_data['answers'][str(q_num)] = {
            'question_number': q_num,
            'selected_answers': selected_answers,  # List of filled bubble labels
            'bubbles': bubbles_data  # Detailed info for each bubble
        }
    
    # Generate filename
    # base_name = os.path.splitext(os.path.basename(source_image_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"answers_{timestamp}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Save to JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(answers_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] Answers saved to: {json_path}")
    
    return json_path


def load_answers_from_json(json_path):
    """
    Load saved answers from JSON file
    
    Args:
        json_path: Path to answers JSON file
        
    Returns:
        Dictionary containing answers data
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        answers_data = json.load(f)
    
    print(f"[LOADED] Answers from: {json_path}")
    print(f"  Source image: {answers_data['metadata']['source_image']}")
    print(f"  Scanned at: {answers_data['metadata']['scanned_at']}")
    print(f"  Total questions: {answers_data['metadata']['total_questions']}")
    
    return answers_data


def main():
    """Example usage of answer extraction"""
    
    print("="*70)
    print("ANSWER SHEET EXTRACTION WITH FILL DETECTION")
    print("="*70)
    
    # Load template from JSON
    template_path = 'template/answer_sheet_template.json'
    
    if not os.path.exists(template_path):
        print(f"\n[ERROR] Template not found: {template_path}")
        print("Please create a template first using main.py")
        return
    
    # Load template
    template = BubbleTemplate(template_path)
    
    # Print debug info (original template coordinates)
    template.print_debug_info()
    
    # Extract answers from filled sheet
    answer_sheet_path = 'filled_sheet.png'  # Change this to your filled sheet
    
    if not os.path.exists(answer_sheet_path):
        print(f"\n[ERROR] Answer sheet not found: {answer_sheet_path}")
        print("Please provide a filled answer sheet image")
        return
    
    # Create extractor and process answer sheet
    extractor = AnswerExtractor(template)
    
    # Extract answers with customizable threshold (default 50%)
    questions = extractor.extract_answers(
        answer_sheet_path, 
        threshold_percent=50,  # Adjust this value as needed (0-100)
        debug=True
    )
    
    if questions:
        # Save answers to JSON
        json_path = save_answers_to_json(
            questions=questions,
            source_image_path=answer_sheet_path,
            template_path=template_path,
            threshold_percent=50
        )
        
        # Example: Access individual bubbles
        print("\n" + "="*70)
        print("EXAMPLE: Accessing bubble data")
        print("="*70)
        
        if questions:
            first_q = questions[0]
            print(f"\nFirst question ({first_q.question_number}):")
            for bubble in first_q.bubbles:
                print(f"  {bubble}")
            print(f"\nAnswer: {first_q.get_answer()}")
        
        # Example: Load the saved answers
        print("\n" + "="*70)
        print("EXAMPLE: Loading saved answers")
        print("="*70)
        loaded_answers = load_answers_from_json(json_path)
        print(f"\nFirst question from saved file:")
        first_saved = loaded_answers['answers']['1']
        print(f"  Question {first_saved['question_number']}: {first_saved['selected_answers']}")


if __name__ == "__main__":
    main()