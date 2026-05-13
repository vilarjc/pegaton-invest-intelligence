import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

app = FastAPI(
    title="Pegaton Invest Intelligence API",
    description="API for macro-technical investment signals",
    version="0.1.0",
)

# CORS middleware - adjust origins as needed for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from backend.app.api.v1.endpoints.score import router as score_router
app.include_router(score_router, prefix="/api/v1/score", tags=["score"])
from backend.app.api.v1.endpoints.system import router as system_router
app.include_router(system_router, prefix="/api/v1/system", tags=["system"])

# Roundtable (multi-model consensus) router
from backend.app.api.v1.endpoints.roundtable import router as roundtable_router
app.include_router(roundtable_router, prefix="/api/v1/roundtable", tags=["roundtable"])

# Signal router
from backend.app.api.v1.endpoints.signal import router as signal_router
app.include_router(signal_router, prefix="/api/v1", tags=["signal"])

# Model Evaluation router
from backend.app.api.v1.endpoints.eval import router as eval_router
app.include_router(eval_router, prefix="/api/v1/eval", tags=["evaluation"])

# Model Objectives (OKRs) + Auto-Assignment router
from backend.app.api.v1.endpoints.objectives import router as objectives_router
app.include_router(objectives_router, prefix="/api/v1/objectives", tags=["objectives"])

# Fear & Greed router
from backend.app.api.v1.endpoints.fear_greed import router as fear_greed_router
app.include_router(fear_greed_router, prefix="/api/v1/fear-greed", tags=["fear-greed"])

# Requirements router
from backend.app.api.v1.endpoints.requirements import router as requirements_router
app.include_router(requirements_router, prefix="/api/v1", tags=["requirements"])

# News Sentiment router
from backend.app.api.v1.endpoints.news_sentiment import router as news_sentiment_router
app.include_router(news_sentiment_router, prefix="/api/v1", tags=["news-sentiment"])

# Static files (frontend)
from backend.app.static import setup_static_files, FRONTEND_DIR
setup_static_files(app)

# Widget route for Fear & Greed
from fastapi.responses import FileResponse
import os

@app.get("/widget/{widget_path:path}")
async def serve_widget(widget_path: str):
    widget_file = os.path.join(FRONTEND_DIR, "widgets", widget_path)
    if os.path.isfile(widget_file):
        return FileResponse(widget_file)
    from fastapi.responses import HTMLResponse
    return HTMLResponse("<h1>Widget not found</h1>", status_code=404)
# Future routers:
# from app.api.v1.endpoints import macro, technical, watchlist, portfolio
# app.include_router(macro.router, prefix="/api/v1/macro", tags=["macro"])
# app.include_router(technical.router, prefix="/api/v1/technical", tags=["technical"])
# app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
# app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)