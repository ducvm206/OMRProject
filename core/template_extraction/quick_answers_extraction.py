import cv2
import numpy as np
import json
import os
import fitz  # PyMuPDF
from datetime import datetime


def detect_quick_answer_markers(image, show_debug=True):
    """
    Detect the 4 black square corner markers that define the Quick Number Answers region
    Markers are 9pt squares
    
    Args:
        image: Input image (BGR)
        show_debug: If True, show debug visualization
        
    Returns:
        Bounding box (x_min, y_min, x_max, y_max) of Quick Answers region, or None if not found
    """
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Look for 9pt square markers
    qa_markers = []
    debug_img = image.copy() if show_debug else None
    
    print(f"\n[DEBUG] Analyzing {len(contours)} contours for Quick Answer markers...")
    print(f"[DEBUG] Looking for 9pt squares (area: 800-1500)")
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # 9pt markers: smaller squares for Quick Answers
        if 800 < area < 1500:
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
                        # Store top-left corner and dimensions
                        qa_markers.append((x, y, w, h))
                        print(f"  [9pt QA marker] pos=({x},{y}), size={w}x{h}, area={area:.0f}")
    
    print(f"\n[INFO] Found {len(qa_markers)} markers (9pt Quick Answers)")
    
    # Check if we have enough markers
    if len(qa_markers) < 4:
        print(f"[WARNING] Found only {len(qa_markers)} QA markers (need 4+)")
        if show_debug and debug_img is not None:
            cv2.imshow('Quick Answer Marker Detection - FAILED', debug_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None
    
    # Calculate bounding box using ALL 4 corner markers
    # The region extends from the outer edges of the markers
    all_x_left = min([m[0] for m in qa_markers])  # Leftmost edge
    all_x_right = max([m[0] + m[2] for m in qa_markers])  # Rightmost edge
    all_y_top = min([m[1] for m in qa_markers])  # Topmost edge
    all_y_bottom = max([m[1] + m[3] for m in qa_markers])  # Bottommost edge
    
    print(f"\n[REGION ANALYSIS]")
    print(f"All markers X range: {all_x_left} to {all_x_right}")
    print(f"All markers Y range: {all_y_top} to {all_y_bottom}")
    
    # The QA region is defined by the outer bounds of these 4 markers
    x_min = all_x_left
    y_min = all_y_top
    x_max = all_x_right
    y_max = all_y_bottom
    
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    print(f"Quick Answers region bounds: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    print(f"Region size: {x_range}x{y_range} pixels")
    
    # Final validation
    if x_range < 50 or y_range < 100:
        print("[WARNING] Quick Answers region too small - likely incorrect detection")
        return None
    
    print(f"\n[SUCCESS] Quick Answers region: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    print(f"           Size: {x_range}x{y_range} pixels")
    print(f"           Marker type: 9pt Quick Answers markers")
    
    # Show debug visualization
    if show_debug and debug_img is not None:
        # Quick Answers region
        cv2.rectangle(debug_img, (x_min, y_min), (x_max, y_max), (255, 165, 0), 3)
        cv2.putText(debug_img, "QUICK ANSWERS REGION", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
        
        # Highlight markers with blue circles
        for (x, y, w, h) in qa_markers:
            cx = x + w // 2
            cy = y + h // 2
            cv2.circle(debug_img, (cx, cy), 8, (255, 0, 0), -1)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 255), 2)
        
        # Resize for display if needed
        height, width = debug_img.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            debug_img = cv2.resize(debug_img, (new_width, new_height))
        
        cv2.imshow('01 - Marker Detection - QA Region Identified', debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return (x_min, y_min, x_max, y_max)


def detect_hollow_rectangles(binary_image, x_offset=0, y_offset=0, min_width=150, max_width=500, min_height=20, max_height=100):
    """
    Detect hollow rectangular boxes (answer boxes with borders but no fill)
    
    Args:
        binary_image: Binary image
        x_offset: X offset for absolute coordinates
        y_offset: Y offset for absolute coordinates
        min_width, max_width: Width range
        min_height, max_height: Height range
        
    Returns:
        List of detected hollow rectangles
    """
    hollow_rects = []
    
    # Find all contours
    contours, _ = cv2.findContours(binary_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Skip if outside size range
        if not (min_width < w < max_width and min_height < h < max_height):
            continue
        
        # Check aspect ratio for rectangles
        aspect_ratio = float(w) / h if h > 0 else 0
        if aspect_ratio < 2.0 or aspect_ratio > 8.0:
            continue
        
        # For hollow rectangles, the area should be much smaller than w*h
        # (because it's just the border, not filled)
        rect_area = w * h
        fill_ratio = area / rect_area if rect_area > 0 else 0
        
        # Hollow box: low fill ratio (5-40%)
        if 0.05 < fill_ratio < 0.4:
            abs_x = x_offset + x
            abs_y = y_offset + y
            
            hollow_rects.append({
                'x': abs_x,
                'y': abs_y,
                'width': w,
                'height': h,
                'center_x': abs_x + w // 2,
                'center_y': abs_y + h // 2,
                'area': area,
                'aspect_ratio': aspect_ratio,
                'fill_ratio': fill_ratio,
                'method': 'hollow_detection'
            })
    
    return hollow_rects


def detect_answer_rectangles(image, qa_region, show_visualization=False):
    """
    Detect rectangular outline answer boxes within the Quick Answers region
    Includes hollow rectangles and solid line detection
    
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
    
    # Create debug images
    roi_debug = roi.copy()
    
    rectangles = []
    
    # ========== METHOD 1: Detect HOLLOW rectangles ==========
    print("[DEBUG] Method 1: Detecting hollow rectangular boxes...")
    
    # Use binary threshold to find borders
    _, binary_hollow = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    
    # Show binary image for hollow detection
    if show_visualization:
        display_binary_hollow = binary_hollow.copy()
        cv2.imshow('02 - Binary (Hollow Detection)', display_binary_hollow)
    
    # Get hollow rectangles
    hollow_rects = detect_hollow_rectangles(
        binary_hollow, 
        x_offset=x_min, 
        y_offset=y_min,
        min_width=120,
        max_width=600,
        min_height=15,
        max_height=120
    )
    
    rectangles.extend(hollow_rects)
    print(f"[DEBUG] Found {len(hollow_rects)} hollow rectangles")
    
    for rect in hollow_rects:
        print(f"  ✓ Hollow rect: ({rect['x']}, {rect['y']}), {rect['width']}x{rect['height']}px, fill_ratio={rect['fill_ratio']:.2f}")
    
    # ========== METHOD 2: Line detection (fallback) ==========
    if len(rectangles) < 3:
        print("[DEBUG] Method 2: Using line detection approach...")
        
        # Use binary threshold to highlight dark lines
        _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
        
        # Detect horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Detect vertical lines  
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Show line detection images
        if show_visualization:
            cv2.imshow('03a - Horizontal Lines', horizontal_lines)
            cv2.imshow('03b - Vertical Lines', vertical_lines)
        
        # Combine horizontal and vertical lines
        line_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
        
        if show_visualization:
            cv2.imshow('03c - Line Mask Combined', line_mask)
        
        # Find contours of the line intersections (potential rectangles)
        contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"[DEBUG] Found {len(contours)} contours from line detection")
        
        line_rects = []
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Basic size filtering
            if w < 150 or h < 25 or area < 1000:
                continue
                
            aspect_ratio = float(w) / h
            
            # Look for wide rectangles (answer boxes)
            if aspect_ratio > 2.0 and aspect_ratio < 8.0:
                abs_x = x_min + x
                abs_y = y_min + y
                
                line_rects.append({
                    'x': abs_x,
                    'y': abs_y,
                    'width': w,
                    'height': h,
                    'center_x': abs_x + w // 2,
                    'center_y': abs_y + h // 2,
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'fill_ratio': area / (w * h) if w * h > 0 else 0,
                    'method': 'line_detection'
                })
                
                print(f"  ✓ Line detection: ({abs_x}, {abs_y}), {w}x{h}px")
        
        if line_rects:
            rectangles.extend(line_rects)
    
    # ========== METHOD 3: Contour approximation (fallback) ==========
    if len(rectangles) < 3:
        print("[DEBUG] Method 3: Trying contour approximation...")
        
        # Use a cleaner binary image
        _, clean_binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        if show_visualization:
            cv2.imshow('04 - Clean Binary (Contour Approx)', clean_binary)
        
        # Find contours
        contours, _ = cv2.findContours(clean_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        approx_rects = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue
                
            # Get bounding rect
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Check if it's a wide rectangle
            aspect_ratio = float(w) / h
            if aspect_ratio > 2.0 and w > 120 and h > 20:
                abs_x = x_min + x
                abs_y = y_min + y
                
                approx_rects.append({
                    'x': abs_x,
                    'y': abs_y,
                    'width': w,
                    'height': h,
                    'center_x': abs_x + w // 2,
                    'center_y': abs_y + h // 2,
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'fill_ratio': area / (w * h) if w * h > 0 else 0,
                    'method': 'bounding_rect'
                })
                
                print(f"  ✓ Bounding rect: ({abs_x}, {abs_y}), {w}x{h}px")
        
        if approx_rects:
            rectangles.extend(approx_rects)
    
    # ========== METHOD 4: Manual grid detection (fallback) ==========
    if len(rectangles) < 3:
        print("[DEBUG] Method 4: Using manual grid detection...")
        
        _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
        
        # Look for horizontal lines that span most of the width
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 1))
        horizontal_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        if show_visualization:
            cv2.imshow('05 - Grid Horizontal Mask', horizontal_mask)
        
        horizontal_contours, _ = cv2.findContours(horizontal_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Get Y positions of horizontal lines
        y_positions = []
        for cnt in horizontal_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 200:  # Long horizontal line
                y_positions.append(y + h // 2)
        
        # Sort and group by Y position
        y_positions.sort()
        
        grid_rects = []
        
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
                
                abs_x = x_min + x_left
                abs_y = y_min + y_top
                
                grid_rects.append({
                    'x': abs_x,
                    'y': abs_y,
                    'width': width,
                    'height': height,
                    'center_x': abs_x + width // 2,
                    'center_y': abs_y + height // 2,
                    'area': width * height,
                    'aspect_ratio': float(width) / height,
                    'fill_ratio': 0.0,
                    'method': 'manual_grid'
                })
                
                print(f"  ✓ Manual grid: ({abs_x}, {abs_y}), {width}x{height}px")
        
        if grid_rects:
            rectangles.extend(grid_rects)
    
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
        if show_visualization:
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None
    
    # Sort by Y position
    rectangles.sort(key=lambda r: r['center_y'])
    
    # Assign question numbers
    for i, rect in enumerate(rectangles, start=1):
        rect['question_number'] = i
    
    print(f"\n[SUCCESS] Detected {len(rectangles)} answer rectangles using {rectangles[0]['method'] if rectangles else 'unknown'}")
    
    for rect in rectangles:
        print(f"  Q{rect['question_number']}: ({rect['x']}, {rect['y']}) - {rect['width']}x{rect['height']}px [method: {rect['method']}]")
    
    # ========== VISUALIZATION ==========
    if show_visualization:
        output = image.copy()
        
        # Draw Quick Answers region border
        cv2.rectangle(output, (x_min, y_min), (x_max, y_max), (255, 165, 0), 3)
        cv2.putText(output, "QUICK ANSWERS REGION", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 165, 0), 2)
        
        # Draw detected rectangles in RED with question numbers
        for rect in rectangles:
            x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
            qnum = rect['question_number']
            
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(output, f"Q{qnum}", (x - 40, y + h // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
        
        # Resize and display
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('06 - Final Detected Answer Rectangles (RED)', output)
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
    
    # Step 1: Detect Quick Answers region markers
    qa_region = detect_quick_answer_markers(image, show_debug=show_visualization)
    
    if qa_region is None:
        print("\n[WARNING] Could not detect Quick Answers region!")
        return None
    
    # Step 2: Detect answer rectangles
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
        pdf_path='test_sheet_with_key.pdf',
        dpi=300,
        keep_png=False,
        show_visualization=True
    )
    
    if json_path:
        print(f"\nProcessing complete! Template saved to: {json_path}")