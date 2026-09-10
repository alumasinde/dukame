import smtplib
from email.message import EmailMessage
from functools import partial

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings


async def send_email(to: str, subject: str, text: str) -> None:
    if not settings.smtp_host:
        if settings.environment in {"development", "test"}:
            return
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)

    def deliver() -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            server.send_message(message)

    await run_in_threadpool(partial(deliver))
