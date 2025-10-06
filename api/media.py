# backend/api/media.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
import os
from uuid import uuid4
import shutil
from datetime import datetime

from sqlmodel import Session, select, func

from database import get_session
from services.auth_service import get_current_user
from services.file_service import save_upload_file, save_upload_file_async
from config import UPLOAD_DIR
from models.media import Media, MediaStatusUpdate
from models.user import User, UserRole
from schemas.media import PaginatedMedia, MediaRead
from sqlalchemy.orm import selectinload 

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


@router.get("/media-management", response_model=PaginatedMedia)
def users_list(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number, starts from 1"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(None, description="Search term to filter media by title or description (case-insensitive)"),
    session: Session = Depends(get_session),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all users"
        )
    
    statement = select(Media)

    if search:
        search_pattern = f"%{search}%"

        statement = statement.where(
            (Media.title.ilike(search_pattern)) | (Media.description.ilike(search_pattern))
        )

    total_count = session.exec(select(func.count()).select_from(statement)).one()

    offset = (page - 1) * size

    statement = statement.order_by(Media.id).offset(offset).limit(size)

    media = session.exec(statement).all()
    
    total_pages = (total_count + size -1) // size if total_count > 0 else 0
    
    return PaginatedMedia(
        total_count=total_count,
        page=page,
        size= size,
        items=media,
        total_pages=total_pages
    )


@router.post("/media/change-status")
def changeUserStatus(
    media_data: MediaStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    media = session.exec(select(Media).where(Media.id == media_data.id)).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")
    media.status = media_data.status
    session.add(media)
    session.commit()
    session.refresh(media)
    return {"status": 200, "detail": "Status changed successfully."}


@router.delete("/admin-media/delete/{media_id}")
def admin_delete_media(
    media_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete associated files (if exist)
    if media.file_url and os.path.exists(media.file_url):
        os.remove(media.file_url)

    if media.thumbnail_url and os.path.exists(media.thumbnail_url):
        os.remove(media.thumbnail_url)

    # Remove from DB
    session.delete(media)
    session.commit()

    return {"message": "Media deleted successfully"}


@router.get("/media-view/{media_id}", response_model=MediaRead)
def get_media(
    media_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.exec(select(Media).where(Media.id == media_id).options(selectinload(Media.category))).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media