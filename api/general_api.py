from fastapi import APIRouter, status, HTTPException, Depends, BackgroundTasks
from schemas.contact_us import ContactUsMessage
from schemas.user import UserRead
from models.media import Media
from models.user import User

from core.mail import fast_mail
from fastapi_mail import MessageSchema, MessageType, MultipartSubtypeEnum
from core.config import settings
from database import get_session
from sqlmodel import Session, select

router = APIRouter()

@router.post("/contact-us", status_code=status.HTTP_201_CREATED)
async def contact_us_message(
    data: ContactUsMessage,
    background_tasks: BackgroundTasks 
):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 15px; border: 1px solid #eee; border-radius: 8px;">
        <h2 style="color: #4F46E5;">New Contact Us Message</h2>
        <p><strong>Name:</strong> {data.name}</p>
        <p><strong>Email:</strong> {data.email}</p>
        <p style="margin-top: 15px;"><strong>Message:</strong></p>
        <div style="border-left: 3px solid #ccc; padding-left: 10px; margin-top: 5px; white-space: pre-wrap;">
            {data.message}
        </div>
    </div>
    """

    messageData = MessageSchema(
        subject="New Contact Us Message",
        recipients=[settings.OWNER_EMAIL],
        body=html,
        subtype=MessageType.html,
        multipart_subtype=MultipartSubtypeEnum.alternative  
    )

    try:
        background_tasks.add_task(
            fast_mail.send_message, 
            messageData, 
            MessageType.html
        )
        return {"message": "Message successfully scheduled for sending."}
        
    except Exception as e:
        print("Email scheduling error:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to schedule the message delivery. Please try again later."
        )