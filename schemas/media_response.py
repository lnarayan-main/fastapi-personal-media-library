from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from schemas.media import MediaRead
from schemas.user import UserRead
from schemas.comment_interaction import CommentReactionsData

class CommentResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime
    user: Optional[UserRead] = None
    reactions: List[CommentReactionsData] = None

    class Config:
        from_attributes = True 

class MediaReactionSummary(BaseModel):
    likes: int
    dislikes: int
    
    class Config:
        from_attributes = True 

class MediaResponse(BaseModel):
    media: MediaRead
    reactions: MediaReactionSummary
    comments: List[CommentResponse]

    class Config:
        from_attributes = True 


