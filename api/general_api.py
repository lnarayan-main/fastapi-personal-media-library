from fastapi import APIRouter, status, HTTPException, Depends
from schemas.contact_us import ContactUsMessage
from schemas.user import UserRead
from models.media import Media
from models.user import User

from core.mail import fast_mail
from fastapi_mail import MessageSchema
from core.config import settings
from database import get_session
from sqlmodel import Session, select

router = APIRouter()

@router.post("/contact-us", status_code=status.HTTP_201_CREATED)
async def contact_us_message(data: ContactUsMessage):
    html = f"""
    <h2>Contact Us Message</h2>
    <p><strong>Name:</strong> {data.name}</p>
    <p><strong>Email:</strong> {data.email}</p>
    <p><strong>Message:</strong><br>{data.message}</p>
    """

    messageData = MessageSchema(
        subject="New Contact Us Message",
        recipients=[settings.OWNER_EMAIL],
        body=html,
        subtype="html"
    )

    try:
        await fast_mail.send_message(messageData)
        return {"message": "Message has been sent successfully."}
    except Exception as e:
        print("Email sending error:", e)
        raise HTTPException(
            status_code=500, detail="Failed to send the message. Please try again later."
        )


