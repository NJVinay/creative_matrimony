"""
Chat API.
Trace: @context_documents/MVP_BACKLOG.md Epic G
"""

from typing import Annotated, List, Literal, Dict

from fastapi import APIRouter, Depends, HTTPException, Body, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, decode_token
from app.models.user import User
from app.models.communication import InterestStatus, ChatParticipant
from app.services.chat_service import ChatService
from app.schemas.chat import InterestOut, ChatRoomOut, ChatMessageOut, MessageCreate
from sqlalchemy import select

router = APIRouter(tags=["Communication"])

# ── WebSocket Manager ──────────────────────────────────────
# TODO(Scaling): The ConnectionManager uses an in-memory dictionary to track websockets.
# This works for a single-instance MVP. If deployed across multiple backend pods,
# this must be refactored to use a Redis Pub/Sub mechanism (e.g. `broadcaster`) 
# so that messages sent to one pod are broadcasted to users connected to other pods.
class ConnectionManager:
    def __init__(self):
        # Maps room_id to a list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: dict, room_id: int):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# ── Interests ──────────────────────────────────────────────

@router.post("/interests/{profile_id}")
async def send_interest(
    profile_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    if user.profile.id == profile_id:
        raise HTTPException(status_code=400, detail="Cannot connect with self")

    try:
        interest = await ChatService.send_interest(db, user.profile.id, profile_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "sent", "id": interest.id}

@router.get("/interests/received", response_model=List[InterestOut])
async def get_received_interests(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    return await ChatService.get_interests(db, user.profile.id, type="received")

@router.get("/interests/sent", response_model=List[InterestOut])
async def get_sent_interests(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    return await ChatService.get_interests(db, user.profile.id, type="sent")

@router.put("/interests/{id}/{action}")
async def respond_to_interest(
    id: int,
    action: Literal["accept", "reject"],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required")
        
    status = InterestStatus.accepted if action == "accept" else InterestStatus.rejected
    
    # We pass user's profile ID as the 'receiver' verifier? 
    # ChatService check uses 'user_id' for check. Wait, interest stores profile_id. 
    # Service implementation: `where(Interest.receiver_id == user_id)`
    # So I must pass profile_id to service if service expects profile_id.
    
    # Let's check service: 
    # `where(Interest.receiver_id == user_id)` -> variable name user_id implies ID, but Context is Profile ID.
    # Yes, Interest.receiver_id is a profile ID. So I should pass profile ID.
    
    updated = await ChatService.update_interest_status(db, id, status, user.profile.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Interest not found")
        
    return {"status": action, "chat_room_created": status == InterestStatus.accepted}

# ── Chat ───────────────────────────────────────────────────

@router.get("/chat/rooms", response_model=List[ChatRoomOut])
async def list_chats(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    return await ChatService.get_user_chats(db, user.id)

@router.get("/chat/rooms/{room_id}/messages", response_model=List[ChatMessageOut])
async def get_chat_history(
    room_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    return await ChatService.get_chat_history(db, room_id, user.id)

@router.post("/chat/rooms/{room_id}/messages", response_model=ChatMessageOut)
async def send_message(
    room_id: int,
    message: MessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Send a message to a chat room. The sender must be a participant.
    Returns 403 if not authorized, 400 on empty/oversized content.
    """
    content = (message.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")
    if len(content) > 4000:
        raise HTTPException(status_code=400, detail="Message too long (max 4000 chars).")

    try:
        msg = await ChatService.send_message(db, room_id, user.id, content)
        # Broadcast to active websocket connections
        await manager.broadcast({
            "id": msg.id,
            "room_id": msg.room_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }, room_id)
        return msg
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.websocket("/chat/rooms/{room_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Authenticate via cookie for WS
    token = websocket.cookies.get("access_token")
    if not token:
        # Fallback to query param
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008)
            return
        
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=1008)
        return

    # Verify participation
    participant_check = await db.execute(
        select(ChatParticipant).where(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == user_id,
        )
    )
    if not participant_check.scalar_one_or_none():
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            content = data.strip()
            if content:
                try:
                    msg = await ChatService.send_message(db, room_id, user_id, content)
                    await manager.broadcast({
                        "id": msg.id,
                        "room_id": msg.room_id,
                        "sender_id": msg.sender_id,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None
                    }, room_id)
                except ValueError as e:
                    await websocket.send_json({"error": str(e)})
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)

