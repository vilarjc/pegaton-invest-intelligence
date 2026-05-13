"""
API v1 Router — Agrupa todos los endpoints de la API.
Registra: /signal, /news-sentiment
"""
from fastapi import APIRouter
from backend.app.api.v1.endpoints.signal import router as signal_router
from backend.app.api.v1.endpoints.news_sentiment import router as news_router
from backend.app.api.v1.endpoints.requirements import router as requirements_router

api_v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

# Registrar sub-routers
api_v1_router.include_router(signal_router)
api_v1_router.include_router(news_router)
api_v1_router.include_router(requirements_router)