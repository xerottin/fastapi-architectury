from pydantic import BaseModel, EmailStr


class EmailSendRequest(BaseModel):
    email: EmailStr
    subject: str = "Сообщение"
    text: str
