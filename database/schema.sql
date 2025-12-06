PRAGMA foreign_keys = ON;

-- ============================================
-- TABLES
-- ============================================

-- 1. Sheets - Store blank template sheet PDFs
CREATE TABLE IF NOT EXISTS sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 2. Templates - Store extracted template JSON from sheets
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sheet_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE,
    template_info TEXT NOT NULL,

    -- NEW SPLIT
    multiple_choice_questions INTEGER NOT NULL DEFAULT 0,
    written_answer_questions INTEGER NOT NULL DEFAULT 0,

    has_student_id BOOLEAN DEFAULT 1,
    has_key BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sheet_id) REFERENCES sheets(id) ON DELETE CASCADE
);

-- 3. Exams - Group multiple answer keys (A-E) together
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    max_score REAL NOT NULL DEFAULT 100.0,  -- Total possible points for this exam
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Answer Keys (unified key_info containing both MCQ and written answers)
CREATE TABLE IF NOT EXISTS answer_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    
    name TEXT NOT NULL,  -- e.g., "Key A", "Key B", etc.
    label CHAR(1) NOT NULL DEFAULT 'A',  -- Single letter label A-E
    json_path TEXT NOT NULL UNIQUE,

    -- Unified JSON containing both MCQ and written answer keys
    -- Structure: {
    --   "mcq": {...},
    --   "written": {...},
    --   "metadata": {
    --     "mcq_max_points": ...,
    --     "written_max_points": ...,
    --     "total_max_points": ...
    --   }
    -- }
    key_info TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'manual',

    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE,
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    UNIQUE(exam_id, label)  -- Ensure unique labels per exam
);

-- 5. Students (simplified - no name or class tracking)
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,

    total_exams INTEGER DEFAULT 0,
    total_score REAL DEFAULT 0.0,
    total_possible_points REAL DEFAULT 0.0,
    avg_percentage REAL DEFAULT 0.0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Graded Sheets (FIXED: Added key_id column)
CREATE TABLE IF NOT EXISTS graded_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    key_id INTEGER NOT NULL,  -- CRITICAL: Added missing column

    exam_name TEXT,
    filled_sheet_path TEXT,

    -- NEW SPLIT OF QUESTION TYPES
    total_mcq_questions INTEGER NOT NULL DEFAULT 0,
    total_written_questions INTEGER NOT NULL DEFAULT 0,

    mcq_correct_count INTEGER NOT NULL DEFAULT 0,
    mcq_wrong_count INTEGER NOT NULL DEFAULT 0,
    mcq_blank_count INTEGER NOT NULL DEFAULT 0,

    written_correct_count INTEGER NOT NULL DEFAULT 0,
    written_wrong_count INTEGER NOT NULL DEFAULT 0,
    written_blank_count INTEGER NOT NULL DEFAULT 0,

    -- Actual score achieved (points)
    score REAL DEFAULT 0.0,
    
    -- Max possible score for this specific key
    max_score REAL DEFAULT 0.0,
    
    -- Calculated percentage
    percentage REAL DEFAULT 0.0,
    
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    threshold_used INTEGER DEFAULT 50,

    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    FOREIGN KEY (key_id) REFERENCES answer_keys(id) ON DELETE CASCADE  -- Added foreign key
);

