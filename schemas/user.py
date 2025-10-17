from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models.user import UserRole, UserStatus
from sqlmodel import SQLModel, Field
from schemas.subscription import ReadSubscription

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    about: Optional[str] = None

class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    about: Optional[str] = None
    profile_pic_url: Optional[str] = None
    background_pic_url: Optional[str] = None
    created_at: datetime
    subscribers: Optional[List[ReadSubscription]] = None
    
    class Config:
        # ⭐️ ADD THIS LINE ⭐️
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    about: Optional[str] = None
    password: Optional[str] = None

class PaginatedUsers(SQLModel):
    items: List[UserRead] = Field(description="The list of users for the current page.")
    page: int = Field(description="The current page number (1-based).")
    size: int = Field(description="The number of items per page.")
    total_count: int = Field(description="Total number of users matching the filter.")
    total_pages: int
