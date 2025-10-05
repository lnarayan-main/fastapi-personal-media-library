from sqlmodel import SQLModel
from typing import List, Optional
from schemas.media import MediaRead
from schemas.user import UserRead


class DashboardPayload(SQLModel):
    total_categories: Optional[int] = None
    total_users: Optional[int] = None
    total_media: int  # This one is still required
    recent_users: Optional[List[UserRead]] = None
    recent_media: List[MediaRead]  # This one is still required
    
    class Config:
        from_attributes = True