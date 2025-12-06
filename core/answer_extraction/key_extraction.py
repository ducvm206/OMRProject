"""
key_extraction.py - Answer Key Extraction from KEY Region

Extracts the answer key (5 bubbles: A, B, C, D, E) from the marked KEY region
in the answer sheet template or from a scanned sheet.

The KEY region contains exactly 5 bubbles indicating the correct answers for
reference/grading purposes.

Usage:
    from key_extraction import KeyExtractor, extract_key_from_template
    
    # Method 1: From template JSON
    key_data = extract_key_from_template('template/sheet_template.json')
    
    # Method 2: From scanned sheet with detection
    extractor = KeyExtractor()
    key_data = extractor.extract_key_from_sheet(
        image_path='filled_sheet.png',
        template_path='template/sheet_template.json'
    )
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime


class KeyBubble:
    """Represents a single bubble in the KEY region"""
    
    def __init__(self, position, x, y, radius):
        """
        Args:
            position: Position in key (1-5 corresponding to A-E)
            x, y: Center coordinates
            radius: Bubble radius in pixels
        """
        self.position = position
        self.label = chr(64 + position)  # 1->A, 2->B, 3->C, 4->D, 5->E
        self.x = x
        self.y = y
        self.radius = radius
        self.filled = False
        self.fill_percentage = 0.0
    
    def scale(self, scale_x, scale_y):
        """Scale bubble coordinates"""
        scale_avg = (scale_x + scale_y) / 2
        scaled = KeyBubble(
            position=self.position,
            x=int(self.x * scale_x),
            y=int(self.y * scale_y),
            radius=int(self.radius * scale_avg)
        )
        scaled.filled = self.filled
        scaled.fill_percentage = self.fill_percentage
        return scaled
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'position': self.position,
            'label': self.label,
            'x': self.x,
            'y': self.y,
            'radius': self.radius,
            'filled': self.filled,
            'fill_percentage': round(self.fill_percentage, 2)
        }
    
    def __repr__(self):
        filled_str = "Filled" if self.filled else "Empty"
        return f"KeyBubble({self.label}, ({self.x}, {self.y}), r={self.radius}, {filled_str})"


class KeyExtractor:
    """Extract answer key from KEY region of answer sheets"""
    
    def __init__(self):
        """Initialize the key extractor"""
        self.template_data = None
        self.template_width = None
        self.template_height = None
        self.key_bubbles = None
    
    def load_template(self, template_path):
        """
        Load template JSON and extract key bubble data.
        
        Args:
            template_path: Path to template JSON file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(template_path):
            print(f"[ERROR] Template not found: {template_path}")
            return False
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                self.template_data = json.load(f)
            
            # Extract KEY data from page_1
            page1 = self.template_data.get('page_1')
            if not page1:
                print("[ERROR] No page_1 found in template")
                return False
            
            # Get image dimensions
            dims = page1.get('image_dimensions', {})
            self.template_width = dims.get('width')
            self.template_height = dims.get('height')
            
            if not self.template_width or not self.template_height:
                print("[ERROR] Image dimensions not found in template")
                return False
            
            # Extract KEY bubbles
            key_data = page1.get('key')
            if not key_data:
                print("[INFO] No KEY data found in template")
                return False
            
            # Convert raw key data to KeyBubble objects
            self.key_bubbles = []
            for bubble_data in key_data:
                bubble = KeyBubble(
                    position=bubble_data.get('position'),
                    x=bubble_data.get('x'),
                    y=bubble_data.get('y'),
                    radius=bubble_data.get('radius')
                )
                self.key_bubbles.append(bubble)
            
            print(f"[SUCCESS] Loaded KEY template with {len(self.key_bubbles)} bubbles")
            print(f"  Template dimensions: {self.template_width}x{self.template_height}")
            for bubble in self.key_bubbles:
                print(f"  {bubble}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load template: {e}")
            return False
    
    def scale_key_bubbles(self, target_width, target_height):
        """
        Scale key bubbles to match target image dimensions.
        
        Args:
            target_width: Target image width
            target_height: Target image height
            
        Returns:
            List of scaled KeyBubble objects
        """
        if not self.key_bubbles:
            print("[ERROR] No key bubbles loaded")
            return None
        
        scale_x = target_width / self.template_width
        scale_y = target_height / self.template_height
        
        scaled_bubbles = []
        for bubble in self.key_bubbles:
            scaled = bubble.scale(scale_x, scale_y)
            scaled_bubbles.append(scaled)
        
        return scaled_bubbles
    
    def check_bubble_filled(self, image, bubble, threshold_percent=50):
        """
        Check if a bubble is filled by analyzing pixel darkness.
        
        Args:
            image: Grayscale image
            bubble: KeyBubble object
            threshold_percent: Fill percentage threshold to consider filled
            
        Returns:
            Tuple of (is_filled: bool, fill_percentage: float)
        """
        x = bubble.x
        y = bubble.y
        radius = bubble.radius
        
        # Create circular mask
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (x, y), radius, 255, -1)
        
        # Get bubble region
        bubble_region = cv2.bitwise_and(image, image, mask=mask)
        
        # Count circle pixels
        circle_pixels = cv2.countNonZero(mask)
        
        # Threshold and count dark pixels
        _, thresh = cv2.threshold(bubble_region, 127, 255, cv2.THRESH_BINARY_INV)
        dark_pixels = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
        
        if circle_pixels == 0:
            return False, 0.0
        
        fill_percentage = (dark_pixels / circle_pixels) * 100
        is_filled = fill_percentage >= threshold_percent
        
        return is_filled, fill_percentage
    
    def extract_key_from_sheet(self, image_path, template_path, 
                              threshold_percent=50, debug=False):
        """
        Extract KEY from a scanned answer sheet.
        
        Args:
            image_path: Path to scanned sheet image
            template_path: Path to template JSON
            threshold_percent: Fill detection threshold
            debug: If True, show visualization
            
        Returns:
            Dictionary with key extraction results or None
        """
        # Load template
        if not self.load_template(template_path):
            return None
        
        # Load image
        if not os.path.exists(image_path):
            print(f"[ERROR] Image not found: {image_path}")
            return None
        
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] Could not load image: {image_path}")
            return None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        target_height, target_width = image.shape[:2]
        
        print(f"\n{'='*70}")
        print("EXTRACTING KEY FROM SCANNED SHEET")
        print(f"{'='*70}")
        print(f"Image: {os.path.basename(image_path)}")
        print(f"Dimensions: {target_width}x{target_height}")
        print(f"Threshold: {threshold_percent}%")
        
        # Scale key bubbles to match image
        scaled_bubbles = self.scale_key_bubbles(target_width, target_height)
        
        if not scaled_bubbles:
            print("[ERROR] Failed to scale key bubbles")
            return None
        
        # Check which bubbles are filled
        filled_answers = []
        
        for bubble in scaled_bubbles:
            is_filled, fill_percent = self.check_bubble_filled(
                gray, bubble, threshold_percent
            )
            bubble.filled = is_filled
            bubble.fill_percentage = fill_percent
            
            status = "✓ FILLED" if is_filled else "  empty"
            print(f"  {bubble.label}: {status} ({fill_percent:.1f}%)")
            
            if is_filled:
                filled_answers.append(bubble.label)
        
        # Build result
        result = {
            'metadata': {
                'source_image': image_path,
                'template_used': template_path,
                'extracted_at': datetime.now().isoformat(),
                'threshold_percent': threshold_percent
            },
            'key_bubbles': [bubble.to_dict() for bubble in scaled_bubbles],
            'filled_answers': filled_answers,
            'answer_key': ''.join(filled_answers) if filled_answers else None,
            'total_marked': len(filled_answers),
            'total_positions': len(scaled_bubbles)
        }
        
        print(f"\n[RESULT]")
        print(f"  Answer Key: {result['answer_key'] if result['answer_key'] else 'NONE'}")
        print(f"  Marked: {result['total_marked']}/{result['total_positions']}")
        
        # Visualization
        if debug:
            self._visualize_key(image, scaled_bubbles)
        
        return result
    
    def _visualize_key(self, image, bubbles):
        """Visualize KEY extraction on image"""
        output = image.copy()
        
        for bubble in bubbles:
            # Color: green if filled, red if empty
            color = (0, 255, 0) if bubble.filled else (0, 0, 255)
            thickness = 3 if bubble.filled else 2
            
            # Draw bubble
            cv2.circle(output, (bubble.x, bubble.y), bubble.radius, color, thickness)
            
            # Draw label
            label_text = f"{bubble.label}"
            cv2.putText(output, label_text, 
                       (bubble.x - 10, bubble.y - bubble.radius - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # Draw fill percentage
            fill_text = f"{bubble.fill_percentage:.0f}%"
            cv2.putText(output, fill_text,
                       (bubble.x - 15, bubble.y + bubble.radius + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        
        # Resize if needed
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('KEY Region Extraction', output)
        print("\n[VISUALIZATION]")
        print("  GREEN = Filled bubble (marked as answer)")
        print("  RED = Empty bubble (not marked)")
        print("\nPress any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def extract_key_from_template(template_path):
    """
    Extract KEY data directly from template JSON (no image analysis).
    
    Args:
        template_path: Path to template JSON file
        
    Returns:
        Dictionary with key data or None
    """
    if not os.path.exists(template_path):
        print(f"[ERROR] Template not found: {template_path}")
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        page1 = template_data.get('page_1')
        if not page1:
            print("[ERROR] No page_1 found in template")
            return None
        
        key_data = page1.get('key')
        if not key_data:
            print("[INFO] No KEY region in template")
            return None
        
        # Convert to KeyBubble objects
        bubbles = []
        for bubble_data in key_data:
            bubble = KeyBubble(
                position=bubble_data.get('position'),
                x=bubble_data.get('x'),
                y=bubble_data.get('y'),
                radius=bubble_data.get('radius')
            )
            bubbles.append(bubble)
        
        result = {
            'source_template': template_path,
            'total_positions': len(bubbles),
            'key_bubbles': [bubble.to_dict() for bubble in bubbles],
            'extracted_at': datetime.now().isoformat()
        }
        
        print(f"[SUCCESS] Extracted {len(bubbles)} KEY bubbles from template")
        for bubble in bubbles:
            print(f"  {bubble.label}: ({bubble.x}, {bubble.y}), r={bubble.radius}")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Failed to extract key from template: {e}")
        return None


def save_key_extraction(result, output_dir='extraction_results'):
    """
    Save KEY extraction results to JSON.
    
    Args:
        result: Extraction result dictionary
        output_dir: Directory to save JSON
        
    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"key_extraction_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] KEY extraction saved to: {filepath}")
    
    return filepath


def main():
    """Example usage"""
    
    print("="*70)
    print("KEY REGION EXTRACTION")
    print("="*70)
    
    template_path = 'template/test_sheet_with_key_complete_template.json'
    
    # Method 1: Extract KEY from template only (no image needed)
    print("\n[METHOD 1] Extract from template JSON")
    print("-"*70)
    
    key_data_template = extract_key_from_template(template_path)
    if key_data_template:
        save_key_extraction(key_data_template)
    
    # Method 2: Extract KEY from scanned sheet (requires image + template)
    print("\n[METHOD 2] Extract from scanned sheet")
    print("-"*70)
    
    test_image = 'test_sheet_with_key_page_1.png'
    
    if os.path.exists(test_image):
        extractor = KeyExtractor()
        key_data_scanned = extractor.extract_key_from_sheet(
            image_path=test_image,
            template_path=template_path,
            threshold_percent=50,
            debug=True
        )
        
        if key_data_scanned:
            save_key_extraction(key_data_scanned)
    else:
        print(f"[INFO] Test image not found: {test_image}")
        print("[INFO] Skipping scanned sheet extraction")


if __name__ == "__main__":
    main()