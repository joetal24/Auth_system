import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured, skipping email to %s", to)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to
    msg.set_content(body)
    msg.add_alternative(body, subtype="html")

    def _send():
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send)


def build_verification_email(token: str) -> tuple[str, str]:
    subject = "Verify your email"
    link = f"http://localhost:8000/api/v1/auth/verify-email?token={token}"
    html = f"""<h1>Email Verification</h1>
<p>Click the link below to verify your email:</p>
<a href="{link}">{link}</a>
<p>This link expires in 24 hours.</p>"""
    return subject, html
