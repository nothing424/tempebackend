# ===== TEMPEPLAY BACKEND - routes/rooms.py =====
# Room management API (backup dari Firebase)
# Firebase Firestore jadi primary, ini sebagai fallback/REST API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import random
import string
import time

router = APIRouter()

# In-memory rooms (gunakan Redis atau DB untuk production)
rooms: Dict[str, dict] = {}


def gen_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ---- Models ----
class CreateRoomRequest(BaseModel):
    host_uid: str
    host_name: str
    anime_id: Optional[str] = None
    episode: Optional[str] = "1"


class JoinRoomRequest(BaseModel):
    user_uid: str
    user_name: str
    user_photo: Optional[str] = ""


class SyncRequest(BaseModel):
    uid: str
    video_time: float
    playing: bool


class ChatMessage(BaseModel):
    uid: str
    name: str
    photo: Optional[str] = ""
    text: str


# ---- Endpoints ----
@router.post("/rooms/create")
async def create_room(req: CreateRoomRequest):
    code = gen_code()
    while code in rooms:
        code = gen_code()

    rooms[code] = {
        "code": code,
        "host": req.host_uid,
        "hostName": req.host_name,
        "animeId": req.anime_id,
        "episode": req.episode,
        "videoTime": 0,
        "playing": False,
        "members": {
            req.host_uid: {
                "name": req.host_name,
                "photo": "",
                "joinedAt": time.time()
            }
        },
        "chat": [],
        "createdAt": time.time()
    }
    return {"code": code, "room": rooms[code]}


@router.get("/rooms/{code}")
async def get_room(code: str):
    code = code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Room tidak ditemukan")
    return rooms[code]


@router.post("/rooms/{code}/join")
async def join_room(code: str, req: JoinRoomRequest):
    code = code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Room tidak ditemukan")
    rooms[code]["members"][req.user_uid] = {
        "name": req.user_name,
        "photo": req.user_photo,
        "joinedAt": time.time()
    }
    return {"success": True, "room": rooms[code]}


@router.delete("/rooms/{code}/leave/{uid}")
async def leave_room(code: str, uid: str):
    code = code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Room tidak ditemukan")
    rooms[code]["members"].pop(uid, None)
    # Auto delete if empty
    if not rooms[code]["members"]:
        del rooms[code]
        return {"success": True, "deleted": True}
    return {"success": True, "room": rooms[code]}


@router.put("/rooms/{code}/sync")
async def sync_room(code: str, req: SyncRequest):
    code = code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Room tidak ditemukan")
    # Only host can sync
    if rooms[code]["host"] != req.uid:
        raise HTTPException(status_code=403, detail="Hanya host yang bisa sync")
    rooms[code]["videoTime"] = req.video_time
    rooms[code]["playing"] = req.playing
    return {"success": True}


@router.post("/rooms/{code}/chat")
async def send_chat(code: str, msg: ChatMessage):
    code = code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Room tidak ditemukan")
    if msg.uid not in rooms[code]["members"]:
        raise HTTPException(status_code=403, detail="Kamu bukan anggota room ini")
    message = {
        "uid": msg.uid,
        "name": msg.name,
        "photo": msg.photo,
        "text": msg.text[:200],  # max 200 chars
        "time": time.time()
    }
    rooms[code]["chat"].append(message)
    # Keep only last 100 messages
    if len(rooms[code]["chat"]) > 100:
        rooms[code]["chat"] = rooms[code]["chat"][-100:]
    return {"success": True, "message": message}


@router.get("/rooms/{code}/chat")
async def get_chat(code: str, since: float = 0):
    code = code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Room tidak ditemukan")
    msgs = [m for m in rooms[code]["chat"] if m["time"] > since]
    return {"messages": msgs}


@router.get("/rooms")
async def list_rooms():
    """List active rooms (admin only in production)"""
    return {
        "total": len(rooms),
        "rooms": [
            {"code": r["code"], "members": len(r["members"]), "anime": r.get("animeId")}
            for r in rooms.values()
        ]
    }
