from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, BackgroundTasks
from typing import List, Optional
import os
from uuid import uuid4
import shutil
from datetime import datetime

from sqlmodel import Session, select, func

from database import get_session
from services.auth_service import get_current_user
from services.file_service import save_upload_file, save_upload_file_async
from models.media import Media, MediaStatusUpdate
from models.user import User, UserRole
from models.media_interaction import Comment, MediaReaction
from schemas.media import PaginatedMedia, MediaRead, MediaWithRelatedCategoryMedia
from sqlalchemy.orm import selectinload 
from core.config import settings
from schemas.media_response import MediaResponse, CommentResponse, MediaReactionSummary
from schemas.user import UserRead
from schemas.comment_interaction import CommentReactionsData
from models.comment_interaction import CommentReaction
import subprocess
from pathlib import Path
import json
import ffmpeg

router = APIRouter()

UPLOAD_DIR=settings.UPLOAD_MEDIA_DIR

# @router.post("/media/create", response_model=Media)
# async def create_media(
#     title: str = Form(...),
#     description: str | None = Form(None),
#     media_type: str = Form(...),  # image, video, audio
#     category_id: Optional[int] = Form(None),
#     file: UploadFile = File(...),
#     thumbnail: Optional[UploadFile] = File(None),
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ):
#     # Ensure upload dir exists
#     os.makedirs(UPLOAD_DIR, exist_ok=True)

#     # Save media file
#     file_ext = os.path.splitext(file.filename)[1]
#     unique_name = f"{current_user.id}_{uuid4().hex}{file_ext}"
#     file_path = os.path.join(UPLOAD_DIR, unique_name)

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     file_url = file_path

#     # Handle thumbnail if provided
#     thumbnail_url = None
#     if thumbnail:
#         thumb_ext = os.path.splitext(thumbnail.filename)[1]
#         thumb_name = f"{current_user.id}_thumb_{uuid4().hex}{thumb_ext}"
#         thumb_path = os.path.join(UPLOAD_DIR, thumb_name)

#         with open(thumb_path, "wb") as f:
#             f.write(await thumbnail.read())

#         thumbnail_url = thumb_path

#     # Save in DB
#     media = Media(
#         title=title,
#         description=description,
#         media_type=media_type,
#         file_url=file_url,
#         thumbnail_url=thumbnail_url,
#         owner_id=current_user.id,
#         category_id=category_id,
#         created_at=datetime.utcnow(),
#     )
#     session.add(media)
#     session.commit()
#     session.refresh(media)

#     return media



