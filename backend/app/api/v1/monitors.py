import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_verified_user
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.monitor import MonitorCreate, MonitorRead, MonitorUpdate, PageType
from app.services.monitor_service import (
    create_monitor,
    get_monitor,
    list_monitors,
    restore_monitor,
    soft_delete_monitor,
    update_monitor,
)
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.post("", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
async def create(
    body: MonitorCreate,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        monitor = await create_monitor(db, user, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return monitor


@router.get("", response_model=dict)
async def list_all(
    pagination: PaginationParams = Depends(),
    is_active: bool | None = None,
    page_type: PageType | None = None,
    search: str | None = Query(default=None, max_length=255),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    monitors, total = await list_monitors(
        db,
        user.id,
        pagination.page,
        pagination.per_page,
        is_active=is_active,
        page_type=page_type.value if page_type else None,
        search=search,
    )
    return pagination.paginate(
        [MonitorRead.model_validate(m) for m in monitors],
        total,
    )


@router.get("/{monitor_id}", response_model=MonitorRead)
async def get_one(
    monitor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return monitor


@router.patch("/{monitor_id}", response_model=MonitorRead)
async def update(
    monitor_id: uuid.UUID,
    body: MonitorUpdate,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    try:
        monitor = await update_monitor(db, monitor, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    monitor_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    await soft_delete_monitor(db, monitor)


@router.post("/{monitor_id}/restore", response_model=MonitorRead)
async def restore(
    monitor_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    monitor = await restore_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted monitor not found")
    return monitor


@router.post("/{monitor_id}/scrape", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape(
    monitor_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    from workers.tasks.scraping import scrape_single_url

    task = scrape_single_url.delay(str(monitor.id))
    return {"task_id": task.id, "status": "accepted"}
