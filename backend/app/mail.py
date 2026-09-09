import asyncio

import aiosmtplib
from email.message import EmailMessage

from .config import settings

SEND_TIMEOUT = 20  # seconds; keep the request/background task from hanging


async def send_magic_link(to_email: str, link: str) -> None:
    """Best-effort send. Never raises to the caller — logs and moves on."""
    if settings.dev_echo_magic_link or not settings.smtp_host:
        print(f"[magic-link] {to_email} -> {link}", flush=True)

    if not settings.smtp_host:
        return

    subject = "Вход в Chasy"
    body = (
        "Здравствуйте!\n\n"
        "Чтобы войти в Chasy, откройте эту ссылку "
        f"(действует {settings.magic_link_ttl_minutes} мин.):\n\n"
        f"{link}\n\n"
        "Если вы не запрашивали вход — просто проигнорируйте это письмо.\n"
    )
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await asyncio.wait_for(
            aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user or None,
                password=settings.smtp_password or None,
                start_tls=settings.smtp_starttls,
                timeout=SEND_TIMEOUT,
            ),
            timeout=SEND_TIMEOUT + 5,
        )
    except Exception as exc:  # noqa: BLE001 - don't break the login flow
        print(f"[mail] failed to send to {to_email}: {exc!r}", flush=True)
