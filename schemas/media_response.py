from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from schemas.media import MediaRead
from schemas.user import UserRead

class CommentResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime
    owner: Optional[UserRead] = None

class MediaReactionSummary(BaseModel):
    likes: int
    dislikes: int

class MediaResponse(BaseModel):
    media: MediaRead
    reactions: MediaReactionSummary
    comments: List[CommentResponse]


