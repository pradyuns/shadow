import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.alert_cluster import AlertCluster


async def list_clusters(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int,
    per_page: int,
    is_resolved: bool | None = None,
    competitor_name: str | None = None,
) -> tuple[list[AlertCluster], int]:
    query = select(AlertCluster).where(AlertCluster.user_id == user_id)
    count_query = select(func.count(AlertCluster.id)).where(AlertCluster.user_id == user_id)

    if is_resolved is not None:
        query = query.where(AlertCluster.is_resolved == is_resolved)
        count_query = count_query.where(AlertCluster.is_resolved == is_resolved)
    if competitor_name:
        query = query.where(AlertCluster.competitor_name == competitor_name)
        count_query = count_query.where(AlertCluster.competitor_name == competitor_name)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.options(selectinload(AlertCluster.alerts))
        .order_by(AlertCluster.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(result.scalars().all()), total


async def get_cluster(db: AsyncSession, cluster_id: uuid.UUID, user_id: uuid.UUID) -> AlertCluster | None:
    result = await db.execute(
        select(AlertCluster)
        .where(AlertCluster.id == cluster_id, AlertCluster.user_id == user_id)
        .options(selectinload(AlertCluster.alerts))
    )
    return result.scalar_one_or_none()


async def resolve_cluster(db: AsyncSession, cluster: AlertCluster) -> AlertCluster:
    cluster.is_resolved = True
    cluster.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(cluster)
    return cluster


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
