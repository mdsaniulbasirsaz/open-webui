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
    webui_name: str,
    otp: str,
    ttl_minutes: int,
    recipient: str,
    verification_link: str | None = None,
) -> tuple[str, str, str]:
    subject = f"Verify your email for {webui_name}"
    verification_link_section = ""
    if verification_link:
        verification_link_section = f"""
						<tr>
							<td style="padding:0 28px 20px 28px;color:#4b5563;font-size:13px;line-height:1.5;">
								<p style="margin:0 0 12px 0;">Or verify with this link:</p>
								<a
									href="{verification_link}"
									style="display:inline-block;background:#92278f;color:#ffffff;text-decoration:none;padding:10px 18px;border-radius:999px;font-size:13px;font-weight:bold;"
								>
									Verify email
								</a>
								<p style="margin:12px 0 0 0;font-size:12px;color:#6b7280;">
									This link can be used once.
								</p>
								<p style="margin:12px 0 0 0;font-size:12px;color:#9ca3af;word-break:break-all;">
									{verification_link}
								</p>
							</td>
						</tr>
""".strip(
            "\n"
        )
    html = _load_template("verify_signup.html").format(
        webui_name=webui_name,
        otp=otp,
        ttl_minutes=ttl_minutes,
        recipient=recipient,
        verification_link_section=verification_link_section,
    )
    text = (
        f"{webui_name} email verification\n\n"
        f"Use this code to finish signing up: {otp}\n"
        f"This code expires in {ttl_minutes} minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )
    if verification_link:
        text = (
            f"{text}\n\n"
            "Or verify using this link:\n"
            f"{verification_link}\n"
            "This link can be used once."
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
