from fastapi import APIRouter
from starlette import status

from schemas.email import EmailSendRequest
from tasks.resend_task import send_custom_email

router = APIRouter()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def send_email_endpoint(payload: EmailSendRequest):
    send_custom_email.delay(
        to=payload.email,
        subject=payload.subject,
        html=f"<p>{payload.text}</p>",
    )
    return {"detail": "Email queued"}
