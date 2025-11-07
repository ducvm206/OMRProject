import cv2
import numpy as np
import pytesseract
import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe'

def convert_pdf_to_png(pdf_path, output_folder='pdf_converted', dpi=300):
    """
    Convert all pages of a PDF to PNG images using PyMuPDF
    
    Args:
        pdf_path: Path to PDF file
        output_folder: Folder to save converted PNG files
        dpi: Resolution (300 is good quality, 150 for faster processing)
        
    Returns:
        List of paths to generated PNG files
    """
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Converting PDF: {pdf_path}")
    print(f"Output folder: {output_folder}")
    print(f"DPI: {dpi}")
    
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
        print("\nMake sure PyMuPDF is installed:")
        print("  pip install PyMuPDF")
        raise


def detect_corner_markers(image, show_debug=True):
    """
    Detect the 4 black square corner markers that define the Student ID region
    
    Args:
        image: Input image (BGR)
        show_debug: If True, show debug visualization
        
    Returns:
        Bounding box (x_min, y_min, x_max, y_max) of ID region, or None if not found
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Look for square-shaped contours (corner markers)
    markers = []
    debug_img = image.copy() if show_debug else None
    
    print(f"\n[DEBUG] Analyzing {len(contours)} contours for corner markers...")
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Adjust this range based on your actual corner marker size
        # Try different values: 200-1000, 300-2000, etc.
        if 200 < area < 2000:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # More strict square requirement
            if 0.85 < aspect_ratio < 1.15:
                # Check if it's filled (dark)
                mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                mean_val = cv2.mean(gray, mask=mask)[0]
                
                # Should be very dark (corner markers are solid black)
                if mean_val < 60:
                    # Check it's actually rectangular (not circular like bubbles)
                    rect_area = w * h
                    fill_ratio = area / rect_area if rect_area > 0 else 0
                    
                    # Rectangles fill their bounding box more than circles do
                    # Circles fill ~78% (π/4), rectangles fill ~100%
                    if fill_ratio > 0.85:
                        center_x = x + w // 2
                        center_y = y + h // 2
                        markers.append((center_x, center_y, area, w, h))
                        print(f"  Found candidate: area={area}, size={w}x{h}, "
                              f"aspect={aspect_ratio:.2f}, darkness={mean_val:.1f}, "
                              f"fill={fill_ratio:.2f}")
                        
                        if show_debug:
                            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.circle(debug_img, (center_x, center_y), 5, (0, 255, 0), -1)
    
    print(f"\n[INFO] Found {len(markers)} corner marker candidates")
    
    # Need exactly 4 markers (or at least 4)
    if len(markers) < 4:
        print(f"[WARNING] Found only {len(markers)} corner markers (need 4 for ID region)")
        if show_debug and debug_img is not None:
            cv2.imshow('Corner Marker Detection - FAILED', debug_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None
    
    # Take the 4 largest markers
    markers_sorted = sorted(markers, key=lambda m: m[2], reverse=True)[:4]
    
    xs = [m[0] for m in markers_sorted]
    ys = [m[1] for m in markers_sorted]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    # Validate that markers form a proper rectangle
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    print(f"\n[VALIDATION] Marker spread: {x_range}px wide x {y_range}px tall")
    
    # The 4 corners should span a reasonable area
    if x_range < 100 or y_range < 100:
        print("[WARNING] Markers too close together - might not be actual corner markers")
        if show_debug and debug_img is not None:
            cv2.rectangle(debug_img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 3)
            cv2.imshow('Corner Marker Detection - TOO SMALL', debug_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None
    
    # Check aspect ratio of the region
    region_aspect = x_range / y_range if y_range > 0 else 0
    print(f"[VALIDATION] Region aspect ratio: {region_aspect:.2f}")
    
    print(f"\n[SUCCESS] Student ID region: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    print(f"           Size: {x_range}x{y_range} pixels")
    
    # Show debug visualization
    if show_debug and debug_img is not None:
        # Highlight the 4 selected markers
        for (cx, cy, area, w, h) in markers_sorted:
            cv2.circle(debug_img, (cx, cy), 10, (255, 0, 0), -1)
        
        # Draw the ID region boundary
        cv2.rectangle(debug_img, (x_min, y_min), (x_max, y_max), (0, 255, 255), 3)
        cv2.putText(debug_img, "ID REGION", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        # Resize for display if needed
        height, width = debug_img.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            debug_img = cv2.resize(debug_img, (new_width, new_height))
        
        cv2.imshow('Corner Marker Detection - SUCCESS', debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return (x_min, y_min, x_max, y_max)


def detect_bubbles_in_region(image, region_mask=None, show_visualization=False):
    """
    Detect bubbles in image, optionally restricted to a region
    
    Args:
        image: Input image (BGR)
        region_mask: Binary mask (255=detect, 0=ignore), or None for entire image
        show_visualization: If True, display detection visualization
        
    Returns:
        List of detected bubble groups with coordinates
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Apply region mask if provided
    if region_mask is not None:
        thresh = cv2.bitwise_and(thresh, thresh, mask=region_mask)
    
    if show_visualization:
        cv2.imshow('Thresholded', thresh)
        cv2.waitKey(500)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bubble_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 100 < area < 4000:
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            if 10 < radius < 50:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * (area / (perimeter * perimeter))
                # Bubbles should be circular, unlike square corner markers
                if 0.7 < circularity < 1.2:
                    bubble_contours.append((int(x), int(y), int(radius), cnt))
    
    return bubble_contours


