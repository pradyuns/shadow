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
async def trigger_scrape_cycle(admin: User = Depends(get_current_admin)):
    from workers.tasks.scraping import initiate_scrape_cycle

    task = initiate_scrape_cycle.delay()
    return {"task_id": task.id, "status": "accepted"}


@router.get("/stats")
async def system_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    monitor_count = (await db.execute(select(func.count(Monitor.id)).where(Monitor.deleted_at.is_(None)))).scalar()
    active_monitor_count = (
        await db.execute(select(func.count(Monitor.id)).where(Monitor.is_active == True, Monitor.deleted_at.is_(None)))
    ).scalar()
    alert_count = (await db.execute(select(func.count(Alert.id)))).scalar()
    unacknowledged_count = (
        await db.execute(select(func.count(Alert.id)).where(Alert.is_acknowledged == False))
    ).scalar()

    mongo_db = get_mongo_db()
    snapshot_count = await mongo_db.snapshots.count_documents({})
    diff_count = await mongo_db.diffs.count_documents({})
    analysis_count = await mongo_db.analyses.count_documents({})

    return {
        "users": user_count,
        "monitors": {"total": monitor_count, "active": active_monitor_count},
        "alerts": {"total": alert_count, "unacknowledged": unacknowledged_count},
        "snapshots": snapshot_count,
        "diffs": diff_count,
        "analyses": analysis_count,
    }
