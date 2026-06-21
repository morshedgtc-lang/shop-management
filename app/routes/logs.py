from fastapi import APIRouter, Depends, Query

from app.utils.auth import get_current_user
from app.utils.permissions import require_role
from app.utils.logger import get_logs, get_log_summary

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def list_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    level: str = Query(None),
    source: str = Query(None),
    action: str = Query(None),
    user_id: int = Query(None),
    entity_type: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    current_user=Depends(require_role("admin")),
):
    return await get_logs(
        page=page, per_page=per_page, level=level, source=source,
        action=action, user_id=user_id, entity_type=entity_type,
        date_from=date_from, date_to=date_to,
    )


@router.get("/summary")
async def log_summary(
    current_user=Depends(require_role("admin")),
):
    return await get_log_summary()
