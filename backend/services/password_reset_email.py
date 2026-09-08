import logging
import smtplib
from email.message import EmailMessage
from html import escape

from ..config import settings

logger = logging.getLogger(__name__)
development_outbox = []


def email_delivery_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL) or (
        settings.PASSWORD_RESET_DEV_MODE and not settings.is_production
    )


def send_password_reset_email(recipient: str, reset_url: str) -> bool:
    """Send through configured SMTP. Never log the URL because it contains the raw token."""
    if not email_delivery_configured():
        return False
    if settings.PASSWORD_RESET_DEV_MODE and not settings.is_production and not settings.SMTP_HOST:
        development_outbox.append({"recipient": recipient, "reset_url": reset_url})
        return True

    message = EmailMessage()
    message["Subject"] = "Reset your HomeWiseEdu password"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(
        "HomeWiseEdu password reset\n\n"
        "We received a request to reset the password for your HomeWiseEdu account.\n\n"
        f"Reset your password: {reset_url}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes and can only be used once.\n"
        "If you did not request this, you can ignore this email.\n\n"
        "Need help? Contact support@homewiseedu.com."
    )
    safe_url = escape(reset_url, quote=True)
    message.add_alternative(
        f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f8f4ee;font-family:Arial,sans-serif;color:#35104f;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f8f4ee;padding:32px 12px;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #eadff2;border-radius:16px;">
          <tr><td style="padding:32px;">
            <div style="font-size:24px;font-weight:700;color:#4b1768;margin-bottom:20px;">HomeWiseEdu</div>
            <h1 style="font-size:22px;line-height:1.3;margin:0 0 16px;color:#35104f;">Reset your password</h1>
            <p style="font-size:16px;line-height:1.6;margin:0 0 24px;">We received a request to reset the password for your HomeWiseEdu account.</p>
            <p style="margin:0 0 24px;"><a href="{safe_url}" style="display:inline-block;background:#ff6f61;color:#ffffff;text-decoration:none;font-weight:700;padding:13px 22px;border-radius:8px;">Reset password</a></p>
            <p style="font-size:14px;line-height:1.6;margin:0 0 12px;">This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes and can only be used once.</p>
            <p style="font-size:14px;line-height:1.6;margin:0 0 12px;">If you did not request this, you can ignore this email.</p>
            <p style="font-size:14px;line-height:1.6;margin:0;">Need help? Contact <a href="mailto:support@homewiseedu.com" style="color:#4b1768;">support@homewiseedu.com</a>.</p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>""",
        subtype="html",
    )
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception as exc:
        logger.warning("Password reset email delivery failed type=%s", type(exc).__name__)
        return False
