-- Answer Sheet Grading System Database Schema
-- SQLite 3.x

PRAGMA foreign_keys = ON;

-- ============================================
-- TABLES
-- ============================================

-- 1. Sheets - Store blank template sheet PDFs
CREATE TABLE IF NOT EXISTS sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,         -- path to the blank sheet PDF
    name TEXT NOT NULL,                     -- descriptive name for the sheet
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 2. Templates - Store extracted template JSON from sheets
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sheet_id INTEGER NOT NULL,              -- FK -> sheets(id)
    name TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE,         -- path to the template JSON file
    template_info TEXT NOT NULL,            -- full template JSON as text
    total_questions INTEGER NOT NULL,
    has_student_id BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sheet_id) REFERENCES sheets(id) ON DELETE CASCADE
);

-- 3. Answer Keys - Store answer keys linked to templates
CREATE TABLE IF NOT EXISTS answer_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,           -- FK -> templates(id)
    name TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE,         -- path to the answer key JSON file
    key_info TEXT NOT NULL,                 -- full answer key JSON as text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'manual',       -- 'manual' or 'scan'
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

-- 4. Students - Store student information and performance
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT,
    class TEXT,
    total_exams INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    avg_percentage REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Graded Sheets - Main results table
CREATE TABLE IF NOT EXISTS graded_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id INTEGER NOT NULL,                -- FK -> answer_keys(id)
    student_id TEXT NOT NULL,               -- Student identifier
    exam_name TEXT,                         -- Name/title of the exam
    filled_sheet_path TEXT,                 -- path to the filled/scanned sheet image
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    percentage REAL NOT NULL,
    correct_count INTEGER NOT NULL,
    wrong_count INTEGER NOT NULL,
    blank_count INTEGER NOT NULL,
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    threshold_used INTEGER DEFAULT 50,      -- bubble detection threshold
    FOREIGN KEY (key_id) REFERENCES answer_keys(id) ON DELETE CASCADE
);

-- 6. Question Results - Detailed per-question results
CREATE TABLE IF NOT EXISTS question_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graded_sheet_id INTEGER NOT NULL,       -- FK -> graded_sheets(id)
    question_number INTEGER NOT NULL,
    student_answer TEXT,                    -- e.g., "A,C" or NULL for blank
    correct_answer TEXT NOT NULL,           -- e.g., "A,C"
    is_correct BOOLEAN NOT NULL,
    points REAL DEFAULT 1.0,
    FOREIGN KEY (graded_sheet_id) REFERENCES graded_sheets(id) ON DELETE CASCADE
);

-- ============================================
-- INDEXES (for performance)
-- ============================================

