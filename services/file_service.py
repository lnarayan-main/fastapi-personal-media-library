import os
import re
import time
from uuid import uuid4
import shutil
from fastapi import UploadFile
from core.config import settings


def safe_filename(user_id: int, original_filename: str) -> str:
    # Remove unwanted characters and spaces, replace with underscores
    name, ext = os.path.splitext(original_filename)
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    # Append user ID and timestamp for uniqueness
    timestamp = int(time.time())
    filename = f"{user_id}_{name}_{timestamp}{ext.lower()}"
    return filename

def save_upload_file(upload_file: UploadFile, dest_dir: str, dest_filename: str) -> str:
    """Save UploadFile to disk and return the saved path (relative or absolute as you prefer)."""
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, dest_filename)

    # Use shutil.copyfileobj for streamed saving
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return dest_path

async def save_upload_file_async(upload_file: UploadFile, dest_dir: str, dest_filename: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, dest_filename)
    with open(dest_path, "wb") as f:
        f.write(await upload_file.read())
    return dest_path
