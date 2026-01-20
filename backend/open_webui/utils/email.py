import logging
import smtplib
from email.message import EmailMessage

from open_webui.env import (
    OPEN_WEBUI_DIR,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SSL,
    SMTP_TLS,
    SMTP_USER,
)

log = logging.getLogger(__name__)


def _load_template(template_name: str) -> str:
    template_path = OPEN_WEBUI_DIR / "templates" / "email" / template_name
    return template_path.read_text(encoding="utf-8")


def build_signup_verification_email(
    webui_name: str, otp: str, ttl_minutes: int, recipient: str
) -> tuple[str, str, str]:
    subject = f"Verify your email for {webui_name}"
    html = _load_template("verify_signup.html").format(
        webui_name=webui_name,
        otp=otp,
        ttl_minutes=ttl_minutes,
        recipient=recipient,
    )
    text = (
        f"{webui_name} email verification\n\n"
        f"Use this code to finish signing up: {otp}\n"
        f"This code expires in {ttl_minutes} minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )
    return subject, html, text


def send_email(to_email: str, subject: str, html: str, text: str) -> None:
    if not SMTP_HOST:
        raise ValueError("SMTP_HOST is not configured")

    msg = EmailMessage()
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    if SMTP_SSL:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

    try:
        if SMTP_TLS and not SMTP_SSL:
            server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            log.exception("Failed to close SMTP connection")
