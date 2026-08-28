from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from pathlib import Path

from .rooms import router as rooms_router
from .database import db

app = FastAPI(
    title="Zoom Clone Pro",
    description="Professional Video Conferencing Platform",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rooms_router)

# Serve frontend
frontend_path = Path(__file__).parent.parent.parent / "frontend"

@app.get("/")
async def serve_index():
    return FileResponse(frontend_path / "index.html")

@app.get("/style.css")
async def serve_css():
    return FileResponse(frontend_path / "style.css")

@app.get("/script.js")
async def serve_js():
    return FileResponse(frontend_path / "script.js")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Zoom Clone Pro is running!",
        "version": "1.0.0",
        "server": "PC Self-Hosted"
    }

@app.get("/api/stats")
async def get_stats():
    rooms = db.get_all_rooms()
    active_rooms = [r for r in rooms if r.get("is_active")]
    
    return {
        "total_rooms": len(rooms),
        "active_rooms": len(active_rooms),
        "total_participants": sum(len(db.get_participants(r["id"])) for r in active_rooms)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
