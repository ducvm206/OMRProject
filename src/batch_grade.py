def batch_grade(template_json, key_json, images_path, output_dir=None, threshold=50, partial_credit=False, show_visualization=False):
    """
    Batch process and grade a folder (or list) of filled answer sheet images.
    Saves two summaries:
      - batch_summary.json (existing detailed summary)
      - batch_results_compact.csv (compact CSV with format:
          student_id,score,percentage,Q1,Q2,...,Qn
        where Qk is 1 for correct, 0 for wrong)
    """
    from core.extraction import BubbleTemplate, AnswerSheetExtractor, save_extraction_to_json
    from core.grading import load_answer_key, grade_answers, save_grade_report

    import glob
    import csv
    import json
    import os
    import datetime

    # Resolve images list
    if isinstance(images_path, str) and os.path.isdir(images_path):
        patterns = ['*.png', '*.jpg', '*.jpeg', '*.tif', '*.tiff', '*.bmp']
        image_files = []
        for p in patterns:
            image_files.extend(sorted(glob.glob(os.path.join(images_path, p))))
    elif isinstance(images_path, str) and (',' in images_path):
        image_files = [p.strip() for p in images_path.split(',') if p.strip()]
    else:
        image_files = [images_path] if images_path else []

    image_files = [p for p in image_files if os.path.exists(p)]
    if not image_files:
        print(f"[ERROR] No valid images found for: {images_path}")
        return None

    if output_dir is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join(os.getcwd(), f"batch_results_{ts}")
    os.makedirs(output_dir, exist_ok=True)

    answer_key_data = load_answer_key(key_json)
    # Attempt to get canonical answer mapping and number of questions
    key_answers = answer_key_data.get('answers') if isinstance(answer_key_data, dict) else None
    try:
        total_questions = int(answer_key_data.get('metadata', {}).get('total_questions') or len(key_answers or {}))
    except Exception:
        total_questions = None

    template = BubbleTemplate(template_json)
    extractor = AnswerSheetExtractor(template)

    summary = []
    compact_rows = []  # rows for the compact CSV: [student_id, score, percentage, q1,...,qN]

    def _per_question_outcomes_from_grade(grade_results, total_q=None):
        """
        Try to extract per-question correct(1)/wrong(0) sequence from grader output.
        Returns list length total_q if known, else best-effort list.
        """
        outcomes = []
        # Preferred: grade_results['details'] where each question has 'points' and full points known
        details = grade_results.get('details') if isinstance(grade_results, dict) else None
        summary = grade_results.get('summary') if isinstance(grade_results, dict) else None

        points_per_q = None
        if summary and isinstance(summary, dict):
            points_per_q = summary.get('points_per_question') or None
            if points_per_q is None:
                maxp = summary.get('max_points') or summary.get('max_score') or None
                tq = summary.get('total_questions') or summary.get('total') or None
                try:
                    if maxp is not None and tq:
                        points_per_q = float(maxp) / int(tq)
                except Exception:
                    points_per_q = None

            if total_q is None:
                total_q = summary.get('total_questions') or summary.get('total') or total_q

        if details and isinstance(details, dict):
            # details keys may be "1","2",...
            ordered_keys = sorted(details.keys(), key=lambda k: int(k))
            for k in ordered_keys:
                info = details[k] or {}
                pts = info.get('points')
                if pts is None:
                    # maybe boolean 'correct'
                    correct_flag = info.get('correct')
                    outcomes.append(1 if correct_flag else 0)
                else:
                    if points_per_q is not None:
                        outcomes.append(1 if abs(float(pts) - float(points_per_q)) < 1e-6 else 0)
                    else:
                        outcomes.append(1 if float(pts) > 0 else 0)
            # pad/truncate to total_q if known
            if total_q:
                outcomes = (outcomes + [0]*total_q)[:total_q]
            return outcomes

        # Fallback: try grade_results['answers_correct'] or similar structures
        if isinstance(grade_results.get('answers'), dict):
            # compare each answer with key if available
            if key_answers:
                for q in sorted(key_answers.keys(), key=lambda kk: int(kk)):
                    correct_ans = key_answers.get(q)
                    scanned_ans = grade_results.get('answers', {}).get(q)  # sometimes included
                    outcomes.append(1 if scanned_ans == correct_ans else 0)
                if total_q:
                    outcomes = (outcomes + [0]*total_q)[:total_q]
                return outcomes

        return outcomes

    for img_path in image_files:
        try:
            print(f"\n[INFO] Processing: {img_path}")
            result = extractor.extract_complete(img_path, threshold_percent=threshold, debug=show_visualization)
            if not result:
                print(f"[WARN] Extraction failed for {img_path}")
                summary.append({'image': img_path, 'status': 'extraction_failed'})
                continue

            extraction_json = save_extraction_to_json(result, output_dir=output_dir)

            # Prepare scanned answers format expected by grader
            scanned_answers_data = {
                'metadata': result.get('metadata', {}),
                'answers': result.get('answers', {})
            }

            grade_results = grade_answers(answer_key_data, scanned_answers_data, max_points=None, partial_credit=partial_credit)
            report_json = save_grade_report(grade_results, key_json, extraction_json)

            # Extract student id if present
            student_id = None
            sid = result.get('student_id')
            if isinstance(sid, dict):
                student_id = sid.get('student_id')
            elif isinstance(sid, str):
                student_id = sid

            # Extract core score/percentage
            score = None
            percentage = None
            try:
                sc = grade_results.get('summary', {}).get('score') if isinstance(grade_results.get('summary'), dict) else grade_results.get('score')
                mp = grade_results.get('summary', {}).get('max_points') if isinstance(grade_results.get('summary'), dict) else grade_results.get('max_points')
                pct = grade_results.get('summary', {}).get('percentage') if isinstance(grade_results.get('summary'), dict) else grade_results.get('percentage')
                if sc is not None:
                    score = sc
                if pct is not None:
                    percentage = pct
                elif score is not None and mp is not None:
                    percentage = (float(score) / float(mp) * 100.0) if mp else None
            except Exception:
                pass

            # Determine per-question outcomes (1/0)
            outcomes = _per_question_outcomes_from_grade(grade_results, total_q=total_questions)
            # If outcomes empty and we have scanned answers + key, compute directly
            if (not outcomes or len(outcomes) == 0) and key_answers:
                scanned = scanned_answers_data.get('answers') or {}
                ordered_qs = sorted(key_answers.keys(), key=lambda kk: int(kk))
                for q in ordered_qs:
                    outcomes.append(1 if str(scanned.get(q)).strip() == str(key_answers.get(q)).strip() else 0)
                if total_questions:
                    outcomes = (outcomes + [0]*total_questions)[:total_questions]

            # Prepare compact row
            sid_display = student_id if student_id else ""
            score_display = score if score is not None else grade_results.get('score')
            pct_display = percentage if percentage is not None else grade_results.get('percentage')

            compact_row = [sid_display, score_display, pct_display]
            compact_row.extend(outcomes)

            # Print simple line as requested
            # Print student id, score, correct/total
            correct_count = sum(outcomes) if outcomes else None
            total_q_display = total_questions if total_questions is not None else (len(outcomes) if outcomes else "N/A")
            if correct_count is not None:
                print(f"{sid_display} | score: {score_display} | {correct_count}/{total_q_display}")
            else:
                print(f"{sid_display} | score: {score_display} | details unavailable")

            summary.append({
                'image': img_path,
                'status': 'ok',
                'student_id': student_id,
                'extraction_json': extraction_json,
                'report_json': report_json,
                'score': score_display,
                'max_points': grade_results.get('max_points'),
                'percentage': pct_display
            })
            compact_rows.append(compact_row)

        except Exception as e:
            print(f"[ERROR] Processing {img_path} failed: {e}")
            summary.append({'image': img_path, 'status': 'error', 'error': str(e)})

    # Save detailed summary JSON (existing)
    summary_json_path = os.path.join(output_dir, 'batch_summary.json')
    with open(summary_json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Build and save compact CSV with header: student_id,score,percentage,Q1,Q2,...Qn
    csv_path = os.path.join(output_dir, 'batch_results.csv')
    # determine max question columns present
    max_qcols = 0
    for row in compact_rows:
        qcols = max(0, len(row) - 3)
        if qcols > max_qcols:
            max_qcols = qcols
    # If total_questions known prefer that
    if total_questions:
        max_qcols = total_questions

    headers = ['student_id', 'score', 'percentage'] + [f"Q{i+1}" for i in range(max_qcols)]
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(headers)
        for row in compact_rows:
            # ensure row length equals 3 + max_qcols
            base = row[:3]
            qvals = row[3:] if len(row) > 3 else []
            qvals = qvals + [0] * (max_qcols - len(qvals))
            writer.writerow(base + qvals)

    print(f"\n[SUMMARY] Batch finished. Compact CSV saved to: {csv_path}")
    return {'output_dir': output_dir, 'summary_json': summary_json_path, 'compact_csv': csv_path, 'items': summary}