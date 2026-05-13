"""Roundtable Engine: multi-model consensus analysis system.

Takes a symbol, runs the same analysis on multiple models,
compares results, finds consensus, and produces a final decision.
If uncertainty is high, can consult expert agents."""
import asyncio
import json
import re
from typing import Optional
from .providers import get_provider, get_active_models


# === PROMPTS ===

SYSTEM_PROMPT = """Eres un analista de inversiones experto. Recibes datos macroeconómicos y técnicos de un activo financiero.
Debes:
1. Analizar los datos proporcionados
2. Calcular un score de inversión (0-100)
3. Recomendar una acción: COMPRAR (80+), ACUMULAR (60-79), MANTENER (40-59), REDUCIR (20-39), EVITAR (0-19)
4. Explicar tu razonamiento en detalle
5. Evaluar el nivel de riesgo (BAJO, MEDIO, ALTO)
6. Identificar los 2-3 factores más importantes que influyen en tu decisión

Responde ÚNICAMENTE en el siguiente formato JSON (sin markdown, sin ```, solo JSON puro):
{
  "score": <número 0-100>,
  "action": "COMPRAR|ACUMULAR|MANTENER|REDUCIR|EVITAR",
  "risk": "BAJO|MEDIO|ALTO",
  "reasoning": "<explicación detallada de 2-3 párrafos>",
  "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "confidence": <número 0-100>
}"""


def build_analysis_prompt(symbol: str, macro_data: dict, technical_data: dict) -> str:
    """Build the analysis prompt with real data for a symbol."""
    
    # Format macro data
    macro_str = "Datos Macroeconómicos:\n"
    indicators = macro_data.get("details", {}).get("indicators", {})
    if indicators:
        for name, info in indicators.items():
            macro_str += f"- {name}: {info.get('value', 'N/A')} (Score parcial: {info.get('score', 'N/A')})\n"
        macro_str += f"\nScore macro combinado: {macro_data.get('macro_score', 'N/A')}\n"
    else:
        macro_str += "- No hay datos macro disponibles (usando valor neutral)\n"
    
    # Format technical data
    tech_str = "\nDatos Técnicos:\n"
    details = technical_data.get("details", {})
    if details and "error" not in details:
        tech_str += f"- Precio actual: ${details.get('last_close', 'N/A')}\n"
        tech_str += f"- RSI(14): {details.get('rsi', 'N/A')}\n"
        tech_str += f"- MACD: {'Alcista (señal de compra)' if details.get('macd_bullish') else 'Bajista (señal de venta)'}\n"
        tech_str += f"- MACD Histograma: {details.get('macd_histogram', 'N/A')}\n"
        tech_str += f"- SMA50: {'Precio POR ENCIMA (alcista)' if details.get('sma50_above') else 'Precio POR DEBAJO (bajista)'} ({details.get('sma50_distance', 'N/A')}% de distancia)\n"
        tech_str += f"- SMA200: {'Precio POR ENCIMA (alcista)' if details.get('sma200_above') else 'Precio POR DEBAJO (bajista)'} ({details.get('sma200_distance', 'N/A')}% de distancia)\n"
    else:
        tech_str += "- No hay datos técnicos disponibles localmente. Datos aproximados.\n"
    
    prompt = f"""Eres un analista de inversiones experto analizando {symbol}.

{macro_str}
{tech_str}

Basado en estos datos, genera tu análisis y score para {symbol}."""
    
    return prompt


def parse_llm_response(content: str) -> dict:
    """Parse the LLM response, extracting JSON from various formats."""
    if not content:
        return {
            "score": 50,
            "action": "MANTENER",
            "risk": "MEDIO",
            "reasoning": "No se pudo obtener respuesta del modelo.",
            "key_factors": ["Error de conexión"],
            "confidence": 0,
            "parse_error": True,
        }
    
    # Try direct JSON parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object anywhere in the text
    json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Fallback: extract score via regex
    score_match = re.search(r'(?:score|puntuaci[óo]n|calificaci[óo]n)\s*[:\s]+(\d{1,3})', content, re.I)
    score = int(score_match.group(1)) if score_match else 50
    
    action_match = re.search(r'(COMPRAR|ACUMULAR|MANTENER|REDUCIR|EVITAR)', content)
    action = action_match.group(1) if action_match else "MANTENER"
    
    risk_match = re.search(r'(BAJO|MEDIO|ALTO)', content)
    risk = risk_match.group(1) if risk_match else "MEDIO"
    
    return {
        "score": score,
        "action": action,
        "risk": risk,
        "reasoning": content[:500],
        "key_factors": ["Parseo automático - ver reasoning completo"],
        "confidence": 50,
        "parse_fallback": True,
    }


# === CONSENSUS ENGINE ===

