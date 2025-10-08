from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlmodel import Session, select
from datetime import timedelta

from database import get_session
from services.auth_service import authenticate_user, create_access_token, get_password_hash
from services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES as _unused # keep consistent (not used)
from services.auth_service import oauth2_scheme  # imported to preserve previous behavior
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from schemas.auth import Token, LoginRequest
from models.user import User, UserBase, UserStatus
from services.auth_service import get_password_hash as _get_password_hash  # alias to avoid name clash
import uuid

from core.mail import fast_mail
from fastapi_mail import MessageSchema

from models.auth import ForgotPasswordRequest, ResetPasswordRequest
from core.config import settings


router = APIRouter()

@router.post("/user/register", status_code=status.HTTP_201_CREATED)
def register_user(*, session: Session = Depends(get_session), user_in: dict):
    """
    NOTE: This endpoint keeps the original behavior where UserCreate is expected.
    To avoid accidental schema mismatch when migrating, this function accepts a dict
    and constructs User similarly to original main.py.

    If you prefer to strictly enforce Pydantic schema, swap `user_in: dict` -> `user_in: LoginRequest` or your UserCreate schema.
    """
    # We try to mimic original behavior while being a router
    email = user_in.get("email")
    password = user_in.get("password")
    name = user_in.get("name")
    about = user_in.get("about", None)

    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered."
        )

    hashed_password = _get_password_hash(password)

    # prepare user data (similar to original main.py)
    user_data = {
        "name": name,
        "email": email,
        "about": about
    }

    db_user = User(**user_data, hashed_password=hashed_password)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return {"message": "Registration successful"}


@router.post("/auth/login", response_model=Token)
def login_for_access_token(
    form_data: LoginRequest,
    session: Session = Depends(get_session),
):
    # ⚠️ OAuth2PasswordRequestForm still provides "username"
    # so treat it as "email"
    # email = form_data.username
    email = form_data.email

    user = authenticate_user(session, email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact admin.",
            # headers={"WWW-Authenticate": "Bearer"},
        )
    
    remember_me = getattr(form_data, "remember_me", False)

    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expires = timedelta(days=30) if remember_me else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")

@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    token = str(uuid.uuid4())
    user.reset_token = token
    session.add(user)
    session.commit()
    session.refresh(user)

    front_orgin_url = settings.FRONTEND_ORIGINS[0]

    reset_link = f"{front_orgin_url}/reset-password/{token}"
    html = f"""
    <h3>Password Reset Request</h3>
    <p>Click the link below to reset your password:</p>
    <a href="{reset_link}">{reset_link}</a>
    """

    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[payload.email],
        body=html,
        subtype="html"
    )

    await fast_mail.send_message(message)
    return {"message": "Password reset email sent successfully"}


@router.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest, session: Session = Depends(get_session)):
    print("######################33",request)
    user = session.exec(select(User).where(User.reset_token == request.token)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.hashed_password = _get_password_hash(request.new_password)  
    user.reset_token = None
    session.add(user)
    session.commit()
    return {"message": "Password reset successful"}

