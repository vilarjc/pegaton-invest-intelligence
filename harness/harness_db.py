#!/usr/bin/env python3
"""
============================================================================
HARNESS DB — Shared Memory Interface for AI Agents
============================================================================
Spec-Driven Development + Harness Engineering
Pegaton Invest Intelligence

This module IS the external memory. Agents call these functions instead of
reading/writing JSON/MD files for state. Follows:
  - SDD Nivel 2/3: Specs are source of truth
  - Regla 20-40%: Track context usage to prevent degradation
  - Atomic operations: Every code change is linked to a task_id

Usage (from any agent session):
    from harness.harness_db import HarnessDB
    db = HarnessDB()
    task = db.get_next_task()
    db.log_activity(session_id, agent_name, task['id'], ...)
============================================================================
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime
from typing import Optional, Any


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "harness.db")


class HarnessDB:
    """Shared memory interface. One instance per agent session."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return dict(row)

    def _rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # EPICS
    # ------------------------------------------------------------------
    def get_epics(self, status: str | None = None) -> list[dict]:
        conn = self.connect()
        if status:
            cur = conn.execute("SELECT * FROM epics WHERE status = ? ORDER BY priority, code", (status,))
        else:
            cur = conn.execute("SELECT * FROM epics ORDER BY priority, code")
        return self._rows_to_dicts(cur.fetchall())

    def create_epic(self, code: str, title: str, description: str = "", priority: int = 5) -> int:
        conn = self.connect()
        cur = conn.execute(
            "INSERT INTO epics (code, title, description, priority) VALUES (?, ?, ?, ?)",
            (code, title, description, priority)
        )
        conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------
    # TASKS — Core operations
    # ------------------------------------------------------------------
    def get_all_tasks(self, epic_id: int | None = None, status: str | None = None) -> list[dict]:
        conn = self.connect()
        query = "SELECT * FROM tasks"
        params = []
        conditions = []
        if epic_id is not None:
            conditions.append("epic_id = ?")
            params.append(epic_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY priority, code"
        cur = conn.execute(query, params)
        return self._rows_to_dicts(cur.fetchall())

    def get_next_task(self, tags: list[str] | None = None) -> dict | None:
        """
        Get the highest-priority pending task. Returns None if nothing pending.
        Optionally filter by tags (e.g. ['backend', 'urgent']).
        This is the primary "what do I do next?" function.
        """
        conn = self.connect()
        if tags:
            # SQLite JSON matching — find tasks whose tags JSON contains any of the given tags
            placeholders = ",".join(f"?" for _ in tags)
            cur = conn.execute(f"""
                SELECT * FROM tasks
                WHERE status = 'pending'
                AND (tags IS NULL OR tags = '[]'
                     OR EXISTS (SELECT 1 FROM json_each(tags) WHERE value IN ({placeholders})))
                ORDER BY priority, id
                LIMIT 1
            """, tags)
        else:
            cur = conn.execute(
                "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority, id LIMIT 1"
            )
        return self._row_to_dict(cur.fetchone())

    def get_tasks_by_epic(self, epic_code: str) -> list[dict]:
        conn = self.connect()
        cur = conn.execute("""
            SELECT t.* FROM tasks t
            JOIN epics e ON t.epic_id = e.id
            WHERE e.code = ?
            ORDER BY t.priority, t.code
        """, (epic_code,))
        return self._rows_to_dicts(cur.fetchall())

    def get_tasks_by_epic_code_query(self, epic_id: int) -> list[dict]:
        """Get tasks linked to an epic by epic ID (used by requirements endpoint)."""
        conn = self.connect()
        cur = conn.execute("SELECT * FROM tasks WHERE epic_id = ? ORDER BY priority, code", (epic_id,))
        return self._rows_to_dicts(cur.fetchall())

    def create_task(self, code: str, title: str, epic_id: int | None = None,
                    description: str = "", acceptance_criteria: list | None = None,
                    priority: int = 5, tags: list | None = None) -> int:
        conn = self.connect()
        cur = conn.execute(
            """INSERT INTO tasks (code, epic_id, title, description, acceptance_criteria,
               priority, tags) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, epic_id, title, description,
             json.dumps(acceptance_criteria or []),
             priority, json.dumps(tags or []))
        )
        conn.commit()
        return cur.lastrowid

    def update_task_status(self, task_id: int, status: str):
        conn = self.connect()
        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, task_id)
        )
        conn.commit()

    def assign_task(self, task_id: int, agent_name: str, context_pct: float = 0):
        conn = self.connect()
        conn.execute(
            "UPDATE tasks SET assignee = ?, context_usage_at_assignment = ?, "
            "status = 'in_progress', updated_at = datetime('now') WHERE id = ?",
            (agent_name, context_pct, task_id)
        )
        conn.commit()

    def get_task(self, task_id: int) -> dict | None:
        conn = self.connect()
        cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return self._row_to_dict(cur.fetchone())

    def get_task_by_code(self, code: str) -> dict | None:
        conn = self.connect()
        cur = conn.execute("SELECT * FROM tasks WHERE code = ?", (code,))
        return self._row_to_dict(cur.fetchone())

    def add_acceptance_criterion(self, task_id: int, criterion: str):
        """Add a single acceptance criterion to an existing task."""
        conn = self.connect()
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        criteria = json.loads(task['acceptance_criteria'] or '[]')
        criteria.append(criterion)
        conn.execute(
            "UPDATE tasks SET acceptance_criteria = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(criteria), task_id)
        )
        conn.commit()

    # ------------------------------------------------------------------
    # SPECS — Spec-Driven Development
    # ------------------------------------------------------------------
    def create_spec(self, task_id: int, title: str, content: str,
                    sdd_level: int = 2, generated_files: list | None = None) -> int:
        """
        Create a spec and link it to a task.
        sdd_level:
          1 = Spec First (write spec, then implement)
          2 = Spec Anchor (spec evolves with code)
          3 = Spec as Source (human only edits spec, AI generates code)
        """
        conn = self.connect()
        # Mark previous specs for this task as superseded
        conn.execute(
            "UPDATE specs SET status = 'superseded', updated_at = datetime('now') "
            "WHERE task_id = ? AND status IN ('draft', 'approved', 'implemented')",
            (task_id,)
        )
        cur = conn.execute(
            """INSERT INTO specs (task_id, title, content, sdd_level, status, generated_files)
               VALUES (?, ?, ?, ?, 'approved', ?)""",
            (task_id, title, content, sdd_level, json.dumps(generated_files or []))
        )
        # Link task to this spec
        conn.execute(
            "UPDATE tasks SET spec_id = ?, updated_at = datetime('now') WHERE id = ?",
            (cur.lastrowid, task_id)
        )
        conn.commit()
        return cur.lastrowid

    def get_spec(self, spec_id: int) -> dict | None:
        conn = self.connect()
        cur = conn.execute("SELECT * FROM specs WHERE id = ?", (spec_id,))
        return self._row_to_dict(cur.fetchone())

    def get_task_spec(self, task_id: int) -> dict | None:
        """Get the active (approved or implemented) spec for a task."""
        conn = self.connect()
        cur = conn.execute(
            "SELECT * FROM specs WHERE task_id = ? AND status IN ('approved', 'implemented') "
            "ORDER BY version DESC LIMIT 1",
            (task_id,)
        )
        return self._row_to_dict(cur.fetchone())

    def update_spec_status(self, spec_id: int, status: str):
        conn = self.connect()
        conn.execute(
            "UPDATE specs SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, spec_id)
        )
        conn.commit()

    # ------------------------------------------------------------------
    # AGENT LOGS — External Memory (replaces /progress/)
    # ------------------------------------------------------------------
    def log_activity(self, session_id: str, agent_name: str, task_id: int | None,
                     action: str, summary: str, files_changed: list | None = None,
                     context_usage_pct: float = 0, tokens_used: int = 0,
                     status: str = 'completed', error_message: str | None = None) -> int:
        """
        Log every agent action. This IS the external memory.
        Before closing a session, the agent should call this with a summary
        so the next agent can pick up where it left off.
        """
        conn = self.connect()
        cur = conn.execute(
            """INSERT INTO agent_logs (session_id, agent_name, task_id, action, summary,
               files_changed, context_usage_pct, tokens_used, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, agent_name, task_id, action, summary,
             json.dumps(files_changed or []), context_usage_pct, tokens_used,
             status, error_message)
        )
        conn.commit()
        return cur.lastrowid

    def get_recent_logs(self, limit: int = 10, task_id: int | None = None,
                        agent_name: str | None = None) -> list[dict]:
        """Get recent agent activity. Useful for context recovery."""
        conn = self.connect()
        query = "SELECT * FROM agent_logs WHERE 1=1"
        params = []
        if task_id is not None:
            query += " AND task_id = ?"
            params.append(task_id)
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(query, params)
        return self._rows_to_dicts(cur.fetchall())

    def get_logs_since(self, timestamp: str, limit: int = 20) -> list[dict]:
        """Get all activity since a given timestamp."""
        conn = self.connect()
        cur = conn.execute(
            "SELECT * FROM agent_logs WHERE created_at >= ? ORDER BY created_at LIMIT ?",
            (timestamp, limit)
        )
        return self._rows_to_dicts(cur.fetchall())

    def get_context_summary(self, task_id: int) -> str:
        """Produce a short text summary of what's happened on a task."""
        logs = self.get_recent_logs(limit=5, task_id=task_id)
        if not logs:
            return f"No activity recorded for task #{task_id}."
        lines = []
        for log in logs:
            lines.append(f"[{log['created_at']}] {log['agent_name']} -> {log['action']}: {log['summary']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # ARTIFACTS — Track generated files
    # ------------------------------------------------------------------
    def register_artifact(self, task_id: int, file_path: str,
                          description: str = "", is_generated_from_spec: bool = False) -> int:
        checksum = self._compute_checksum(file_path)
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        conn = self.connect()
        cur = conn.execute(
            """INSERT INTO artifacts (task_id, file_path, checksum, description, size_bytes,
               is_generated_from_spec) VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, file_path, checksum, description, size, 1 if is_generated_from_spec else 0)
        )
        conn.commit()
        return cur.lastrowid

    def check_artifact_integrity(self, artifact_id: int) -> bool:
        """Verify a generated file hasn't been modified manually."""
        conn = self.connect()
        cur = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
        art = self._row_to_dict(cur.fetchone())
        if not art or not os.path.exists(art['file_path']):
            return False
        current = self._compute_checksum(art['file_path'])
        return current == art['checksum']

    def _compute_checksum(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # SESSIONS — Context window lifecycle
    # ------------------------------------------------------------------
    def open_session(self, session_id: str, agent_name: str,
                     tasks_focused: list | None = None,
                     context_usage_start: float = 0) -> str:
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO sessions (session_id, agent_name, tasks_focused,
               context_usage_start, status)
               VALUES (?, ?, ?, ?, 'active')""",
            (session_id, agent_name, json.dumps(tasks_focused or []), context_usage_start)
        )
        conn.commit()
        return session_id

    def close_session(self, session_id: str, summary: str = "",
                      context_usage_end: float = 0):
        conn = self.connect()
        conn.execute(
            """UPDATE sessions SET status = 'closed', summary = ?,
               context_usage_end = ?, closed_at = datetime('now')
               WHERE session_id = ?""",
            (summary, context_usage_end, session_id)
        )
        conn.commit()

    def get_session(self, session_id: str) -> dict | None:
        conn = self.connect()
        cur = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        return self._row_to_dict(cur.fetchone())

    def get_last_session(self, agent_name: str | None = None) -> dict | None:
        """Get the most recent session. Useful for the 'next agent' to resume."""
        conn = self.connect()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM sessions WHERE agent_name = ? ORDER BY created_at DESC LIMIT 1",
                (agent_name,)
            )
        else:
            cur = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 1"
            )
        return self._row_to_dict(cur.fetchone())

    # ------------------------------------------------------------------
    # DECISIONS — Decision log
    # ------------------------------------------------------------------
    def log_decision(self, task_id: int | None, title: str, context: str,
                     options: list | None = None, chosen: str = "",
                     rationale: str = "", decided_by: str = "") -> int:
        conn = self.connect()
        cur = conn.execute(
            """INSERT INTO decisions (task_id, title, context, options, chosen,
               rationale, decided_by) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task_id, title, context, json.dumps(options or []), chosen, rationale, decided_by)
        )
        conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------
    # REPORTS & UTILITIES
    # ------------------------------------------------------------------
    def get_project_summary(self) -> dict:
        """Quick overview: counts by status, recent activity."""
        conn = self.connect()
        epics_total = conn.execute("SELECT COUNT(*) FROM epics").fetchone()[0]
        tasks_total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        tasks_pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'").fetchone()[0]
        tasks_in_progress = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'").fetchone()[0]
        tasks_done = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'").fetchone()[0]
        tasks_blocked = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'blocked'").fetchone()[0]
        recent_logs = self.get_recent_logs(limit=5)
        recent_logs_text = "\n".join(
            f"  [{l['created_at']}] {l['agent_name']}: {l['action']} - {l['summary'][:80]}"
            for l in recent_logs
        )
        return {
            'epics': epics_total,
            'tasks': {'total': tasks_total, 'pending': tasks_pending,
                      'in_progress': tasks_in_progress, 'done': tasks_done,
                      'blocked': tasks_blocked},
            'recent_activity': recent_logs_text
        }


# ============================================================================
# CLI — Quick operations from terminal
# ============================================================================
if __name__ == "__main__":
    import sys
    db = HarnessDB()

    if len(sys.argv) < 2:
        summary = db.get_project_summary()
        print(f"=== HARNESS DB — Project Summary ===")
        print(f"Epics: {summary['epics']}")
        print(f"Tasks: {summary['tasks']['total']} total "
              f"({summary['tasks']['pending']} pending, "
              f"{summary['tasks']['in_progress']} in_progress, "
              f"{summary['tasks']['done']} done, "
              f"{summary['tasks']['blocked']} blocked)")
        print(f"\nRecent activity:\n{summary['recent_activity']}")
        sys.exit(0)

    command = sys.argv[1]

    if command == "next":
        task = db.get_next_task()
        if task:
            print(f"NEXT TASK: [{task['code']}] {task['title']}")
            print(f"  Priority: {task['priority']}  |  Status: {task['status']}")
            print(f"  Description: {task['description'][:200]}")
            if task['acceptance_criteria']:
                criteria = json.loads(task['acceptance_criteria'])
                for c in criteria:
                    print(f"  ✓ {c}")
        else:
            print("No pending tasks. 🎉")

    elif command == "tasks":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        tasks = db.get_all_tasks(status=status)
        for t in tasks:
            print(f"[{t['code']}] {t['status']:12}  {t['title'][:60]}")

    elif command == "logs":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        logs = db.get_recent_logs(limit=limit)
        for l in logs:
            print(f"[{l['created_at']}] {l['agent_name']:20} {l['action']:12} {l['summary'][:80]}")

    elif command == "summary":
        import pprint
        pprint.pprint(db.get_project_summary())

    else:
        print(f"Unknown command: {command}")
        print("Usage: python harness_db.py [next|tasks|logs|summary]")
