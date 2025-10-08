from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
import os
from sqlmodel import Session, select, func
from datetime import datetime

from database import get_session
from services.auth_service import get_current_user, require_admin
from models.user import User, UserStatusUpdate
from services.file_service import safe_filename, save_upload_file, save_upload_file_async
from config import UPLOAD_DIR
from typing import List
from schemas.user import PaginatedUsers, UserRole, UserRead

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


@router.get("/users", response_model=PaginatedUsers)
def users_list(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number, starts from 1"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(None, description="Search term to filter users by name or email (case-insensitive)"),
    session: Session = Depends(get_session),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all users"
        )

    statement = select(User).where(User.role != UserRole.ADMIN)

    if search:
        search_pattern = f"%{search}%"

        statement = statement.where(
            (User.name.ilike(search_pattern)) | (User.email.ilike(search_pattern))
        )

    total_count = session.exec(select(func.count()).select_from(statement)).one()

    offset = (page - 1) * size

    statement = statement.order_by(User.id).offset(offset).limit(size)

    users = session.exec(statement).all()
    
    total_pages = (total_count + size - 1) // size if total_count > 0 else 0

    return PaginatedUsers(
        total_count=total_count,
        page=page,
        size= size,
        items=users,
        total_pages=total_pages
    )

@router.get("/users/{user_id}", response_model=UserRead)
def user_view(user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/user/change-status")
def changeUserStatus(
    user_data: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.id == user_data.id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.status = user_data.status
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"status": 200, "detail": "Status changed successfully."}

@router.delete("/user/delete/{user_id}")
def user_delete(user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.id ==user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.profile_pic_url:
        file_path = user.profile_pic_url.lstrip("/")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Failed to delete {file_path}: {e}")

    session.delete(user)
    session.commit()
    return {"status": 200, "detail": "User deleted successfully."}
    
    