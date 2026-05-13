#!/usr/bin/env python3
"""
Model Inventory System — v1

SQLite database that tracks every model in production:
  • What models exist and their specs (pricing, context, capabilities)
  • Where each model is referenced (configs, skills, scripts, crons)
  • Verification history (health check results)

Usage:
  python model_inventory.py --scan     # Full scan of all known files
  python model_inventory.py --report   # Print summary report
  python model_inventory.py --verify   # Run live health checks
"""

import sqlite3
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path("/root/pegaton_invest_intelligence")
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "model_inventory.db"
HERMES_SRC = Path("/usr/local/lib/hermes-agent")
HERMES_HOME = Path("/root/.hermes")
SKILLS_DIR = HERMES_HOME / "skills"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS models (
    id                  TEXT PRIMARY KEY,
    provider            TEXT NOT NULL,
    display_name        TEXT NOT NULL,
    api_model           TEXT,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','deprecated','removed')),
    is_free             INTEGER NOT NULL DEFAULT 0,
    input_price_per_M   REAL,
    output_price_per_M  REAL,
    cache_hit_price_per_M REAL,
    context_window      INTEGER,
    max_output_tokens   INTEGER,
    supports_tools      INTEGER DEFAULT 0,
    supports_vision     INTEGER DEFAULT 0,
    supports_streaming  INTEGER DEFAULT 0,
    last_verified       TEXT,
    verified_ok         INTEGER,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS references_ (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        TEXT NOT NULL REFERENCES models(id),
    file_path       TEXT NOT NULL,
    line_number     INTEGER,
    context_type    TEXT NOT NULL
                    CHECK (context_type IN (
                        'config.yaml','models.py','__init__.py',
                        'cron','skill','script','fallback_providers'
                    )),
    context_section TEXT,
    last_checked    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verification_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id    TEXT NOT NULL REFERENCES models(id),
    checked_at  TEXT NOT NULL DEFAULT (datetime('now')),
    available   INTEGER NOT NULL,
    response_ms INTEGER,
    error       TEXT
);

CREATE INDEX IF NOT EXISTS idx_refs_model ON references_(model_id);
CREATE INDEX IF NOT EXISTS idx_refs_file ON references_(file_path);
CREATE INDEX IF NOT EXISTS idx_vlog_model ON verification_log(model_id);
CREATE INDEX IF NOT EXISTS idx_vlog_time ON verification_log(checked_at);
"""

# ---------------------------------------------------------------------------
# Known model definitions (source of truth for pricing/context)
# ---------------------------------------------------------------------------
# These are compiled from:
#   - backend/app/core/providers/__init__.py
#   - /usr/local/lib/hermes-agent/hermes_cli/models.py (_PROVIDER_MODELS)
#   - hermes-agent skill references/free-model-providers.md
#   - Live API checks
MODEL_SPECS: list[dict] = [
    # ── DeepSeek ────────────────────────────────────────────────────
    {
        "id": "deepseek-v4-flash",
        "provider": "deepseek",
        "display_name": "V4 Flash",
        "api_model": "deepseek-v4-flash",
        "is_free": False,
        "input_price_per_M": 0.14,
        "output_price_per_M": 0.28,
        "cache_hit_price_per_M": 0.0028,
        "context_window": 1_048_576,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_vision": False,
        "supports_streaming": True,
        "notes": "Recomendado para uso diario. Cache hit rate ~98%.",
    },
    {
        "id": "deepseek-v4-pro",
        "provider": "deepseek",
        "display_name": "V4 Pro",
        "api_model": "deepseek-v4-pro",
        "is_free": False,
        "input_price_per_M": 0.435,
        "output_price_per_M": 0.87,
        "cache_hit_price_per_M": 0.003625,
        "context_window": 1_048_576,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_vision": True,
        "supports_streaming": True,
        "notes": "75% OFF hasta 31-May-2026. Críticas.",
    },
    {
        "id": "deepseek-chat",
        "provider": "deepseek",
        "display_name": "Chat (legacy)",
        "api_model": "deepseek-chat",
        "is_free": False,
        "status": "deprecated",
        "input_price_per_M": 0.28,
        "output_price_per_M": 0.42,
        "cache_hit_price_per_M": 0.0028,
        "context_window": 1_048_576,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_vision": False,
        "supports_streaming": True,
        "notes": "DEPRECATED — será removido 24-Jul-2026. Migrar a deepseek-v4-flash.",
    },
    {
        "id": "deepseek-reasoner",
        "provider": "deepseek",
        "display_name": "Reasoner",
        "api_model": "deepseek-reasoner",
        "is_free": False,
        "status": "deprecated",
        "input_price_per_M": 0.55,
        "output_price_per_M": 2.19,
        "cache_hit_price_per_M": 0.0028,
        "context_window": 1_048_576,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_vision": False,
        "supports_streaming": True,
        "notes": "DEPRECATED — caro y no necesario. Usar deepseek-v4-flash o v4-pro.",
    },
    # ── Gemini (Google) ─────────────────────────────────────────────
    {
        "id": "gemini-2.5-flash",
        "provider": "gemini",
        "display_name": "Gemini 2.5 Flash",
        "api_model": "gemini-2.5-flash",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "cache_hit_price_per_M": 0.0,
        "context_window": 1_048_576,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_vision": True,
        "supports_streaming": True,
        "notes": "✅ Funciona en tier gratuito. ~1000 RPM. El mejor modelo gratuito.",
    },
    {
        "id": "gemini-2.5-pro",
        "provider": "gemini",
        "display_name": "Gemini 2.5 Pro",
        "api_model": "gemini-2.5-pro",
        "is_free": True,
        "status": "deprecated",
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 1_048_576,
        "supports_tools": True,
        "supports_vision": True,
        "notes": "BLOQUEADO — 429 en tier gratuito. Solo 2.5 Flash funciona.",
    },
    # ── OpenRouter (free, text-oriented) ────────────────────────────
    {
        "id": "openrouter/owl-alpha",
        "provider": "openrouter",
        "display_name": "Owl Alpha",
        "api_model": "openrouter/owl-alpha",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 1_048_756,
        "supports_tools": True,
        "supports_vision": True,
        "notes": "Mejor modelo gratuito en OR. Agentic, 1M ctx.",
    },
    {
        "id": "nvidia/nemotron-3-super-120b-a12b:free",
        "provider": "openrouter",
        "display_name": "Nemotron 3 Super",
        "api_model": "nvidia/nemotron-3-super-120b-a12b:free",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 262_144,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "120B MoE, 12B active. Bueno para tareas generales.",
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "provider": "openrouter",
        "display_name": "Gemma 4 31B",
        "api_model": "google/gemma-4-31b-it:free",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 262_144,
        "supports_tools": True,
        "supports_vision": True,
        "notes": "Dense 31B, multimodal.",
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "provider": "openrouter",
        "display_name": "Llama 3.3 70B",
        "api_model": "meta-llama/llama-3.3-70b-instruct:free",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 65_536,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "Sólido generalista.",
    },
    {
        "id": "qwen/qwen3-coder:free",
        "provider": "openrouter",
        "display_name": "Qwen3 Coder",
        "api_model": "qwen/qwen3-coder:free",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 262_000,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "480B MoE. Excelente para código.",
    },
    {
        "id": "minimax/minimax-m2.5:free",
        "provider": "openrouter",
        "display_name": "MiniMax M2.5",
        "api_model": "minimax/minimax-m2.5:free",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 196_608,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "SOTA en productividad.",
    },
    # ── Groq (free, text-oriented) ──────────────────────────────────
    {
        "id": "llama-3.3-70b-versatile",
        "provider": "groq",
        "display_name": "Llama 3.3 70B (Groq)",
        "api_model": "llama-3.3-70b-versatile",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 8_192,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "30 RPM, 1K RPD. Ultra rápido.",
    },
    {
        "id": "llama-3.1-8b-instant",
        "provider": "groq",
        "display_name": "Llama 3.1 8B (Groq)",
        "api_model": "llama-3.1-8b-instant",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 8_192,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "Ultrarrápido, 30 RPM.",
    },
    {
        "id": "qwen3-32b",
        "provider": "groq",
        "display_name": "Qwen3 32B (Groq)",
        "api_model": "qwen3-32b",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 8_192,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "60 RPM — más rápido de Groq.",
    },
    {
        "id": "mixtral-8x7b-32768",
        "provider": "groq",
        "display_name": "Mixtral 8x7B (Groq)",
        "api_model": "mixtral-8x7b-32768",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 32_768,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "Buena calidad, 32K ctx.",
    },
    {
        "id": "deepseek-r1-distill-llama-70b",
        "provider": "groq",
        "display_name": "DeepSeek V4 Flash 70B (Groq)",
        "api_model": "deepseek-r1-distill-llama-70b",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 8_192,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "Razonamiento profundo. 30 RPM.",
    },
    {
        "id": "gemma2-9b-it",
        "provider": "groq",
        "display_name": "Gemma 2 9B (Groq)",
        "api_model": "gemma2-9b-it",
        "is_free": True,
        "input_price_per_M": 0.0,
        "output_price_per_M": 0.0,
        "context_window": 8_192,
        "supports_tools": True,
        "supports_vision": False,
        "notes": "Ligero y rápido.",
    },
]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"  ✓ DB initialized at {DB_PATH}")


# ---------------------------------------------------------------------------
# Scan: populate models table from MODEL_SPECS
# ---------------------------------------------------------------------------
def scan_models():
    """Upsert all known models from MODEL_SPECS into the DB."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    for spec in MODEL_SPECS:
        status = spec.get("status", "active")
        cur = conn.execute(
            """SELECT id FROM models WHERE id = ?""", (spec["id"],)
        )
        if cur.fetchone():
            conn.execute(
                """UPDATE models SET
                    provider=?, display_name=?, api_model=?,
                    status=?, is_free=?, input_price_per_M=?,
                    output_price_per_M=?, cache_hit_price_per_M=?,
                    context_window=?, max_output_tokens=?,
                    supports_tools=?, supports_vision=?, supports_streaming=?,
                    notes=?
                   WHERE id=?""",
                (
                    spec["provider"], spec["display_name"], spec.get("api_model"),
                    status, int(spec.get("is_free", False)),
                    spec.get("input_price_per_M"), spec.get("output_price_per_M"),
                    spec.get("cache_hit_price_per_M"),
                    spec.get("context_window"), spec.get("max_output_tokens"),
                    int(spec.get("supports_tools", False)),
                    int(spec.get("supports_vision", False)),
                    int(spec.get("supports_streaming", False)),
                    spec.get("notes", ""),
                    spec["id"],
                ),
            )
            updated += 1
        else:
            conn.execute(
                """INSERT INTO models (
                    id, provider, display_name, api_model, status, is_free,
                    input_price_per_M, output_price_per_M, cache_hit_price_per_M,
                    context_window, max_output_tokens,
                    supports_tools, supports_vision, supports_streaming,
                    notes
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    spec["id"], spec["provider"], spec["display_name"],
                    spec.get("api_model"), status,
                    int(spec.get("is_free", False)),
                    spec.get("input_price_per_M"), spec.get("output_price_per_M"),
                    spec.get("cache_hit_price_per_M"),
                    spec.get("context_window"), spec.get("max_output_tokens"),
                    int(spec.get("supports_tools", False)),
                    int(spec.get("supports_vision", False)),
                    int(spec.get("supports_streaming", False)),
                    spec.get("notes", ""),
                ),
            )
            inserted += 1
    conn.commit()
    conn.close()
    print(f"  ✓ Models: {inserted} inserted, {updated} updated")


# ---------------------------------------------------------------------------
# Scan: find all references to models in files
# ---------------------------------------------------------------------------
def _find_models_in_file(path: Path) -> list[dict]:
    """Search a file for known model IDs and return (model_id, line_number, section)."""
    results = []
    if not path.exists():
        return results
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return results

    # Build pattern: match any known model ID
    known_ids = [spec["id"] for spec in MODEL_SPECS]
    # Also match patterns like 'model: deepseek-v4-flash', '"deepseek-v4-flash"'
    for i, line in enumerate(text.split("\n"), 1):
        for mid in known_ids:
            if mid in line:
                # Determine context section
                section = _infer_section(text, i)
                results.append({
                    "model_id": mid,
                    "line_number": i,
                    "context_section": section,
                })
                break  # one model per line match is enough
    return results


def _infer_section(text: str, line_num: int) -> str:
    """Look upward from line_num to find the nearest YAML key / section header."""
    lines = text.split("\n")
    for i in range(min(line_num - 2, len(lines) - 1), -1, -1):
        line = lines[i].strip()
        if line.endswith(":") and not line.startswith(" "):
            return line.rstrip(":")
        # Python dict key
        m = re.match(r'^\s+["\']?(\w[\w-]*)["\']?\s*:', line)
        if m:
            return m.group(1)
    return "unknown"


def _classify_file(path: Path) -> str:
    """Classify a file into a reference context_type."""
    name = path.name
    if name == "config.yaml":
        return "config.yaml"
    if name == "models.py" and "hermes-agent" in str(path):
        return "models.py"
    if name == "__init__.py" and "providers" in str(path):
        return "__init__.py"
    if name.endswith(".md") and "skills" in str(path):
        return "skill"
    if name.endswith(".py") and "scripts" in str(path):
        return "script"
    return "config.yaml"


def scan_references():
    """Scan all known files for model references."""
    conn = get_conn()
    conn.execute("DELETE FROM references_")
    now = datetime.now(timezone.utc).isoformat()
    total = 0

    files_to_scan = [
        # Hermes config
        HERMES_HOME / "config.yaml",
        # Hermes source
        HERMES_SRC / "hermes_cli" / "models.py",
        HERMES_SRC / "hermes_cli" / "model_switch.py",
        # Backend providers
        BACKEND_DIR / "app" / "core" / "providers" / "__init__.py",
        # Skills directory — all SKILL.md files
        *list(SKILLS_DIR.rglob("SKILL.md")),
        # Scripts directory — all .py files
        *list(BACKEND_DIR.rglob("scripts/*.py")),
        # Cron jobs — we scan the crontab output separately
    ]

    for fpath in files_to_scan:
        if not fpath.exists():
            continue
        refs = _find_models_in_file(fpath)
        ctx_type = _classify_file(fpath)
        for ref in refs:
            conn.execute(
                """INSERT INTO references_ (model_id, file_path, line_number,
                   context_type, context_section, last_checked)
                   VALUES (?,?,?,?,?,?)""",
                (
                    ref["model_id"], str(fpath), ref["line_number"],
                    ctx_type, ref["context_section"], now,
                ),
            )
            total += 1

    conn.commit()
    conn.close()
    print(f"  ✓ References: {total} found across {len(files_to_scan)} files")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_report():
    """Print a human-readable summary of the inventory."""
    conn = get_conn()

    print("\n" + "=" * 72)
    print("  MODEL INVENTORY REPORT")
    print("=" * 72)

    # Summary by provider
    print("\n📦 Models by Provider:\n")
    rows = conn.execute(
        """SELECT provider,
                  COUNT(*) as total,
                  SUM(is_free) as free,
                  SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
                  SUM(CASE WHEN status='deprecated' THEN 1 ELSE 0 END) as deprecated
           FROM models
           GROUP BY provider
           ORDER BY provider"""
    ).fetchall()
    for r in rows:
        print(f"  {r['provider']:12s}  {r['total']:2d} total  "
              f"{r['free']:2d} free  {r['active']:2d} active  "
              f"{r['deprecated']:2d} deprecated")

    # Active models with pricing
    print("\n💰 Active Models — Pricing:\n")
    print(f"  {'Model ID':40s} {'Input$/M':10s} {'Output$/M':10s} {'Ctx':10s} {'Free':5s}")
    print(f"  {'-'*40} {'-'*10} {'-'*10} {'-'*10} {'-'*5}")
    rows = conn.execute(
        """SELECT id, input_price_per_M, output_price_per_M,
                  context_window, is_free
           FROM models WHERE status='active'
           ORDER BY provider, id"""
    ).fetchall()
    for r in rows:
        inp = f"${r['input_price_per_M']:.4f}" if r['input_price_per_M'] else "n/a"
        out = f"${r['output_price_per_M']:.4f}" if r['output_price_per_M'] else "n/a"
        ctx = f"{r['context_window']:,}" if r['context_window'] else "?"
        free = "🆓" if r['is_free'] else "💰"
        print(f"  {r['id']:40s} {inp:>10s} {out:>10s} {ctx:>10s} {free:>5s}")

    # Deprecated models
    print("\n⚠️  Deprecated Models:\n")
    rows = conn.execute(
        """SELECT m.id, m.provider, m.notes
           FROM models m WHERE m.status='deprecated'"""
    ).fetchall()
    if rows:
        for r in rows:
            print(f"  ❌ {r['id']:40s} [{r['provider']}]  {r['notes']}")
    else:
        print("  (none)")

    # References by file
    print("\n📎 References by File:\n")
    rows = conn.execute(
        """SELECT r.file_path, r.context_type,
                  COUNT(*) as refs,
                  GROUP_CONCAT(DISTINCT r.model_id) as models
           FROM references_ r
           GROUP BY r.file_path
           ORDER BY r.context_type, r.file_path"""
    ).fetchall()
    for r in rows:
        short = r["file_path"][:70] if len(r["file_path"]) > 70 else r["file_path"]
        print(f"  [{r['context_type']:15s}] {short}")
        print(f"          {r['refs']} references — {r['models']}")

    # Unreferenced models
    print("\n🔍 Models without references:\n")
    rows = conn.execute(
        """SELECT m.id FROM models m
           WHERE m.id NOT IN (SELECT DISTINCT model_id FROM references_)
           AND m.status = 'active'"""
    ).fetchall()
    if rows:
        for r in rows:
            print(f"  ⚠️  {r['id']} — defined but not used anywhere")
    else:
        print("  (all active models have at least 1 reference)")

    conn.close()
    print()


# ---------------------------------------------------------------------------
# Verify — live health checks (simple stubs, expandable)
# ---------------------------------------------------------------------------
def run_verifications():
    """Ping active models to verify they're reachable."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()

    active = conn.execute(
        """SELECT id, provider, api_model FROM models WHERE status='active'"""
    ).fetchall()

    print(f"\n  Running health checks on {len(active)} active models...\n")

    for m in active:
        model_id = m["id"]
        api_model = m["api_model"] or model_id
        # For now, just log a pending check
        conn.execute(
            """INSERT INTO verification_log (model_id, checked_at, available, error)
               VALUES (?,?,0,'pending — implement live probe')""",
            (model_id, now),
        )
        print(f"  ⏳ {model_id:45s} — pending live probe")

    conn.commit()
    conn.close()
    print("  ⚠️  Live verification stubbed. Implement per-provider HTTP probes.\n")


# ---------------------------------------------------------------------------
# Propose — find deprecated models and suggest replacements
# ---------------------------------------------------------------------------
REPLACEMENT_SUGGESTIONS = {
    "deepseek-chat": {
        "replace_with": "deepseek-v4-flash",
        "reason": "deepseek-chat está deprecado (remoción 24-Jul-2026). deepseek-v4-flash es más barato ($0.14/M vs $0.28/M) y más rápido.",
    },
    "deepseek-reasoner": {
        "replace_with": "deepseek-v4-pro",
        "reason": "deepseek-reasoner es caro ($2.19/M output). deepseek-v4-pro ($0.87/M, 75% OFF hasta 31-May) es suficiente para razonamiento crítico.",
    },
    "gemini-2.5-pro": {
        "replace_with": "gemini-2.5-flash",
        "reason": "gemini-2.5-pro devuelve 429 (quota exceeded) en tier gratuito. gemini-2.5-flash funciona sin límites.",
    },
}


def propose_changes() -> list[dict]:
    """Find deprecated models referenced in files and propose replacements.
    
    Returns a list of dicts, each with:
      - model_id: the deprecated model
      - replacement: suggested replacement model ID
      - reason: why this replacement
      - references: list of {file_path, line_number, context_type, context_section}
    """
    conn = get_conn()
    deprecated = conn.execute(
        "SELECT id, notes FROM models WHERE status='deprecated'"
    ).fetchall()

    proposals = []
    for dep in deprecated:
        dep_id = dep["id"]
        suggestion = REPLACEMENT_SUGGESTIONS.get(dep_id, {})
        replacement = suggestion.get("replace_with", "?")
        reason = suggestion.get("reason", dep["notes"] or "Modelo deprecado sin reemplazo sugerido")

        refs = conn.execute(
            """SELECT file_path, line_number, context_type, context_section
               FROM references_
               WHERE model_id = ? AND file_path NOT LIKE '%model_inventory.py'
               ORDER BY file_path, line_number""",
            (dep_id,),
        ).fetchall()

        if not refs:
            continue

        proposals.append({
            "model_id": dep_id,
            "replacement": replacement,
            "reason": reason,
            "references": [dict(r) for r in refs],
        })

    conn.close()
    return proposals


def print_proposal():
    """Print a human-readable change proposal."""
    proposals = propose_changes()

    print("\n" + "=" * 72)
    print("  📋 MODEL REPLACEMENT PROPOSAL")
    print("=" * 72)

    if not proposals:
        print("\n  ✅ No deprecated models found in active references.")
        print()
        return

    total_refs = sum(len(p["references"]) for p in proposals)
    print(f"\n  Found {len(proposals)} deprecated models with {total_refs} references.\n")

    for i, prop in enumerate(proposals, 1):
        print(f"\n{'─' * 72}")
        print(f"  #{i}  ❌ {prop['model_id']}  →  ✅ {prop['replacement']}")
        print(f"      {prop['reason']}")
        print(f"      References: {len(prop['references'])}")
        print()

        for ref in prop["references"]:
            short = ref["file_path"]
            if len(short) > 75:
                short = "..." + short[-72:]
            print(f"      📄 {short}:{ref['line_number']}")
            print(f"         [{ref['context_type']}] {ref['context_section']}")

    print(f"\n{'═' * 72}")
    print(f"  To apply these changes:  python model_inventory.py --apply")
    print(f"  To review details:       python model_inventory.py --report")
    print()


def apply_proposals():
    """Apply the proposed replacements to all referenced files."""
    import subprocess

    proposals = propose_changes()
    if not proposals:
        print("\n  No proposals to apply.\n")
        return

    total_patches = 0
    for prop in proposals:
        old_id = prop["model_id"]
        new_id = prop["replacement"]
        print(f"\n  🔄 Replacing {old_id} → {new_id}")

        # Group references by file to avoid patching the same file twice
        files_seen = set()
        for ref in prop["references"]:
            fpath = ref["file_path"]
            if fpath in files_seen:
                continue
            files_seen.add(fpath)

            try:
                # Read file content
                with open(fpath, "r") as f:
                    content = f.read()
                
                if old_id not in content:
                    print(f"     ⚠️  {old_id} not found in {fpath} (already clean?)")
                    continue
                
                # Count occurrences
                count = content.count(old_id)
                content = content.replace(old_id, new_id)
                
                with open(fpath, "w") as f:
                    f.write(content)
                
                print(f"     ✅ {fpath}: {count} occurrence(s) replaced")
                total_patches += count
            except Exception as e:
                print(f"     ❌ {fpath}: {e}")

    print(f"\n  ✅ Applied {total_patches} replacements across {len(proposals)} proposals.\n")
    print(f"  ⚠️  Restart Hermes Agent for changes to take effect.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model Inventory System")
    parser.add_argument("--init", action="store_true", help="Initialize DB")
    parser.add_argument("--scan", action="store_true", help="Full scan (models + references)")
    parser.add_argument("--propose", action="store_true", help="Show replacement proposal")
    parser.add_argument("--apply", action="store_true", help="Apply proposed replacements")
    parser.add_argument("--report", action="store_true", help="Print inventory report")
    parser.add_argument("--verify", action="store_true", help="Run live health checks")
    args = parser.parse_args()

    if args.propose:
        init_db()
        print_proposal()
        sys.exit(0)

    if args.apply:
        init_db()
        apply_proposals()
        sys.exit(0)

    if args.init:
        init_db()

    if args.scan:
        init_db()
        scan_models()
        scan_references()

    if args.report:
        init_db()
        print_report()

    if args.verify:
        init_db()
        run_verifications()

    if not any(vars(args).values()):
        # Default: init + scan + report
        init_db()
        scan_models()
        scan_references()
        print_report()

