# ===== TEMPEPLAY BACKEND - main.py =====
# FastAPI backend untuk proxy streaming anime
# Deploy ke Render: https://render.com (free tier)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routes.anime import router as anime_router
from routes.rooms import router as rooms_router

app = FastAPI(
    title="TempePlay API",
    description="Backend streaming anime untuk TempePlay 🍿",
    version="1.0.0"
)

# CORS - izinkan semua origin (untuk dev lokal & deploy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(anime_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "app": "TempePlay API",
        "status": "🟢 Online",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
