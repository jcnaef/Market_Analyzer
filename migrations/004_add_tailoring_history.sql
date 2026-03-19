CREATE TABLE tailoring_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    experience_company TEXT NOT NULL DEFAULT '',
    experience_title TEXT NOT NULL DEFAULT '',
    original_bullets JSONB NOT NULL,
    tailored_bullets JSONB NOT NULL,
    job_description TEXT NOT NULL DEFAULT '',
    allowed_additions JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tailoring_history_user ON tailoring_history (user_id);
