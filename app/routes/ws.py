import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.utils.auth import decode_access_token
from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select
from app.utils.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user = None
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            await websocket.close(code=4001)
            return
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == int(user_id_str)))
            user = result.scalar_one_or_none()
            if user is None or not user.active:
                await websocket.close(code=4001)
                return
            await ws_manager.connect(websocket, user.id)
    except Exception:
        await websocket.close(code=4001)
        return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if user:
            ws_manager.disconnect(websocket, user.id)
