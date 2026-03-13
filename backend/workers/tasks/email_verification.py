"""Email verification task — send verification emails via SendGrid."""

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="workers.tasks.email_verification.send_verification_email",
    queue="default",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_verification_email(self, user_id: str):
    from sqlalchemy import select

    from app.config import settings
    from app.db.postgres_sync import get_sync_db
    from app.models.user import User
    from app.utils.security import create_email_verification_token

    db = get_sync_db()
    try:
        result = db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("verification_email_user_not_found", user_id=user_id)
            return {"status": "skipped", "reason": "user_not_found"}

        if user.is_email_verified:
            logger.info("verification_email_already_verified", user_id=user_id)
            return {"status": "skipped", "reason": "already_verified"}

        token = create_email_verification_token({"sub": str(user.id)})
        verify_url = f"{settings.frontend_url}/api/v1/auth/verify-email?token={token}"

        if not settings.sendgrid_api_key:
            logger.warning("verification_email_no_sendgrid_key", user_id=user_id, verify_url=verify_url)
            return {"status": "skipped", "reason": "sendgrid_not_configured", "verify_url": verify_url}

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Content, Email, Mail, To

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
  <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <div style="background-color: #1e293b; color: white; padding: 20px 24px;">
      <h1 style="margin: 0; font-size: 18px;">Verify your email</h1>
      <p style="margin: 8px 0 0; opacity: 0.9; font-size: 14px;">Shadow &mdash; Competitive Intelligence Monitor</p>
    </div>
    <div style="padding: 24px;">
      <p style="font-size: 15px; line-height: 1.6; color: #374151; margin-top: 0;">
        Hi {user.full_name},
      </p>
      <p style="font-size: 15px; line-height: 1.6; color: #374151;">
        Click the button below to verify your email address and unlock full access to Shadow.
      </p>
      <div style="margin: 32px 0; text-align: center;">
        <a href="{verify_url}" style="display: inline-block; background-color: #2563EB; color: white; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600;">
          Verify Email
        </a>
      </div>
      <p style="font-size: 13px; line-height: 1.6; color: #6B7280;">
        This link expires in {settings.email_verification_token_expire_hours} hours. If you didn't create an account, you can safely ignore this email.
      </p>
    </div>
    <div style="padding: 16px 24px; background-color: #F9FAFB; font-size: 12px; color: #9CA3AF; border-top: 1px solid #E5E7EB;">
      Sent by Shadow Competitive Intelligence Monitor
    </div>
  </div>
</body>
</html>"""

        plain_text = f"""Verify your email — Shadow

Hi {user.full_name},

Click the link below to verify your email address:
{verify_url}

This link expires in {settings.email_verification_token_expire_hours} hours.
If you didn't create an account, you can safely ignore this email.

— Shadow Competitive Intelligence Monitor"""

        message = Mail(
            from_email=Email(settings.sendgrid_from_email),
            to_emails=To(user.email),
            subject="Verify your email — Shadow",
        )
        message.content = [
            Content("text/plain", plain_text),
            Content("text/html", html_body),
        ]

        try:
            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in (200, 201, 202):
                logger.info("verification_email_sent", user_id=user_id, email=user.email)
                return {"status": "sent", "email": user.email}
            else:
                logger.warning("verification_email_failed", status=response.status_code)
                raise self.retry(exc=Exception(f"SendGrid returned {response.status_code}"))

        except self.MaxRetriesExceededError:
            raise
        except Exception as e:
            logger.error("verification_email_error", error=str(e), exc_info=True)
            raise self.retry(exc=e)

    finally:
        db.close()
