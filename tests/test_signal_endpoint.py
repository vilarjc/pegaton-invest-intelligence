#!/usr/bin/env python3
"""Test unitarios para el endpoint GET /api/v1/signal
Spec ref: docs/architecture.md Sección 6, 9.4"""
import pytest
import json
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestSignalEndpoint:
    """Tests para GET /signal"""

    def test_signal_response_schema(self, client):
        """SPEC: test_response_schema — verificar todas las claves de la respuesta"""
        response = client.get("/api/v1/signal")
        assert response.status_code == 200
        data = response.json()
        required_keys = [
            "symbol", "timestamp", "pegaton_score", "action",
            "macro_score", "technical_score", "blend", "factors", "details"
        ]
        for key in required_keys:
            assert key in data, f"Missing key in response: {key}"

    def test_signal_default_symbol(self, client):
        """SPEC: test_signal_default_symbol"""
        response = client.get("/api/v1/signal")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "SPY"

    def test_signal_custom_symbol(self, client):
        """SPEC: test_signal_custom_symbol"""
        response = client.get("/api/v1/signal?symbol=AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"

    def test_signal_status_200(self, client):
        """SPEC: test_signal_status_200"""
        response = client.get("/api/v1/signal")
        assert response.status_code == 200

    def test_signal_pegaton_score_in_range(self, client):
        """SPEC: test_signal_pegaton_score_in_range — score siempre entre 0 y 100"""
        response = client.get("/api/v1/signal")
        data = response.json()
        assert 0 <= data["pegaton_score"] <= 100

    def test_signal_action_valid(self, client):
        """SPEC: test_signal_action_valid — acción debe ser una de las válidas"""
        response = client.get("/api/v1/signal")
        data = response.json()
        action_raw = data["action"]
        action_name = action_raw.split(" ", 1)[1] if " " in action_raw else action_raw
        valid_actions = ["COMPRAR", "ACUMULAR", "MANTENER", "REDUCIR", "EVITAR",
                         "FUERTE_COMPRA", "FUERTE_VENTA", "COMPRA", "VENTA"]
        assert action_name in valid_actions, f"Action '{action_name}' not in valid list"

    def test_signal_blend_weights_sum_one(self, client):
        """SPEC: test_signal_blend_weights"""
        response = client.get("/api/v1/signal")
        data = response.json()
        total_weight = data["blend"]["macro_weight"] + data["blend"]["technical_weight"]
        assert abs(total_weight - 1.0) < 0.001

    def test_signal_signals_endpoint(self, client):
        """Test GET /signals — endpoint de resumen"""
        response = client.get("/api/v1/signals")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "timestamp" in data

    def test_signal_with_include_details_false(self, client):
        """SPEC: test_signal_include_details_false"""
        response = client.get("/api/v1/signal?include_details=false")
        assert response.status_code == 200
        data = response.json()
        assert "pegaton_score" in data
        assert "action" in data

    def test_signal_error_missing_macro_data(self, mocker, client):
        """SPEC: test_signal_error_missing_data — sin datos macro
        FIX: mockea en el módulo donde se importa, no donde se define."""
        mocker.patch(
            "backend.app.core.macro.macro_score",
            return_value={"macro_score": None, "factors": [], "details": {}}
        )
        response = client.get("/api/v1/signal")
        assert response.status_code == 503

    def test_signal_error_symbol_not_found(self, mocker, client):
        """SPEC test_signal_custom_symbol con símbolo sin datos
        FIX: mockea technical_score en su módulo real."""
        mocker.patch(
            "backend.app.core.technical.technical_score",
            return_value={"technical_score": None, "factors": [], "details": {}}
        )
        response = client.get("/api/v1/signal?symbol=INVALID_SYMBOL")
        assert response.status_code in (200, 404)


# ── Fixtures para FastAPI TestClient ──

@pytest.fixture
def client():
    """Crea un TestClient de FastAPI con los endpoints registrados."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.app.api.v1.endpoints.signal import router as signal_router

    app = FastAPI(title="Pegaton API Test")
    app.include_router(signal_router, prefix="/api/v1")

    return TestClient(app)