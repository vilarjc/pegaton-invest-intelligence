## Spec: HU-1.2 — Desglose de Factores del Score

### Contexto
Actualmente el endpoint `/api/v1/score/{symbol}` devuelve el Pegaton Score final (0-100)
con macro_score y technical_score agregados, pero sin desglosar los factores individuales
que contribuyen a cada sub-score. El usuario necesita entender QUÉ está impulsando cada score
para poder confiar en la señal y tomar decisiones informadas.

### Interfaz / Contrato
El endpoint existente `/api/v1/score/{symbol}` se extiende para incluir un campo `factors`
en la respuesta. No se crea un endpoint nuevo.

**Request:** GET /api/v1/score/SPY (sin cambios)

**Response** (nuevo campo `factors`):
```json
{
    "symbol": "SPY",
    "pegaton_score": 50.7,
    "action": "MANTENER",
    "macro_score": 45.0,
    "technical_score": 55.0,
    "factors": {
        "macro": [
            {"name": "FEDFUNDS", "score": 35.0, "weight": 0.20, "contribution": 7.0, "direction": "bajista"},
            {"name": "PAYEMS",   "score": 60.0, "weight": 0.15, "contribution": 9.0, "direction": "alcista"}
        ],
        "technical": [
            {"name": "RSI(14)", "score": 45.0, "weight": 0.30, "contribution": 13.5, "direction": "neutral"},
            {"name": "MACD",    "score": 65.0, "weight": 0.25, "contribution": 16.25, "direction": "alcista"}
        ],
        "summary": {
            "factores_alcistas": 3,
            "factores_bajistas": 2,
            "factor_dominante": {"name": "MACD", "direction": "alcista", "contribution": 16.25}
        }
    }
}
```

### Reglas de Negocio
1. **Dirección**: score >= 55 → "alcista", score <= 45 → "bajista", entre 45-55 → "neutral"
2. **Contribución**: score_del_factor * weight (0-100 escalado por peso)
3. **Factor dominante**: el factor con mayor contribución absoluta
4. **Compatibilidad hacia atrás**: campos existentes no cambian

### Criterios de Aceptación
- CA-1: Endpoint /api/v1/score/{symbol} incluye campo `factors`
- CA-2: Cada factor tiene: name, score, weight, contribution, direction
- CA-3: La dirección se calcula dinámicamente según el score del factor
- CA-4: El summary identifica el factor dominante
- CA-5: Compatible con versiones anteriores (campos existentes no cambian)

### Archivos Modificados
- `backend/app/core/macro.py` — añadir lista de factors al dict de retorno
- `backend/app/core/technical.py` — añadir lista de factors al dict de retorno
- `backend/app/core/score.py` — combinar factors en la respuesta final

### Notas Técnicas
- No romper API existente. Solo añadir campo nuevo.
- macro_score() ya calcula contribution por indicador; solo falta formatearlo como lista.
- technical_score() ya calcula rsi_score, macd_score, sma_scores; solo falta exponerlos como factores.
