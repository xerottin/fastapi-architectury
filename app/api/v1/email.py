import resend

from fastapi import APIRouter, status

from core.config import settings
from core.exceptions import AppException
from schemas.email import EmailSendRequest
from tasks.resend_task import send_custom_email

router = APIRouter()

resend.api_key = settings.resend_api_key

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def send_email_endpoint(payload: EmailSendRequest):
    send_custom_email.delay(
        to=payload.email,
        subject=payload.subject,
        html=f"<p>{payload.text}</p>",
    )
    return {"detail": "Email queued"}


@router.post("/send")
async def send_email(body: EmailSendRequest):
    try:
        params: resend.Emails.SendParams = {
            "from": settings.email_from,
            "to": [body.email],
            "subject": body.subject,
            "html": f"<p>{body.text}</p>",
        }
        response = resend.Emails.send(params)
        return {"message": "Письмо отправлено", "id": response["id"]}
    except Exception as e:
        raise AppException(
            code="email_send_failed",
            detail=str(e),
            status_code=500,
        )