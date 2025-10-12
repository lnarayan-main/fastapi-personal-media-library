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

    # Relationships
    category: Optional["Category"] = Relationship(back_populates="media")
    user: Optional["User"] = Relationship(back_populates="media")

    comments: List["Comment"] = Relationship(back_populates="media")
    reactions: List["MediaReaction"] = Relationship(back_populates="media")

    views: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MediaCreate(SQLModel):
    title: str
    description: Optional[str] = None
    media_type: str  # image / video / audio
    category_id: Optional[int] = None

class MediaRead(SQLModel):
    id: int
    title: str
    description: Optional[str]
    media_type: str
    file_url: str
    thumbnail_url: Optional[str]
    owner_id: int
    category_id: Optional[int]
    category: Optional[CategoryRead] = None 
    created_at: datetime
    status: MediaStatus
    views: int

class MediaStatusUpdate(SQLModel):
    id: int
    status: MediaStatus


