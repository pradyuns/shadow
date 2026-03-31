import asyncio
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.mongodb import get_mongo_db
from app.db.postgres import get_db
from app.models.alert import Alert
from app.models.monitor import Monitor
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/scrape-cycle", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape_cycle(admin: User = Depends(get_current_admin)) -> dict[str, Any]:
    from workers.tasks.scraping import initiate_scrape_cycle

    task = initiate_scrape_cycle.delay()
    return {"task_id": task.id, "status": "accepted"}


@router.get("/stats")
async def system_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # postgres counts (sequential — single session isn't safe for concurrent use)
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    monitor_count = (await db.execute(select(func.count(Monitor.id)).where(Monitor.deleted_at.is_(None)))).scalar()
    active_monitor_count = (
        await db.execute(
            select(func.count(Monitor.id)).where(Monitor.is_active.is_(True), Monitor.deleted_at.is_(None))
        )
    ).scalar()
    alert_count = (await db.execute(select(func.count(Alert.id)))).scalar()
    unacknowledged_count = (
        await db.execute(select(func.count(Alert.id)).where(Alert.is_acknowledged.is_(False)))
    ).scalar()

    # mongo counts run in parallel since they use independent connections
    mongo_db = get_mongo_db()
    snapshot_count, diff_count, analysis_count = await asyncio.gather(
        mongo_db.snapshots.count_documents({}),
        mongo_db.diffs.count_documents({}),
        mongo_db.analyses.count_documents({}),
    )

    return {
        "users": user_count,
        "monitors": {"total": monitor_count, "active": active_monitor_count},
        "alerts": {"total": alert_count, "unacknowledged": unacknowledged_count},
        "snapshots": snapshot_count,
        "diffs": diff_count,
        "analyses": analysis_count,
    }
