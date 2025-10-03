# backend/schemas/media.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MediaCreate(BaseModel):
    title: str
    description: Optional[str] = None
    media_type: str  # image / video / audio
    category_id: Optional[int] = None

class MediaRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    media_type: str
    file_url: str
    thumbnail_url: Optional[str]
    owner_id: int
    category_id: Optional[int]
    created_at: datetime
