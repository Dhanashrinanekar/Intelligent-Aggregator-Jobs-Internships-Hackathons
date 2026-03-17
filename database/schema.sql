-- ============================================
-- Complete Database Schema for AI Job Aggregator
-- ============================================

-- Drop existing tables if recreating
DROP TABLE IF EXISTS similarity_score CASCADE;
DROP TABLE IF EXISTS job_vector CASCADE;
DROP TABLE IF EXISTS resume_vector CASCADE;
DROP TABLE IF EXISTS users CASCADE;
-- Don't drop opportunities table as it already exists

-- ============================================
-- 1. USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Hashed password
    skills TEXT,                      -- Comma-separated skills
    resume_file VARCHAR(500),         -- Path to resume file
    resume_text TEXT,                 -- Extracted resume text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- 2. OPPORTUNITIES TABLE (Already exists - just ensure it has these fields)
-- ============================================
-- This table already exists from your scraping code
-- Just verify it has these columns:
-- id, company_name, role, opportunity_type, application_start_date,
-- application_end_date, skills, experience_required, job_portal_name,
-- application_link, created_at, updated_at

-- Add index if not exists
CREATE INDEX IF NOT EXISTS idx_opportunities_created_at ON opportunities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_skills ON opportunities USING gin(to_tsvector('english', skills));

-- ============================================
-- 3. RESUME_VECTOR TABLE
-- ============================================
CREATE TABLE resume_vector (
    vector_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    vector_data TEXT NOT NULL,        -- JSON string of TF-IDF vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one vector per user
    UNIQUE(user_id)
);

CREATE INDEX idx_resume_vector_user ON resume_vector(user_id);

-- ============================================
-- 4. JOB_VECTOR TABLE
-- ============================================
CREATE TABLE job_vector (
    job_vector_id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    vector_data TEXT NOT NULL,        -- JSON string of TF-IDF vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one vector per job
    UNIQUE(job_id)
);

CREATE INDEX idx_job_vector_job ON job_vector(job_id);

-- ============================================
-- 5. SIMILARITY_SCORE TABLE
-- ============================================
CREATE TABLE similarity_score (
    match_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    similarity_score DECIMAL(5,4) NOT NULL,  -- Score between 0.0000 and 1.0000
    rank_position INTEGER,                    -- Rank among all jobs for this user
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_sent BOOLEAN DEFAULT FALSE,         -- Track if email notification sent
    
    -- Prevent duplicate matches
    UNIQUE(user_id, job_id)
);

CREATE INDEX idx_similarity_user ON similarity_score(user_id, similarity_score DESC);
CREATE INDEX idx_similarity_score ON similarity_score(similarity_score DESC);
CREATE INDEX idx_similarity_email_sent ON similarity_score(email_sent) WHERE email_sent = FALSE;

-- ============================================
-- 6. EMAIL_NOTIFICATIONS TABLE (Track sent emails)
-- ============================================
CREATE TABLE email_notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    similarity_score DECIMAL(5,4) NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_status VARCHAR(50) DEFAULT 'sent',  -- sent, failed, pending
    
    -- Prevent duplicate notifications
    UNIQUE(user_id, job_id)
);

CREATE INDEX idx_email_notifications_user ON email_notifications(user_id);
CREATE INDEX idx_email_notifications_sent ON email_notifications(sent_at DESC);

-- ============================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================

-- Sample user (password is 'password123' hashed with bcrypt)
INSERT INTO users (name, email, password, skills) VALUES
('John Doe', 'john@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LS2LFpUbNNrK', 'Python, Machine Learning, SQL, FastAPI');

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS (Useful queries)
-- ============================================

-- View: Top matched jobs per user
CREATE OR REPLACE VIEW user_top_matches AS
SELECT 
    u.user_id,
    u.name,
    u.email,
    o.id as job_id,
    o.company_name,
    o.role,
    s.similarity_score,
    s.rank_position,
    o.application_link
FROM users u
JOIN similarity_score s ON u.user_id = s.user_id
JOIN opportunities o ON s.job_id = o.id
WHERE s.similarity_score >= 0.75
ORDER BY u.user_id, s.similarity_score DESC;

-- View: Jobs requiring email notification
CREATE OR REPLACE VIEW pending_email_notifications AS
SELECT DISTINCT
    s.match_id,
    u.user_id,
    u.name,
    u.email,
    o.id as job_id,
    o.company_name,
    o.role,
    o.application_link,
    s.similarity_score
FROM similarity_score s
JOIN users u ON s.user_id = u.user_id
JOIN opportunities o ON s.job_id = o.id
LEFT JOIN email_notifications en ON s.user_id = en.user_id AND s.job_id = en.job_id
WHERE s.similarity_score >= 0.75
AND en.notification_id IS NULL
ORDER BY s.similarity_score DESC;

-- ============================================
-- GRANT PERMISSIONS (if using specific user)
-- ============================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO job_aggregator_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO job_aggregator_user;

-- ============================================
-- VERIFY SCHEMA
-- ============================================
SELECT 'Database schema created successfully!' as status;

-- Check table counts
SELECT 
    'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'opportunities', COUNT(*) FROM opportunities
UNION ALL
SELECT 'resume_vector', COUNT(*) FROM resume_vector
UNION ALL
SELECT 'job_vector', COUNT(*) FROM job_vector
UNION ALL
SELECT 'similarity_score', COUNT(*) FROM similarity_score
UNION ALL
SELECT 'email_notifications', COUNT(*) FROM email_notifications;