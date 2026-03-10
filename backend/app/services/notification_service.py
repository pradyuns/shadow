import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_setting import NotificationSetting


async def get_user_settings(db: AsyncSession, user_id: uuid.UUID) -> list[NotificationSetting]:
    result = await db.execute(
        select(NotificationSetting).where(NotificationSetting.user_id == user_id)
    )
    return list(result.scalars().all())


async def upsert_setting(
    db: AsyncSession, user_id: uuid.UUID, channel: str, data: dict
) -> NotificationSetting:
    result = await db.execute(
        select(NotificationSetting).where(
            NotificationSetting.user_id == user_id,
            NotificationSetting.channel == channel,
        )
    )
    setting = result.scalar_one_or_none()

    if setting:
        for key, value in data.items():
            if hasattr(setting, key):
                setattr(setting, key, value)
    else:
        setting = NotificationSetting(user_id=user_id, channel=channel, **data)
        db.add(setting)

    await db.commit()
    await db.refresh(setting)
    return setting
