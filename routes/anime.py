# ===== TEMPEPLAY BACKEND - routes/anime.py =====
# Scraper/proxy untuk episode list dan streaming sources
# Menggunakan requests + BeautifulSoup sebagai fallback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import asyncio
import re
import json
from typing import Optional

router = APIRouter()

# ==========================================
# CONSUMET API - self-hosted or public
# Ganti dengan URL Consumet lo sendiri setelah deploy
# Deploy Consumet gratis: https://render.com
# Repo: https://github.com/consumet/api.consumet.org
# ==========================================
CONSUMET_BASE = "https://your-consumet.onrender.com"  # GANTI INI

# Fallback providers (tambahkan sesuai kebutuhan)
PROVIDERS = ["gogoanime", "animepahe", "zoro"]


@router.get("/episodes/{anime_slug}")
async def get_episodes(anime_slug: str, provider: str = "gogoanime"):
    """
    Ambil daftar episode dari Consumet API
    anime_slug: judul anime yang sudah di-encode (contoh: naruto-shippuden)
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Coba Consumet API dulu
        for prov in [provider] + [p for p in PROVIDERS if p != provider]:
            try:
                url = f"{CONSUMET_BASE}/anime/{prov}/{anime_slug}"
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    episodes = data.get("episodes", [])
                    if episodes:
                        return {
                            "provider": prov,
                            "total": len(episodes),
                            "episodes": [
                                {
                                    "id": ep.get("id", ""),
                                    "number": ep.get("number", i + 1),
                                    "title": ep.get("title", f"Episode {i + 1}"),
                                    "isFiller": ep.get("isFiller", False),
                                }
                                for i, ep in enumerate(episodes)
                            ]
                        }
            except Exception as e:
                continue

        # Jika semua gagal, return error dengan info
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Consumet API tidak tersedia",
                "help": "Deploy Consumet ke Render: https://github.com/consumet/api.consumet.org",
                "consumet_url": CONSUMET_BASE
            }
        )


@router.get("/stream/{episode_id:path}")
async def get_stream(episode_id: str, provider: str = "gogoanime"):
    """
    Ambil streaming sources untuk episode tertentu
    episode_id: ID episode dari Consumet API
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        for prov in [provider] + [p for p in PROVIDERS if p != provider]:
            try:
                url = f"{CONSUMET_BASE}/anime/{prov}/watch/{episode_id}"
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    sources = data.get("sources", [])
                    if sources:
                        # Format sources
                        formatted = []
                        for s in sources:
                            formatted.append({
                                "url": s.get("url", ""),
                                "quality": s.get("quality", "default"),
                                "type": "hls" if ".m3u8" in s.get("url", "") else "mp4",
                                "isM3U8": s.get("isM3U8", False),
                            })

                        return {
                            "provider": prov,
                            "sources": formatted,
                            "subtitles": data.get("subtitles", []),
                            "intro": data.get("intro", None),
                        }
            except Exception:
                continue

        raise HTTPException(
            status_code=503,
            detail={"error": "Tidak dapat mengambil stream. Consumet API tidak tersedia."}
        )


@router.get("/proxy/hls")
async def proxy_hls(url: str):
    """
    Proxy HLS stream untuk menghindari CORS issues
    """
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL tidak valid")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://gogoanime.cl/",
        "Origin": "https://gogoanime.cl",
    }

    async def stream_generator():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", url, headers=headers) as res:
                async for chunk in res.aiter_bytes(chunk_size=8192):
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
        }
    )


@router.get("/search/{query}")
async def search_anime(query: str, provider: str = "gogoanime"):
    """
    Cari anime berdasarkan judul
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            url = f"{CONSUMET_BASE}/anime/{provider}/{query}"
            res = await client.get(url)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))

    raise HTTPException(status_code=404, detail="Tidak ditemukan")
