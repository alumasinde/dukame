import os
import smtplib
from email.message import EmailMessage
from functools import partial

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings


async def send_email(to: str, subject: str, text: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        if settings.environment in {"development", "test"}:
            return
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["From"] = os.getenv("EMAIL_FROM", "no-reply@dukame.local")
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_timeout = int(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    smtp_tls = os.getenv("SMTP_TLS", "true").lower() == "true"
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    def deliver() -> None:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout) as server:
            if smtp_tls:
                server.starttls()
            if smtp_username:
                server.login(smtp_username, smtp_password)
            server.send_message(message)

    await run_in_threadpool(partial(deliver))