def compute_consensus(results: list) -> dict:
    """Analyze results from multiple models and compute consensus."""
    valid_results = [r for r in results if r.get("score") is not None and "error" not in r]
    
    if not valid_results:
        return {
            "consensus_score": 50,
            "consensus_action": "MANTENER",
            "consensus_risk": "MEDIO",
            "confidence": 0,
            "agreements": [],
            "disagreements": ["Ningún modelo pudo completar el análisis"],
            "final_reasoning": "Error: no hay resultados válidos para generar consenso.",
            "model_count": len(results),
            "valid_count": 0,
        }
    
    # Scores
    scores = [r["score"] for r in valid_results]
    avg_score = round(sum(scores) / len(scores), 1)
    score_spread = max(scores) - min(scores)
    
    # Actions
    action_counts = {}
    for r in valid_results:
        act = r.get("action", "MANTENER")
        action_counts[act] = action_counts.get(act, 0) + 1
    majority_action = max(action_counts, key=action_counts.get)
    majority_pct = action_counts[majority_action] / len(valid_results)
    
    # Risk
    risk_counts = {}
    for r in valid_results:
        risk = r.get("risk", "MEDIO")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    consensus_risk = max(risk_counts, key=risk_counts.get) if risk_counts else "MEDIO"
    
    # Confidence
    # High: score spread < 15 AND majority > 60% AND no errors
    # Medium: score spread < 25 OR majority > 50%
    # Low: otherwise
    if score_spread < 15 and majority_pct >= 0.6:
        confidence_level = "ALTA"
        confidence_score = 80 + (majority_pct - 0.6) * 50
    elif score_spread < 25 and majority_pct >= 0.5:
        confidence_level = "MEDIA"
        confidence_score = 50 + (1 - score_spread / 50) * 30
    else:
        confidence_level = "BAJA"
        confidence_score = max(20, 50 - score_spread * 2)
    
    confidence_score = min(99, round(confidence_score))
    
    # Agreements: find common points in reasoning
    agreements = []
    if score_spread < 20:
        agreements.append(f"Los modelos coinciden en el rango de score ({min(scores)}-{max(scores)})")
    if majority_pct >= 0.5:
        agreements.append(f"{int(majority_pct*100)}% de los modelos recomiendan '{majority_action}'")
    if len(set(r.get("risk") for r in valid_results)) == 1:
        agreements.append(f"Todos los modelos coinciden en riesgo {consensus_risk}")
    
    # Key factors (common themes)
    all_factors = []
    for r in valid_results:
        all_factors.extend(r.get("key_factors", []))
    factor_counts = {}
    for f in all_factors:
        # Normalize factor text for comparison
        f_norm = f.lower().strip()
        factor_counts[f_norm] = factor_counts.get(f_norm, 0) + 1
    common_factors = [f for f, c in factor_counts.items() if c >= 2]
    if common_factors:
        agreements.append(f"Factores comunes identificados: {', '.join(common_factors[:3])}")
    
    # Disagreements
    disagreements = []
    if score_spread >= 20:
        disagreements.append(f"Diferencia de {score_spread} puntos en scores ({min(scores)} vs {max(scores)})")
    if len(action_counts) > 1:
        other_actions = [a for a in action_counts if a != majority_action]
        disagreements.append(f"Discrepancia en acción: {majority_action} vs {', '.join(other_actions)}")
    if len(set(r.get("risk") for r in valid_results)) > 1:
        risks_set = list(set(r.get("risk") for r in valid_results))
        disagreements.append(f"Diferencia en evaluación de riesgo: {' vs '.join(risks_set)}")
    
    # If confidence is low, suggest expert consultation
    needs_expert = confidence_level == "BAJA"
    expert_suggestion = None
    if needs_expert and score_spread > 30:
        expert_suggestion = "Se recomienda consultar al Agente de Geoeconomía para evaluar factores externos (aranceles, tensiones geopolíticas) que podrían estar causando las señales contradictorias."
    elif needs_expert:
        expert_suggestion = "Se recomienda consultar a un agente experto (Macro o Geopolítica) para resolver las discrepancias entre modelos."
    
    # Build final reasoning
    final_reason = f"Consenso tras analizar {len(valid_results)} modelos: "
    if confidence_level == "ALTA":
        final_reason += f"Alta confianza. Score promedio {avg_score} ({majority_action}). "
    elif confidence_level == "MEDIA":
        final_reason += f"Confianza media. Score promedio {avg_score}. Mayoría opta por {majority_action}. "
    else:
        final_reason += f"Confianza baja. Scores divergentes ({min(scores)}-{max(scores)}). "
    
    final_reason += f"Riesgo {consensus_risk}. "
    if disagreements:
        final_reason += f"Puntos de discrepancia: {'; '.join(disagreements[:2])}. "
    if needs_expert:
        final_reason += expert_suggestion
    
    return {
        "consensus_score": avg_score,
        "consensus_action": majority_action,
        "consensus_risk": consensus_risk,
        "confidence": confidence_level,
        "confidence_score": confidence_score,
        "agreements": agreements,
        "disagreements": disagreements,
        "final_reasoning": final_reason,
        "needs_expert_consult": needs_expert,
        "expert_suggestion": expert_suggestion,
        "model_count": len(results),
        "valid_count": len(valid_results),
        "score_spread": score_spread,
        "majority_pct": round(majority_pct * 100),
    }


