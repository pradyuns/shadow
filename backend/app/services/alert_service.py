import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def list_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int,
    per_page: int,
    severity: str | None = None,
    monitor_id: uuid.UUID | None = None,
    is_acknowledged: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> tuple[list[Alert], int]:
    query = select(Alert).where(Alert.user_id == user_id)
    count_query = select(func.count(Alert.id)).where(Alert.user_id == user_id)

    if severity:
        query = query.where(Alert.severity == severity)
        count_query = count_query.where(Alert.severity == severity)
    if monitor_id:
        query = query.where(Alert.monitor_id == monitor_id)
        count_query = count_query.where(Alert.monitor_id == monitor_id)
    if is_acknowledged is not None:
        query = query.where(Alert.is_acknowledged == is_acknowledged)
        count_query = count_query.where(Alert.is_acknowledged == is_acknowledged)
    if since:
        query = query.where(Alert.created_at >= since)
        count_query = count_query.where(Alert.created_at >= since)
    if until:
        query = query.where(Alert.created_at <= until)
        count_query = count_query.where(Alert.created_at <= until)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.order_by(Alert.created_at.desc()).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def get_alert(db: AsyncSession, alert_id: uuid.UUID, user_id: uuid.UUID) -> Alert | None:
    result = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id))
    return result.scalar_one_or_none()


async def acknowledge_alert(db: AsyncSession, alert: Alert) -> Alert:
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert
