import aiosmtplib
from email.message import EmailMessage

from .config import settings


async def send_magic_link(to_email: str, link: str) -> None:
    subject = "Вход в WorkLog"
    body = (
        "Здравствуйте!\n\n"
        "Чтобы войти в WorkLog, откройте эту ссылку "
        f"(действует {settings.magic_link_ttl_minutes} мин.):\n\n"
        f"{link}\n\n"
        "Если вы не запрашивали вход — просто проигнорируйте это письмо.\n"
    )

    if settings.dev_echo_magic_link or not settings.smtp_host:
        print(f"[magic-link] {to_email} -> {link}", flush=True)

    if not settings.smtp_host:
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_starttls,
    )
