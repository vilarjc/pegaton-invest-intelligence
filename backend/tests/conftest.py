"""
Conftest global para pytest — fixtures compartidos
"""
import pytest
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


@pytest.fixture
def client():
    """
    FastAPI TestClient con todos los endpoints v1 registrados.
    """   
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.app.api.v1.router import api_v1_router

    app = FastAPI(
        title="Pegaton Invest Intelligence API",
        version="1.0.0",
    )
    app.include_router(api_v1_router)

    yield TestClient(app)