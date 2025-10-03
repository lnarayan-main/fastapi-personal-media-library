# backend/api/media.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
import os
from uuid import uuid4
import shutil
from datetime import datetime

from sqlmodel import Session, select

from database import get_session
from services.auth_service import get_current_user
from services.file_service import save_upload_file, save_upload_file_async
from config import UPLOAD_DIR
from models.media import Media
from models.user import User

router = APIRouter()

@router.post("/media/create", response_model=Media)
async def create_media(
    title: str = Form(...),
    description: str | None = Form(None),
    media_type: str = Form(...),  # image, video, audio
    category_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    thumbnail: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Ensure upload dir exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save media file
    file_ext = os.path.splitext(file.filename)[1]
    unique_name = f"{current_user.id}_{uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_url = file_path

    # Handle thumbnail if provided
    thumbnail_url = None
    if thumbnail:
        thumb_ext = os.path.splitext(thumbnail.filename)[1]
        thumb_name = f"{current_user.id}_thumb_{uuid4().hex}{thumb_ext}"
        thumb_path = os.path.join(UPLOAD_DIR, thumb_name)

        with open(thumb_path, "wb") as f:
            f.write(await thumbnail.read())

        thumbnail_url = thumb_path

    # Save in DB
    media = Media(
        title=title,
        description=description,
        media_type=media_type,
        file_url=file_url,
        thumbnail_url=thumbnail_url,
        owner_id=current_user.id,
        category_id=category_id,
        created_at=datetime.utcnow(),
    )
    session.add(media)
    session.commit()
    session.refresh(media)

    return media


@router.get("/media/list", response_model=List[Media])
def list_media(
    skip: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Media).where(Media.owner_id == current_user.id).offset(skip).limit(limit)
    media_list = session.exec(query).all()
    return media_list


@router.get("/media/lists", response_model=List[Media])
def list_media_all(
    skip: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    query = select(Media).offset(skip).limit(limit)
    media_list = session.exec(query).all()
    return media_list


@router.get("/media/detail/{media_id}", response_model=Media)
def get_media(
    media_id: int,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    # if media.owner_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized to view this media")
    return media


@router.put("/media/update/{media_id}", response_model=Media)
async def update_media(
    media_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    media_type: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    thumbnail: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # 1. Fetch media object
    media = session.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this media")

    # 2. Update simple fields
    if title:
        media.title = title
    if description:
        media.description = description
    if media_type:
        media.media_type = media_type
    if category_id is not None:
        media.category_id = category_id

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 3. Handle file replacement (main media file)
    if file:
        # Remove old file if exists
        if media.file_url and os.path.exists(media.file_url):
            os.remove(media.file_url)

        file_ext = os.path.splitext(file.filename)[1]
        unique_name = f"{current_user.id}_{media_id}_{uuid4().hex}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        media.file_url = file_path

    # 4. Handle thumbnail replacement
    if thumbnail:
        if media.thumbnail_url and os.path.exists(media.thumbnail_url):
            os.remove(media.thumbnail_url)

        thumb_ext = os.path.splitext(thumbnail.filename)[1]
        thumb_name = f"{current_user.id}_{media_id}_thumb_{uuid4().hex}{thumb_ext}"
        thumb_path = os.path.join(UPLOAD_DIR, thumb_name)

        with open(thumb_path, "wb") as f:
            f.write(await thumbnail.read())

        media.thumbnail_url = thumb_path

    session.add(media)
    session.commit()
    session.refresh(media)

    return media


@router.delete("/media/delete/{media_id}")
def delete_media(
    media_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this media")

    # Delete associated files (if exist)
    if media.file_url and os.path.exists(media.file_url):
        os.remove(media.file_url)

    if media.thumbnail_url and os.path.exists(media.thumbnail_url):
        os.remove(media.thumbnail_url)

    # Remove from DB
    session.delete(media)
    session.commit()

    return {"message": "Media deleted successfully"}