-- 7. Question Results
CREATE TABLE IF NOT EXISTS question_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graded_sheet_id INTEGER NOT NULL,

    question_number INTEGER NOT NULL,

    -- NEW
    question_type TEXT NOT NULL DEFAULT 'mcq',  -- 'mcq' or 'written'

    student_answer TEXT,
    correct_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    points REAL DEFAULT 1.0,

    -- OCR metadata for written answers
    digit_details TEXT DEFAULT NULL,

    FOREIGN KEY (graded_sheet_id) REFERENCES graded_sheets(id) ON DELETE CASCADE
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_templates_sheet ON templates(sheet_id);
CREATE INDEX IF NOT EXISTS idx_answer_keys_template ON answer_keys(template_id);
CREATE INDEX IF NOT EXISTS idx_answer_keys_exam ON answer_keys(exam_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_key ON graded_sheets(key_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_student ON graded_sheets(student_id);
CREATE INDEX IF NOT EXISTS idx_question_results_sheet ON question_results(graded_sheet_id);
CREATE INDEX IF NOT EXISTS idx_question_results_qnum ON question_results(question_number);
CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id);

-- ============================================
-- TRIGGERS
-- ============================================

-- Calculate percentage when inserting/updating graded sheet
CREATE TRIGGER IF NOT EXISTS calculate_percentage_on_graded_sheet
AFTER INSERT ON graded_sheets
BEGIN
    UPDATE graded_sheets 
    SET percentage = CASE 
        WHEN max_score > 0 THEN (score / max_score) * 100 
        ELSE 0 
    END
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS calculate_percentage_on_update
AFTER UPDATE OF score, max_score ON graded_sheets
BEGIN
    UPDATE graded_sheets 
    SET percentage = CASE 
        WHEN max_score > 0 THEN (score / max_score) * 100 
        ELSE 0 
    END
    WHERE id = NEW.id;
END;

-- Update student performance after grading
CREATE TRIGGER IF NOT EXISTS update_student_performance_after_grade
AFTER INSERT ON graded_sheets
BEGIN
    INSERT OR IGNORE INTO students (student_id) VALUES (NEW.student_id);

    UPDATE students
    SET 
        total_exams = total_exams + 1,
        
        -- Track actual scores (points)
        total_score = total_score + NEW.score,
        
        -- Track total possible points from the exam's max_score
        total_possible_points = total_possible_points + (
            SELECT e.max_score 
            FROM answer_keys ak 
            JOIN exams e ON ak.exam_id = e.id 
            WHERE ak.id = NEW.key_id
        ),
        
        -- Calculate average percentage based on score/max_score
        avg_percentage = ROUND(
            CASE 
                WHEN (total_possible_points + (
                    SELECT e.max_score 
                    FROM answer_keys ak 
                    JOIN exams e ON ak.exam_id = e.id 
                    WHERE ak.id = NEW.key_id
                )) > 0 
                THEN ((total_score + NEW.score) / (total_possible_points + (
                    SELECT e.max_score 
                    FROM answer_keys ak 
                    JOIN exams e ON ak.exam_id = e.id 
                    WHERE ak.id = NEW.key_id
                ))) * 100
                ELSE 0
            END,
            2
        ),
        
        updated_at = CURRENT_TIMESTAMP
    WHERE student_id = NEW.student_id;
END;

-- Recalculate on delete
CREATE TRIGGER IF NOT EXISTS recalc_student_performance_after_delete
AFTER DELETE ON graded_sheets
BEGIN
    UPDATE students
    SET 
        total_exams = (
            SELECT COUNT(*) 
            FROM graded_sheets 
            WHERE student_id = OLD.student_id
        ),
        total_score = (
            SELECT COALESCE(SUM(score), 0.0)
            FROM graded_sheets 
            WHERE student_id = OLD.student_id
        ),
        total_possible_points = (
            SELECT COALESCE(
                SUM(e.max_score),
                0.0
            )
            FROM graded_sheets gs
            JOIN answer_keys ak ON gs.key_id = ak.id
            JOIN exams e ON ak.exam_id = e.id
            WHERE gs.student_id = OLD.student_id
        ),
        avg_percentage = ROUND(
            CASE 
                WHEN (
                    SELECT COALESCE(
                        SUM(e.max_score),
                        0.0
                    )
                    FROM graded_sheets gs
                    JOIN answer_keys ak ON gs.key_id = ak.id
                    JOIN exams e ON ak.exam_id = e.id
                    WHERE gs.student_id = OLD.student_id
                ) > 0 
                THEN (
                    CAST((SELECT SUM(score) FROM graded_sheets WHERE student_id = OLD.student_id) AS REAL) /
                    CAST((
                        SELECT COALESCE(
                            SUM(e.max_score),
                            0.0
                        )
                        FROM graded_sheets gs
                        JOIN answer_keys ak ON gs.key_id = ak.id
                        JOIN exams e ON ak.exam_id = e.id
                        WHERE gs.student_id = OLD.student_id
                    ) AS REAL)
                ) * 100
                ELSE 0
            END,
            2
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE student_id = OLD.student_id;
END;

-- ============================================
-- VIEWS
-- ============================================

-- Student Performance Summary
CREATE VIEW IF NOT EXISTS student_performance AS
SELECT 
    s.student_id,
    s.total_exams,
    s.avg_percentage,
    ROUND(s.total_score, 2) || '/' || ROUND(s.total_possible_points, 2) AS overall_score,
    s.updated_at AS last_exam_date
FROM students s;

-- Exam Summary with score tracking
CREATE VIEW IF NOT EXISTS exam_summary AS
SELECT 
    e.name AS exam_name,
    e.description,
    e.max_score AS exam_max_score,
    
    COUNT(DISTINCT ak.label) AS total_keys,
    GROUP_CONCAT(DISTINCT ak.label) AS available_keys,
    
    COUNT(gs.id) AS total_students,
    
    ROUND(AVG(gs.score), 2) AS avg_score,
    ROUND(MIN(gs.score), 2) AS min_score,
    ROUND(MAX(gs.score), 2) AS max_score,
    
    -- Average percentage based on score/max_score
    ROUND(AVG(gs.percentage), 2) AS avg_percentage,
    
    SUM(gs.mcq_correct_count) AS total_mcq_correct,
    SUM(gs.written_correct_count) AS total_written_correct,
    
    SUM(gs.total_mcq_questions) AS total_mcq_questions,
    SUM(gs.total_written_questions) AS total_written_questions

FROM exams e
LEFT JOIN answer_keys ak ON e.id = ak.exam_id
LEFT JOIN graded_sheets gs ON ak.id = gs.key_id
GROUP BY e.id;

-- Key-specific summary
CREATE VIEW IF NOT EXISTS key_summary AS
SELECT 
    e.name AS exam_name,
    ak.label AS key_label,
    t.name AS template_name,
    
    COUNT(gs.id) AS total_students,
    
    ROUND(AVG(gs.score), 2) AS avg_score,
    ROUND(MIN(gs.score), 2) AS min_score,
    ROUND(MAX(gs.score), 2) AS max_score,
    
    ROUND(AVG(gs.percentage), 2) AS avg_percentage

FROM answer_keys ak
JOIN exams e ON ak.exam_id = e.id
JOIN templates t ON ak.template_id = t.id
LEFT JOIN graded_sheets gs ON ak.id = gs.key_id
GROUP BY ak.id;

-- MCQ difficulty
CREATE VIEW IF NOT EXISTS mcq_difficulty AS
SELECT 
    gs.key_id,
    ak.label AS key_label,
    e.name AS exam_name,
    qr.question_number,
    COUNT(*) AS attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate,
    ROUND(AVG(qr.points), 2) AS avg_points
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
JOIN answer_keys ak ON gs.key_id = ak.id
JOIN exams e ON ak.exam_id = e.id
WHERE qr.question_type = 'mcq'
GROUP BY gs.key_id, qr.question_number;

-- Written question difficulty
CREATE VIEW IF NOT EXISTS written_difficulty AS
SELECT 
    gs.key_id,
    ak.label AS key_label,
    e.name AS exam_name,
    qr.question_number,
    COUNT(*) AS attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate,
    ROUND(AVG(qr.points), 2) AS avg_points
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
JOIN answer_keys ak ON gs.key_id = ak.id
JOIN exams e ON ak.exam_id = e.id
WHERE qr.question_type = 'written'
GROUP BY gs.key_id, qr.question_number;

-- Overall question difficulty
CREATE VIEW IF NOT EXISTS overall_question_difficulty AS
SELECT
    gs.key_id,
    ak.label AS key_label,
    e.name AS exam_name,
    qr.question_number,
    qr.question_type,
    COUNT(*) AS attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate,
    ROUND(AVG(qr.points), 2) AS avg_points
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
JOIN answer_keys ak ON gs.key_id = ak.id
JOIN exams e ON ak.exam_id = e.id
GROUP BY gs.key_id, qr.question_number, qr.question_type;

-- Exam keys view
CREATE VIEW IF NOT EXISTS exam_keys AS
SELECT 
    e.id AS exam_id,
    e.name AS exam_name,
    ak.id AS key_id,
    ak.label AS key_label,
    ak.name AS key_name,
    t.name AS template_name,
    COUNT(gs.id) AS graded_count
FROM exams e
LEFT JOIN answer_keys ak ON e.id = ak.exam_id
LEFT JOIN templates t ON ak.template_id = t.id
LEFT JOIN graded_sheets gs ON ak.id = gs.key_id
GROUP BY e.id, ak.id;