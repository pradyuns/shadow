import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor import Monitor
from app.models.user import User
from app.utils.validators import validate_regex_pattern, validate_url_safe


# validate limits, url safety, duplicates, then persist a new monitor
async def create_monitor(db: AsyncSession, user: User, data: dict) -> Monitor:
    # Check monitor limit
    count_result = await db.execute(
        select(func.count(Monitor.id)).where(Monitor.user_id == user.id, Monitor.deleted_at.is_(None))
    )
    current_count = count_result.scalar()
    if current_count >= user.max_monitors:
        raise ValueError(f"Monitor limit reached ({user.max_monitors})")

    # Validate URL safety
    url_str = str(data["url"])
    is_safe, error = validate_url_safe(url_str)
    if not is_safe:
        raise ValueError(error)

    # Check duplicate URL for this user
    existing = await db.execute(
        select(Monitor).where(
            Monitor.user_id == user.id,
            Monitor.url == url_str,
            Monitor.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("You are already monitoring this URL")

    # Validate noise patterns
    for pattern in data.get("noise_patterns", []):
        valid, err = validate_regex_pattern(pattern)
        if not valid:
            raise ValueError(f"Invalid noise pattern: {err}")

    monitor = Monitor(
        user_id=user.id,
        url=url_str,
        name=data["name"],
        competitor_name=data.get("competitor_name"),
        page_type=data["page_type"],
        render_js=data.get("render_js", False),
        use_firecrawl=data.get("use_firecrawl", False),
        check_interval_hours=data.get("check_interval_hours", 6),
        css_selector=data.get("css_selector"),
        noise_patterns=data.get("noise_patterns", []),
        next_check_at=datetime.now(timezone.utc),
        last_scrape_status="pending",
    )
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    return monitor


async def get_monitor(db: AsyncSession, monitor_id: uuid.UUID, user_id: uuid.UUID) -> Monitor | None:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == user_id,
            Monitor.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_monitors(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int,
    per_page: int,
    is_active: bool | None = None,
    page_type: str | None = None,
    search: str | None = None,
) -> tuple[list[Monitor], int]:
    query = select(Monitor).where(Monitor.user_id == user_id, Monitor.deleted_at.is_(None))
    count_query = select(func.count(Monitor.id)).where(Monitor.user_id == user_id, Monitor.deleted_at.is_(None))

    if is_active is not None:
        query = query.where(Monitor.is_active == is_active)
        count_query = count_query.where(Monitor.is_active == is_active)

    if page_type:
        query = query.where(Monitor.page_type == page_type)
        count_query = count_query.where(Monitor.page_type == page_type)

    if search:
        search_filter = Monitor.name.ilike(f"%{search}%") | Monitor.url.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.order_by(Monitor.created_at.desc()).offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total


async def update_monitor(db: AsyncSession, monitor: Monitor, data: dict) -> Monitor:
    for key, value in data.items():
        if value is not None and hasattr(monitor, key):
            if key == "noise_patterns":
                for pattern in value:
                    valid, err = validate_regex_pattern(pattern)
                    if not valid:
                        raise ValueError(f"Invalid noise pattern: {err}")
            setattr(monitor, key, value)
    await db.commit()
    await db.refresh(monitor)
    return monitor


# deactivate and mark for deletion — hard delete runs after retention period
async def soft_delete_monitor(db: AsyncSession, monitor: Monitor) -> None:
    monitor.is_active = False
    monitor.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def restore_monitor(db: AsyncSession, monitor_id: uuid.UUID, user_id: uuid.UUID) -> Monitor | None:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.user_id == user_id,
            Monitor.deleted_at.isnot(None),
        )
    )
    monitor = result.scalar_one_or_none()
    if not monitor:
        return None

    monitor.is_active = True
    monitor.deleted_at = None
    monitor.next_check_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(monitor)
    return monitor