CREATE INDEX IF NOT EXISTS idx_templates_sheet ON templates(sheet_id);
CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(name);
CREATE INDEX IF NOT EXISTS idx_answer_keys_template ON answer_keys(template_id);
CREATE INDEX IF NOT EXISTS idx_answer_keys_name ON answer_keys(name);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_key ON graded_sheets(key_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_student ON graded_sheets(student_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_date ON graded_sheets(graded_at);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_exam ON graded_sheets(exam_name);
CREATE INDEX IF NOT EXISTS idx_question_results_sheet ON question_results(graded_sheet_id);
CREATE INDEX IF NOT EXISTS idx_question_results_question ON question_results(question_number);
CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id);

-- ============================================
-- TRIGGERS (for maintaining student performance)
-- ============================================

-- Update student performance after grading
CREATE TRIGGER IF NOT EXISTS update_student_performance_after_grade
AFTER INSERT ON graded_sheets
BEGIN
    -- Insert student if not exists
    INSERT OR IGNORE INTO students (student_id, name, class)
    VALUES (NEW.student_id, NULL, NULL);
    
    -- Update student performance statistics
    UPDATE students
    SET 
        total_exams = total_exams + 1,
        total_score = total_score + NEW.correct_count,
        total_questions = total_questions + NEW.total_questions,
        avg_percentage = ROUND(
            (CAST(total_score + NEW.correct_count AS REAL) / 
             CAST(total_questions + NEW.total_questions AS REAL)) * 100, 2
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE student_id = NEW.student_id;
END;

-- Recalculate student performance on grade deletion
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
            SELECT COALESCE(SUM(correct_count), 0)
            FROM graded_sheets 
            WHERE student_id = OLD.student_id
        ),
        total_questions = (
            SELECT COALESCE(SUM(total_questions), 0)
            FROM graded_sheets 
            WHERE student_id = OLD.student_id
        ),
        avg_percentage = ROUND(
            CASE 
                WHEN (SELECT SUM(total_questions) FROM graded_sheets WHERE student_id = OLD.student_id) > 0
                THEN (
                    CAST((SELECT SUM(correct_count) FROM graded_sheets WHERE student_id = OLD.student_id) AS REAL) /
                    CAST((SELECT SUM(total_questions) FROM graded_sheets WHERE student_id = OLD.student_id) AS REAL)
                ) * 100
                ELSE 0
            END, 2
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
    s.total_score || '/' || s.total_questions AS overall_score,
    MIN(gs.percentage) AS lowest_score,
    MAX(gs.percentage) AS highest_score,
    s.updated_at AS last_exam_date
FROM students s
LEFT JOIN graded_sheets gs ON s.student_id = gs.student_id
GROUP BY s.student_id;

-- Exam Results Summary
CREATE VIEW IF NOT EXISTS exam_summary AS
SELECT 
    gs.exam_name,
    ak.name AS answer_key_name,
    t.name AS template_name,
    COUNT(gs.id) AS total_students,
    ROUND(AVG(gs.percentage), 2) AS avg_score,
    MIN(gs.percentage) AS min_score,
    MAX(gs.percentage) AS max_score,
    SUM(CASE WHEN gs.percentage >= 80 THEN 1 ELSE 0 END) AS excellent_count,
    SUM(CASE WHEN gs.percentage >= 60 AND gs.percentage < 80 THEN 1 ELSE 0 END) AS good_count,
    SUM(CASE WHEN gs.percentage < 60 THEN 1 ELSE 0 END) AS needs_improvement
FROM graded_sheets gs
JOIN answer_keys ak ON gs.key_id = ak.id
JOIN templates t ON ak.template_id = t.id
GROUP BY gs.exam_name, ak.name, t.name;

-- Question Difficulty Analysis (Fixed)
CREATE VIEW IF NOT EXISTS question_difficulty AS
SELECT 
    gs.key_id,
    ak.name AS answer_key_name,
    gs.exam_name,
    qr.question_number,
    COUNT(*) AS total_attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
    SUM(CASE WHEN qr.is_correct = 0 THEN 1 ELSE 0 END) AS wrong_count,
    SUM(CASE WHEN qr.student_answer IS NULL THEN 1 ELSE 0 END) AS blank_count,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate
FROM question_results qr
JOIN graded_sheets gs ON qr.graded_sheet_id = gs.id
JOIN answer_keys ak ON gs.key_id = ak.id
GROUP BY gs.key_id, qr.question_number
ORDER BY gs.key_id, qr.question_number;

-- Recent Grading Results
CREATE VIEW IF NOT EXISTS recent_grades AS
SELECT 
    gs.id,
    gs.student_id,
    gs.exam_name,
    gs.percentage,
    gs.correct_count || '/' || gs.total_questions AS score,
    gs.graded_at,
    ak.name AS answer_key_name,
    t.name AS template_name
FROM graded_sheets gs
JOIN answer_keys ak ON gs.key_id = ak.id
JOIN templates t ON ak.template_id = t.id
ORDER BY gs.graded_at DESC
LIMIT 50;

-- Template-Sheet Overview
CREATE VIEW IF NOT EXISTS template_overview AS
SELECT 
    s.id AS sheet_id,
    s.name AS sheet_name,
    s.file_path AS sheet_path,
    t.id AS template_id,
    t.name AS template_name,
    t.total_questions,
    COUNT(DISTINCT ak.id) AS answer_keys_count,
    s.created_at
FROM sheets s
LEFT JOIN templates t ON s.id = t.sheet_id
LEFT JOIN answer_keys ak ON t.id = ak.template_id
GROUP BY s.id;