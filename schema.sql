BEGIN;

CREATE TABLE users (
    id SERIAL NOT NULL,
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    role VARCHAR,
    avatar VARCHAR,
    account_status VARCHAR DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_users_account_status CHECK (account_status IN ('active', 'suspended'))
);

CREATE TABLE subjects (
    id SERIAL NOT NULL,
    title VARCHAR NOT NULL,
    slug VARCHAR NOT NULL,
    icon VARCHAR,
    color VARCHAR,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    UNIQUE (title)
);

CREATE TABLE children (
    id SERIAL NOT NULL,
    parent_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    age INTEGER,
    date_of_birth VARCHAR,
    education_system VARCHAR NOT NULL,
    level INTEGER NOT NULL,
    grade VARCHAR,
    avatar VARCHAR,
    xp INTEGER,
    streak_days INTEGER,
    active BOOLEAN,
    last_active_date TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES users (id)
);

CREATE TABLE units (
    id SERIAL NOT NULL,
    subject_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    order_num INTEGER,
    PRIMARY KEY (id),
    FOREIGN KEY(subject_id) REFERENCES subjects (id)
);

CREATE TABLE child_subjects (
    id SERIAL NOT NULL,
    child_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT uq_child_subject UNIQUE (child_id, subject_id),
    FOREIGN KEY(child_id) REFERENCES children (id),
    FOREIGN KEY(subject_id) REFERENCES subjects (id)
);

CREATE TABLE lessons (
    id SERIAL NOT NULL,
    unit_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    topic VARCHAR,
    order_num INTEGER,
    curriculum_country VARCHAR,
    objectives JSON,
    learn_content TEXT NOT NULL,
    examples JSON,
    vocabulary JSON,
    key_points JSON,
    bible_reflection TEXT,
    character_connection TEXT,
    default_evidence_task TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(unit_id) REFERENCES units (id)
);

CREATE TABLE lesson_days (
    id SERIAL NOT NULL,
    lesson_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    activity_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    learning_objectives JSON,
    key_concept TEXT,
    bible_reference VARCHAR,
    biblical_theme VARCHAR,
    biblical_application TEXT,
    character_reference VARCHAR,
    estimated_duration VARCHAR,
    ai_script TEXT,
    real_world_context TEXT,
    visual_support TEXT,
    origin_of_knowledge TEXT,
    video_url TEXT,
    practice_questions JSON,
    vocabulary JSON,
    reading_recommendations JSON,
    status VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT uq_lesson_day UNIQUE (lesson_id, day_number),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE lesson_sessions (
    id SERIAL NOT NULL,
    child_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    current_tab INTEGER,
    pedagogical_state JSON,
    messages JSON,
    is_completed BOOLEAN,
    started_at TIMESTAMP WITHOUT TIME ZONE,
    last_active_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT uq_lesson_session_child_lesson_day UNIQUE (child_id, lesson_id, day_number),
    FOREIGN KEY(child_id) REFERENCES children (id),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE quiz_questions (
    id SERIAL NOT NULL,
    lesson_id INTEGER NOT NULL,
    question VARCHAR NOT NULL,
    options JSON NOT NULL,
    correct_answer VARCHAR NOT NULL,
    explanation_correct VARCHAR,
    explanation_incorrect VARCHAR,
    PRIMARY KEY (id),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE student_progress (
    id SERIAL NOT NULL,
    child_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    activity_type VARCHAR,
    status VARCHAR,
    quiz_score INTEGER,
    mastery_status VARCHAR,
    remediation_needed BOOLEAN,
    quiz_xp_awarded BOOLEAN NOT NULL,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT uq_student_progress_child_lesson_day UNIQUE (child_id, lesson_id, day_number),
    FOREIGN KEY(child_id) REFERENCES children (id),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE learning_evidence (
    id SERIAL NOT NULL,
    child_id INTEGER NOT NULL,
    lesson_id INTEGER,
    day_number INTEGER,
    subject VARCHAR NOT NULL,
    lesson_title VARCHAR NOT NULL,
    skill VARCHAR NOT NULL,
    evidence_type VARCHAR,
    submission_type VARCHAR,
    content TEXT,
    file_upload VARCHAR,
    stored_file_name VARCHAR,
    score INTEGER,
    ai_feedback TEXT NOT NULL,
    verified BOOLEAN,
    completion_xp_awarded BOOLEAN NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(child_id) REFERENCES children (id),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE ai_interactions (
    id SERIAL NOT NULL,
    child_id INTEGER NOT NULL,
    lesson_id INTEGER,
    day_number INTEGER,
    session_id VARCHAR,
    role VARCHAR,
    prompt TEXT,
    response TEXT,
    metadata_json JSON,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(child_id) REFERENCES children (id),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE parent_alerts (
    id SERIAL NOT NULL,
    parent_id INTEGER NOT NULL,
    child_id INTEGER,
    severity VARCHAR,
    title VARCHAR NOT NULL,
    subtitle VARCHAR NOT NULL,
    is_read BOOLEAN,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES users (id),
    FOREIGN KEY(child_id) REFERENCES children (id)
);

CREATE TABLE ai_recommendations (
    id SERIAL NOT NULL,
    parent_id INTEGER NOT NULL,
    child_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES users (id),
    FOREIGN KEY(child_id) REFERENCES children (id)
);

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_subjects_id ON subjects (id);
CREATE UNIQUE INDEX ix_subjects_slug ON subjects (slug);
CREATE INDEX ix_children_id ON children (id);
CREATE INDEX ix_units_id ON units (id);
CREATE INDEX ix_child_subjects_id ON child_subjects (id);
CREATE INDEX ix_lessons_id ON lessons (id);
CREATE INDEX ix_lesson_days_id ON lesson_days (id);
CREATE INDEX ix_lesson_sessions_id ON lesson_sessions (id);
CREATE INDEX ix_quiz_questions_id ON quiz_questions (id);
CREATE INDEX ix_student_progress_id ON student_progress (id);
CREATE INDEX ix_learning_evidence_id ON learning_evidence (id);
CREATE INDEX ix_ai_interactions_id ON ai_interactions (id);
CREATE INDEX ix_parent_alerts_id ON parent_alerts (id);
CREATE INDEX ix_ai_recommendations_id ON ai_recommendations (id);

COMMIT;
