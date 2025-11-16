-- Answer Sheet Grading System Database Schema
-- SQLite 3.x

PRAGMA foreign_keys = ON;

-- ============================================
-- TABLES
-- ============================================

-- 1. Templates - Store answer sheet templates
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    total_questions INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    has_student_id BOOLEAN DEFAULT 1,
    metadata TEXT  -- JSON for additional info
);

-- 2. Answer Keys - Store correct answers
CREATE TABLE IF NOT EXISTS answer_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'manual',  -- 'manual' or 'scan'
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

-- 3. Students - Store student information
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT,
    class TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Grading Sessions - Group related gradings
CREATE TABLE IF NOT EXISTS grading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template_id INTEGER NOT NULL,
    answer_key_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_batch BOOLEAN DEFAULT 0,
    total_sheets INTEGER DEFAULT 0,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_key_id) REFERENCES answer_keys(id) ON DELETE CASCADE
);

-- 5. Graded Sheets - Main results table
CREATE TABLE IF NOT EXISTS graded_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id TEXT,
    image_path TEXT NOT NULL,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    percentage REAL NOT NULL,
    correct_count INTEGER NOT NULL,
    wrong_count INTEGER NOT NULL,
    blank_count INTEGER NOT NULL,
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    threshold_used INTEGER DEFAULT 50,
    extraction_json TEXT,  -- Full extraction result as JSON
    FOREIGN KEY (session_id) REFERENCES grading_sessions(id) ON DELETE CASCADE
);

-- 6. Question Results - Detailed per-question results
CREATE TABLE IF NOT EXISTS question_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graded_sheet_id INTEGER NOT NULL,
    question_number INTEGER NOT NULL,
    student_answer TEXT,  -- Comma-separated: "A,C"
    correct_answer TEXT NOT NULL,  -- Comma-separated: "A,C"
    is_correct BOOLEAN NOT NULL,
    points REAL DEFAULT 1.0,
    FOREIGN KEY (graded_sheet_id) REFERENCES graded_sheets(id) ON DELETE CASCADE
);

-- ============================================
-- INDEXES (for performance)
-- ============================================

CREATE INDEX IF NOT EXISTS idx_graded_sheets_session ON graded_sheets(session_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_student ON graded_sheets(student_id);
CREATE INDEX IF NOT EXISTS idx_graded_sheets_date ON graded_sheets(graded_at);
CREATE INDEX IF NOT EXISTS idx_question_results_sheet ON question_results(graded_sheet_id);
CREATE INDEX IF NOT EXISTS idx_answer_keys_template ON answer_keys(template_id);

-- ============================================
-- VIEWS (pre-built queries)
-- ============================================

-- Student Performance Summary
CREATE VIEW IF NOT EXISTS student_performance AS
SELECT 
    s.student_id,
    s.name,
    s.class,
    COUNT(gs.id) AS total_sheets,
    ROUND(AVG(gs.percentage), 2) AS avg_percentage,
    SUM(gs.correct_count) AS total_correct,
    SUM(gs.total_questions) AS total_questions,
    MIN(gs.percentage) AS lowest_score,
    MAX(gs.percentage) AS highest_score
FROM students s
LEFT JOIN graded_sheets gs ON s.student_id = gs.student_id
GROUP BY s.student_id;

-- Session Summary
CREATE VIEW IF NOT EXISTS session_summary AS
SELECT 
    sess.id,
    sess.name,
    sess.created_at,
    sess.is_batch,
    t.name AS template_name,
    t.total_questions,
    COUNT(gs.id) AS sheets_graded,
    ROUND(AVG(gs.percentage), 2) AS avg_score,
    MIN(gs.percentage) AS min_score,
    MAX(gs.percentage) AS max_score
FROM grading_sessions sess
LEFT JOIN templates t ON sess.template_id = t.id
LEFT JOIN graded_sheets gs ON sess.id = gs.session_id
GROUP BY sess.id;

-- Question Difficulty Analysis
CREATE VIEW IF NOT EXISTS question_difficulty AS
SELECT 
    qr.question_number,
    COUNT(*) AS total_attempts,
    SUM(CASE WHEN qr.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
    SUM(CASE WHEN qr.is_correct = 0 THEN 1 ELSE 0 END) AS wrong_count,
    ROUND(AVG(CASE WHEN qr.is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS success_rate
FROM question_results qr
GROUP BY qr.question_number
ORDER BY success_rate ASC;

-- Recent Grading Results
CREATE VIEW IF NOT EXISTS recent_grades AS
SELECT 
    gs.id,
    gs.student_id,
    gs.percentage,
    gs.correct_count || '/' || gs.total_questions AS score,
    gs.graded_at,
    sess.name AS session_name,
    t.name AS template_name
FROM graded_sheets gs
JOIN grading_sessions sess ON gs.session_id = sess.id
JOIN templates t ON sess.template_id = t.id
ORDER BY gs.graded_at DESC
LIMIT 50;