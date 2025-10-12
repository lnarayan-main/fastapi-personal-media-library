from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum as PyEnum
from datetime import datetime

class CommentReply(SQLModel, table=True):
    __tablename__ = "comment_replies"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    comment_id: int = Field(foreign_key="comments.id")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    comment: Optional["Comment"] = Relationship(back_populates="replies")
    user: Optional["User"] = Relationship(back_populates="comment_replies")
    


class CommentReaction(SQLModel, table=True):
    __tablename__ = "comment_reactions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    comment_id: int = Field(foreign_key="comments.id")
    is_like: bool

    comment: Optional["Comment"] = Relationship(back_populates="reactions")
    user: Optional["User"] = Relationship(back_populates="comment_reactions")

