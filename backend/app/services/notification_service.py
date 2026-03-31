import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_setting import NotificationSetting
from app.schemas.notification import NotificationSettingRead


async def get_user_settings(db: AsyncSession, user_id: uuid.UUID) -> list[NotificationSetting]:
    result = await db.execute(select(NotificationSetting).where(NotificationSetting.user_id == user_id))
    return list(result.scalars().all())


def serialize_setting(setting: NotificationSetting) -> NotificationSettingRead:
    return NotificationSettingRead(
        id=setting.id,
        user_id=setting.user_id,
        channel=setting.channel,
        is_enabled=setting.is_enabled,
        min_severity=setting.min_severity,
        slack_webhook_url=None,
        slack_configured=bool(setting.slack_webhook_url),
        email_address=setting.email_address,
        digest_mode=setting.digest_mode,
        digest_hour_utc=setting.digest_hour_utc,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


async def upsert_setting(
    db: AsyncSession, user_id: uuid.UUID, channel: str, data: dict[str, Any]
) -> NotificationSetting:
    result = await db.execute(
        select(NotificationSetting).where(
            NotificationSetting.user_id == user_id,
            NotificationSetting.channel == channel,
        )
    )
    setting = result.scalar_one_or_none()

    if channel == "slack" and not data.get("slack_webhook_url"):
        if setting is None and data.get("is_enabled", True):
            raise ValueError("Slack webhook URL is required to enable Slack notifications")
        data.pop("slack_webhook_url", None)

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
