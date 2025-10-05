# backend/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models.user import UserRole, UserStatus

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
    created_at: datetime
    
    class Config:
        # ⭐️ ADD THIS LINE ⭐️
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    about: Optional[str] = None
    password: Optional[str] = None
