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
    user: Optional["User"] = Relationship(back_populates="comments")

    replies: List["CommentReply"] = Relationship(
            back_populates="comment",
            sa_relationship_kwargs={
                "cascade": "all, delete-orphan",
            }    
        )

    reactions: List["CommentReaction"] = Relationship(
            back_populates="comment",
            sa_relationship_kwargs={
                "cascade": "all, delete-orphan",
            }
        )



class MediaReaction(SQLModel, table=True):
    __tablename__ = "media_reactions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    media_id: int = Field(foreign_key="media.id")
    is_like: bool

    user: Optional["User"] = Relationship(back_populates="media_reactions")
    media: Optional["Media"] = Relationship(back_populates="reactions")

