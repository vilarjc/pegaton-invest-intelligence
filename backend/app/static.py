import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static files from the frontend directory
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'frontend')

def setup_static_files(app):
    """Configure the FastAPI app to serve frontend static files."""
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    
    PAGES = {
        "/": "index.html",
        "/investor": "investor.html",
        "/roundtable": "roundtable.html",
        "/budget": "budget.html",
        "/eval": "eval.html",
        "/processes": "processes.html",
        "/health": "health.html",
        "/agents": "agents.html",
        "/projects": "projects.html",
    }
    
    for route, page in PAGES.items():
        @app.get(route)
        async def serve_page(page=page):
            return FileResponse(os.path.join(FRONTEND_DIR, page))
