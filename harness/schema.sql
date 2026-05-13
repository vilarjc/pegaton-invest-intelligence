-- ============================================================================
-- HARNESS ENGINEERING - Database Schema
-- Pegaton Invest Intelligence
-- ============================================================================
-- This is the shared truth for all agents. No file-based state.
-- Follows the spec-driven development (SDD) methodology.
-- Context Management: Regla 20-40% — agents check agent_logs.context_usage_pct
-- ============================================================================

-- 1. EPICS: High-level project themes
CREATE TABLE IF NOT EXISTS epics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,          -- e.g. "EP-01"
    title TEXT NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 5,         -- 1 (highest) to 10
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'cancelled')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 2. TASKS: Atomic units of work (historias de usuario)
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,          -- e.g. "HU-1.1"
    epic_id INTEGER REFERENCES epics(id),
    title TEXT NOT NULL,
    description TEXT,
    acceptance_criteria TEXT,           -- JSON array of criteria
    priority INTEGER DEFAULT 5,         -- 1 (highest) to 10
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'done', 'blocked', 'cancelled')),
    spec_id INTEGER REFERENCES specs(id),  -- Link to active spec
    assignee TEXT,                      -- Agent name
    context_usage_at_assignment REAL,   -- % de contexto usado al asignar (20-40% rule)
    tags TEXT,                          -- JSON array
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 3. SPECS: Spec-Driven Development (SDD) — Nivel 2/3
CREATE TABLE IF NOT EXISTS specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,              -- Full spec in markdown
    version INTEGER DEFAULT 1,
    sdd_level INTEGER DEFAULT 2 CHECK(sdd_level IN (1, 2, 3)),
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'approved', 'implemented', 'superseded')),
    generated_files TEXT,               -- JSON array of file paths with "// Generated from spec"
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 4. AGENT_LOGS: External memory (replaces /progress/ folder)
CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                    -- Groups logs from same agent session
    agent_name TEXT NOT NULL,
    task_id INTEGER REFERENCES tasks(id),
    action TEXT NOT NULL,               -- 'implement', 'review', 'debug', 'research', 'verify', 'refactor'
    summary TEXT NOT NULL,
    files_changed TEXT,                 -- JSON array
    context_usage_pct REAL,            -- 0-100, for 20-40% rule enforcement
    tokens_used INTEGER,
    status TEXT DEFAULT 'started' CHECK(status IN ('started', 'completed', 'failed')),
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 5. ARTIFACTS: Track generated files (chequeo + integridad)
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id),
    file_path TEXT NOT NULL,
    checksum TEXT,
    description TEXT,
    size_bytes INTEGER,
    is_generated_from_spec INTEGER DEFAULT 0,  -- 1 = "do not edit manually"
    created_at TEXT DEFAULT (datetime('now'))
);

-- 6. SESSIONS: Track agent working sessions (context window lifecycle)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    tasks_focused TEXT,                 -- JSON array of task IDs worked on
    context_usage_start REAL DEFAULT 0,
    context_usage_end REAL,
    summary TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'closed', 'interrupted')),
    created_at TEXT DEFAULT (datetime('now')),
    closed_at TEXT
);

-- 7. DECISIONS: Decision log (why things were done)
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id),
    title TEXT NOT NULL,
    context TEXT,                       -- What prompted the decision
    options TEXT,                       -- JSON array of options considered
    chosen TEXT,
    rationale TEXT,
    decided_by TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_tasks_epic ON tasks(epic_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_specs_task ON specs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_session ON agent_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_task ON agent_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created ON agent_logs(created_at);
