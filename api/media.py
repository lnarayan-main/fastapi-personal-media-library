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
from models.media import Media, MediaStatusUpdate, MediaStatus
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
import logging
from core.cloudinary_config import cloudinary
from cloudinary.utils import cloudinary_url

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


# simple conversion
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
            str(output_dir / "master.m3u8"),
        ]
        subprocess.run(cmd, check=True)
        print(f"✅ HLS conversion complete for {video_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed: {e}")



logger = logging.getLogger(__name__)

# multi quality conversion
def convert_video_to_hls(video_path: Path, output_dir: Path) -> Path:
    """
    Convert a video into multiple quality HLS streams with proper error handling.
    Creates 480p, 720p, 1080p variant playlists and a master.m3u8 file.
    
    Fix applied: Changed the complex scale filter logic to use '-2' for 
    automatically calculating the width to ensure it is divisible by 2.
    """

    try:
        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
           
            # --- Stream Filters ---
            # Use the simple and robust '-2' to ensure the calculated dimension (width) 
            # is automatically divisible by 2 while maintaining aspect ratio.
            "-filter_complex",
            "[v:0]split=3[v1][v2][v3];"
            "[v1]scale=-2:480[v1out];"   # Scale to height 480, calculate even width
            "[v2]scale=-2:720[v2out];"   # Scale to height 720, calculate even width
            "[v3]scale=-2:1080[v3out]",  # Scale to height 1080, calculate even width

            # --- 480p Output ---
            # Maps video stream [v1out] and the audio stream (a:0?)
            "-map", "[v1out]", "-c:v:0", "libx264", "-b:v:0", "800k", "-maxrate", "1000k", "-bufsize", "1200k",
            "-map", "a:0?", "-c:a:0", "aac", "-b:a:0", "96k",
            # HLS settings
            "-f", "hls", "-hls_time", "10", "-hls_list_size", "0",
            "-hls_segment_filename", str(output_dir / "480p_%03d.ts"),
            str(output_dir / "480p.m3u8"),

            # --- 720p Output ---
            "-map", "[v2out]", "-c:v:1", "libx264", "-b:v:1", "2500k", "-maxrate", "3000k", "-bufsize", "3750k",
            "-map", "a:0?", "-c:a:1", "aac", "-b:a:1", "128k",
            # HLS settings
            "-f", "hls", "-hls_time", "10", "-hls_list_size", "0",
            "-hls_segment_filename", str(output_dir / "720p_%03d.ts"),
            str(output_dir / "720p.m3u8"),

            # --- 1080p Output ---
            "-map", "[v3out]", "-c:v:2", "libx264", "-b:v:2", "5000k", "-maxrate", "6000k", "-bufsize", "7500k",
            "-map", "a:0?", "-c:a:2", "aac", "-b:a:2", "192k",
            # HLS settings
            "-f", "hls", "-hls_time", "10", "-hls_list_size", "0",
            "-hls_segment_filename", str(output_dir / "1080p_%03d.ts"),
            str(output_dir / "1080p.m3u8"),
        ]
        
        # NOTE: Added c:v:n 'libx264', maxrate, and bufsize for better streaming quality.

        # Run FFmpeg safely
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        logger.info(f"FFmpeg stdout: {result.stdout}")
        logger.error(f"FFmpeg stderr: {result.stderr}")

        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            # Clean up partial outputs
            shutil.rmtree(output_dir, ignore_errors=True)
            raise RuntimeError("HLS conversion failed. See logs for details.")

        # Verify all expected variant playlists exist
        for res in ["480p", "720p", "1080p"]:
            if not (output_dir / f"{res}.m3u8").exists():
                raise FileNotFoundError(f"Missing {res}.m3u8 variant playlist")

        # Write master playlist (using common 16:9 resolutions for demonstration)
        master_playlist = output_dir / "master.m3u8"
        with open(master_playlist, "w") as f:
            f.write("#EXTM3U\n")
            f.write('#EXT-X-VERSION:3\n')
            # Use fixed resolution for HLS master playlist for simplicity, 
            # though FFmpeg calculates the actual width based on the input aspect ratio.
            f.write('#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=854x480\n480p.m3u8\n') # Updated BANDWIDTH/BITRATE
            f.write('#EXT-X-STREAM-INF:BANDWIDTH=3750000,RESOLUTION=1280x720\n720p.m3u8\n')
            f.write('#EXT-X-STREAM-INF:BANDWIDTH=7500000,RESOLUTION=1920x1080\n1080p.m3u8\n')

        return master_playlist

    except Exception as e:
        logger.exception(f"Error converting {video_path} to HLS: {e}")
        shutil.rmtree(output_dir, ignore_errors=True)
        # Re-raise the exception to propagate the failure
        raise



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

