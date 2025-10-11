from pydantic import BaseModel

class LikeDisLikeRequest(BaseModel):
    is_like: bool

class CommentRequest(BaseModel):
    content: str