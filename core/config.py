from pydantic_settings import BaseSettings
from pydantic import EmailStr
from typing import List

class Settings(BaseSettings):
    # 1️⃣ Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    # 2️⃣ JWT / Auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # 3️⃣ Uploads
    UPLOAD_DIR: str

    UPLOAD_MEDIA_DIR: str
    UPLOAD_PROFILE_DIR: str

    # 4️⃣ Admin seed
    ADMIN_EMAIL: EmailStr
    ADMIN_PASSWORD: str
    ADMIN_NAME: str

    # 5️⃣ Email config
    MAIL_USERNAME: EmailStr
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    USE_CREDENTIALS: bool

    # frontend origins
    FRONTEND_ORIGINS: List[str]

    OWNER_EMAIL: EmailStr

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # optional, for safety

settings = Settings()