def detect_question_bubbles(image, id_region=None, show_visualization=False):
    """
    Detect question bubbles (excluding ID region)
    
    Args:
        image: Input image
        id_region: (x_min, y_min, x_max, y_max) to exclude, or None
        show_visualization: If True, display detection
        
    Returns:
        List of detected questions with coordinates
    """
    # Create mask for question region (everything EXCEPT ID region)
    height, width = image.shape[:2]
    region_mask = np.ones((height, width), dtype=np.uint8) * 255
    
    if id_region is not None:
        x_min, y_min, x_max, y_max = id_region
        # Expand exclusion zone slightly
        padding = 20
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(width, x_max + padding)
        y_max = min(height, y_max + padding)
        
        # Black out ID region in mask
        region_mask[y_min:y_max, x_min:x_max] = 0
        print(f"[INFO] Excluding ID region from question detection: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    else:
        print(f"[INFO] No ID region to exclude - detecting questions in entire image")
    
    # Detect bubbles in question region
    bubble_contours = detect_bubbles_in_region(image, region_mask, show_visualization)
    
    print(f"Detected {len(bubble_contours)} question bubble candidates.")
    
    # Sort and group bubbles
    bubble_contours = sorted(bubble_contours, key=lambda b: (b[1], b[0]))
    
    # Group bubbles into rows
    rows = []
    y_threshold = 30
    for bubble in bubble_contours:
        x, y, r, cnt = bubble
        placed = False
        for row in rows:
            if abs(y - np.mean([b[1] for b in row])) < y_threshold:
                row.append(bubble)
                placed = True
                break
        if not placed:
            rows.append([bubble])
    
    for row in rows:
        row.sort(key=lambda b: b[0])
    
    detected_questions = []
    
    for row in rows:
        radii = [b[2] for b in row]
        if len(radii) == 0:
            continue
        median_radius = np.median(radii)
        filtered_row = [b for b in row if abs(b[2] - median_radius) < 0.3 * median_radius]
        filtered_row = sorted(filtered_row, key=lambda b: b[0])
        
        # Group into sets of 4 (A, B, C, D)
        for i in range(0, len(filtered_row), 4):
            group = filtered_row[i:i+4]
            if len(group) == 4:
                xs = [x for (x, y, r, cnt) in group]
                ys = [y for (x, y, r, cnt) in group]
                r_avg = int(np.mean([r for (x, y, r, cnt) in group]))
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                
                detected_questions.append((group, (x_min, x_max, y_min, y_max, r_avg)))
    
    if not detected_questions:
        return []
    
    # Group into columns and sort
    column_tolerance = 100
    columns = []
    
    for question in detected_questions:
        x_min = question[1][0]
        placed = False
        
        for col in columns:
            col_x_avg = np.mean([q[1][0] for q in col])
            if abs(x_min - col_x_avg) < column_tolerance:
                col.append(question)
                placed = True
                break
        
        if not placed:
            columns.append([question])
    
    columns.sort(key=lambda col: np.mean([q[1][0] for q in col]))
    
    for col in columns:
        col.sort(key=lambda q: q[1][2])
    
    detected_questions_sorted = []
    for col in columns:
        detected_questions_sorted.extend(col)
    
    # Visualization
    if show_visualization:
        output = image.copy()
        pad = 10
        
        # Draw excluded ID region if it exists
        if id_region is not None:
            x_min, y_min, x_max, y_max = id_region
            cv2.rectangle(output, (x_min - padding, y_min - padding), 
                         (x_max + padding, y_max + padding), (0, 0, 255), 2)
            cv2.putText(output, "EXCLUDED (ID)", (x_min, y_min - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        for i, (group, (x_min, x_max, y_min, y_max, r_avg)) in enumerate(detected_questions_sorted):
            cv2.rectangle(
                output,
                (x_min - r_avg - pad, y_min - r_avg - pad),
                (x_max + r_avg + pad, y_max + r_avg + pad),
                (255, 0, 0), 2
            )
            for (x, y, r, cnt) in group:
                cv2.circle(output, (x, y), r, (0, 255, 0), 2)
            print(f"Question {i+1} detected at ({x_min - r_avg - pad}, {y_min - r_avg - pad})")
        
        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))
        
        cv2.imshow('Detected Question Bubbles', output)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return detected_questions_sorted


def detect_id_bubbles(image, id_region, show_visualization=False):
    """
    Detect Student ID bubbles within the marked region (improved column detection).

    Strategy:
    - Detect contours in the ID region (reuse detect_bubbles_in_region).
    - Filter by median radius to remove outliers.
    - Cluster columns by looking for large gaps in sorted x-coordinates (adaptive).
    - Accept columns that are close to 10 bubbles (allow tolerance).
    - If needed, fall back to a simpler x-threshold grouping.
    - When columns have >10 bubbles, pick 10 positions evenly (nearest to ideal positions).
    """
    x_min, y_min, x_max, y_max = id_region

    print(f"\n[INFO] Detecting ID bubbles in region: ({x_min}, {y_min}) to ({x_max}, {y_max})")

    # Create mask for ID region only
    height, width = image.shape[:2]
    region_mask = np.zeros((height, width), dtype=np.uint8)
    region_mask[y_min:y_max, x_min:x_max] = 255

    # Detect bubbles in ID region
    bubble_contours = detect_bubbles_in_region(image, region_mask, False)
    print(f"Detected {len(bubble_contours)} ID bubble candidates.")

    if not bubble_contours:
        print("[WARNING] No ID bubbles detected in the marked region!")
        return None

    # Filter by radius relative to median to remove gross outliers
    radii = np.array([b[2] for b in bubble_contours])
    med_r = np.median(radii)
    if med_r <= 0:
        med_r = np.mean(radii) if len(radii) else 0

    filtered = [b for b in bubble_contours if abs(b[2] - med_r) < 0.45 * med_r]
    if not filtered:
        # if too aggressive, fall back to original list
        filtered = bubble_contours.copy()

    # Sort by x (primary) then y
    filtered.sort(key=lambda b: (b[0], b[1]))
    xs = np.array([b[0] for b in filtered])

    # If we don't have enough points for gap analysis, fallback to threshold grouping
    if len(xs) < 3:
        print("[INFO] Not enough bubbles for adaptive clustering, using simple grouping.")
        x_threshold = 30
        columns = []
        for b in filtered:
            x, y, r, cnt = b
            placed = False
            for col in columns:
                col_x_avg = np.mean([c[0] for c in col])
                if abs(x - col_x_avg) < x_threshold:
                    col.append(b)
                    placed = True
                    break
            if not placed:
                columns.append([b])
    else:
        # Adaptive 1D clustering using large gaps in sorted x
        gaps = np.diff(xs)
        median_gap = np.median(gaps)
        std_gap = np.std(gaps)
        split_thresh = max(1.8 * median_gap, median_gap + 1.5 * std_gap, 30)  # at least 30 px
        split_indices = np.where(gaps > split_thresh)[0]

        columns = []
        start = 0
        for idx in split_indices:
            columns.append(filtered[start:idx + 1])
            start = idx + 1
        columns.append(filtered[start:])

    # Sort columns left-to-right and entries top-to-bottom
    columns = [sorted(col, key=lambda b: b[1]) for col in columns]
    columns.sort(key=lambda col: np.mean([b[0] for b in col]) if col else 0)

    print(f"[INFO] Found {len(columns)} raw columns after clustering")

    # Keep only columns that are near 10 bubbles (allow tolerance)
    valid_columns = [col for col in columns if 8 <= len(col) <= 12]

    # If none found, relax criteria: pick columns closest to 10 bubbles
    if not valid_columns:
        # rank cols by closeness to 10
        columns_sorted = sorted(columns, key=lambda c: abs(len(c) - 10))
        # keep up to a reasonable number (e.g., top 6)
        valid_columns = columns_sorted[:min(6, len(columns_sorted))]
        print(f"[INFO] No strict-valid columns; selected {len(valid_columns)} best candidates by count")

    # For each selected column ensure exactly 10 bubbles:
    final_columns = []
    for col in valid_columns:
        col = sorted(col, key=lambda b: b[1])  # top-to-bottom
        if len(col) == 10:
            final_columns.append(col)
            continue
        if len(col) > 10:
            # pick 10 by matching to 10 evenly spaced targets across the column's y-range
            ys = np.array([b[1] for b in col])
            targets = np.linspace(ys.min(), ys.max(), 10)
            chosen = []
            used = set()
            for t in targets:
                idx = int(np.argmin(np.abs(ys - t)))
                # avoid picking same bubble twice
                if idx in used:
                    # choose nearest unused neighbor
                    offsets = np.arange(len(ys))
                    best = None
                    best_dist = 1e9
                    for off in offsets:
                        if off in used:
                            continue
                        d = abs(ys[off] - t)
                        if d < best_dist:
                            best_dist = d
                            best = off
                    idx = best if best is not None else idx
                used.add(idx)
                chosen.append(col[idx])
            # de-duplicate and keep order top-to-bottom
            chosen_unique = []
            seen = set()
            for b in chosen:
                key = (b[0], b[1])
                if key not in seen:
                    seen.add(key)
                    chosen_unique.append(b)
            # If still not 10 due to duplicates, take first 10
            chosen_unique = sorted(chosen_unique, key=lambda b: b[1])[:10]
            if len(chosen_unique) == 10:
                final_columns.append(chosen_unique)
            else:
                # fallback: take 10 largest by y spacing
                final_columns.append(sorted(col, key=lambda b: b[1])[:10])
        else:
            # len < 10: skip if too few, otherwise keep as-is (best effort)
            if len(col) >= 7:
                final_columns.append(col)
            else:
                print(f"[DEBUG] Rejecting small column with {len(col)} bubbles")

    if not final_columns:
        print("[WARNING] No final ID columns found after refinement")
        return None

    # Build id_data structure
    id_data = {
        'digit_columns': [],
        'total_digits': len(final_columns)
    }

    for col_idx, col in enumerate(final_columns):
        # sort top-to-bottom
        col = sorted(col, key=lambda b: b[1])
        digit_data = {
            'digit_position': col_idx + 1,
            'bubbles': []
        }
        for row_idx, (x, y, r, cnt) in enumerate(col):
            digit_data['bubbles'].append({
                'digit': row_idx,  # 0-9 (order by position)
                'x': int(x),
                'y': int(y),
                'radius': int(r)
            })
        id_data['digit_columns'].append(digit_data)

    print(f"[SUCCESS] {len(final_columns)} valid digit columns after clustering/refinement")

    # Visualization (only valid bubbles)
    if show_visualization:
        output = image.copy()
        cv2.rectangle(output, (x_min, y_min), (x_max, y_max), (0, 255, 255), 3)
        cv2.putText(output, "ID REGION", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        for col_idx, col in enumerate(final_columns):
            for row_idx, (x, y, r, cnt) in enumerate(col):
                cv2.circle(output, (x, y), r, (255, 0, 255), 2)
                cv2.putText(output, str(row_idx), (x - 5, y + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

        height, width = output.shape[:2]
        max_height = 900
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            output = cv2.resize(output, (new_width, new_height))

        cv2.imshow('Detected ID Bubbles (refined)', output)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return id_data


def detect_bubbles_in_image(image_path, show_visualization=False):
    """
    Main detection function: detects both questions and student ID
    
    Args:
        image_path: Path to image file
        show_visualization: If True, display detection visualization
        
    Returns:
        Tuple of (questions, id_data)
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Image not found at {image_path}")
        return [], None
    
    print("\n" + "="*60)
    print("STEP 1: Detecting Student ID Region (Corner Markers)")
    print("="*60)
    
    # Detect corner markers to find ID region
    id_region = detect_corner_markers(image, show_debug=show_visualization)
    
    if id_region is None:
        print("\n[WARNING] Could not detect ID region!")
        print("Possible issues:")
        print("  - Corner markers not visible or too small/large")
        print("  - Markers not dark enough")
        print("  - Markers not square-shaped enough")
        print("\nTip: Adjust area threshold (200-2000) and darkness threshold (<60)")
        print("     in detect_corner_markers() function")
    
    print("\n" + "="*60)
    print("STEP 2: Detecting Question Bubbles")
    print("="*60)
    
    # Detect question bubbles (excluding ID region)
    questions = detect_question_bubbles(image, id_region, show_visualization)
    
    # Detect ID bubbles if region was found
    id_data = None
    if id_region is not None:
        print("\n" + "="*60)
        print("STEP 3: Detecting Student ID Bubbles")
        print("="*60)
        id_data = detect_id_bubbles(image, id_region, show_visualization)
    else:
        print("\n" + "="*60)
        print("STEP 3: Skipping ID Bubble Detection (no region found)")
        print("="*60)
    
    return questions, id_data


def save_template_to_json(template_data, source_file, output_dir='template'):
    """
    Save template data to JSON file in template directory
    
    Args:
        template_data: Dictionary containing template information
        source_file: Original source file path (PDF or image)
        output_dir: Directory to save JSON template
        
    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    json_filename = f"{base_name}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Add metadata
    template_data['metadata'] = {
        'source_file': source_file,
        'created_at': datetime.now().isoformat(),
        'total_pages': len([k for k in template_data.keys() if k.startswith('page_')]),
        'total_questions': sum(
            template_data[page]['questions_detected'] 
            for page in template_data 
            if page.startswith('page_')
        )
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Template saved to: {json_path}")
    return json_path


def convert_question_data_to_json_serializable(questions):
    """
    Convert question detection data to JSON-serializable format
    
    Args:
        questions: List of detected questions with contours
        
    Returns:
        List of question dictionaries with serializable data
    """
    json_questions = []
    
    for i, (group, (x_min, x_max, y_min, y_max, r_avg)) in enumerate(questions):
        question_dict = {
            'question_number': i + 1,
            'bounding_box': {
                'x_min': int(x_min),
                'x_max': int(x_max),
                'y_min': int(y_min),
                'y_max': int(y_max),
                'avg_radius': int(r_avg)
            },
            'bubbles': []
        }
        
        # Add individual bubble coordinates (A, B, C, D)
        bubble_labels = ['A', 'B', 'C', 'D']
        for j, (x, y, r, cnt) in enumerate(group):
            if j < len(bubble_labels):
                question_dict['bubbles'].append({
                    'label': bubble_labels[j],
                    'x': int(x),
                    'y': int(y),
                    'radius': int(r)
                })
        
        json_questions.append(question_dict)
    
    return json_questions


def process_pdf_answer_sheet(pdf_path, dpi=300, keep_png=False, show_visualization=True):
    """
    Complete workflow: Convert PDF to PNG, detect bubbles, save to JSON
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for PDF conversion
        keep_png: If True, keep converted PNG files
        show_visualization: If True, show detection visualization
        
    Returns:
        Path to saved JSON template file
    """
    
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
        print(f"File: {png_path}")
        
        # Detect both questions and ID
        questions, id_data = detect_bubbles_in_image(png_path, show_visualization=show_visualization)
        
        # Get image dimensions
        img = cv2.imread(png_path)
        height, width = img.shape[:2]
        
        template_data[f"page_{i}"] = {
            'png_path': png_path if keep_png else None,
            'image_dimensions': {
                'width': width,
                'height': height,
                'dpi': dpi
            },
            'questions_detected': len(questions),
            'questions': convert_question_data_to_json_serializable(questions),
            'student_id': id_data
        }
        
        print(f"\nPage {i} Summary:")
        print(f"  Questions: {len(questions)}")
        if id_data:
            print(f"  Student ID: Detected ({id_data['total_digits']} digits)")
        else:
            print(f"  Student ID: Not found")
    
    # Save to JSON
    json_path = save_template_to_json(template_data, pdf_path)
    
    # Cleanup PNG files if not keeping
    if not keep_png:
        print("\n" + "="*60)
        print("CLEANING UP TEMPORARY FILES")
        print("="*60)
        for png_path in png_paths:
            try:
                os.remove(png_path)
                print(f"  Deleted: {png_path}")
            except:
                pass
    
    # Summary
    total_questions = template_data['metadata']['total_questions']
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total pages: {template_data['metadata']['total_pages']}")
    print(f"Total questions: {total_questions}")
    print(f"Template saved: {json_path}")
    
    return json_path


def load_template_from_json(json_path):
    """
    Load a saved template from JSON file
    
    Args:
        json_path: Path to JSON template file
        
    Returns:
        Dictionary containing template data
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    print(f"[LOADED] Template from: {json_path}")
    print(f"  Pages: {template_data['metadata']['total_pages']}")
    print(f"  Questions: {template_data['metadata']['total_questions']}")
    print(f"  Created: {template_data['metadata']['created_at']}")
    
    return template_data


# Example usage
if __name__ == "__main__":
    
    # Process a PDF
    print("Processing PDF with Student ID detection")
    json_path = process_pdf_answer_sheet(
        pdf_path='answer_sheet_10q.pdf',
        dpi=300,
        keep_png=False,
        show_visualization=True
    )
    
    # Load and inspect
    if json_path:
        template = load_template_from_json(json_path)
        
        # Show structure
        for page_key in template:
            if page_key.startswith('page_'):
                page_data = template[page_key]
                print(f"\n{page_key}:")
                print(f"  Questions: {page_data['questions_detected']}")
                print(f"  Student ID: {page_data['student_id'] is not None}")
                
                if page_data['student_id']:
                    print(f"  ID Digits: {page_data['student_id']['total_digits']}")