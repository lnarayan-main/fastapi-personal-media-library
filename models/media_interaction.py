from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum as PyEnum
from datetime import datetime

class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    media_id: int = Field(foreign_key="media.id")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    media: Optional["Media"] = Relationship(back_populates="comments")
    owner: Optional["User"] = Relationship(back_populates="comments")


class MediaReaction(SQLModel, table=True):
    __tablename__ = "media_reactions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    media_id: int = Field(foreign_key="media.id")
    is_like: bool

    media: Optional["Media"] = Relationship(back_populates="reactions")

