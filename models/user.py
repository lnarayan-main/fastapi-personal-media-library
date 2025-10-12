from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum as PyEnum
from datetime import datetime

# Token/TokenData were previously in models.py; keep Token/TokenData in schemas/auth.py now
# (we will use Pydantic for tokens in schemas). Keep user models here.

# --- User Role Enum ---
class UserRole(str, PyEnum):
    USER = "user"
    ADMIN = "admin"

# --- Enums for status field ---
class UserStatus(PyEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING_VERIFICATION = 'pending'

class UserBase(SQLModel):
    name: str = Field(min_length=3, max_length=100)
    email: str = Field(unique=True, index=True, max_length=100)
    status: UserStatus = Field(default=UserStatus.ACTIVE, sa_column_kwargs={"default": UserStatus.ACTIVE})
    role: UserRole = Field(default=UserRole.USER)
    profile_pic_url: Optional[str] = None
    about: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=32)

class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    media: List["Media"] = Relationship(back_populates="owner")
    reset_token: Optional[str] = None
    reset_token_expires_at: Optional[datetime] = None
    comments: List["Comment"] = Relationship(back_populates="owner")

class UserRead(UserBase):
    id: int
    role: UserRole
    created_at : datetime

class UserUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[UserStatus] = None
    about: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)

class UserStatusUpdate(SQLModel):
    id: int
    status: UserStatus
