from datetime import datetime, timedelta

from sqlalchemy import select, func as sqlfunc

from app.database import AsyncSessionLocal
from app.models.log import LogEntry


async def log_event(
    level="info",
    source="system",
    action="",
    user_id=None,
    user_name="",
    details="",
    ip_address="",
    entity_type="",
    entity_id=None,
):
    async with AsyncSessionLocal() as db:
        db.add(LogEntry(
            level=level,
            source=source,
            action=action,
            user_id=user_id,
            user_name=user_name,
            details=details,
            ip_address=ip_address,
            entity_type=entity_type,
            entity_id=entity_id,
        ))
        await db.commit()


async def get_logs(
    page=1,
    per_page=50,
    level=None,
    source=None,
    action=None,
    user_id=None,
    entity_type=None,
    date_from=None,
    date_to=None,
):
    query = select(LogEntry).order_by(LogEntry.created_at.desc())
    count_query = select(sqlfunc.count(LogEntry.id))

    if level:
        query = query.where(LogEntry.level == level)
        count_query = count_query.where(LogEntry.level == level)
    if source:
        query = query.where(LogEntry.source == source)
        count_query = count_query.where(LogEntry.source == source)
    if action:
        query = query.where(LogEntry.action == action)
        count_query = count_query.where(LogEntry.action == action)
    if user_id:
        query = query.where(LogEntry.user_id == user_id)
        count_query = count_query.where(LogEntry.user_id == user_id)
    if entity_type:
        query = query.where(LogEntry.entity_type == entity_type)
        count_query = count_query.where(LogEntry.entity_type == entity_type)
    if date_from:
        query = query.where(LogEntry.created_at >= date_from)
        count_query = count_query.where(LogEntry.created_at >= date_from)
    if date_to:
        end = datetime.fromisoformat(date_to) + timedelta(days=1)
        query = query.where(LogEntry.created_at < end.isoformat())
        count_query = count_query.where(LogEntry.created_at < end.isoformat())

    async with AsyncSessionLocal() as db:
        total = (await db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        rows = (
            (await db.execute(query.offset(offset).limit(per_page)))
            .scalars()
            .all()
        )
        items = [
            {
                "id": r.id,
                "level": r.level,
                "source": r.source,
                "action": r.action,
                "user_id": r.user_id,
                "user_name": r.user_name,
                "details": r.details,
                "ip_address": r.ip_address,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "created_at": str(r.created_at) if r.created_at else "",
            }
            for r in rows
        ]
        return {"items": items, "total": total, "page": page, "per_page": per_page}


async def get_log_summary():
    async with AsyncSessionLocal() as db:
        level_counts_raw = await db.execute(
            select(LogEntry.level, sqlfunc.count(LogEntry.id).label("cnt"))
            .group_by(LogEntry.level)
        )
        level_counts = {row[0]: row[1] for row in level_counts_raw}

        action_counts_raw = await db.execute(
            select(LogEntry.action, sqlfunc.count(LogEntry.id).label("cnt"))
            .group_by(LogEntry.action)
            .order_by(sqlfunc.count(LogEntry.id).desc())
            .limit(10)
        )
        top_actions = {row[0]: row[1] for row in action_counts_raw}

        source_counts_raw = await db.execute(
            select(LogEntry.source, sqlfunc.count(LogEntry.id).label("cnt"))
            .group_by(LogEntry.source)
            .order_by(sqlfunc.count(LogEntry.id).desc())
        )
        source_counts = {row[0]: row[1] for row in source_counts_raw}

    return {
        "level_counts": level_counts,
        "top_actions": top_actions,
        "source_counts": source_counts,
    }