def convert_audio_to_hls(input_path: Path, output_dir: Path):
    """Convert audio file to HLS (for adaptive streaming)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    hls_master = output_dir / "master.m3u8"

    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-vn",  # no video
        "-c:a", "aac",
        "-b:a", "128k",
        "-hls_time", "10",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(output_dir / "audio_%03d.aac"),
        str(hls_master)
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return str(hls_master)

MEDIA_UPLOAD_DIR = Path("static/media/uploads")
HLS_OUTPUT_DIR = Path("static/media/hls")
THUMBNAIL_DIR = Path("static/media/thumbnails")

MEDIA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


# @router.post("/media/create", response_model=Media)
# async def create_media(
#     background_tasks: BackgroundTasks,
#     title: str = Form(...),
#     description: str | None = Form(None),
#     media_type: str = Form(...),  # video, audio
#     category_id: Optional[int] = Form(None),
#     file: UploadFile = File(...),
#     thumbnail: Optional[UploadFile] = File(None),
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ):
#     hls_path = ''
#     thumbnail_url = None
#     width = None
#     height = None
#     duration = None
#     if media_type == 'audio':
#         file_ext = os.path.splitext(file.filename)[1]
#         unique_folder_name = f"{current_user.id}_{uuid4().hex}"
#         unique_name = f"{unique_folder_name}{file_ext}"
#         file_path = os.path.join(MEDIA_UPLOAD_DIR, unique_name)

#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         file_url = file_path

#         output_dir = HLS_OUTPUT_DIR / unique_folder_name
#         background_tasks.add_task(convert_audio_to_hls, file_url, output_dir)
#         hls_path = f"{output_dir}/master.m3u8"

#         if thumbnail:
#             thumb_ext = os.path.splitext(thumbnail.filename)[1]
#             thumb_name = f"{current_user.id}_thumb_{uuid4().hex}{thumb_ext}"
#             thumb_path = os.path.join(THUMBNAIL_DIR, thumb_name)

#             with open(thumb_path, "wb") as f:
#                 f.write(await thumbnail.read())

#             thumbnail_url = thumb_path

#         duration = get_audio_metadata(file_url)['duration']

#     elif media_type == 'video':
#         if not file.filename.endswith((".mp4", ".mov", ".mkv")):
#             raise HTTPException(status_code=400, detail="Unsupported video format")
        
#         file_ext = os.path.splitext(file.filename)[1]
#         unique_folder_name = f"{current_user.id}_{uuid4().hex}"
#         unique_name = f"{unique_folder_name}{file_ext}"

#         file_url = MEDIA_UPLOAD_DIR / unique_name
#         with open(file_url, "wb") as f:
#             f.write(await file.read())

#         width, height, duration = get_video_metadata(file_url)

#         # Generate thumbnail
#         thumbnail_url = generate_thumbnail(file_url, THUMBNAIL_DIR, duration)

#         # Prepare output directory for HLS
#         output_dir = HLS_OUTPUT_DIR / unique_folder_name
#         # Run conversion in background
#         background_tasks.add_task(convert_video_to_hls, file_url, output_dir)

#         hls_path = f"{output_dir}/master.m3u8"

#      # Save in DB
#     media = Media(
#         title=title,
#         description=description,
#         media_type=media_type,
#         file_url=str(file_url),
#         hls_path=hls_path,
#         thumbnail_url=str(thumbnail_url),
#         width=width,
#         height=height,
#         duration=duration,
#         owner_id=current_user.id,
#         category_id=category_id,
#         created_at=datetime.utcnow(),
#     )
#     session.add(media)
#     session.commit()
#     session.refresh(media)

#     return {"message": "Video uploaded successfully!", "media": media}


@router.post("/media/create", response_model=Media)
async def create_media(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str | None = Form(None),
    media_type: str = Form(...),  # 'video' or 'audio'
    category_id: int | None = Form(None),
    file: UploadFile = File(...),
    thumbnail: UploadFile | None = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    mime = file.content_type or ""
    resource_type = "video" if mime.startswith(("video/", "audio/")) else "image"

    folder_type = "videos" if media_type == "video" else "audios"

    try:
        res = cloudinary.uploader.upload(
            file.file,
            resource_type="video",  # Cloudinary uses 'video' for both video/audio
            folder=f"mediahub/{folder_type}/{current_user.id}",
            use_filename=True,
            unique_filename=True,
        )

        public_id = res.get("public_id")
        secure_url = res.get("secure_url")
        cloud_name = cloudinary.config().cloud_name

        # --- Generate HLS URL (Cloudinary auto-generates m3u8 for video/audio) ---
        hls_url = f"https://res.cloudinary.com/{cloud_name}/video/upload/{public_id}.m3u8"

        thumb_public_id = None

        if media_type == "video":
            thumb_url, _ = cloudinary_url(
                public_id,
                resource_type="video",
                format="jpg",
                transformation=[{"width": 400, "height": 225, "crop": "fill"}],
            )
        elif media_type == "audio":
            if thumbnail:
                thumb_res = cloudinary.uploader.upload(
                    thumbnail.file,
                    folder=f"mediahub/audio_thumbnails/{current_user.id}",
                    use_filename=True,
                    unique_filename=True,
                    resource_type="image",
                )
                thumb_url = thumb_res.get("secure_url")
                thumb_public_id = thumb_res.get('public_id')
            else:
                thumb_url = None
        else:
            thumb_url = None

        duration = res.get("duration")
        width = res.get("width")
        height = res.get("height")

        media = Media(
            title=title,
            description=description,
            media_type=media_type, 
            file_url=secure_url,
            public_id=public_id,
            hls_path=hls_url,
            thumbnail_url=thumb_url,
            thumbnail_public_id=thumb_public_id,
            duration=duration,
            width=width,
            height=height,
            owner_id=current_user.id,
            category_id=category_id,
            created_at=datetime.utcnow(),
        )

        session.add(media)
        session.commit()
        session.refresh(media)

        return {
            "message": f"{media_type.capitalize()} uploaded successfully!",
            "media": media,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# @router.put("/media/update/{media_id}", response_model=Media)
# async def update_media(
#     media_id: int,
#     title: Optional[str] = Form(None),
#     description: Optional[str] = Form(None),
#     media_type: Optional[str] = Form(None),
#     category_id: Optional[str] = Form(None),
#     file: Optional[UploadFile] = File(None),
#     thumbnail: Optional[UploadFile] = File(None),
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ):
#     # 1. Fetch media object
#     media = session.get(Media, media_id)
#     if not media:
#         raise HTTPException(status_code=404, detail="Media not found")

#     if media.owner_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not authorized to update this media")

#     # 2. Update simple fields
#     if title:
#         media.title = title
#     if description:
#         media.description = description
#     if media_type:
#         media.media_type = media_type
#     if category_id is not None:
#         media.category_id = category_id

#     os.makedirs(UPLOAD_DIR, exist_ok=True)

#     # 3. Handle file replacement (main media file)
#     if file:
#         # Remove old file if exists
#         if media.file_url and os.path.exists(media.file_url):
#             os.remove(media.file_url)

#         file_ext = os.path.splitext(file.filename)[1]
#         unique_name = f"{current_user.id}_{media_id}_{uuid4().hex}{file_ext}"
#         file_path = os.path.join(UPLOAD_DIR, unique_name)

#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         media.file_url = file_path

#     # 4. Handle thumbnail replacement
#     if thumbnail:
#         if media.thumbnail_url and os.path.exists(media.thumbnail_url):
#             os.remove(media.thumbnail_url)

#         thumb_ext = os.path.splitext(thumbnail.filename)[1]
#         thumb_name = f"{current_user.id}_{media_id}_thumb_{uuid4().hex}{thumb_ext}"
#         thumb_path = os.path.join(UPLOAD_DIR, thumb_name)

#         with open(thumb_path, "wb") as f:
#             f.write(await thumbnail.read())

#         media.thumbnail_url = thumb_path

#     session.add(media)
#     session.commit()
#     session.refresh(media)

#     return media


@router.put("/media/update/{media_id}", response_model=Media)
async def update_media(
    media_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    media_type: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    thumbnail: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.query(Media).filter(Media.id == media_id, Media.owner_id == current_user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found or not owned by user")

    try:
        # Update metadata
        if title:
            media.title = title
        if description:
            media.description = description
        if category_id:
            media.category_id = category_id
        if media_type:
            media.media_type = media_type

        # Preserve existing thumbnail info
        public_id = media.public_id
        thumb_url = media.thumbnail_url
        thumb_public_id = media.thumbnail_public_id

        # Replace media file if provided
        if file:
            # Delete old media from Cloudinary
            if media.public_id:
                try:
                    cloudinary.uploader.destroy(media.public_id, resource_type="video")
                except Exception as e:
                    print("Warning: Failed to delete old media:", e)

            mime = file.content_type or ""
            resource_type = "video" if mime.startswith(("video/", "audio/")) else "auto"

            upload_res = cloudinary.uploader.upload(
                file.file,
                resource_type=resource_type,
                folder=f"mediahub/media/{current_user.id}",
                use_filename=True,
                unique_filename=False,
                overwrite=True
            )

            public_id = upload_res.get("public_id")
            secure_url = upload_res.get("secure_url")
            cloud_name = cloudinary.config().cloud_name
            hls_url = f"https://res.cloudinary.com/{cloud_name}/video/upload/{public_id}.m3u8"

            # Generate video thumbnail if applicable
            if media.media_type == "video":
                thumb_url, _ = cloudinary_url(
                    public_id,
                    resource_type="video",
                    format="jpg",
                    transformation=[{"width": 400, "height": 225, "crop": "fill"}],
                )

            media.file_url = secure_url
            media.public_id = public_id
            media.hls_path = hls_url
            media.duration = upload_res.get("duration")
            media.width = upload_res.get("width")
            media.height = upload_res.get("height")

        # Replace thumbnail for audio if provided
        if media.media_type == "audio" and thumbnail:
            if thumb_public_id:
                try:
                    cloudinary.uploader.destroy(thumb_public_id, resource_type="image")
                except Exception as e:
                    print("Warning: Failed to delete old thumbnail:", e)

            thumb_res = cloudinary.uploader.upload(
                thumbnail.file,
                folder=f"mediahub/audio_thumbnails/{current_user.id}",
                use_filename=True,
                unique_filename=True,
                resource_type="image",
            )
            thumb_url = thumb_res.get("secure_url")
            thumb_public_id = thumb_res.get("public_id")

        # Finalize thumbnail info
        media.thumbnail_url = thumb_url
        media.thumbnail_public_id = thumb_public_id
        media.updated_at = datetime.utcnow()

        session.add(media)
        session.commit()
        session.refresh(media)

        return {"message": "Media updated successfully", "media": media}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update media: {str(e)}")


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
    query = select(Media).where(Media.status == MediaStatus.ACTIVE).offset(skip).limit(limit)
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



# @router.delete("/media/delete/{media_id}")
# def delete_media(
#     media_id: int,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ):
#     media = session.get(Media, media_id)
#     # if not media:
#     #     raise HTTPException(status_code=404, detail="Media not found")

#     if media.owner_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not authorized to delete this media")

#     # if media.file_url and os.path.exists(media.file_url):
#     #     os.remove(media.file_url)

#     if media.file_url:
#         file_path = Path(media.file_url)
#         if file_path.exists() and file_path.is_file():
#             try:
#                 file_path.unlink()
#                 print(f"✅ Deleted original file: {file_path}")
#             except Exception as e:
#                 print(f"⚠️ Error deleting file {file_path}: {e}")

#     if media.hls_path:
#         hls_path = Path(media.hls_path).parent  # remove the folder (not just index.m3u8)
#         if hls_path.exists() and hls_path.is_dir():
#             try:
#                 shutil.rmtree(hls_path)
#                 print(f"✅ Deleted HLS directory: {hls_path}")
#             except Exception as e:
#                 print(f"⚠️ Error deleting HLS directory {hls_path}: {e}")

#     if media.thumbnail_url and os.path.exists(media.thumbnail_url):
#         os.remove(media.thumbnail_url)

#     # Remove from DB
#     session.delete(media)
#     session.commit()

#     return {"message": "Media deleted successfully"}



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
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete files from Cloudinary
    try:
        if media.public_id:
            cloudinary.uploader.destroy(media.public_id, resource_type="video")
        if getattr(media, "thumbnail_public_id", None):
            cloudinary.uploader.destroy(media.thumbnail_public_id, resource_type="image")
    except Exception as e:
        print(f"Cloudinary deletion failed: {e}")

    # Delete DB record
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