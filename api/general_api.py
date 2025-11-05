from fastapi import APIRouter, status, HTTPException, Depends, BackgroundTasks, UploadFile, File
from schemas.contact_us import ContactUsMessage
from schemas.user import UserRead
from schemas.media import MediaRead
from models.media import Media
from models.user import User
from services.auth_service import get_current_user
from services.file_service import safe_filename, save_upload_file

from core.mail import fast_mail
from fastapi_mail import MessageSchema, MessageType, MultipartSubtypeEnum
from core.config import settings
from database import get_session
from sqlmodel import Session, select
import os
from core.cloudinary_config import cloudinary

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
    

@router.get("/users/{user_id}/profile", response_model=UserRead)
def get_user_profile(user_id: int, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return user
    
@router.get("/media/user/{user_id}", response_model=list[MediaRead])
def get_user_media(user_id: int, session: Session = Depends(get_session)):
    query = select(Media).where(Media.owner_id == user_id)
    media = session.exec(query).all()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")

    return media

@router.post("/user/{user_id}/bg-profile-update")
async def bg_profile_update(
        user_id: int, 
        bg_file: UploadFile = File(...), 
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
    ):
    if not bg_file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if user_id != current_user.id:
        raise HTTPException(status_code=404, detail="User not found.")
    # if bg_file:
    #     upload_dir = settings.UPLOAD_PROFILE_DIR
    #     os.makedirs(upload_dir, exist_ok=True)

    #     if current_user.background_pic_url:
    #         old_file_path = current_user.background_pic_url.lstrip("/")
    #         if os.path.exists(old_file_path):
    #             os.remove(old_file_path)

    #     filename = safe_filename(current_user.id, bg_file.filename)
    #     file_path = os.path.join(upload_dir, filename)

    #     # Save file
    #     save_upload_file(bg_file, upload_dir, filename)

    #     current_user.background_pic_url = f"/{upload_dir}/{filename}"


    # image uploading to cloudinary
    if bg_file:
        try:
            if current_user.background_pic_public_id:
                try:
                    cloudinary.uploader.destroy(current_user.background_pic_public_id)
                except Exception as delete_error:
                    print(f"⚠️ Failed to delete old background pic: {delete_error}")

            res = cloudinary.uploader.upload(
                bg_file.file,
                folder=f"mediahub/profile_pics/{current_user.id}",
                transformation=[{"width": 600, "height": 600, "crop": "limit"}],  
                overwrite=True
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


        current_user.background_pic_url = res.get("secure_url")
        current_user.background_pic_public_id = res.get("public_id")

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return {'message': "Background Pic saved successfully.", "bg_pic_url": current_user.background_pic_url}