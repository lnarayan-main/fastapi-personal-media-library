from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from schemas.category import CategoryRead
from schemas.user import UserRead
from sqlmodel import SQLModel, Field
from models.media import MediaStatus

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
    category: Optional[CategoryRead] = None
    status: MediaStatus
    user: Optional[UserRead] = None
    views: int
    hls_path: Optional[str]
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int] = None

    class Config:
        from_attributes = True 

class PaginatedMedia(SQLModel):
    items: List[MediaRead] = Field(description="The list of media for the current page.")
    page: int = Field(description="The current page number (1-based).")
    size: int = Field(description="The number of items per page.")
    total_count: int = Field(description="Total number of media matching the filter.")
    total_pages: int


class MediaWithRelatedCategoryMedia(SQLModel):
    media: MediaRead
    related_media: List[MediaRead]

    class Config:
        from_attributes = True
