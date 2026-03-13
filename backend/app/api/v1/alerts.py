import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_verified_user
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.alert import AlertDetail, AlertRead, Severity
from app.services.alert_service import acknowledge_alert, get_alert, list_alerts
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=dict)
async def list_all(
    pagination: PaginationParams = Depends(),
    severity: Severity | None = None,
    monitor_id: uuid.UUID | None = None,
    is_acknowledged: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alerts, total = await list_alerts(
        db,
        user.id,
        pagination.page,
        pagination.per_page,
        severity=severity.value if severity else None,
        monitor_id=monitor_id,
        is_acknowledged=is_acknowledged,
        since=since,
        until=until,
    )
    return pagination.paginate(
        [AlertRead.model_validate(a) for a in alerts],
        total,
    )


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_one(
    alert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alert = await get_alert(db, alert_id, user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/acknowledge", response_model=AlertDetail)
async def acknowledge(
    alert_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    alert = await get_alert(db, alert_id, user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert = await acknowledge_alert(db, alert)
    return alert
