"""Macroeconomic indicator scoring for Pegaton Invest Intelligence.
SDD Nivel 2: Parameters defined in pegaton_config.py — Spec #2.
"""
import sqlite3
import os
import pandas as pd
import numpy as np

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pegaton.db')

# Load parameters from config (Spec A)
from backend.app.core.pegaton_config import MACRO_SCORING, FACTOR_ALCISTA, FACTOR_BAJISTA


def get_macro_data(days: int = 90) -> pd.DataFrame:
    """Fetch latest macro indicators from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, indicator, value FROM macro_indicators ORDER BY date DESC",
        conn
    )
    conn.close()
    return df


def get_latest_values() -> dict:
    """Get the most recent value for each indicator."""
    df = get_macro_data()
    if df.empty:
        return {}
    latest = df.groupby('indicator').first().reset_index()
    return {
        row['indicator']: {'value': row['value'], 'date': row['date']}
        for _, row in latest.iterrows()
    }


def apply_scoring_rules(value: float, rules: list) -> float:
    """
    Apply a list of (operator, threshold, score) rules to a value.
    Rules are evaluated in order; first match wins.
    If no match, returns the default score.
    """
    for op, threshold, score in rules:
        if op == 'default':
            return float(score)
        if op == '<=' and value <= threshold:
            return float(score)
        if op == '<' and value < threshold:
            return float(score)
        if op == '>=' and value >= threshold:
            return float(score)
        if op == '>' and value > threshold:
            return float(score)
    return 50.0  # fallback neutral


def macro_score() -> dict:
    """Compute combined macro score (0-100)."""
    data = get_latest_values()
    if not data:
        return {'macro_score': 50, 'factors': [], 'details': {'error': 'No macro data available'}}

    scores = {}
    details = {}
    macro_factors = []
    total_weight = 0.0
    final = 0.0

    for indicator, info in data.items():
        config = MACRO_SCORING.get(indicator)
        if not config:
            continue

        val = info['value']
        score = apply_scoring_rules(val, config['rules'])
        weight = config['weight']

        scores[indicator] = score
        final += score * weight
        total_weight += weight

        details[indicator] = {
            'value': val, 'date': info['date'], 'score': round(score, 1)
        }

        # Direction based on config thresholds
        if score >= FACTOR_ALCISTA:
            direction = 'alcista'
        elif score <= FACTOR_BAJISTA:
            direction = 'bajista'
        else:
            direction = 'neutral'

        macro_factors.append({
            'name': indicator,
            'score': round(score, 1),
            'weight': weight,
            'contribution': round(score * weight, 2),
            'direction': direction,
        })

    if total_weight == 0:
        return {'macro_score': 50, 'factors': [], 'details': details}

    final = final / total_weight

    return {
        'macro_score': round(final, 1),
        'factors': macro_factors,
        'details': {
            'indicators': details,
        }
    }