# === MAIN ROUNDTABLE FUNCTION ===

async def run_roundtable(
    symbol: str,
    macro_data: dict,
    technical_data: dict,
    models: Optional[list] = None,
    provider_names: Optional[list] = None,
) -> dict:
    """
    Run a multi-model roundtable analysis for a symbol.
    
    Args:
        symbol: The ticker symbol (e.g., 'SPY', 'BTC/USD')
        macro_data: Pre-fetched macro data dict
        technical_data: Pre-fetched technical data dict
        models: List of model IDs to use (e.g., ['deepseek-v4-flash', 'deepseek-reasoner'])
                If None, uses all available models
        provider_names: List of provider names to include (e.g., ['deepseek'])
                        If None, uses all providers with available models
    
    Returns:
        Dict with individual model results + consensus analysis
    """
    prompt = build_analysis_prompt(symbol, macro_data, technical_data)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    
    # Determine which models to use
    if models is None:
        available = get_active_models()
        # Filter by provider if specified
        if provider_names:
            available = [m for m in available if m["provider"] in provider_names]
        models = [m["id"] for m in available]
    
    # Execute all model calls in parallel with timing
    tasks = []
    for model_id in models:
        provider_name = model_id.split("/")[0] if "/" in model_id else \
                        model_id.split("-")[0]  # e.g., 'deepseek-v4-flash' -> 'deepseek'

        # Handle model ID mapping for provider lookup
        if model_id.startswith("deepseek"):
            provider_name = "deepseek"
        elif model_id.startswith("gemini"):
            provider_name = "gemini"
        elif model_id.startswith("groq"):
            provider_name = "groq"
        elif model_id.startswith("nvidia") or model_id.startswith("google") or model_id.startswith("meta") or model_id.startswith("qwen"):
            provider_name = "openrouter"

        try:
            provider = get_provider(provider_name)
            tasks.append((model_id, provider_name, provider.chat(model_id, messages)))
        except ValueError:
            # Unknown provider, skip
            continue

    # Execute all calls in parallel and track timing
    raw_results = []
    import time as time_module
    for model_id, provider_name, task in tasks:
        start = time_module.time()
        try:
            result = await task
            elapsed = time_module.time() - start
            if isinstance(result, dict) and "content" in result:
                result["response_time"] = elapsed
            raw_results.append(result)
        except Exception as e:
            raw_results.append({"error": str(e), "model": model_id})
            elapsed = time_module.time() - start
    
    # Process results
    results = []
    for r in raw_results:
        if isinstance(r, Exception):
            results.append({"error": str(r), "parsed": None})
        elif isinstance(r, dict) and "error" in r:
            # Provider returned an error message — propagate it
            results.append({"error": r["error"], "model": r.get("model", "unknown"), "parsed": None})
        elif isinstance(r, dict) and "content" in r:
            parsed = parse_llm_response(r["content"])
            parsed["_raw"] = r  # Keep raw provider info
            results.append(parsed)
        else:
            results.append({"error": "Invalid response", "parsed": None})
    
    # Compute consensus
    consensus = compute_consensus(results)
    
    # Build model summary
    model_summaries = []
    for r in results:
        raw = r.get("_raw", {})
        model_summaries.append({
            "provider": raw.get("provider", "unknown"),
            "model": raw.get("model", r.get("model", "unknown")),
            "model_name": raw.get("model_name", raw.get("model", r.get("model", "unknown"))),
            "score": r.get("score"),
            "action": r.get("action"),
            "risk": r.get("risk"),
            "confidence": r.get("confidence"),
            "cost": raw.get("cost", 0),
            "tokens_in": raw.get("tokens_in", 0),
            "tokens_out": raw.get("tokens_out", 0),
            "total_tokens": raw.get("total_tokens", 0),
            "reasoning": (r.get("reasoning", "") or "")[:300],
            "key_factors": r.get("key_factors", []),
            "error": r.get("error") or raw.get("error"),
            "parse_error": r.get("parse_error"),
            "parse_fallback": r.get("parse_fallback"),
        })
    
    # Calculate total cost
    total_cost = sum(ms.get("cost", 0) for ms in model_summaries)
    total_tokens = sum(ms.get("total_tokens", 0) for ms in model_summaries)
    
    return {
        "symbol": symbol,
        "timestamp": None,  # Will be set by API
        "models_used": len(model_summaries),
        "total_cost": round(total_cost, 6),
        "total_tokens": total_tokens,
        "consensus": consensus,
        "models": model_summaries,
    }
