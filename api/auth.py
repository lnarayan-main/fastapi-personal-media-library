# backend/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import timedelta

from database import get_session
from services.auth_service import authenticate_user, create_access_token, get_password_hash
from services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES as _unused # keep consistent (not used)
from services.auth_service import oauth2_scheme  # imported to preserve previous behavior
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from schemas.auth import Token, LoginRequest
from models.user import User
from services.auth_service import get_password_hash as _get_password_hash  # alias to avoid name clash

router = APIRouter()

@router.post("/user/register", response_model=User, status_code=status.HTTP_201_CREATED)
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
    return db_user


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

    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expires = timedelta(days=30) if form_data.remember_me else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")
