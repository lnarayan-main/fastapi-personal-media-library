from pydantic import BaseModel

class LikeDisLikeRequest(BaseModel):
    is_like: bool

class ReplyRequest(BaseModel):
    content: str

class CommentReactionsData(BaseModel):
    id: int
    user_id: int
    comment_id: int
    is_like: bool

    class Config:
        from_attributes = True 