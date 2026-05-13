"""
Requirements API — Endpoint para gestión de requerimientos del cliente.
SDD Nivel 2 — Parte de HU-REQ-001, HU-REQ-003, HU-REQ-004.

Endpoints:
  POST   /api/v1/requirements          → Crear requerimiento
  GET    /api/v1/requirements          → Listar con filtros
  GET    /api/v1/requirements/{id}     → Detalle + tareas + progreso
  PUT    /api/v1/requirements/{id}/status → Cambiar estado
"""
import os, sys, json
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from harness.requirements_db import get_requirements_db
from harness.harness_db import HarnessDB

router = APIRouter()


def _enrich(req: dict) -> dict:
    """Agrega tareas derivadas y progreso a un requerimiento."""
    enriched = dict(req)
    tasks = []
    if req.get('epic_id'):
        db = HarnessDB()
        tasks = db.get_tasks_by_epic_code_query(req['epic_id'])
        # fallback: buscar tareas por req_code en tags/description
    # Buscar tareas cuyo code referencia al REQ
    req_code = req.get('req_code', '')
    enriched['linked_tasks'] = tasks
    pct = req.get('progress_pct', 0)
    enriched['progress'] = {
        'tasks_total': req.get('tasks_count', 0),
        'tasks_done': req.get('tasks_done', 0),
        'pct': pct
    }
    enriched['is_complete'] = pct >= 100 and req.get('status') == 'done'
    return enriched


@router.post("/requirements")
async def create_requirement(
    source: str = Query(default="manual", description="Fuente del requerimiento"),
    req_type: str = Query(default="feature", description="Tipo: feature, bug, mejora"),
    client_priority: str = Query(default="medium", description="Prioridad del cliente"),
    title: str = Query(..., description="Título corto del requerimiento"),
    description: str = Query(default="", description="Descripción completa"),
    internal_priority: str = Query(default="P2", description="P0/P1/P2/P3"),
):
    """Registra un nuevo requerimiento del cliente."""
    rdb = get_requirements_db()
    rid = rdb.create_requirement(
        source=source, req_type=req_type,
        client_priority=client_priority, title=title,
        description=description, internal_priority=internal_priority
    )
    req = rdb.get_requirement(rid)
    return {"status": "created", "requirement": _enrich(req)}


@router.get("/requirements")
async def list_requirements(
    status: str = Query(None, description="Filtrar por estado"),
    req_type: str = Query(None, description="Filtrar por tipo"),
    priority: str = Query(None, description="Filtrar por prioridad P0-P3"),
):
    """Lista requerimientos con filtros opcionales."""
    rdb = get_requirements_db()
    reqs = rdb.list_requirements(status=status, req_type=req_type, internal_priority=priority)
    enriched = [_enrich(r) for r in reqs]
    return {"count": len(enriched), "requirements": enriched}


@router.get("/requirements/{req_id}")
async def get_requirement(req_id: int):
    """Detalle de un requerimiento específico."""
    rdb = get_requirements_db()
    req = rdb.get_requirement(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requerimiento no encontrado")
    return {"requirement": _enrich(req)}


@router.put("/requirements/{req_id}/status")
async def update_requirement_status(req_id: int, status: str = Query(..., description="Nuevo estado")):
    """Actualiza el estado de un requerimiento."""
    valid = ['pending', 'classified', 'decomposed', 'in_progress', 'done', 'blocked']
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Usar: {valid}")
    rdb = get_requirements_db()
    rdb.update_requirement_status(req_id, status)
    return {"status": "updated", "new_status": status}


@router.put("/requirements/{req_id}/classify")
async def classify_requirement(
    req_id: int,
    priority: str = Query(..., description="P0/P1/P2/P3"),
    justification: str = Query(default="", description="Justificación de clasificación"),
):
    """Clasifica un requerimiento con prioridad interna."""
    valid = ['P0', 'P1', 'P2', 'P3']
    if priority not in valid:
        raise HTTPException(status_code=400, detail=f"Prioridad inválida. Usar: {valid}")
    rdb = get_requirements_db()
    req = rdb.classify_requirement(req_id, priority, justification)
    return {"status": "classified", "requirement": _enrich(req)}


@router.get("/requirements/{req_id}/progress")
async def get_progress(req_id: int):
    """Progreso del requerimiento — tareas completadas vs esperadas."""
    rdb = get_requirements_db()
    req = rdb.get_requirement(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requerimiento no encontrado")
    return {
        "req_code": req['req_code'],
        "title": req['title'],
        "progress": {
            "tasks_total": req.get('tasks_count', 0),
            "tasks_done": req.get('tasks_done', 0),
            "pct": req.get('progress_pct', 0),
            "bar": "█" * int(req.get('progress_pct', 0) / 10) + "░" * (10 - int(req.get('progress_pct', 0) / 10))
        },
        "status": req['status'],
        "is_complete": req.get('progress_pct', 0) >= 100 and req['status'] == 'done'
    }