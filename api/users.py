# backend/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
import os
from sqlmodel import Session, select
from datetime import datetime

from database import get_session
from services.auth_service import get_current_user, require_admin
from models.user import User
from services.file_service import safe_filename, save_upload_file, save_upload_file_async
from config import UPLOAD_DIR
from typing import List

router = APIRouter()

@router.get("/user/profile", response_model=User)
def get_profile_details(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/user/profile", response_model=User)
def update_profile(
    name: str | None = Form(None),
    email: str | None = Form(None),
    about: str | None = Form(None),
    password: str | None = Form(None),
    profile_pic: UploadFile = File(None),  # Optional file upload
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Update text fields
    if name is not None:
        current_user.name = name

    if email is not None:
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = email

    if about is not None:
        current_user.about = about

    if password is not None:
        from services.auth_service import get_password_hash
        current_user.hashed_password = get_password_hash(password)

    # Handle file upload
    if profile_pic:
        upload_dir = "static/profile_pics"
        os.makedirs(upload_dir, exist_ok=True)

        # Delete old profile pic
        if current_user.profile_pic_url:
            old_file_path = current_user.profile_pic_url.lstrip("/")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

        # Safe and unique filename
        filename = safe_filename(current_user.id, profile_pic.filename)
        file_path = os.path.join(upload_dir, filename)

        # Save file
        save_upload_file(profile_pic, upload_dir, filename)

        current_user.profile_pic_url = f"/{upload_dir}/{filename}"

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return current_user


@router.get("/users", response_model=List[User])
def users_list(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Optional: restrict to admins only
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all users"
        )

    users = session.exec(select(User).where(User.role != 'admin')).all()
    if not users:
        raise HTTPException(status_code=404, detail="Users not found.")
    return users