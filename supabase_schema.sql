-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    full_name TEXT NOT NULL,
    student_id TEXT,
    language TEXT DEFAULT 'en',
    role TEXT NOT NULL DEFAULT 'STUDENT',
    department TEXT,
    semester INTEGER,
    pref_class_reminders BOOLEAN DEFAULT TRUE,
    pref_deadline_reminders BOOLEAN DEFAULT TRUE,
    pref_daily_digest BOOLEAN DEFAULT TRUE,
    pref_notices BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create Teacher-Classes Mapping Table
CREATE TABLE IF NOT EXISTS teacher_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id BIGINT REFERENCES users(id),
    class_id TEXT NOT NULL, -- Format: Dept_Sem
    UNIQUE(teacher_id, class_id)
);

-- 3. Create Timetable Table
CREATE TABLE IF NOT EXISTS timetable (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id TEXT NOT NULL, -- Format: Dept_Sem
    subject TEXT NOT NULL,
    day_of_week INTEGER NOT NULL, -- 0-6 (Mon-Sun)
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    room TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Deadlines Table
CREATE TABLE IF NOT EXISTS deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id TEXT NOT NULL, -- Format: Dept_Sem
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL, -- ASSIGNMENT, EXAM
    due_datetime TIMESTAMPTZ NOT NULL,
    file_id TEXT, -- Optional Telegram file UI for attachments
    reminded_24h BOOLEAN DEFAULT FALSE,
    reminded_1h BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create Notices Table
CREATE TABLE IF NOT EXISTS notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id TEXT NOT NULL, -- Format: Dept_Sem
    author_id BIGINT REFERENCES users(id),
    title TEXT,
    description TEXT,
    content TEXT NOT NULL, -- Kept for backwards compatibility
    file_id TEXT, -- Optional attachment
    category TEXT DEFAULT 'GENERAL', -- GENERAL, EMERGENCY, ACADEMIC
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Create Cancelled Classes Table (Overrides)
CREATE TABLE IF NOT EXISTS cancelled_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot_id UUID REFERENCES timetable(id) ON DELETE CASCADE,
    cancel_date DATE NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(slot_id, cancel_date)
);

-- 7. Create Shared Resources Table
CREATE TABLE IF NOT EXISTS resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id TEXT NOT NULL,
    author_id BIGINT REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    resource_type TEXT NOT NULL, -- 'FILE' or 'LINK'
    content TEXT NOT NULL, -- file_id or URL
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Create Class Overrides Table (for rescheduling)
CREATE TABLE IF NOT EXISTS class_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot_id UUID REFERENCES timetable(id) ON DELETE CASCADE,
    override_date DATE NOT NULL,
    new_start_time TIME,
    new_end_time TIME,
    new_room TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(slot_id, override_date)
);

-- 9. Create Class Configs Table (settings)
CREATE TABLE IF NOT EXISTS class_configs (
    class_id TEXT PRIMARY KEY, -- Dept_Sem
    routine_image_id TEXT, -- Telegram file_id for official routine
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Create Polls Table
CREATE TABLE IF NOT EXISTS polls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id TEXT NOT NULL,
    author_id BIGINT REFERENCES users(id),
    question TEXT NOT NULL,
    options JSONB NOT NULL, -- Array of strings
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Create Poll Votes Table (Internal tracking if needed)
CREATE TABLE IF NOT EXISTS poll_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    poll_id UUID REFERENCES polls(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id),
    option_index INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(poll_id, user_id)
);

-- 12. Create Scheduled Notifications Table (Batching)
CREATE TABLE IF NOT EXISTS scheduled_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id TEXT NOT NULL,
    target_date DATE NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_users_dept_sem ON users(department, semester);
CREATE INDEX IF NOT EXISTS idx_timetable_class ON timetable(class_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_class ON deadlines(class_id);
CREATE INDEX IF NOT EXISTS idx_notices_class ON notices(class_id);
CREATE INDEX IF NOT EXISTS idx_resources_class ON resources(class_id);
CREATE INDEX IF NOT EXISTS idx_polls_class ON polls(class_id);
CREATE INDEX IF NOT EXISTS idx_sched_notif ON scheduled_notifications(status, scheduled_time);

-- 13. Create Results Table
CREATE TABLE IF NOT EXISTS results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    class_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    title TEXT NOT NULL, -- e.g. "CT-1", "Assignment 1"
    marks TEXT, -- e.g. "18/20"
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_results_user ON results(user_id);