def convert_to_hls(video_path: Path, output_dir: Path):
    """
    Convert uploaded video to HLS format (.m3u8 + .ts)
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-profile:v", "baseline",
            "-level", "3.0",
            "-start_number", "0",
            "-hls_time", "10",
            "-hls_list_size", "0",
            "-f", "hls",
            str(output_dir / "index.m3u8"),
        ]
        subprocess.run(cmd, check=True)
        print(f"✅ HLS conversion complete for {video_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed: {e}")


def get_video_metadata(video_path: Path):
    """Extract width, height, and duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json",
        str(video_path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("FFprobe error:", result.stderr)
        return None
    data = json.loads(result.stdout)
    if "streams" in data and len(data["streams"]) > 0:
        width = data["streams"][0].get("width")
        height = data["streams"][0].get("height")
        duration = float(data["streams"][0].get("duration", 0))
        return width, height, duration
    return None, None, 0


def generate_thumbnail(video_path: Path, output_dir: Path, duration: float):
    """Generate a thumbnail from the middle of the video."""
    thumbnail_path = output_dir / f"{video_path.stem}_thumb.jpg"
    os.makedirs(output_dir, exist_ok=True)
    # Capture frame at half duration (middle)
    capture_time = max(duration / 2, 1)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(capture_time),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(thumbnail_path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return thumbnail_path


def get_audio_metadata(file_path: str):
    """Extract metadata from audio file using ffmpeg.probe."""
    probe = ffmpeg.probe(file_path)
    audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
    
    if not audio_stream:
        raise ValueError("No audio stream found in the file.")
    
    duration = float(probe["format"]["duration"])
    sample_rate = int(audio_stream.get("sample_rate", 0))
    channels = int(audio_stream.get("channels", 0))
    bit_rate = int(probe["format"].get("bit_rate", 0))

    return {
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "bit_rate": bit_rate,
    }

MEDIA_UPLOAD_DIR = Path("static/media/uploads")
HLS_OUTPUT_DIR = Path("static/media/hls")
THUMBNAIL_DIR = Path("static/media/thumbnails")

MEDIA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/media/create", response_model=Media)
async def create_media(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str | None = Form(None),
    media_type: str = Form(...),  # image, video, audio
    category_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    thumbnail: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    hls_path = ''
    thumbnail_url = None
    width = None
    height = None
    duration = None
    if media_type == 'audio':
        file_ext = os.path.splitext(file.filename)[1]
        unique_name = f"{current_user.id}_{uuid4().hex}{file_ext}"
        file_path = os.path.join(MEDIA_UPLOAD_DIR, unique_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = file_path

        if thumbnail:
            thumb_ext = os.path.splitext(thumbnail.filename)[1]
            thumb_name = f"{current_user.id}_thumb_{uuid4().hex}{thumb_ext}"
            thumb_path = os.path.join(THUMBNAIL_DIR, thumb_name)

            with open(thumb_path, "wb") as f:
                f.write(await thumbnail.read())

            thumbnail_url = thumb_path

        duration = get_audio_metadata(file_url)['duration']

    elif media_type == 'video':
        if not file.filename.endswith((".mp4", ".mov", ".mkv")):
            raise HTTPException(status_code=400, detail="Unsupported video format")
        
        unique_name = f"{current_user.id}_{uuid4().hex}"

        file_url = MEDIA_UPLOAD_DIR / unique_name
        with open(file_url, "wb") as f:
            f.write(await file.read())

        width, height, duration = get_video_metadata(file_url)

        # Generate thumbnail
        thumbnail_url = generate_thumbnail(file_url, THUMBNAIL_DIR, duration)

        # Prepare output directory for HLS
        output_dir = HLS_OUTPUT_DIR / unique_name
        # Run conversion in background
        background_tasks.add_task(convert_to_hls, file_url, output_dir)

        hls_path = f"{output_dir}/index.m3u8"

     # Save in DB
    media = Media(
        title=title,
        description=description,
        media_type=media_type,
        file_url=str(file_url),
        hls_path=hls_path,
        thumbnail_url=str(thumbnail_url),
        width=width,
        height=height,
        duration=duration,
        owner_id=current_user.id,
        category_id=category_id,
        created_at=datetime.utcnow(),
    )
    session.add(media)
    session.commit()
    session.refresh(media)

    return {"message": "Video uploaded successfully!", "media": media}


@router.get("/media/list", response_model=List[MediaRead])
def list_media(
    skip: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Media).where(Media.owner_id == current_user.id).offset(skip).limit(limit)
    media_list = session.exec(query).all()
    return media_list


@router.get("/media/lists", response_model=List[MediaRead])
def list_media_all(
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    query = select(Media).offset(skip).limit(limit)
    media_list = session.exec(query).all()
    return media_list


@router.get("/media/detail/{media_id}", response_model=MediaResponse)
def get_media(
    media_id: int,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_user),
):
    media = session.exec(select(Media).where(Media.id == media_id).options(selectinload(Media.category))).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Comments
    comments = session.exec(
        select(Comment).where(Comment.media_id == media_id).order_by(Comment.created_at.desc())
    ).all()

    likes_count = session.exec(
        select(func.count()).where(MediaReaction.media_id == media_id, MediaReaction.is_like == True)
    ).one()

    dislikes_count = session.exec(
        select(func.count()).where(MediaReaction.media_id == media_id, MediaReaction.is_like == False)
    ).one()

    return MediaResponse(
        media=media,
        reactions=MediaReactionSummary(
            likes=likes_count,
            dislikes=dislikes_count
        ),
        comments=[
            CommentResponse(
                id=c.id,
                user_id=c.user_id,
                content=c.content,
                created_at=c.created_at
            )
            for c in comments
        ]
    )


# @router.get("/media/{media_id}/details", response_model=MediaWithRelatedCategoryMedia)
@router.get("/media/{media_id}/details")
def get_media(
    media_id: int,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_user),
):
    media = session.exec(select(Media).where(Media.id == media_id)).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
   
    # Comments
    comments = session.exec(
        select(Comment).where(Comment.media_id == media_id).order_by(Comment.created_at.desc())
    ).all()

    likes_count = session.exec(
        select(func.count()).where(MediaReaction.media_id == media_id, MediaReaction.is_like == True)
    ).one()

    dislikes_count = session.exec(
        select(func.count()).where(MediaReaction.media_id == media_id, MediaReaction.is_like == False)
    ).one()

    related_media = session.exec(
        select(Media)
        .where(
            (Media.category_id == media.category_id) & 
            (Media.id != media_id)                     
        )
        .options(selectinload(Media.category))
    ).all()

    media_read = MediaRead.model_validate(media)

    comment_responses = []
    for c in comments:
        # ✅ Fetch owner info
        owner = session.exec(select(User).where(User.id == c.user_id)).first()
        owner_data = UserRead.model_validate(owner)

        # ✅ Fetch reactions for this comment
        reactions = session.exec(select(CommentReaction).where(CommentReaction.comment_id == c.id)).all()
        reaction_data = [CommentReactionsData.model_validate(r) for r in reactions]

        # ✅ Build response object
        comment_responses.append(
            CommentResponse(
                id=c.id,
                user_id=c.user_id,
                content=c.content,
                created_at=c.created_at,
                user=owner_data,
                reactions=reaction_data
            )
        )

    return {
        'media': media_read,
        'reactions': MediaReactionSummary(
            likes=likes_count,
            dislikes=dislikes_count
        ),
        'comments': comment_responses,
        # 'related_media': related_media,
        "related_media": [MediaRead.model_validate(m) for m in related_media]
    }


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
    # if not media:
    #     raise HTTPException(status_code=404, detail="Media not found")

    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this media")

    if media.file_url and os.path.exists(media.file_url):
        os.remove(media.file_url)

    if media.file_url:
        file_path = Path(media.file_url)
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                print(f"✅ Deleted original file: {file_path}")
            except Exception as e:
                print(f"⚠️ Error deleting file {file_path}: {e}")

    if media.hls_path:
        hls_path = Path(media.hls_path).parent  # remove the folder (not just index.m3u8)
        if hls_path.exists() and hls_path.is_dir():
            try:
                shutil.rmtree(hls_path)
                print(f"✅ Deleted HLS directory: {hls_path}")
            except Exception as e:
                print(f"⚠️ Error deleting HLS directory {hls_path}: {e}")

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
    # media = session.exec(select(Media).where(Media.id == media_id).options(selectinload(Media.category))).first()
    media = session.exec(select(Media).where(Media.id == media_id)).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media



@router.post("/media/views/{media_id}")
def increment_media_views(media_id: int, session: Session = Depends(get_session)):
    media = session.exec(select(Media).where(Media.id == media_id)).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    media.views += 1
    session.add(media)
    session.commit()
    session.refresh(media)
    return {'message': "Media views incremented"}