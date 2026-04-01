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
                "from": f"{settings.email_from_name} <{settings.email_from}>",
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


def _build_newsletter_html(user) -> str:
    return f"<h2>Привет, {user.name}!</h2><p>Вот твой еженедельный дайджест...</p>"
