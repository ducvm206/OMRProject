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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sheet_id) REFERENCES sheets(id) ON DELETE CASCADE
);

-- 3. Answer Keys (now supports MCQ + written numeric)
CREATE TABLE IF NOT EXISTS answer_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,

    name TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE,

    -- MCQ JSON answer key (existing)
    key_info TEXT NOT NULL,

    -- Numeric written answers (NEW)
    written_key_info TEXT DEFAULT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'manual',

    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

-- 4. Students
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT,
    class TEXT,

    total_exams INTEGER DEFAULT 0,
    total_score REAL DEFAULT 0.0,
    total_possible_points REAL DEFAULT 0.0,
    avg_percentage REAL DEFAULT 0.0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Graded Sheets
CREATE TABLE IF NOT EXISTS graded_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,

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
    
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    threshold_used INTEGER DEFAULT 50,

    FOREIGN KEY (key_id) REFERENCES answer_keys(id) ON DELETE CASCADE
);

-- 6. Question Results
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
CREATE INDEX IF NOT EXISTS idx_graded_sheets_key ON graded_sheets(key_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_student ON graded_sheets(student_id);
CREATE INDEX IF NOT EXISTS idx_question_results_sheet ON question_results(graded_sheet_id);
CREATE INDEX IF NOT EXISTS idx_question_results_qnum ON question_results(question_number);
CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id);

-- ============================================
-- TRIGGERS
-- ============================================

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
        
        -- Track total possible points from the answer key
        total_possible_points = total_possible_points + (
            SELECT COALESCE(
                json_extract(key_info, '$.metadata.mcq_max_points'), 0
            ) + COALESCE(
                json_extract(key_info, '$.metadata.written_max_points'), 0
            )
            FROM answer_keys WHERE id = NEW.key_id
        ),
        
        -- Calculate average percentage
        avg_percentage = ROUND(
            CASE 
                WHEN (total_score + NEW.score) > 0 AND 
                     (total_possible_points + (
                        SELECT COALESCE(
                            json_extract(key_info, '$.metadata.mcq_max_points'), 0
                        ) + COALESCE(
                            json_extract(key_info, '$.metadata.written_max_points'), 0
                        )
                        FROM answer_keys WHERE id = NEW.key_id
                     )) > 0
                THEN (
                    CAST(total_score + NEW.score AS REAL) / 
                    CAST(total_possible_points + (
                        SELECT COALESCE(
                            json_extract(key_info, '$.metadata.mcq_max_points'), 0
                        ) + COALESCE(
                            json_extract(key_info, '$.metadata.written_max_points'), 0
                        )
                        FROM answer_keys WHERE id = NEW.key_id
                    ) AS REAL)
                ) * 100
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
                SUM(
                    COALESCE(json_extract(ak.key_info, '$.metadata.mcq_max_points'), 0) +
                    COALESCE(json_extract(ak.key_info, '$.metadata.written_max_points'), 0)
                ),
                0.0
            )
            FROM graded_sheets gs
            JOIN answer_keys ak ON gs.key_id = ak.id
            WHERE gs.student_id = OLD.student_id
        ),
        avg_percentage = ROUND(
            CASE 
                WHEN (
                    SELECT SUM(
                        COALESCE(json_extract(ak.key_info, '$.metadata.mcq_max_points'), 0) +
                        COALESCE(json_extract(ak.key_info, '$.metadata.written_max_points'), 0)
                    )
                    FROM graded_sheets gs
                    JOIN answer_keys ak ON gs.key_id = ak.id
                    WHERE gs.student_id = OLD.student_id
                ) > 0 
                THEN (
                    CAST((SELECT SUM(score) FROM graded_sheets WHERE student_id = OLD.student_id) AS REAL) /
                    CAST((
                        SELECT SUM(
                            COALESCE(json_extract(ak.key_info, '$.metadata.mcq_max_points'), 0) +
                            COALESCE(json_extract(ak.key_info, '$.metadata.written_max_points'), 0)
                        )
                        FROM graded_sheets gs
                        JOIN answer_keys ak ON gs.key_id = ak.id
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
    s.name,
    s.class,
    s.total_exams,
    s.avg_percentage,
    ROUND(s.total_score, 2) || '/' || ROUND(s.total_possible_points, 2) AS overall_score,
    s.updated_at AS last_exam_date
FROM students s;

-- Exam Summary with score tracking
CREATE VIEW IF NOT EXISTS exam_summary AS
SELECT 
    gs.exam_name,
    ak.name AS answer_key_name,
    t.name AS template_name,
    
    COUNT(gs.id) AS total_students,
    
    ROUND(AVG(gs.score), 2) AS avg_score,
    ROUND(MIN(gs.score), 2) AS min_score,
    ROUND(MAX(gs.score), 2) AS max_score,
    
    -- Calculate average percentage for the exam
    ROUND(
        AVG(
            CASE 
                WHEN (
                    COALESCE(json_extract(ak.key_info, '$.metadata.mcq_max_points'), 0) +
                    COALESCE(json_extract(ak.key_info, '$.metadata.written_max_points'), 0)
                ) > 0
                THEN (gs.score / (
                    COALESCE(json_extract(ak.key_info, '$.metadata.mcq_max_points'), 0) +
                    COALESCE(json_extract(ak.key_info, '$.metadata.written_max_points'), 0)
                )) * 100
                ELSE 0
            END
        ),
        2
    ) AS avg_percentage,
    
    SUM(gs.mcq_correct_count) AS total_mcq_correct,
    SUM(gs.written_correct_count) AS total_written_correct,
    
    SUM(gs.total_mcq_questions) AS total_mcq_questions,
    SUM(gs.total_written_questions) AS total_written_questions

FROM graded_sheets gs
JOIN answer_keys ak ON gs.key_id = ak.id
JOIN templates t ON ak.template_id = t.id
GROUP BY gs.exam_name, ak.name, t.name;

-- MCQ difficulty
CREATE VIEW IF NOT EXISTS mcq_difficulty AS
SELECT 
    gs.key_id,
    qr.question_number,
    COUNT(*) AS attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate,
    ROUND(AVG(qr.points), 2) AS avg_points
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
WHERE qr.question_type = 'mcq'
GROUP BY gs.key_id, qr.question_number;

-- Written question difficulty
CREATE VIEW IF NOT EXISTS written_difficulty AS
SELECT 
    gs.key_id,
    qr.question_number,
    COUNT(*) AS attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate,
    ROUND(AVG(qr.points), 2) AS avg_points
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
WHERE qr.question_type = 'written'
GROUP BY gs.key_id, qr.question_number;

-- Overall question difficulty
CREATE VIEW IF NOT EXISTS overall_question_difficulty AS
SELECT
    gs.key_id,
    qr.question_number,
    qr.question_type,
    COUNT(*) AS attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate,
    ROUND(AVG(qr.points), 2) AS avg_points
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
GROUP BY gs.key_id, qr.question_number, qr.question_type;