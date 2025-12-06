import cv2
import numpy as np
import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from PIL import Image


# -----------------------------------------------------------------------------
# Marker size defaults (in POINTS)
# -----------------------------------------------------------------------------
ID_MARKER_PT = 10   # student ID marker printed size in points (pt)
QA_MARKER_PT = 9   # quick answers marker printed size in points (pt)
KEY_MARKER_PT = 7   # key marker printed size in points (pt) - CHANGED FROM 7 to 8
MARKER_TOLERANCE = 0.1  # ± tolerance fraction when matching printed marker size

def fit_to_screen(image, max_height=1000):
    """
    Resize image to fit screen while maintaining aspect ratio
    
    Args:
        image: Input image (BGR)
        max_height: Maximum height in pixels
        
    Returns:
        Resized image
    """
    height, width = image.shape[:2]
    
    if height <= max_height:
        return image
    
    scale = max_height / height
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    resized = cv2.resize(image, (new_width, new_height))
    return resized
# -----------------------------------------------------------------------------
# PDF -> PNG conversion
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Utility: points -> pixels conversion
# -----------------------------------------------------------------------------
def points_to_pixels(points, dpi):
    """
    Convert PDF points (pt) to pixels using DPI.
    1 pt = 1/72 inch, so pixels = points * dpi / 72
    """
    return (points * dpi) / 72.0


