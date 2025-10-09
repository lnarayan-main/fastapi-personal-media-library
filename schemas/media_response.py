from pydantic import BaseModel
from typing import List
from datetime import datetime
from schemas.media import MediaRead

class CommentResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime

class MediaReactionSummary(BaseModel):
    likes: int
    dislikes: int

class MediaResponse(BaseModel):
    media: MediaRead
    reactions: MediaReactionSummary
    comments: List[CommentResponse]


