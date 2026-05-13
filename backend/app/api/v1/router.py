"""
API v1 Router — Agrupa todos los endpoints de la API.
Registra: /signal, /news-sentiment, /requirements, /technical, /realtime,
          /backtest, /alerts, /risk
"""
from fastapi import APIRouter
from backend.app.api.v1.endpoints.signal import router as signal_router
from backend.app.api.v1.endpoints.news_sentiment import router as news_router
from backend.app.api.v1.endpoints.requirements import router as requirements_router
from backend.app.api.v1.endpoints.technical import router as technical_router
from backend.app.api.v1.endpoints.realtime import router as realtime_router
from backend.app.api.v1.endpoints.backtest import router as backtest_router
from backend.app.api.v1.endpoints.alerts import router as alerts_router
from backend.app.api.v1.endpoints.risk import router as risk_router

api_v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

# Registrar sub-routers
api_v1_router.include_router(signal_router)
api_v1_router.include_router(news_router)
api_v1_router.include_router(requirements_router)
api_v1_router.include_router(technical_router)
api_v1_router.include_router(realtime_router)
api_v1_router.include_router(backtest_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(risk_router)