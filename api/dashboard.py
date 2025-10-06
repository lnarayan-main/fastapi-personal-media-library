from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload 

from database import get_session
from services.auth_service import get_current_user
from models.category import Category
from models.media import Media, MediaStatus
from models.user import User, UserRole, UserStatus
from schemas.dashboard import DashboardPayload

router = APIRouter()

@router.get("/dashboard", response_model=DashboardPayload)
def admin_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN:
        total_categories = session.exec(select(func.count(Category.id))).one()
        total_media = session.exec(
            select(func.count(Media.id))
            # .where(Media.status == MediaStatus.ACTIVE)
            ).one()
        total_users = session.exec(
            select(func.count(User.id))
            .where(User.role != UserRole.ADMIN)
            # .where(User.status == UserStatus.ACTIVE)
            ).one()

        recent_media_statement = (
            select(Media)
            # .where(Media.status == MediaStatus.ACTIVE)
            .options(selectinload(Media.category))
            .order_by(Media.created_at.desc())
            .limit(5)
        )

        recent_media_result = session.exec(recent_media_statement).all()
        
        recent_users_statement = (
            select(User)
            .where(User.role != UserRole.ADMIN)
            # .where(User.status == UserStatus.ACTIVE)
            .order_by(User.created_at.desc())
            .limit(5)
        )

        recent_users_result = session.exec(recent_users_statement).all()

        return {
            "total_categories": total_categories,
            "total_media": total_media,
            "total_users": total_users,
            "recent_users": recent_users_result,
            "recent_media": recent_media_result
        }

    elif current_user.role == UserRole.USER:
        total_media = session.exec(
            select(func.count(Media.id))
            .where(Media.owner_id == current_user.id)
            # .where(Media.status == MediaStatus.ACTIVE)
            ).one()

        recent_media_statement = (
            select(Media)
            # .where(Media.status == MediaStatus.ACTIVE)
            .where(Media.owner_id == current_user.id)
            .options(selectinload(Media.category))
            .order_by(Media.created_at.desc())
            .limit(5)
        )

        recent_media_result = session.exec(recent_media_statement).all()

        return {
            "total_media": total_media,
            "recent_media": recent_media_result
        }


@router.get("/user-dashboard", response_model=DashboardPayload)
def admin_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    total_media = session.exec(select(func.count(Media.id)).where(Media.owner_id == current_user.id).where(Media.status == MediaStatus.ACTIVE)).one()

    recent_media_statement = (
        select(Media)
        .where(Media.status == MediaStatus.ACTIVE)
        .where(Media.owner_id == current_user.id)
        .options(selectinload(Media.category))
        .order_by(Media.created_at.desc())
        .limit(5)
    )

    recent_media_result = session.exec(recent_media_statement).all()

    return {
        "total_media": total_media,
        "recent_media": recent_media_result
    }



