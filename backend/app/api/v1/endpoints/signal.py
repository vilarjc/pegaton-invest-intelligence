"""
Signal Endpoint — GET /api/v1/signal
Combina MacroEngine + TechEngine → Pegaton Score con acción recomendada.
SDD Nivel 2: Referenciado en docs/architecture.md (Sección 6, 8)
"""
import os, sys
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.core.score import pegaton_score, all_scores
from backend.app.core.pegaton_config import ACTIONS

router = APIRouter()


@router.get("/signal")
async def get_signal(
    symbol: str = Query(default="SPY", description="Símbolo a evaluar (ej: SPY, AAPL, EUR/USD)"),
    include_details: bool = Query(default=True, description="Incluir detalles completos de factores"),
):
    """
    Retorna la señal de inversión Pegaton para un símbolo dado.

    **Parámetros:**
    - `symbol` — Símbolo financiero (default: SPY)
    - `include_details` — Si True, incluye desglose completo de factores macro/técnicos

    **Respuesta (200):**
    ```json
    {
      "symbol": "SPY",
      "timestamp": "2026-05-12T19:30:00Z",
      "pegaton_score": 67.4,
      "action": "🔵 ACUMULAR",
      "macro_score": 62.5,
      "technical_score": 70.2,
      "blend": { "macro_weight": 0.40, "technical_weight": 0.60 },
      "factors": { "macro": [...], "technical": [...], "summary": {...} },
      "details": { "macro": {...}, "technical": {...} }
    }
    ```

    **Códigos de error:**
    - 404: Símbolo no encontrado o sin datos disponibles
    - 503: Datos macro no disponibles
    - 500: Error interno inesperado
    """
    try:
        # ── Validar que hay datos macro disponibles ──
        from backend.app.core.macro import macro_score as get_macro
        macro = get_macro()

        if macro is None or macro.get("macro_score") is None:
            raise HTTPException(
                status_code=503,
                detail={"error": "macro_unavailable", "message": "No hay datos macro disponibles"}
            )

        # ── Obtener score técnico (local o on-demand) ──
        from backend.app.core.score import SYMBOLS
        if symbol in SYMBOLS:
            from backend.app.core.technical import technical_score as get_tech
        else:
            from backend.app.core.technical_ondemand import ondemand_technical_score as get_tech

        tech = get_tech(symbol)

        if tech is None or tech.get("technical_score") is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "symbol_not_found", "message": f"No se encontraron datos para el símbolo '{symbol}'"}
            )

        # ── Calcular score combinado ──
        pegaton = pegaton_score(symbol)

        # ── Construir respuesta ──
        result = {
            "symbol": pegaton.get("symbol", symbol),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pegaton_score": pegaton["pegaton_score"],
            "action": pegaton["action"],
            "macro_score": pegaton["macro_score"],
            "technical_score": pegaton["technical_score"],
            "blend": {
                "macro_weight": 0.40,
                "technical_weight": 0.60,
            },
        }

        if include_details:
            result["factors"] = pegaton.get("factors", {})
            result["details"] = {
                "macro": macro.get("details", {}),
                "technical": tech.get("details", {}),
            }

        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": str(exc)}
        )


@router.get("/signals")
async def get_all_signals():
    """
    Retorna las señales para todos los símbolos trackeados.
    Útil para dashboards y vistas de resumen.
    """
    try:
        from backend.app.core.score import all_scores as get_all
        scores = get_all()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(scores),
            "signals": {
                sym: {
                    "pegaton_score": data["pegaton_score"],
                    "action": data["action"],
                    "macro_score": data["macro_score"],
                    "technical_score": data["technical_score"],
                    "factor_dominante": data.get("factors", {}).get("summary", {}).get("factor_dominante"),
                }
                for sym, data in scores.items()
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": str(exc)}
        )