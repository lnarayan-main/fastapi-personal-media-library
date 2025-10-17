from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum as PyEnum
from datetime import datetime
from schemas.category import CategoryRead

class MediaType(str, PyEnum):
    VIDEO = "video"
    AUDIO = "audio"

class MediaStatus(PyEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'

class Media(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    title: str
    description: Optional[str] = None
    media_type: str  # image / video / audio
    file_url: str
    thumbnail_url: Optional[str] = None

    status: MediaStatus = Field(default=MediaStatus.ACTIVE, sa_column_kwargs={"default": MediaStatus.ACTIVE})

    # Foreign keys
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    owner_id: int = Field(foreign_key="users.id")

    views: int = Field(default=0)
    hls_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    category: Optional["Category"] = Relationship(back_populates="media")
    user: Optional["User"] = Relationship(back_populates="media")

    comments: List["Comment"] = Relationship(
            back_populates="media", 
            sa_relationship_kwargs={
                "cascade": "all, delete-orphan",
            }
        )
    reactions: List["MediaReaction"] = Relationship(
            back_populates="media",
            sa_relationship_kwargs={
                "cascade": "all, delete-orphan",
            }
        )

class MediaCreate(SQLModel):
    title: str
    description: Optional[str] = None
    media_type: str  # image / video / audio
    category_id: Optional[int] = None

class MediaStatusUpdate(SQLModel):
    id: int
    status: MediaStatus


