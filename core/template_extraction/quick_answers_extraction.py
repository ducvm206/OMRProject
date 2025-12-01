import cv2
import numpy as np
import json
import os
import fitz  # PyMuPDF
from datetime import datetime


def detect_quick_answer_markers(image, show_debug=True):
    """
    Detect the 4 black square corner markers that define the Quick Number Answers region
    
    Args:
        image: Input image (BGR)
        show_debug: If True, show debug visualization
        
    Returns:
        Bounding box (x_min, y_min, x_max, y_max) of Quick Answers region, or None if not found
    """
    
    def analyze_region_content(image_region):
        """
        Analyze region content to differentiate between Quick Answers (rectangles) 
        and Student ID (circles) regions
        """
        gray_roi = cv2.cvtColor(image_region, cv2.COLOR_BGR2GRAY)
        
        # Use the SAME approach as detect_answer_rectangles
        _, binary = cv2.threshold(gray_roi, 100, 255, cv2.THRESH_BINARY_INV)
        
        # Detect horizontal lines (same as rectangle detection)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Detect vertical lines (same as rectangle detection)  
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combine horizontal and vertical lines
        line_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
        
        # Find contours (same as rectangle detection)
        contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rectangle_count = 0
        circle_count = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Use the SAME criteria as detect_answer_rectangles
            if w < 150 or h < 25 or area < 1000:
                continue
                
            aspect_ratio = float(w) / h
            
            # Look for wide rectangles (same criteria)
            if aspect_ratio > 2.0 and aspect_ratio < 8.0:
                rectangle_count += 1
                    
            # CLASSIFY AS CIRCLE (Student ID bubbles) - keep existing circle detection
            elif (100 < area < 3000 and 
                0.8 < aspect_ratio < 1.2):
                # Additional circle check
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity > 0.7:
                        circle_count += 1
        
        print(f"    Region analysis: {rectangle_count} rectangles, {circle_count} circles")
        return rectangle_count, circle_count

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Look for square-shaped contours (corner markers)
    markers = []
    debug_img = image.copy() if show_debug else None
    
    print(f"\n[DEBUG] Analyzing {len(contours)} contours for Quick Answer markers...")
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Same size range as ID markers
        if 200 < area < 2000:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Strict square requirement
            if 0.85 < aspect_ratio < 1.15:
                # Check if it's filled (dark)
                mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                mean_val = cv2.mean(gray, mask=mask)[0]
                
                # Should be very dark (corner markers are solid black)
                if mean_val < 60:
                    # Check it's actually rectangular
                    rect_area = w * h
                    fill_ratio = area / rect_area if rect_area > 0 else 0
                    
                    if fill_ratio > 0.85:
                        center_x = x + w // 2
                        center_y = y + h // 2
                        markers.append((center_x, center_y, area, w, h))
    
    print(f"\n[INFO] Found {len(markers)} corner marker candidates")
    
    # Need at least 8 markers (4 for Quick Answers + 4 for Student ID)
    if len(markers) < 8:
        print(f"[WARNING] Found only {len(markers)} markers (need at least 8 for both regions)")
        if len(markers) >= 4:
            print("[INFO] But we have enough for one region, continuing...")
        else:
            if show_debug and debug_img is not None:
                cv2.imshow('Quick Answer Marker Detection - FAILED', debug_img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            return None
    
    # Sort markers by Y coordinate to separate top and bottom regions
    markers_sorted_by_y = sorted(markers, key=lambda m: m[1])
    
    # Split into two groups: top half and bottom half
    mid_index = len(markers_sorted_by_y) // 2
    top_markers = markers_sorted_by_y[:mid_index]
    bottom_markers = markers_sorted_by_y[mid_index:]
    
    # Take the best 4 markers from each group (largest area)
    top_4 = sorted(top_markers, key=lambda m: m[2], reverse=True)[:4]
    bottom_4 = sorted(bottom_markers, key=lambda m: m[2], reverse=True)[:4]
    
    # Calculate bounding boxes for both regions
    def calculate_region_bounds(marker_group):
        xs = [m[0] for m in marker_group]
        ys = [m[1] for m in marker_group]
        return (min(xs), min(ys), max(xs), max(ys))
    
    top_region = calculate_region_bounds(top_4)
    bottom_region = calculate_region_bounds(bottom_4)
    
    print(f"\n[REGION ANALYSIS]")
    print(f"Top region bounds: {top_region}")
    print(f"Bottom region bounds: {bottom_region}")
    
    # Analyze content of both regions to determine which is Quick Answers
    top_rectangles, top_circles = analyze_region_content(
        image[top_region[1]:top_region[3], top_region[0]:top_region[2]]
    )
    bottom_rectangles, bottom_circles = analyze_region_content(
        image[bottom_region[1]:bottom_region[3], bottom_region[0]:bottom_region[2]]
    )
    
    # DECISION LOGIC: Quick Answers has rectangles, Student ID has circles
    top_ratio = top_rectangles / (top_circles + 1)  # +1 to avoid division by zero
    bottom_ratio = bottom_rectangles / (bottom_circles + 1)
    
    print(f"\n[REGION DIFFERENTIATION]")
    print(f"Top region - rectangles: {top_rectangles}, circles: {top_circles}, ratio: {top_ratio:.2f}")
    print(f"Bottom region - rectangles: {bottom_rectangles}, circles: {bottom_circles}, ratio: {bottom_ratio:.2f}")
    
    # Determine which region is Quick Answers based on rectangle-to-circle ratio
    if top_ratio > bottom_ratio and top_rectangles > 0:
        qa_region = top_region
        qa_markers = top_4
        print("[DECISION] Quick Answers region identified: TOP (more rectangles)")
    elif bottom_ratio > top_ratio and bottom_rectangles > 0:
        qa_region = bottom_region
        qa_markers = bottom_4
        print("[DECISION] Quick Answers region identified: BOTTOM (more rectangles)")
    elif top_rectangles > 0:
        qa_region = top_region
        qa_markers = top_4
        print("[DECISION] Quick Answers region identified: TOP (has rectangles)")
    elif bottom_rectangles > 0:
        qa_region = bottom_region
        qa_markers = bottom_4
        print("[DECISION] Quick Answers region identified: BOTTOM (has rectangles)")
    else:
        print("[WARNING] Could not identify Quick Answers region - no rectangles found in either region")
        # Fallback: assume top is Quick Answers (typical layout)
        qa_region = top_region
        qa_markers = top_4
        print("[FALLBACK] Using TOP region as Quick Answers")
    
    x_min, y_min, x_max, y_max = qa_region
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    # Final validation
    if x_range < 50 or y_range < 100:
        print("[WARNING] Quick Answers region too small - likely incorrect detection")
        return None
    
    print(f"\n[SUCCESS] Quick Answers region: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    print(f"           Size: {x_range}x{y_range} pixels")
    print(f"           Contains: {top_rectangles if qa_region == top_region else bottom_rectangles} rectangles")
    
    # Show debug visualization
    if show_debug and debug_img is not None:
        # Draw both regions for comparison
        # Student ID region (the other one)
        other_region = bottom_region if qa_region == top_region else top_region
        cv2.rectangle(debug_img, (other_region[0], other_region[1]), 
                     (other_region[2], other_region[3]), (0, 255, 255), 2)
        cv2.putText(debug_img, "STUDENT ID", (other_region[0], other_region[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Quick Answers region
        cv2.rectangle(debug_img, (x_min, y_min), (x_max, y_max), (255, 165, 0), 3)
        cv2.putText(debug_img, "QUICK ANSWERS", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
        
        # Highlight markers
        for (cx, cy, area, w, h) in qa_markers:
            cv2.circle(debug_img, (cx, cy), 8, (255, 0, 0), -1)
        
        # Add info text
        info_text = f"Rectangles: {top_rectangles if qa_region == top_region else bottom_rectangles}"
        cv2.putText(debug_img, info_text, (x_min, y_min - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 165, 0), 2)
        
        # Resize for display if needed
        height, width = debug_img.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            debug_img = cv2.resize(debug_img, (new_width, new_height))
        
        cv2.imshow('Quick Answer Marker Detection - REGIONS IDENTIFIED', debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return (x_min, y_min, x_max, y_max)


def detect_answer_rectangles(image, qa_region, show_visualization=False):
    """
    Detect rectangular outline answer boxes within the Quick Answers region
    
    Args:
        image: Input image (BGR)
        qa_region: (x_min, y_min, x_max, y_max) bounding box of Quick Answers region
        show_visualization: If True, display detection visualization
        
    Returns:
        List of detected rectangles with positions and numbers
    """
    x_min, y_min, x_max, y_max = qa_region
    
    print(f"\n[INFO] Detecting answer rectangles in region: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    
    # Extract region of interest
    roi = image[y_min:y_max, x_min:x_max]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Create debug image for the ROI
    roi_debug = roi.copy()
    
    # Method 1: Simple approach - look for horizontal and vertical lines
    print("[DEBUG] Using line detection approach...")
    
    # Use binary threshold to highlight dark lines
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    
    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    
    # Detect vertical lines  
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    
    # Combine horizontal and vertical lines
    line_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
    
    # Find contours of the line intersections (potential rectangles)
    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"[DEBUG] Found {len(contours)} contours from line detection")
    
    rectangles = []
    
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Basic size filtering
        if w < 150 or h < 25 or area < 1000:
            continue
            
        aspect_ratio = float(w) / h
        
        # Look for wide rectangles (answer boxes)
        if aspect_ratio > 2.0 and aspect_ratio < 8.0:
            # FIXED: Use y_min + y instead of x_min + y
            abs_x = x_min + x
            abs_y = y_min + y  # FIXED THIS LINE
            
            rectangles.append({
                'x': abs_x,
                'y': abs_y,
                'width': w,
                'height': h,
                'center_x': abs_x + w // 2,
                'center_y': abs_y + h // 2,
                'area': area,
                'aspect_ratio': aspect_ratio,
                'method': 'line_detection'
            })
            
            print(f"  ✓ Line detection: ({abs_x}, {abs_y}), {w}x{h}px")
    
    # Method 2: If line detection fails, try contour approximation
    if not rectangles:
        print("[DEBUG] Trying contour approximation...")
        
        # Use a cleaner binary image
        _, clean_binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(clean_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue
                
            # Get bounding rect
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Check if it's a wide rectangle
            aspect_ratio = float(w) / h
            if aspect_ratio > 2.0 and w > 120 and h > 20:
                # FIXED: Use y_min + y instead of x_min + y
                abs_x = x_min + x
                abs_y = y_min + y  # FIXED THIS LINE
                
                rectangles.append({
                    'x': abs_x,
                    'y': abs_y,
                    'width': w,
                    'height': h,
                    'center_x': abs_x + w // 2,
                    'center_y': abs_y + h // 2,
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'method': 'bounding_rect'
                })
                
                print(f"  ✓ Bounding rect: ({abs_x}, {abs_y}), {w}x{h}px")
    
    # Method 3: Manual grid detection (fallback)
    if not rectangles:
        print("[DEBUG] Using manual grid detection...")
        
        # Assume answer boxes are arranged in a vertical grid
        # with consistent spacing and size
        
        # Look for horizontal lines that span most of the width
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 1))
        horizontal_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        horizontal_contours, _ = cv2.findContours(horizontal_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Get Y positions of horizontal lines
        y_positions = []
        for cnt in horizontal_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 200:  # Long horizontal line
                y_positions.append(y + h // 2)
        
        # Sort and group by Y position
        y_positions.sort()
        
        # Create rectangles from consecutive horizontal lines
        for i in range(len(y_positions) - 1):
            y_top = y_positions[i]
            y_bottom = y_positions[i + 1]
            height = y_bottom - y_top
            
            # Check if this could be an answer box height
            if 25 < height < 80:
                # Assume standard width
                x_left = 50
                x_right = 450
                width = x_right - x_left
                
                # FIXED: Use y_min + y_top instead of x_min + y_top
                abs_x = x_min + x_left
                abs_y = y_min + y_top  # FIXED THIS LINE
                
                rectangles.append({
                    'x': abs_x,
                    'y': abs_y,
                    'width': width,
                    'height': height,
                    'center_x': abs_x + width // 2,
                    'center_y': abs_y + height // 2,
                    'area': width * height,
                    'aspect_ratio': float(width) / height,
                    'method': 'manual_grid'
                })
                
                print(f"  ✓ Manual grid: ({abs_x}, {abs_y}), {width}x{height}px")
    
    # Remove duplicates
    unique_rectangles = []
    for rect in rectangles:
        is_duplicate = False
        for existing in unique_rectangles:
            # Check center distance
            center_dist = np.sqrt((rect['center_x'] - existing['center_x'])**2 + 
                                 (rect['center_y'] - existing['center_y'])**2)
            if center_dist < 30:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_rectangles.append(rect)
    
    rectangles = unique_rectangles
    
    if not rectangles:
        print("[ERROR] No rectangles detected with any method!")
        # Show debug images
        if show_visualization:
            cv2.imshow('ROI Gray', gray)
            cv2.imshow('Binary', binary)
            cv2.imshow('Horizontal Lines', horizontal_lines)
            cv2.imshow('Vertical Lines', vertical_lines)
            cv2.imshow('Line Mask', line_mask)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None
    
    # Sort by Y position
    rectangles.sort(key=lambda r: r['center_y'])
    
    # Assign question numbers
    for i, rect in enumerate(rectangles, start=1):
        rect['question_number'] = i
    
    print(f"\n[SUCCESS] Detected {len(rectangles)} answer rectangles using {rectangles[0]['method'] if rectangles else 'unknown'}")
    
    # Visualization
    if show_visualization:
        output = image.copy()
        
        # Draw Quick Answers region
        cv2.rectangle(output, (x_min, y_min), (x_max, y_max), (255, 165, 0), 3)
        cv2.putText(output, "QUICK ANSWERS REGION", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 165, 0), 2)
        
        # Draw detected rectangles in RED
        for rect in rectangles:
            x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
            qnum = rect['question_number']
            
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(output, f"Q{qnum}", (x - 40, y + h // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
            
            print(f"  Q{qnum}: ({x}, {y}) - {w}x{h}px")
        
        # Resize and display
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('Detected Answer Rectangles - RED', output)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return rectangles

def detect_quick_answers_in_image(image_path, show_visualization=False):
    """
    Main detection function for Quick Number Answers
    
    Args:
        image_path: Path to image file
        show_visualization: If True, display detection visualization
        
    Returns:
        Dictionary with Quick Answers data, or None if not found
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Image not found at {image_path}")
        return None
    
    print("\n" + "="*60)
    print("DETECTING QUICK NUMBER ANSWERS REGION")
    print("="*60)
    
    # Detect Quick Answers region markers
    qa_region = detect_quick_answer_markers(image, show_debug=show_visualization)
    
    if qa_region is None:
        print("\n[WARNING] Could not detect Quick Answers region!")
        return None
    
    # Detect answer rectangles
    rectangles = detect_answer_rectangles(image, qa_region, show_visualization)
    
    if rectangles is None:
        print("\n[WARNING] No answer rectangles found in Quick Answers region!")
        return None
    
    qa_data = {
        'region_bounds': {
            'x_min': qa_region[0],
            'y_min': qa_region[1],
            'x_max': qa_region[2],
            'y_max': qa_region[3]
        },
        'total_questions': len(rectangles),
        'answer_boxes': rectangles
    }
    
    print(f"\n[SUCCESS] Quick Answers detection complete:")
    print(f"  Total questions: {len(rectangles)}")
    print(f"  Region: {qa_region}")
    
    return qa_data


# The rest of your functions remain the same...
def convert_pdf_to_png(pdf_path, output_folder='pdf_converted', dpi=300):
    """Convert PDF to PNG images"""
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Converting PDF: {pdf_path}")
    try:
        pdf_document = fitz.open(pdf_path)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        
        png_paths = []
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=mat)
            
            output_path = os.path.join(output_folder, f"{base_name}_page_{page_num + 1}.png")
            pix.save(output_path)
            png_paths.append(output_path)
            print(f"  Saved: {output_path}")
        
        pdf_document.close()
        print(f"[SUCCESS] Converted {len(png_paths)} page(s) successfully!")
        return png_paths
        
    except Exception as e:
        print(f"Error converting PDF: {e}")
        raise


def process_pdf_quick_answers(pdf_path, dpi=300, keep_png=False, show_visualization=True):
    """Complete workflow for PDF processing"""
    print("\n" + "="*60)
    print("QUICK ANSWERS PDF PROCESSING WORKFLOW")
    print("="*60)
    
    try:
        png_paths = convert_pdf_to_png(pdf_path, dpi=dpi)
    except Exception as e:
        print(f"\n[ERROR] Failed to convert PDF: {e}")
        return None
    
    template_data = {}
    
    for i, png_path in enumerate(png_paths, start=1):
        print(f"\n{'='*60}")
        print(f"PROCESSING PAGE {i}/{len(png_paths)}")
        print(f"{'='*60}")
        
        # Detect Quick Answers
        qa_data = detect_quick_answers_in_image(png_path, show_visualization=show_visualization)
        
        # Get image dimensions
        img = cv2.imread(png_path)
        if img is None:
            print(f"[ERROR] Could not read image: {png_path}")
            continue
            
        height, width = img.shape[:2]
        
        template_data[f"page_{i}"] = {
            'png_path': png_path if keep_png else None,
            'image_dimensions': {'width': width, 'height': height, 'dpi': dpi},
            'quick_answers': qa_data
        }
        
        print(f"\nPage {i} Summary:")
        if qa_data:
            print(f"  Quick Answers: Detected ({qa_data['total_questions']} questions)")
        else:
            print(f"  Quick Answers: Not found")
    
    # Save to JSON
    json_path = save_quick_answers_template_to_json(template_data, pdf_path)
    
    # Cleanup if not keeping PNGs
    if not keep_png:
        for png_path in png_paths:
            try:
                os.remove(png_path)
            except:
                pass
    
    return json_path


def save_quick_answers_template_to_json(template_data, source_file, output_dir='template'):
    """Save template data to JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    json_filename = f"{base_name}_quick_answers.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Quick Answers template saved to: {json_path}")
    return json_path


# Example usage
if __name__ == "__main__":
    # Process PDF file
    json_path = process_pdf_quick_answers(
        pdf_path='test_sheet_full.pdf',
        dpi=300,
        keep_png=False,
        show_visualization=True
    )
    
    if json_path:
        print(f"\nProcessing complete! Template saved to: {json_path}")