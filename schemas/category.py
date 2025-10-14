from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryRead(CategoryBase):
    id: int
    status: str

    class Config:
        from_attributes = True


