from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_verified_user
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.notification import Channel, NotificationSettingRead, NotificationSettingUpdate
from app.services.notification_service import get_user_settings, upsert_setting

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/settings", response_model=list[NotificationSettingRead])
async def list_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_user_settings(db, user.id)
    return settings


@router.put("/settings/{channel}", response_model=NotificationSettingRead)
async def update_setting(
    channel: Channel,
    body: NotificationSettingUpdate,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    setting = await upsert_setting(db, user.id, channel.value, body.model_dump())
    return setting


@router.post("/test/{channel}", status_code=status.HTTP_202_ACCEPTED)
async def test_notification(
    channel: Channel,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_user_settings(db, user.id)
    channel_setting = next((s for s in settings if s.channel == channel.value), None)
    if not channel_setting or not channel_setting.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{channel.value} notifications not configured or disabled",
        )
    # Dispatch test notification task
    from workers.tasks.notifications import send_test_notification

    task = send_test_notification.delay(str(user.id), channel.value)
    return {"task_id": task.id, "status": "accepted"}
