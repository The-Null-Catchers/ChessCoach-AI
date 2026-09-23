from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.tasks.celery_app import celery


@celery.task(bind=True, autoretry_for=(OSError, smtplib.SMTPException), retry_backoff=True, max_retries=3)
def send_auth_email(self, to_email: str, subject: str, body: str):
    if not settings.smtp_host:
        return {"status": "skipped", "reason": "smtp_not_configured"}

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return {"status": "sent"}
