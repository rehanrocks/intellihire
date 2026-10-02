"""Outgoing email.

The code that *composes* an email (subject, body, link) is separated from the
code that *delivers* it (the backend). Swapping delivery is then a config
change:

- console: print the email to the server log (local development)
- memory:  keep emails in a list so tests can assert on them
- smtp:    send for real through an SMTP server
"""
import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as _MimeMessage

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str
    # Useful bits tests and dev tools can read without parsing the body.
    meta: dict = field(default_factory=dict)


class ConsoleEmailBackend:
    def send(self, message: EmailMessage) -> None:
        logger.info("EMAIL to=%s subject=%r\n%s", message.to, message.subject, message.body)


class MemoryEmailBackend:
    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)

    def clear(self) -> None:
        self.outbox.clear()


class SMTPEmailBackend:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: EmailMessage) -> None:
        mime = _MimeMessage()
        mime["From"] = self.settings.email_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(mime)


_backend = None


def get_email_backend():
    """Singleton chosen from settings.email_backend."""
    global _backend
    if _backend is None:
        settings = get_settings()
        if settings.email_backend == "memory":
            _backend = MemoryEmailBackend()
        elif settings.email_backend == "smtp":
            _backend = SMTPEmailBackend(settings)
        else:
            _backend = ConsoleEmailBackend()
    return _backend


# ----------------------------------------------------------------------------
# Message composers
# ----------------------------------------------------------------------------
def send_verification_email(to: str, full_name: str, raw_token: str) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url}/verify-email?token={raw_token}"
    body = (
        f"Hi {full_name},\n\n"
        f"Welcome to IntelliHire. Please confirm your email address by opening this link "
        f"within {settings.email_verification_expire_hours} hours:\n\n{link}\n\n"
        "If you did not create an account, you can ignore this message."
    )
    get_email_backend().send(EmailMessage(to=to, subject="Verify your IntelliHire email", body=body, meta={"token": raw_token, "link": link}))


def send_password_reset_email(to: str, full_name: str, raw_token: str) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    body = (
        f"Hi {full_name},\n\n"
        f"We received a request to reset your password. Open this link within "
        f"{settings.password_reset_expire_minutes} minutes to choose a new one:\n\n{link}\n\n"
        "If you did not ask for a reset, ignore this email; your password stays the same."
    )
    get_email_backend().send(EmailMessage(to=to, subject="Reset your IntelliHire password", body=body, meta={"token": raw_token, "link": link}))


def send_company_registration_received(to: str, company_name: str) -> None:
    body = (
        f"Thank you for registering {company_name} on IntelliHire.\n\n"
        "A platform administrator will review your registration. You will receive another "
        "email as soon as the company account is approved."
    )
    get_email_backend().send(EmailMessage(to=to, subject="IntelliHire company registration received", body=body, meta={"company": company_name}))


def send_company_decision(to: str, company_name: str, approved: bool, reason: str | None) -> None:
    if approved:
        subject = "Your IntelliHire company account is approved"
        body = f"Good news: {company_name} has been approved. Log in to open your company dashboard."
    else:
        subject = "Your IntelliHire company registration was not approved"
        body = f"{company_name} was not approved.\n\nReason: {reason or 'No reason given.'}\n\nYou may correct the details and register again."
    get_email_backend().send(EmailMessage(to=to, subject=subject, body=body, meta={"company": company_name, "approved": approved, "reason": reason}))
