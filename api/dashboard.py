from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from database import get_session
from services.auth_service import get_current_user
from models.category import Category
from models.media import Media, MediaStatus
from models.user import User, UserRole, UserStatus

router = APIRouter()

@router.post("/category/create", response_model=Category)
def create_category(
    category: Category,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    # Ensure category name is unique (per user or globally, adjust as needed)
    existing = session.exec(
        select(Category).where(Category.name == category.name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    session.add(category)
    session.commit()
    session.refresh(category)
    return category

@router.get("/admin-dashboard")
def admin_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    total_categories = session.exec(select(func.count(Category.id))).one()
    total_media = session.exec(select(func.count(Media.id)).where(Media.status == MediaStatus.ACTIVE)).one()
    total_users = session.exec(select(func.count(User.id)).where(User.role != UserRole.ADMIN).where(User.status == UserStatus.ACTIVE)).one()

    recent_media_statement = (
        select(Media)
        .where(Media.status == MediaStatus.ACTIVE)
        .order_by(Media.created_at.desc())
        .limit(5)
    )

    recent_media_result = session.exec(recent_media_statement).all()
    
    recent_users_statement = (
        select(User)
        .where(User.role != UserRole.ADMIN)
        .where(User.status == UserStatus.ACTIVE)
        .order_by(User.created_at.desc())
        .limit(5)
    )

    recent_users_result = session.exec(recent_users_statement).all()

    recent_users_statement = (
        select(User)
        .where(User.role != UserRole.ADMIN)
        .where(User.status == UserStatus.ACTIVE)
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



