#!/usr/bin/env python3
"""
Requirements DB Module — Pegaton Invest Intelligence
SDD Nivel 2: Manages client requirements lifecycle.
Part of EP-REQ: Sistema de Gestión de Requerimientos del Cliente

Tabla: requirements
  - Registro central de peticiones del cliente
  - Estado: pending → classified → decomposed → in_progress → done/blocked
  - Linked a epics en harness.db

Uso desde cualquier agente:
    from harness.requirements_db import get_requirements_db
    rdb = get_requirements_db()
    rid = rdb.create_requirement(source="manual", req_type="feature", ...)
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "harness.db")


class RequirementsDB:
    """CRUD operations for client requirements and task decomposition."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        """Always return a usable connection (reuse or create)."""
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

    def _row_to_dict(self, row):
        if row is None:
            return None
        return dict(row)

    def _rows_to_dicts(self, rows):
        return [dict(r) for r in rows]

    # ── REQUIREMENTS CRUD ──

    def create_requirement(self, source="manual", req_type="feature",
                           client_priority="medium", title="", description="",
                           internal_priority="P2") -> int:
        """Register a new client requirement. Returns requirement ID."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
        req_code = f"REQ-{count + 1:04d}"
        conn.execute(
            """INSERT INTO requirements
               (req_code, source, req_type, client_priority, internal_priority,
                title, description, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (req_code, source, req_type, client_priority, internal_priority,
             title, description, now, now)
        )
        conn.commit()
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return rid

    def get_requirement(self, req_id: int) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM requirements WHERE id = ?", (req_id,)).fetchone()
        return dict(row) if row else None

    def get_requirement_by_code(self, req_code: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM requirements WHERE req_code = ?", (req_code,)).fetchone()
        return dict(row) if row else None

    def list_requirements(self, status=None, req_type=None, internal_priority=None, limit=50):
        conn = self._get_conn()
        query = "SELECT * FROM requirements WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if req_type:
            query += " AND req_type = ?"
            params.append(req_type)
        if internal_priority:
            query += " AND internal_priority = ?"
            params.append(internal_priority)
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return self._rows_to_dicts(rows)

    def update_requirement_status(self, req_id: int, status: str):
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        conn.execute(
            "UPDATE requirements SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, req_id)
        )
        conn.commit()

    def classify_requirement(self, req_id: int, internal_priority: str, justification=""):
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        conn.execute(
            """UPDATE requirements
               SET internal_priority = ?, status = 'classified',
                   description = COALESCE(description, '') || ?,
                   updated_at = ?
               WHERE id = ?""",
            (internal_priority, f"\n\n[Clasificacion] {justification}", now, req_id)
        )
        conn.commit()
        return self.get_requirement(req_id)

    def link_epic(self, req_id: int, epic_id: int):
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        conn.execute(
            "UPDATE requirements SET epic_id = ?, updated_at = ? WHERE id = ?",
            (epic_id, now, req_id)
        )
        conn.commit()

    def update_progress(self, req_id: int, tasks_count: int, tasks_done: int):
        progress = (tasks_done / tasks_count * 100) if tasks_count > 0 else 0
        conn = self._get_conn()
        conn.execute(
            """UPDATE requirements
               SET tasks_count = ?, tasks_done = ?, progress_pct = ROUND(?, 1),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (tasks_count, tasks_done, progress, req_id)
        )
        conn.commit()

    def get_stats(self) -> dict:
        conn = self._get_conn()
        stats = {}
        for status in ['pending', 'classified', 'decomposed', 'in_progress', 'done', 'blocked']:
            count = conn.execute(
                "SELECT COUNT(*) FROM requirements WHERE status = ?", (status,)
            ).fetchone()[0]
            stats[status] = count
        total = conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
        stats['total'] = total
        return stats

    # ── DECOMPOSITION TEMPLATES ──

    TEMPLATE_DECOMPOSITION = {
        'feature': [
            {'role': 'Experto', 'task_template': 'Definir criterios de aceptacion y especificacion funcional'},
            {'role': 'PM', 'task_template': 'Especificar historias de usuario y priorizacion'},
            {'role': 'Programador', 'task_template': 'Implementar modulo principal'},
            {'role': 'Tester', 'task_template': 'Escribir tests unitarios y de integracion'},
            {'role': 'Programador', 'task_template': 'Implementar endpoint API'},
            {'role': 'Tester', 'task_template': 'Validar endpoint y documentar respuestas'},
        ],
        'bug': [
            {'role': 'Experto', 'task_template': 'Analizar impacto y definir severidad'},
            {'role': 'PM', 'task_template': 'Priorizar y asignar sprint'},
            {'role': 'Programador', 'task_template': 'Reproducir y diagnosticar causa raiz'},
            {'role': 'Programador', 'task_template': 'Implementar fix y tests de regresion'},
            {'role': 'Tester', 'task_template': 'Validar fix en entorno de pruebas'},
        ],
        'mejora': [
            {'role': 'Experto', 'task_template': 'Definir metricas de mejora esperada'},
            {'role': 'PM', 'task_template': 'Especificar alcance y criterios de exito'},
            {'role': 'Programador', 'task_template': 'Implementar mejora'},
            {'role': 'Tester', 'task_template': 'Comparar metricas antes/despues'},
        ],
    }

    def decompose_requirement(self, req_id: int, task_codes: list) -> dict:
        """Mark requirement as decomposed and track associated tasks."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE requirements SET status = 'decomposed', updated_at = datetime('now') WHERE id = ?",
            (req_id,)
        )
        placeholders = ",".join("?" * len(task_codes))
        all_tasks = conn.execute(
            f"SELECT id, status FROM tasks WHERE code IN ({placeholders})", task_codes
        ).fetchall()
        tasks_count = len(all_tasks)
        tasks_done = sum(1 for t in all_tasks if t['status'] == 'done')
        progress = (tasks_done / tasks_count * 100) if tasks_count > 0 else 0
        conn.execute(
            "UPDATE requirements SET tasks_count = ?, tasks_done = ?, progress_pct = ROUND(?, 1) WHERE id = ?",
            (tasks_count, tasks_done, progress, req_id)
        )
        conn.commit()
        return self.get_requirement(req_id)


# Singleton
_req_db = None


def get_requirements_db() -> RequirementsDB:
    global _req_db
    if _req_db is None:
        _req_db = RequirementsDB()
    return _req_db