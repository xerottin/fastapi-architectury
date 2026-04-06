import logging

import resend
from celery import shared_task
from sqlalchemy import select

from core.config import settings
from db.session import get_db_context
from models.user import User

logger = logging.getLogger(__name__)
resend.api_key = settings.resend_api_key


@shared_task(bind=True, max_retries=3)
def send_weekly_newsletter(self):
    """Еженедельная рассылка всем активным пользователям."""
    with get_db_context() as db:
        users = db.execute(
            select(User).where(User.is_active == True)
        ).scalars().all()

    for user in users:
        try:
            resend.Emails.send({
                "from": settings.email_from,
                "to": user.email,
                "subject": "Еженедельный дайджест",
                "html": _build_newsletter_html(user),
            })
        except Exception as e:
            logger.error("Failed to send newsletter to %s: %s", user.email, e)


@shared_task(bind=True, max_retries=3)
def send_custom_email(self, to: str, subject: str, html: str):
    """Отправить произвольное письмо на указанный адрес."""
    try:
        resend.Emails.send({
            "from": f"{settings.email_from_name} <{settings.email_from}>",
            "to": to,
            "subject": subject,
            "html": html,
        })
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, to: str, username: str):
    """Send a welcome email to a newly registered user."""
    logger.info("Sending welcome email to %s (username=%s)", to, username)
    try:
        response = resend.Emails.send({
            "from": f"{settings.email_from_name} <{settings.email_from}>",
            "to": to,
            "subject": "Welcome to Fast-Arch!",
            "html": _build_welcome_html(username),
        })
        logger.info("Welcome email sent successfully to %s, id=%s", to, response.get("id"))
    except Exception as e:
        logger.error("Failed to send welcome email to %s: %s", to, e)
        raise self.retry(exc=e)


def _build_newsletter_html(user) -> str:
    return f"<h2>Привет, {user.name}!</h2><p>Вот твой еженедельный дайджест...</p>"


def _build_welcome_html(username: str) -> str:
    return f"""
    <h2>Welcome to Fast-Arch, {username}!</h2>
    <p>We're excited to have you on board.</p>
    <p>Your account has been successfully created. You can now log in and start using the platform.</p>
    <p>If you have any questions, feel free to reach out to us.</p>
    <br>
    <p>Best regards,<br>The Fast-Arch Team</p>
    """