# -----------------------------------------------------------------------------
# New: DPI-aware corner marker detection (expects marker size in points)
# -----------------------------------------------------------------------------
def detect_corner_markers_by_expected_size(
    image,
    expected_size_pt,
    dpi=300,
    tolerance=MARKER_TOLERANCE,
    show_debug=True,
    section_name="Region"
):
    """
    Detect 4 corner markers based on expected printed size in POINTS.
    STRICT criteria: markers are SOLID BLACK SQUARES with NO hollow space.
    Expects EXACTLY 4 markers arranged in a rectangle.
    Returns (x_min, y_min, x_max, y_max) or None.
    """
    expected_px = points_to_pixels(expected_size_pt, dpi)
    min_size = expected_px * (1 - tolerance)  # ±25% tolerance
    max_size = expected_px * (1 + tolerance)
    
    # Aggressive area filtering
    min_area = (min_size ** 2) * 0.75
    max_area = (max_size ** 2) * 1.25

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    markers = []
    debug_img = image.copy() if show_debug else None

    print(f"\n[DEBUG] {section_name} detection: expected {expected_size_pt}pt → {expected_px:.1f}px, "
          f"range [{min_size:.1f}px, {max_size:.1f}px], area range [{min_area:.1f}, {max_area:.1f}]")
    print(f"[DEBUG] Analyzing {len(contours)} contours for {section_name} corner markers...")
    print(f"[DEBUG] STRICT CRITERIA: Solid black squares ONLY (no letters/text)")

    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Step 1: Area filtering
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        
        # Step 2: Size range check - require bounding box dims to be close to expected size
        if not (min_size <= w <= max_size and min_size <= h <= max_size):
            continue

        # Step 3: STRICT aspect ratio for perfect squares
        aspect_ratio = float(w) / h if h > 0 else 0
        if not (0.88 < aspect_ratio < 1.12):
            continue

        # Step 4: Corner detection - markers have sharp 90-degree corners, letters don't
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # Markers should approximate to exactly 4 corners
        if len(approx) != 4:
            continue  # Not a rectangle/square, likely a letter
        
        # Check corners are roughly 90 degrees (strict)
        corners_valid = True
        for i in range(4):
            pt1 = approx[i][0].astype(float)
            pt2 = approx[(i+1) % 4][0].astype(float)
            pt3 = approx[(i+2) % 4][0].astype(float)
            
            v1 = pt2 - pt1
            v2 = pt3 - pt2
            dot = np.dot(v1, v2)
            
            # Dot product should be near 0 for 90-degree angles
            # Stricter check: reject angles far from 90 degrees
            if abs(dot) > 500:  # Very strict - markers must have near-perfect corners
                corners_valid = False
                break
        
        if not corners_valid:
            continue

        # Step 5: DARKNESS CHECK - VERY STRICT for solid black
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        mean_val = cv2.mean(gray, mask=mask)[0]
        
        # Require VERY dark - solid black markers only
        if mean_val > 50:  # Much stricter - markers must be very dark
            continue

        # Step 6: SOLIDITY CHECK - interior must be uniformly dark (no hollow centers like letters)
        inner_margin = 3  # pixels from edge
        if w > inner_margin * 2 and h > inner_margin * 2:
            inner_x1 = max(0, x + inner_margin)
            inner_x2 = min(gray.shape[1], x + w - inner_margin)
            inner_y1 = max(0, y + inner_margin)
            inner_y2 = min(gray.shape[0], y + h - inner_margin)
            
            if inner_x2 > inner_x1 and inner_y2 > inner_y1:
                inner_region = gray[inner_y1:inner_y2, inner_x1:inner_x2]
                inner_mean = np.mean(inner_region)
                
                # Interior must also be very dark (no hollow centers)
                if inner_mean > 80:
                    continue  # Reject - has hollow interior (letter)
                
                # Step 7: UNIFORMITY CHECK - markers are uniform, letters have structure variation
                inner_std = np.std(inner_region)
                if inner_std > 40:
                    continue  # Reject - too much variation (letter structure)

        # Step 8: FILL RATIO - marker must be very solid
        rect_area = w * h
        fill_ratio = area / rect_area if rect_area > 0 else 0
        
        # Markers should be very filled (0.9+), not sparse like text strokes
        if fill_ratio < 0.9:
            continue  # Too sparse - likely not a solid marker

        center_x = x + w // 2
        center_y = y + h // 2
        markers.append((center_x, center_y, w, h, area, x, y, fill_ratio, mean_val))

        if show_debug and debug_img is not None:
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(debug_img, (center_x, center_y), 4, (0, 255, 0), -1)

    print(f"[INFO] {section_name}: Found {len(markers)} marker candidates (after STRICT filtering)")
    
    if markers:
        for i, (cx, cy, w, h, a, x, y, fr, mv) in enumerate(markers):
            print(f"  Marker {i+1}: pos=({x},{y}), size={w}x{h}, fill_ratio={fr:.3f}, mean_val={mv:.1f}")

    # REQUIRE EXACTLY 4 markers (no fallback, no tolerance)
    if len(markers) != 4:
        print(f"[ERROR] {section_name}: Expected EXACTLY 4 markers, found {len(markers)}")
        print(f"[HINT] Ensure marker region has 4 solid black squares with no text overlapping")
        if show_debug and debug_img is not None:
            cv2.putText(debug_img, f"{section_name} - FAILED: Found {len(markers)}/4 markers", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            resized = fit_to_screen(debug_img, max_height=1000)
            cv2.imshow(f'{section_name} Corner Marker Detection - FAILED', resized)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None

    markers_sorted = markers  # Already have exactly 4
    
    # Extract coordinates (use top-left corner + dimensions for actual bounds)
    xs_centers = [m[0] for m in markers_sorted]
    ys_centers = [m[1] for m in markers_sorted]
    xs_left = [m[5] for m in markers_sorted]
    ys_top = [m[6] for m in markers_sorted]
    widths = [m[2] for m in markers_sorted]
    heights = [m[3] for m in markers_sorted]
    
    # Region bounds from outer edges of markers
    x_min = min(xs_left)
    y_min = min(ys_top)
    x_max = max([xs_left[i] + widths[i] for i in range(len(markers_sorted))])
    y_max = max([ys_top[i] + heights[i] for i in range(len(markers_sorted))])

    x_range = x_max - x_min
    y_range = y_max - y_min
    print(f"[VALIDATION] {section_name} marker spread: {x_range}px wide x {y_range}px tall")

    # Check marker symmetry (markers should form a rectangle)
    xs_sorted = sorted(xs_centers)
    ys_sorted = sorted(ys_centers)
    
    x_spread = xs_sorted[-1] - xs_sorted[0]
    y_spread = ys_sorted[-1] - ys_sorted[0]
    
    if x_spread < 100 or y_spread < 100:
        print(f"[ERROR] {section_name}: Markers too close together (x_spread={x_spread}, y_spread={y_spread})")
        if show_debug and debug_img is not None:
            cv2.rectangle(debug_img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 3)
            resized = fit_to_screen(debug_img, max_height=1000)
            cv2.imshow(f'{section_name} Corner Marker Detection - INVALID SPREAD', resized)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None

    if show_debug and debug_img is not None:
        # Draw marker centers
        for (cx, cy, w, h, a, x, y, fr, mv) in markers_sorted:
            cv2.circle(debug_img, (cx, cy), 8, (255, 0, 0), -1)
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Draw region bounds
        cv2.rectangle(debug_img, (x_min, y_min), (x_max, y_max), (255, 0, 255), 3)
        cv2.putText(debug_img, f"{section_name} ({expected_size_pt}pt ≈ {expected_px:.1f}px)",
                    (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
        
        # Draw info text
        info_text = f"Markers: 4 ✓ | Region: {x_range}x{y_range}px | STRICT MODE"
        cv2.putText(debug_img, info_text, (x_min, y_max + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)

        resized = fit_to_screen(debug_img, max_height=1000)
        cv2.imshow(f'{section_name} Corner Marker Detection - SUCCESS', resized)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    print(f"[SUCCESS] {section_name} region: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    return (x_min, y_min, x_max, y_max)


# Backwards-compatible wrapper: original detect_corner_markers now calls expected-size detector with ID_MARKER_PT
# Backwards-compatible wrapper: detect Student ID region using 10pt markers
def detect_corner_markers(image, dpi=300, show_debug=True):
    """
    Wrapper that detects the Student ID corner markers using ID_MARKER_PT (10pt).
    STRICT: Requires exactly 4 solid black squares with no text.
    """
    return detect_corner_markers_by_expected_size(image, expected_size_pt=ID_MARKER_PT, dpi=dpi,
                                                  tolerance=MARKER_TOLERANCE, show_debug=show_debug,
                                                  section_name="Student ID")


# Detect KEY region using 7pt markers
def detect_key_region(image, dpi=300, show_debug=True):
    """
    Detect KEY region using 7pt corner markers.
    STRICT: Requires exactly 4 solid black squares with no text.
    """
    return detect_corner_markers_by_expected_size(image, expected_size_pt=KEY_MARKER_PT, dpi=dpi,
                                                  tolerance=MARKER_TOLERANCE, show_debug=show_debug,
                                                  section_name="KEY")

# Detect Quick Answers region using 9pt markers
def detect_qa_region(image, dpi=300, show_debug=True):
    """
    Detect Quick Answers region using 9pt corner markers.
    STRICT: Requires exactly 4 solid black squares with no text.
    """
    return detect_corner_markers_by_expected_size(image, expected_size_pt=QA_MARKER_PT, dpi=dpi,
                                                  tolerance=MARKER_TOLERANCE, show_debug=show_debug,
                                                  section_name="Quick Answers")


# -----------------------------------------------------------------------------
# Bubble detection
# -----------------------------------------------------------------------------
def detect_bubbles_in_region(image, region_mask=None, show_visualization=False):
    """
    Detect bubbles in image, optionally restricted to a region.
    STRICT: Only circular bubbles, reject squares/rectangles.
    
    Args:
        image: Input image (BGR)
        region_mask: Binary mask (255=detect, 0=ignore), or None for entire image
        show_visualization: If True, display detection visualization
        
    Returns:
        List of detected bubble tuples: (cx, cy, radius, contour)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Apply region mask if provided
    if region_mask is not None:
        thresh = cv2.bitwise_and(thresh, thresh, mask=region_mask)
    
    if show_visualization:
        cv2.imshow('Thresholded', fit_to_screen(thresh, max_height=1000))
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
                
                # STRICT: Bubbles must be circular (0.80+), reject squares/rectangles
                # Circle: circularity ≈ 1.0
                # Square: circularity ≈ 0.64 (REJECT)
                # Oval: circularity ≈ 0.85-0.95
                if circularity > 0.80:  # was 0.7 - MUCH stricter
                    # Additional check: aspect ratio of bounding circle vs contour
                    x_min, y_min, w, h = cv2.boundingRect(cnt)
                    aspect_ratio = float(w) / h if h > 0 else 0
                    
                    # Circles should have aspect ratio ~1.0, squares are also ~1.0
                    # But we can use the enclosing circle to filter: 
                    # Circle fit should be tight (contour fills most of circle)
                    circle_area = np.pi * (radius ** 2)
                    circle_fill_ratio = area / circle_area
                    
                    # For a perfect circle: fill_ratio = 1.0
                    # For a square in a circle: fill_ratio ≈ 0.637
                    # For an oval: fill_ratio ≈ 0.8-0.95
                    if circle_fill_ratio > 0.75:  # Reject squares (0.637), keep circles (0.95+) and ovals
                        bubble_contours.append((int(x), int(y), int(radius), cnt))
    
    return bubble_contours


# -----------------------------------------------------------------------------
# Question bubble detection (excludes ID and KEY regions)
# -----------------------------------------------------------------------------
def detect_question_bubbles(image, id_region=None, key_region=None, qa_region=None, show_visualization=False):
    """
    Detect question bubbles (excluding ID, KEY, and Quick Answers regions)
    """
    height, width = image.shape[:2]
    region_mask = np.ones((height, width), dtype=np.uint8) * 255
    
    padding = 20
    for region in [id_region, key_region, qa_region]:
        if region:
            x_min, y_min, x_max, y_max = region
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(width, x_max + padding)
            y_max = min(height, y_max + padding)
            region_mask[y_min:y_max, x_min:x_max] = 0
    
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
        
        # Draw excluded ID region
        if id_region is not None:
            x_min, y_min, x_max, y_max = id_region
            cv2.rectangle(output, (x_min - padding, y_min - padding), 
                         (x_max + padding, y_max + padding), (0, 0, 255), 2)
            cv2.putText(output, "EXCLUDED (ID)", (x_min, y_min - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Draw excluded KEY region
        if key_region is not None:
            kx_min, ky_min, kx_max, ky_max = key_region
            cv2.rectangle(output, (kx_min - padding, ky_min - padding), 
                         (kx_max + padding, ky_max + padding), (0, 255, 255), 2)
            cv2.putText(output, "EXCLUDED (KEY)", (kx_min, ky_min - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Draw excluded Quick Answers region
        if qa_region is not None:
            qx_min, qy_min, qx_max, qy_max = qa_region
            cv2.rectangle(output, (qx_min - padding, qy_min - padding), 
                         (qx_max + padding, qy_max + padding), (255, 0, 255), 2)
            cv2.putText(output, "EXCLUDED (QA)", (qx_min, qy_min - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
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
        
        resized = fit_to_screen(output, max_height=1000)
        cv2.imshow('Detected Question Bubbles', resized)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return detected_questions_sorted


# -----------------------------------------------------------------------------
# Student ID bubble detection (existing implementation preserved)
# -----------------------------------------------------------------------------
def detect_id_bubbles(image, id_region, show_visualization=False):
    """
    Detect Student ID bubbles within the marked region (10 digits, 0-9 each).
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
        filtered = bubble_contours.copy()

    # Sort by x (primary) then y
    filtered.sort(key=lambda b: (b[0], b[1]))
    xs = np.array([b[0] for b in filtered])

    # Adaptive 1D clustering using large gaps in sorted x
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
        gaps = np.diff(xs)
        median_gap = np.median(gaps)
        std_gap = np.std(gaps)
        split_thresh = max(1.8 * median_gap, median_gap + 1.5 * std_gap, 30)
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

    # Keep only columns that are near 10 bubbles
    valid_columns = [col for col in columns if 8 <= len(col) <= 12]

    # If none found, relax criteria
    if not valid_columns:
        columns_sorted = sorted(columns, key=lambda c: abs(len(c) - 10))
        valid_columns = columns_sorted[:min(6, len(columns_sorted))]
        print(f"[INFO] No strict-valid columns; selected {len(valid_columns)} best candidates by count")

    # For each selected column ensure exactly 10 bubbles
    final_columns = []
    for col in valid_columns:
        col = sorted(col, key=lambda b: b[1])
        if len(col) == 10:
            final_columns.append(col)
            continue
        if len(col) > 10:
            ys = np.array([b[1] for b in col])
            targets = np.linspace(ys.min(), ys.max(), 10)
            chosen = []
            used = set()
            for t in targets:
                idx = int(np.argmin(np.abs(ys - t)))
                if idx in used:
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
            chosen_unique = []
            seen = set()
            for b in chosen:
                key = (b[0], b[1])
                if key not in seen:
                    seen.add(key)
                    chosen_unique.append(b)
            chosen_unique = sorted(chosen_unique, key=lambda b: b[1])[:10]
            if len(chosen_unique) == 10:
                final_columns.append(chosen_unique)
            else:
                final_columns.append(sorted(col, key=lambda b: b[1])[:10])
        else:
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
        col = sorted(col, key=lambda b: b[1])
        digit_data = {
            'digit_position': col_idx + 1,
            'bubbles': []
        }
        for row_idx, (x, y, r, cnt) in enumerate(col):
            digit_data['bubbles'].append({
                'digit': row_idx,
                'x': int(x),
                'y': int(y),
                'radius': int(r)
            })
        id_data['digit_columns'].append(digit_data)

    print(f"[SUCCESS] {len(final_columns)} valid digit columns after clustering/refinement")

    # Visualization
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

        resized = fit_to_screen(output, max_height=1000)
        cv2.imshow('Detected ID Bubbles (refined)', resized)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return id_data


# -----------------------------------------------------------------------------
# KEY bubble detection (new)
# -----------------------------------------------------------------------------
def detect_key_bubbles(image, key_region, show_visualization=False):
    """
    Detect the 5 KEY bubbles (A, B, C, D, E) in the key region
    """
    x_min, y_min, x_max, y_max = key_region
    height, width = image.shape[:2]
    region_mask = np.zeros((height, width), dtype=np.uint8)
    region_mask[y_min:y_max, x_min:x_max] = 255

    bubble_contours = detect_bubbles_in_region(image, region_mask, show_visualization)
    if not bubble_contours:
        print("[WARNING] No key bubbles detected!")
        return []

    # Sort left-to-right
    bubble_contours.sort(key=lambda b: b[0])
    # Keep up to 5 left-most bubbles
    key_bubbles = bubble_contours[:5]

    key_data = []
    for idx, (cx, cy, r, cnt) in enumerate(key_bubbles):
        key_data.append({'position': idx+1, 'x': int(cx), 'y': int(cy), 'radius': int(r)})

    if show_visualization:
        output = image.copy()
        cv2.rectangle(output, (x_min, y_min), (x_max, y_max), (0, 255, 255), 2)
        cv2.putText(output, "KEY REGION", (x_min, y_min - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        for b in key_data:
            cv2.circle(output, (b['x'], b['y']), b['radius'], (0, 0, 255), 2)
        
        resized = fit_to_screen(output, max_height=1000)
        cv2.imshow("Detected KEY Bubbles", resized)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return key_data


# -----------------------------------------------------------------------------
# Main detection pipeline (now accepts dpi to convert pt->px)
# -----------------------------------------------------------------------------
def detect_bubbles_in_image(image_path, show_visualization=False, dpi=300):
    """
    Main detection function: detects ID region, KEY region, Quick Answers region, 
    question bubbles, ID bubbles, and KEY bubbles.
    
    Student ID: 10pt corner markers (4 squares)
    KEY: 7pt corner markers (4 squares)
    Quick Answers: 9pt corner markers (4 squares)
    
    Returns (questions, id_data, key_data, qa_data)
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Image not found at {image_path}")
        return [], None, None, None

    print("\n" + "="*60)
    print("STEP 1: Detecting Student ID Region (10pt markers)")
    print("="*60)

    id_region = detect_corner_markers(image, dpi=dpi, show_debug=show_visualization)

    if id_region is None:
        print("\n[WARNING] Could not detect ID region!")

    print("\n" + "="*60)
    print("STEP 2: Detecting KEY Region (7pt markers)")
    print("="*60)

    key_region = detect_key_region(image, dpi=dpi, show_debug=show_visualization)

    if key_region is None:
        print("[INFO] KEY region not detected (may be expected if sheet has no KEY).")

    print("\n" + "="*60)
    print("STEP 3: Detecting Quick Answers Region (9pt markers)")
    print("="*60)

    qa_region = detect_qa_region(image, dpi=dpi, show_debug=show_visualization)

    if qa_region is None:
        print("[INFO] Quick Answers region not detected (may be expected if sheet has no QA).")

    print("\n" + "="*60)
    print("STEP 4: Detecting Question Bubbles")
    print("="*60)

    questions = detect_question_bubbles(image, id_region=id_region, key_region=key_region, 
                                       qa_region=qa_region, show_visualization=show_visualization)

    # Detect ID bubbles if region was found
    id_data = None
    if id_region is not None:
        print("\n" + "="*60)
        print("STEP 5: Detecting Student ID Bubbles")
        print("="*60)
        id_data = detect_id_bubbles(image, id_region, show_visualization)
    else:
        print("\n[INFO] Skipping ID bubble detection (no ID region found)")

    # Detect KEY bubbles if region was found
    key_data = None
    if key_region is not None:
        print("\n" + "="*60)
        print("STEP 6: Detecting KEY Bubbles")
        print("="*60)
        key_data = detect_key_bubbles(image, key_region, show_visualization)
    else:
        print("\n[INFO] Skipping KEY bubble detection (no KEY region found)")

    return questions, id_data, key_data, qa_region


# -----------------------------------------------------------------------------
# Save / load template helpers
# -----------------------------------------------------------------------------
def save_template_to_json(template_data, source_file, output_dir='template'):
    """
    Save template data to JSON file in template directory
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
    
    Student ID markers: 10pt (4 squares)
    KEY markers: 7pt (4 squares)
    Quick Answers markers: 9pt (4 squares)
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
        
        # Detect questions, ID, KEY, and QA (pass dpi for marker conversion)
        questions, id_data, key_data, qa_region = detect_bubbles_in_image(png_path, show_visualization=show_visualization, dpi=dpi)
        
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
            'student_id': id_data,
            'key_bubbles': key_data,
            'quick_answers_region': qa_region
        }
        
        print(f"\nPage {i} Summary:")
        print(f"  Questions: {len(questions)}")
        if id_data:
            print(f"  Student ID: Detected ({id_data['total_digits']} digits)")
        else:
            print(f"  Student ID: Not found")
        if key_data:
            print(f"  Key bubbles: Detected ({len(key_data)} bubbles)")
        else:
            print(f"  Key bubbles: Not found")
        if qa_region:
            print(f"  Quick Answers: Detected")
        else:
            print(f"  Quick Answers: Not found")
    
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
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    print(f"[LOADED] Template from: {json_path}")
    print(f"  Pages: {template_data['metadata']['total_pages']}")
    print(f"  Questions: {template_data['metadata']['total_questions']}")
    print(f"  Created: {template_data['metadata']['created_at']}")
    
    return template_data

def points_to_pixels(points, dpi):
    """
    Convert PDF points (pt) to pixels using DPI.
    1 pt = 1/72 inch, so pixels = points * dpi / 72
    """
    return (points * dpi) / 72.0


# -----------------------------------------------------------------------------
# CLI / main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Process a PDF (default DPI = 300)
    print("Processing PDF with Student ID and KEY detection (DPI=300)")
    json_path = process_pdf_answer_sheet(
        pdf_path='test_sheet_with_key.pdf',
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
                print(f"  Key Bubbles: {page_data['key_bubbles'] is not None}")
