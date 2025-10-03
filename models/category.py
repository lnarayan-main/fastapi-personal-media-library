# backend/models/category.py
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum as PyEnum

class CategoryStatus(PyEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    status: CategoryStatus = Field(default=CategoryStatus.ACTIVE, sa_column_kwargs={"default": CategoryStatus.ACTIVE})
    description: Optional[str] = None

    # Reverse relationship: all media items in this category
    media_items: List["Media"] = Relationship(back_populates="category")
