from pydantic import BaseModel, EmailStr, Field

class ContactUsMessage(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Full name (2–50 characters)")
    email: EmailStr
    message: str = Field(..., min_length=10, max_length=1000, description="Message (10–1000 characters)")
