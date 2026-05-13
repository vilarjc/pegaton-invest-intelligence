import sqlite3

DB_PATH = '/root/pegaton_invest_intelligence/harness.db'
conn = sqlite3.connect(DB_PATH)

conn.executescript('''
CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_code TEXT UNIQUE NOT NULL,
    source TEXT DEFAULT 'manual',
    req_type TEXT DEFAULT 'feature',
    client_priority TEXT DEFAULT 'medium',
    internal_priority TEXT DEFAULT 'P2',
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    epic_id INTEGER DEFAULT NULL,
    tasks_count INTEGER DEFAULT 0,
    tasks_done INTEGER DEFAULT 0,
    progress_pct REAL DEFAULT 0,
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_priority ON requirements(internal_priority);
''')

conn.commit()

# Verify
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requirements'")
print('Tabla requirements:', 'EXISTS' if cur.fetchone() else 'MISSING')

cols = [r[1] for r in conn.execute('PRAGMA table_info(requirements)')]
print('Columns:', cols)

# Verify HarnessDB still works
conn2 = sqlite3.connect(DB_PATH)
cur2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur2.fetchall()]
print('All tables:', tables)
conn2.close()
conn.close()
print('Done!')