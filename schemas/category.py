from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryRead(CategoryBase):
    id: int
    status: str

    class Config:
        from_attributes = True


