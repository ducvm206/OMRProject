import cv2
import numpy as np
import json
from tensorflow.keras.models import load_model  # type: ignore


class QuickAnswerExtraction:
    """
    R-CNN pipeline for extracting handwritten digits from quick answer regions.
    Uses pre-determined bounding boxes from template and CNN model for digit recognition.
    """
    
    def __init__(self, model_path, template_path):
        self.model = load_model(model_path)
        self.template = self._load_template(template_path)
        self.template_width = self.template['page_1']['image_dimensions']['width']
        self.template_height = self.template['page_1']['image_dimensions']['height']
        self.quick_answer_regions = self._extract_quick_answer_regions()
        
    def _load_template(self, template_path):
        with open(template_path, 'r') as f:
            return json.load(f)
    
    def _extract_quick_answer_regions(self):
        regions = []
        quick_answers = self.template['page_1']['quick_answers']
        
        for answer_box in quick_answers['answer_boxes']:
            regions.append({
                'question_number': answer_box['question_number'],
                'x': answer_box['x'],
                'y': answer_box['y'],
                'width': answer_box['width'],
                'height': answer_box['height']
            })
        
        return regions
    
    def expand_bbox_proportional(self, x, y, w, h, region_w, region_h, scale=0.1):
        """
        Expands bounding box proportionally based on bbox dimensions.
        scale: 0.4 means +40% padding around digit (more aggressive than before).
        """
        pad_w = int(w * scale)
        pad_h = int(h * scale)

        x1 = max(x - pad_w, 0)
        y1 = max(y - pad_h, 0)
        x2 = min(x + w + pad_w, region_w)
        y2 = min(y + h + pad_h, region_h)

        return x1, y1, x2 - x1, y2 - y1
    
    def show_preprocessed_digits(self, digit_detections, question_number):
        """
        Display preprocessed 32x32 images in an OpenCV window.
        Shows what the CNN actually sees.
        """
        print(f"\n[DEBUG] show_preprocessed_digits called for Q{question_number}")
        print(f"[DEBUG] Number of digit detections: {len(digit_detections)}")
        
        if not digit_detections:
            print(f"[DEBUG] No digits to display for Q{question_number}")
            return
        
        # Sort by position
        sorted_digits = sorted(digit_detections, key=lambda d: d['cx'])
        
        # Create a horizontal montage
        num_digits = len(sorted_digits)
        cell_size = 128  # Display size (upscale from 32x32 for visibility)
        montage_width = cell_size * num_digits
        montage_height = cell_size + 40  # Extra space for labels
        
        montage = np.ones((montage_height, montage_width, 3), dtype=np.uint8) * 255
        
        for i, d in enumerate(sorted_digits):
            # Get 32x32 preprocessed image
            img_32 = d['preprocessed_image'][:, :, 0]  # Remove channel dim
            
            # Convert to 0-255 range
            img_display = (img_32 * 255).astype(np.uint8)
            
            # Upscale to 128x128 for visibility (use NEAREST to see pixels clearly)
            img_upscaled = cv2.resize(img_display, (cell_size, cell_size), 
                                     interpolation=cv2.INTER_NEAREST)
            
            # Convert to BGR for display
            img_bgr = cv2.cvtColor(img_upscaled, cv2.COLOR_GRAY2BGR)
            
            # Place in montage
            x_offset = i * cell_size
            montage[0:cell_size, x_offset:x_offset+cell_size] = img_bgr
            
            # Add label (predicted digit + confidence)
            label = f"{d['digit']} ({d['confidence']:.2f})"
            cv2.putText(montage, label, (x_offset + 10, cell_size + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Show window
        window_name = f"Q{question_number} - Preprocessed Digits (32x32 -> 128x128)"
        print(f"[DEBUG] Creating window: {window_name}")
        print(f"[DEBUG] Montage size: {montage.shape}")
        print(f"[DEBUG] Press ANY KEY to continue...")
        
        cv2.imshow(window_name, montage)
        key = cv2.waitKey(0)  # Wait for key press
        print(f"[DEBUG] Key pressed: {key}")
        cv2.destroyWindow(window_name)
    
    def preprocess_digit_region(self, digit_roi):
        """
        Preprocess digit ROI to match CNN training data format:
        - Resize to 28x28 maintaining aspect ratio
        - Center on 32x32 white canvas
        - BLACK digit on WHITE background
        """
        
        # Convert to grayscale if needed
        if len(digit_roi.shape) == 3:
            digit_gray = cv2.cvtColor(digit_roi, cv2.COLOR_BGR2GRAY)
        else:
            digit_gray = digit_roi

        # 1. Threshold - Keep as-is for black digit on white background
        _, digit_bin = cv2.threshold(digit_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 2. Resize to 28px max dimension (keep aspect ratio)
        H, W = digit_bin.shape
        if H == 0 or W == 0:
            return None
            
        scale = 28 / max(H, W)
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        
        digit_resize = cv2.resize(digit_bin, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 3. Center on 32x32 WHITE canvas
        canvas = np.ones((32, 32), dtype=np.uint8) * 255
        xo = (32 - new_w) // 2
        yo = (32 - new_h) // 2
        canvas[yo:yo+new_h, xo:xo+new_w] = digit_resize

        # 4. Normalize
        canvas = canvas.astype("float32") / 255.0

        # 5. Shape for CNN (batch_size=1, height=32, width=32, channels=1)
        canvas = np.expand_dims(canvas, -1)
        canvas = np.expand_dims(canvas, 0)

        return canvas
    
    def resize_image_to_template(self, image):
        return cv2.resize(image, (self.template_width, self.template_height))
    
    def detect_digits_in_region(self, image, region_info, debug_mode=False):
        """
        Detect digits in a specific quick answer region.
        Now uses proportional padding based on digit size.
        """
        x, y, w, h = region_info['x'], region_info['y'], region_info['width'], region_info['height']
        region = image[y:y+h, x:x+w]
        
        if debug_mode:
            print(f"\n{'='*60}")
            print(f"[DEBUG] Processing Q{region_info['question_number']}")
            print(f"[DEBUG] Region size: {w}x{h}")
        
        # Preprocessing
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        
        # ✅ KEY FIX: Crop border padding to avoid detecting box edges
        border_padding = 10  # pixels to crop from each edge
        if w > 2*border_padding and h > 2*border_padding:
            gray = gray[border_padding:h-border_padding, border_padding:w-border_padding]
            if debug_mode:
                print(f"[DEBUG] Cropped region to avoid borders: {gray.shape[1]}x{gray.shape[0]}")
        
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # Noise reduction
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # ✅ Use connected components instead of contours (more robust)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh, connectivity=8)
        
        if debug_mode:
            print(f"[DEBUG] Found {num_labels-1} connected components (excluding background)")

        digit_detections = []
        rejected_count = {"area": 0, "aspect": 0, "empty_region": 0, "preprocess_failed": 0}

        # Start from 1 to skip background (label 0)
        for label_idx in range(1, num_labels):
            # Get bounding box from connected component stats
            x2 = stats[label_idx, cv2.CC_STAT_LEFT]
            y2 = stats[label_idx, cv2.CC_STAT_TOP]
            w2 = stats[label_idx, cv2.CC_STAT_WIDTH]
            h2 = stats[label_idx, cv2.CC_STAT_HEIGHT]
            area = stats[label_idx, cv2.CC_STAT_AREA]
            aspect = w2 / h2 if h2 != 0 else 0

            if debug_mode:
                print(f"\n  Component {label_idx}: pos=({x2},{y2}), size={w2}x{h2}, area={area}, aspect={aspect:.2f}")

            # Filter 1: Skip tiny noise
            if area < 80:
                if debug_mode:
                    print(f"    ❌ REJECTED: Area too small ({area} < 80)")
                rejected_count["area"] += 1
                continue

            # Filter 2: Skip extreme aspect ratios
            if aspect < 0.1 or aspect > 4:
                if debug_mode:
                    print(f"    ❌ REJECTED: Bad aspect ratio ({aspect:.2f} not in [0.1, 4])")
                rejected_count["aspect"] += 1
                continue

            # ✅ Passed filters, expand bbox
            # Note: we cropped the region, so adjust coordinates back
            region_w = gray.shape[1]
            region_h = gray.shape[0]
            ex1, ey1, ew, eh = self.expand_bbox_proportional(x2, y2, w2, h2, region_w, region_h, scale=0.2)
            ex2 = ex1 + ew
            ey2 = ey1 + eh

            if debug_mode:
                print(f"    ✅ PASSED filters")
                print(f"    Expanded bbox: ({ex1},{ey1}) {ew}x{eh}")

            # Extract padded region from the cropped gray image
            digit_region = gray[ey1:ey2, ex1:ex2]
            
            # Validate region
            if digit_region.size == 0:
                if debug_mode:
                    print(f"    ❌ REJECTED: Empty region after extraction")
                rejected_count["empty_region"] += 1
                continue
            
            processed = self.preprocess_digit_region(digit_region)
            if processed is None:
                if debug_mode:
                    print(f"    ❌ REJECTED: Preprocessing failed")
                rejected_count["preprocess_failed"] += 1
                continue

            # Predict digit
            predictions = self.model.predict(processed, verbose=0)
            digit = int(np.argmax(predictions))
            confidence = float(np.max(predictions))

            if debug_mode:
                print(f"    ✅ ACCEPTED: Predicted digit={digit}, confidence={confidence:.3f}")

            # Adjust coordinates back to original region (add back border padding)
            digit_detections.append({
                "digit": digit,
                "confidence": confidence,
                "bbox": (x + ex1 + border_padding, y + ey1 + border_padding, ew, eh),
                "cx": x + x2 + w2 // 2 + border_padding,
                "preprocessed_image": processed[0],
            })
        
        if debug_mode:
            print(f"\n[SUMMARY Q{region_info['question_number']}]")
            print(f"  Total contours: {num_labels - 1}")
            print(f"  Rejected by area: {rejected_count['area']}")
            print(f"  Rejected by aspect: {rejected_count['aspect']}")
            print(f"  Rejected by empty region: {rejected_count['empty_region']}")
            print(f"  Rejected by preprocessing: {rejected_count['preprocess_failed']}")
            print(f"  ✅ ACCEPTED: {len(digit_detections)}")
            print(f"{'='*60}")
        
        # 🆕 DEBUG: Show preprocessed images
        if debug_mode and digit_detections:
            print(f"[DEBUG] Calling show_preprocessed_digits...")
            self.show_preprocessed_digits(digit_detections, region_info['question_number'])
        elif debug_mode and not digit_detections:
            print(f"[DEBUG] ⚠️  No digits to display for Q{region_info['question_number']}")
        
        return digit_detections
    
    def merge_digits_to_number(self, digit_detections):
        """
        Merge detected digits into a single number string.
        """
        if not digit_detections:
            return None, 0.0, []
        
        # Sort left to right
        sorted_digits = sorted(digit_detections, key=lambda d: d['cx'])
        merged_number = ''.join(str(d['digit']) for d in sorted_digits)
        avg_confidence = np.mean([d['confidence'] for d in sorted_digits])
        
        return merged_number, float(avg_confidence), sorted_digits
    
    def extract_all_quick_answers(self, image, debug_mode=False):
        """
        Extract answers from all quick answer regions in the sheet.
        """
        image = self.resize_image_to_template(image)
        
        results = {
            'quick_answers': [],
            'total_questions': len(self.quick_answer_regions)
        }
        
        for region_info in self.quick_answer_regions:
            digit_detections = self.detect_digits_in_region(image, region_info, debug_mode)
            merged_number, confidence, digit_list = self.merge_digits_to_number(digit_detections)
            
            # Remove preprocessed images from final results (they're large)
            for d in digit_list:
                if 'preprocessed_image' in d:
                    del d['preprocessed_image']
            
            results['quick_answers'].append({
                'question_number': region_info['question_number'],
                'answer': merged_number,
                'confidence': confidence,
                'digit_count': len(digit_list),
                'individual_digits': digit_list
            })
        
        return results
    
    def annotate_image(self, image, quick_answers_results):
        """
        Create annotated debug image showing all detections.
        - Blue: quick answer region box
        - Yellow: all candidate connected components
        - Red: final accepted digit bounding boxes
        """
        output_image = self.resize_image_to_template(image.copy())
        
        for qa in quick_answers_results['quick_answers']:
            q_num = qa['question_number']
            region = next(r for r in self.quick_answer_regions if r['question_number'] == q_num)
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            
            # Blue: region box
            cv2.rectangle(output_image, (x, y), (x+w, y+h), (255, 0, 0), 3)
            
            # Answer label
            if qa['answer'] is not None:
                label = f"Q{q_num}: {qa['answer']} ({qa['confidence']:.2f})"
            else:
                label = f"Q{q_num}: No answer"
            cv2.putText(output_image, label, (x, y+h+28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # Yellow: Show ALL candidate connected components
            region_img = output_image[y:y+h, x:x+w]
            gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            thresh_clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh_clean, 8)

            for lbl in range(1, num_labels):
                sx = stats[lbl, cv2.CC_STAT_LEFT]
                sy = stats[lbl, cv2.CC_STAT_TOP]
                sw = stats[lbl, cv2.CC_STAT_WIDTH]
                sh = stats[lbl, cv2.CC_STAT_HEIGHT]
                # Yellow boxes for ALL components
                cv2.rectangle(output_image, (x+sx, y+sy), (x+sx+sw, y+sy+sh),
                              (0, 255, 255), 2)

            # Red: Final accepted digits WITH PADDING
            for d in qa['individual_digits']:
                bx, by, bw, bh = d['bbox']
                # Red boxes for accepted digits (now with proper padding)
                cv2.rectangle(output_image, (bx, by), (bx+bw, by+bh), (0, 0, 255), 3)
                # Digit label
                cv2.putText(output_image, str(d['digit']), (bx, by-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        return output_image
    
    def save_results(self, quick_answers_results, output_path):
        """Save extraction results to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(quick_answers_results, f, indent=2)
    
    def process_sheet(self, image_path, output_image_path=None, output_json_path=None, debug_mode=False):
        """
        Complete processing pipeline for a filled answer sheet.
        
        Args:
            image_path: Path to the filled sheet image
            output_image_path: Where to save annotated debug image
            output_json_path: Where to save JSON results
            debug_mode: If True, shows 32x32 preprocessed images for each question
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        # Extract answers
        results = self.extract_all_quick_answers(image, debug_mode=debug_mode)
        
        # Save annotated image
        if output_image_path:
            annotated = self.annotate_image(image, results)
            import os
            root_path = os.path.abspath(output_image_path)
            print("Saving annotated image to:", root_path)
            cv2.imwrite(root_path, annotated)
        
        # Save JSON results
        if output_json_path:
            self.save_results(results, output_json_path)
        
        return results


def main():
    """Example usage with debug mode"""
    scanner = QuickAnswerExtraction(
        model_path="core/cnn_model/cnn_model.h5",
        template_path="files/template/answer_sheet_30mcq_6written_complete_template.json",
    )

    # Process the sheet with DEBUG MODE enabled
    print("Processing sheet with debug visualization...")
    print("Press ANY KEY in each window to continue to next question\n")
    
    result = scanner.process_sheet(
        "answer_sheet_1.png", 
        output_image_path="debug_annotated.jpg",
        debug_mode=True  # 🆕 Enable debug windows
    )

    # Print extracted answers
    print("\n=== EXTRACTION RESULTS ===")
    for qa in result['quick_answers']:
        print(f"Q{qa['question_number']}: {qa['answer']} (confidence: {qa['confidence']:.2f})")

    print("\nDone. Annotated image saved to debug_annotated.jpg")


if __name__ == "__main__":
    main()