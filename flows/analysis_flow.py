import sqlite3
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from typing import Dict, List, Tuple, Optional, Any
import os
from dataclasses import dataclass
import json

matplotlib.use('Agg')  # Use non-interactive backend for UI integration

@dataclass
class ExamStats:
    """Statistics for an exam or key"""
    key_label: str
    highest_score: float
    lowest_score: float
    average_score: float
    median_score: float
    total_students: int

class ExamAnalyzer:
    """Handles exam analytics and visualization"""
    
    def __init__(self, db_path: str = "grading_system.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_exams(self) -> List[Dict]:
        """Get list of all exams"""
        self.connect()
        cursor = self.conn.cursor()
        
        query = """
        SELECT 
            e.id,
            e.name,
            e.description,
            e.max_score,
            COUNT(DISTINCT ak.id) as key_count,
            COUNT(DISTINCT gs.id) as graded_count
        FROM exams e
        LEFT JOIN answer_keys ak ON e.id = ak.exam_id
        LEFT JOIN graded_sheets gs ON ak.id = gs.key_id
        GROUP BY e.id
        ORDER BY e.created_at DESC
        """
        
        cursor.execute(query)
        exams = [dict(row) for row in cursor.fetchall()]
        return exams
    
    def get_exam_keys(self, exam_id: int) -> List[Dict]:
        """Get keys for a specific exam"""
        self.connect()
        cursor = self.conn.cursor()
        
        query = """
        SELECT 
            ak.id,
            ak.label,
            ak.name,
            COUNT(gs.id) as graded_count
        FROM answer_keys ak
        LEFT JOIN graded_sheets gs ON ak.id = gs.key_id
        WHERE ak.exam_id = ?
        GROUP BY ak.id
        ORDER BY ak.label
        """
        
        cursor.execute(query, (exam_id,))
        keys = [dict(row) for row in cursor.fetchall()]
        return keys
    
    def get_incorrect_counts_by_question(self, exam_id: int) -> Dict[str, List[int]]:
        """
        Get count of incorrect answers for each question, grouped by key
        Returns: Dict with key_label -> list of incorrect counts per question
        """
        self.connect()
        cursor = self.conn.cursor()
        
        # First, get all keys for this exam
        keys = self.get_exam_keys(exam_id)
        if not keys:
            return {}
        
        result = {}
        
        for key in keys:
            key_id = key['id']
            key_label = key['label']
            
            query = """
            SELECT 
                qr.question_number,
                qr.question_type,
                COUNT(*) as total_attempts,
                SUM(CASE WHEN qr.is_correct = 0 THEN 1 ELSE 0 END) as incorrect_count
            FROM question_results qr
            JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
            WHERE gs.key_id = ?
            GROUP BY qr.question_number, qr.question_type
            ORDER BY qr.question_number
            """
            
            cursor.execute(query, (key_id,))
            rows = cursor.fetchall()
            
            # Convert to list of incorrect counts per question number
            incorrect_counts = []
            for row in rows:
                incorrect_counts.append({
                    'question_number': row['question_number'],
                    'question_type': row['question_type'],
                    'incorrect_count': row['incorrect_count'],
                    'total_attempts': row['total_attempts']
                })
            
            result[key_label] = incorrect_counts
        
        return result
    
    def get_student_scores(self, exam_id: int) -> Dict[str, List[float]]:
        """
        Get all student scores for an exam, grouped by key
        Returns: Dict with key_label -> list of scores
        """
        self.connect()
        cursor = self.conn.cursor()
        
        query = """
        SELECT 
            ak.label as key_label,
            gs.score
        FROM graded_sheets gs
        JOIN answer_keys ak ON gs.key_id = ak.id
        WHERE gs.exam_id = ?
        ORDER BY ak.label, gs.score
        """
        
        cursor.execute(query, (exam_id,))
        rows = cursor.fetchall()
        
        print(f"DEBUG: get_student_scores for exam {exam_id}, found {len(rows)} rows")
        
        scores_by_key = {}
        all_scores = []
        
        for i, row in enumerate(rows[:10]):  # Print first 10 rows
            print(f"DEBUG: Row {i}: key_label={row['key_label']}, score={row['score']}, type={type(row['score'])}")
        
        for row in rows:
            key_label = row['key_label']
            score = row['score']
            
            # Debug: Check score type
            if not isinstance(score, (int, float)):
                print(f"DEBUG: Non-numeric score for key {key_label}: {score}, type: {type(score)}")
            
            # Convert score to float
            try:
                if score is None:
                    continue
                score_float = float(score)
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Could not convert score {score} to float: {e}")
                continue
            
            if key_label not in scores_by_key:
                scores_by_key[key_label] = []
            
            scores_by_key[key_label].append(score_float)
            all_scores.append(score_float)
        
        # Add overall scores
        if all_scores:
            scores_by_key['Overall'] = all_scores
        
        print(f"DEBUG: Returning scores_by_key with keys: {list(scores_by_key.keys())}")
        for key, scores in scores_by_key.items():
            print(f"DEBUG: Key {key}: {len(scores)} scores, first 3: {scores[:3] if len(scores) >= 3 else scores}")
        
        return scores_by_key
    
    def calculate_exam_stats(self, exam_id: int) -> Dict[str, ExamStats]:
        """
        Calculate statistics for an exam (overall and per key)
        Returns: Dict with key_label -> ExamStats
        """
        scores_by_key = self.get_student_scores(exam_id)
        
        stats = {}
        
        for key_label, scores in scores_by_key.items():
            if not scores:  # Skip if no scores
                continue
            
            try:
                # Ensure all scores are valid numbers
                valid_scores = []
                for score in scores:
                    try:
                        valid_scores.append(float(score))
                    except (ValueError, TypeError):
                        continue
                
                if not valid_scores:
                    continue
                    
                scores_array = np.array(valid_scores)
                
                stats[key_label] = ExamStats(
                    key_label=key_label,
                    highest_score=float(np.max(scores_array)),
                    lowest_score=float(np.min(scores_array)),
                    average_score=float(np.mean(scores_array)),
                    median_score=float(np.median(scores_array)),
                    total_students=len(valid_scores)
                )
            except Exception as e:
                # Skip this key if statistics calculation fails
                print(f"Warning: Could not calculate stats for key {key_label}: {str(e)}")
                continue
        
        return stats
    
    def create_incorrect_histogram(self, exam_id: int, 
                                   figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
        """
        Create histogram showing incorrect counts per question for each key
        """
        incorrect_data = self.get_incorrect_counts_by_question(exam_id)
        
        if not incorrect_data:
            # Create empty figure
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, 'No data available for this exam',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=12)
            ax.set_title('Incorrect Answers per Question')
            return fig
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Get all question numbers
        all_questions = set()
        for key_data in incorrect_data.values():
            for item in key_data:
                all_questions.add(item['question_number'])
        
        question_numbers = sorted(list(all_questions))
        key_labels = sorted(incorrect_data.keys())
        
        # Create bar width and positions
        bar_width = 0.8 / len(key_labels)
        x_positions = np.arange(len(question_numbers))
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(key_labels)))
        
        for i, key_label in enumerate(key_labels):
            key_data = incorrect_data[key_label]
            
            # Create mapping from question number to incorrect count
            incorrect_map = {item['question_number']: item['incorrect_count'] 
                           for item in key_data}
            
            # Get counts in order of question_numbers
            counts = [incorrect_map.get(q, 0) for q in question_numbers]
            
            # Calculate bar positions
            offsets = bar_width * i - (bar_width * (len(key_labels) - 1) / 2)
            
            ax.bar(x_positions + offsets, counts, bar_width,
                   label=f'Key {key_label}', color=colors[i], alpha=0.8)
        
        ax.set_xlabel('Question Number')
        ax.set_ylabel('Number of Incorrect Answers')
        ax.set_title('Incorrect Answers per Question (by Key)')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(question_numbers, rotation=45 if len(question_numbers) > 20 else 0)
        ax.legend(title='Answer Key')
        ax.grid(True, alpha=0.3, axis='y')
        
        fig.tight_layout()
        return fig
    
    def create_score_histogram(self, exam_id: int, bins: int = 10,
                            figsize: Tuple[int, int] = (10, 6),
                            scores_by_key: Optional[Dict[str, List[float]]] = None) -> plt.Figure:
        """
        Create histogram of student scores with adjustable bins
        """
        # Use provided scores_by_key or fetch fresh
        if scores_by_key is None:
            scores_by_key = self.get_student_scores(exam_id)
        
        if not scores_by_key or 'Overall' not in scores_by_key or not scores_by_key['Overall']:
            # Create empty figure
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, 'No score data available for this exam',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=12)
            ax.set_title('Student Score Distribution')
            return fig
        
        all_scores = scores_by_key['Overall']
        
        # Ensure all scores are numeric
        try:
            all_scores = [float(score) for score in all_scores]
        except (ValueError, TypeError) as e:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f'Invalid score data: {str(e)}',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=12)
            ax.set_title('Student Score Distribution - Data Error')
            return fig
        
        # Check if we have valid numeric data
        if not all_scores:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, 'No valid score data available',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=12)
            ax.set_title('Student Score Distribution')
            return fig
        
        fig, ax = plt.subplots(figsize=figsize)
        
        try:
            # Calculate bin edges
            min_score = min(all_scores)
            max_score = max(all_scores)
            
            # Handle edge case where all scores are the same
            if min_score == max_score:
                # Create a single bin with some padding
                min_score = min_score - 0.5
                max_score = max_score + 0.5
            
            bin_edges = np.linspace(min_score, max_score, bins + 1)
            
            # Create histogram - use different variable name for bins
            counts, bin_edges_actual, patches = ax.hist(all_scores, bins=bin_edges,
                                                        edgecolor='black', alpha=0.7,
                                                        color='skyblue')
            
            # Add value labels on top of bars
            for i, (count, patch) in enumerate(zip(counts, patches)):
                if count > 0:
                    height = patch.get_height()
                    ax.text(patch.get_x() + patch.get_width() / 2, height,
                            f'{int(count)}', ha='center', va='bottom')
            
            ax.set_xlabel('Score')
            ax.set_ylabel('Number of Students')
            ax.set_title(f'Student Score Distribution (Overall, {len(all_scores)} students)')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add vertical lines for statistics
            try:
                stats = self.calculate_exam_stats(exam_id)
                if 'Overall' in stats:
                    overall_stats = stats['Overall']
                    ax.axvline(overall_stats.average_score, color='red', 
                            linestyle='--', linewidth=2, label=f'Mean: {overall_stats.average_score:.2f}')
                    ax.axvline(overall_stats.median_score, color='green',
                            linestyle='--', linewidth=2, label=f'Median: {overall_stats.median_score:.2f}')
                    ax.legend()
            except Exception as stats_error:
                # Don't fail if statistics can't be calculated
                ax.text(0.05, 0.95, f'Could not calculate statistics: {str(stats_error)}',
                        transform=ax.transAxes, fontsize=10, alpha=0.7,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
        except Exception as e:
            # Clear the axis and show error message
            import traceback
            traceback.print_exc()
            ax.clear()
            ax.text(0.5, 0.5, f'Error creating histogram: {str(e)}\n'
                    f'Scores: {all_scores[:10]}...',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=10)
            ax.set_title('Student Score Distribution - Error')
        
        fig.tight_layout()
        return fig
    
    def create_comparison_histograms(self, exam_id: int, bins: int = 10) -> List[plt.Figure]:
        """
        Create comparison histograms for each key and overall
        Returns list of figures for each key + overall
        """
        scores_by_key = self.get_student_scores(exam_id)
        if not scores_by_key:
            return []
        
        print(f"DEBUG: scores_by_key keys = {list(scores_by_key.keys())}")
        
        figures = []
        key_labels = sorted([k for k in scores_by_key.keys() if k != 'Overall'])
        
        # Create figure for each key
        for key_label in key_labels:
            scores = scores_by_key[key_label]
            if not scores:
                print(f"DEBUG: Key {key_label} has no scores")
                continue
            
            print(f"DEBUG: Processing key {key_label}, scores type: {type(scores)}, length: {len(scores)}")
            print(f"DEBUG: First few scores for {key_label}: {scores[:5] if len(scores) > 5 else scores}")
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10))
            
            # Histogram 1: Score distribution for this key
            try:
                # Ensure scores is a flat list of numbers
                if isinstance(scores, (np.ndarray, np.generic)):
                    scores = scores.flatten().tolist()
                elif not isinstance(scores, list):
                    scores = list(scores)
                
                # Convert all scores to float
                scores = [float(score) for score in scores if score is not None]
                
                if not scores:
                    raise ValueError(f"No valid numeric scores for key {key_label}")
                
                print(f"DEBUG: Key {key_label} - min: {min(scores)}, max: {max(scores)}")
                
                min_score = min(scores)
                max_score = max(scores)
                
                # Handle edge case where all scores are the same
                if min_score == max_score:
                    min_score = min_score - 0.5
                    max_score = max_score + 0.5
                
                bin_edges = np.linspace(min_score, max_score, bins + 1)
                
                # Create histogram - fix the variable name conflict
                counts, bin_edges_actual, patches = ax1.hist(scores, bins=bin_edges,
                                                            edgecolor='black', alpha=0.7,
                                                            color='lightcoral')
                
                # Add value labels on top of bars
                for i, (count, patch) in enumerate(zip(counts, patches)):
                    if count > 0:
                        height = patch.get_height()
                        ax1.text(patch.get_x() + patch.get_width() / 2, height,
                                f'{int(count)}', ha='center', va='bottom')
                
                ax1.set_xlabel('Score')
                ax1.set_ylabel('Number of Students')
                ax1.set_title(f'Key {key_label} - Score Distribution ({len(scores)} students)')
                ax1.grid(True, alpha=0.3, axis='y')
                
            except Exception as e:
                print(f"ERROR in key {key_label} score histogram: {str(e)}")
                import traceback
                traceback.print_exc()
                ax1.clear()
                ax1.text(0.5, 0.5, f'Error creating score histogram: {str(e)}\n'
                        f'Scores: {scores[:10] if len(scores) > 10 else scores}',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax1.transAxes,
                        fontsize=10)
                ax1.set_title(f'Key {key_label} - Score Distribution')
            
            # Histogram 2: Question incorrect counts
            try:
                incorrect_data = self.get_incorrect_counts_by_question(exam_id)
                if key_label in incorrect_data and incorrect_data[key_label]:
                    key_data = incorrect_data[key_label]
                    
                    question_numbers = []
                    incorrect_counts = []
                    
                    for item in key_data:
                        q_num = item['question_number']
                        # Ensure q_num is a scalar
                        if hasattr(q_num, '__len__') and not isinstance(q_num, (str, bytes)):
                            q_num = q_num[0] if len(q_num) > 0 else 0
                        question_numbers.append(int(q_num))
                        incorrect_counts.append(int(item['incorrect_count']))
                    
                    if question_numbers:
                        ax2.bar(question_numbers, incorrect_counts, alpha=0.7, color='lightblue')
                        ax2.set_xlabel('Question Number')
                        ax2.set_ylabel('Incorrect Answers')
                        ax2.set_title(f'Key {key_label} - Incorrect Answers per Question')
                        ax2.grid(True, alpha=0.3, axis='y')
                        
                        if len(question_numbers) > 20:
                            ax2.tick_params(axis='x', rotation=45)
                    else:
                        raise ValueError("No question data")
                else:
                    raise ValueError("No incorrect data available")
                    
            except Exception as e:
                print(f"ERROR in key {key_label} question histogram: {str(e)}")
                ax2.clear()
                ax2.text(0.5, 0.5, 'No question data available',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax2.transAxes)
                ax2.set_title(f'Key {key_label} - Question Analysis')
            
            fig.tight_layout()
            figures.append((key_label, fig))
        
        # Create overall figure
        if 'Overall' in scores_by_key:
            try:
                # Pass the scores_by_key as keyword argument
                fig = self.create_score_histogram(exam_id, bins, scores_by_key=scores_by_key)
                figures.append(('Overall', fig))
            except Exception as e:
                print(f"ERROR creating overall histogram: {str(e)}")
                import traceback
                traceback.print_exc()
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, f'Error creating overall histogram: {str(e)}',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes)
                ax.set_title('Overall Score Distribution')
                figures.append(('Overall', fig))
        
        return figures