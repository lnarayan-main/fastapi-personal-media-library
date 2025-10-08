from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from services.auth_service import get_current_user
from models.category import Category

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

@router.get("/category/list", response_model=list[Category])
def list_categories(
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_user),
):
    categories = session.exec(
        select(Category)).all()
    return categories

@router.put("/category/update/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    updated_category: Category,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    category.name = updated_category.name
    category.description = updated_category.description
    category.status = updated_category.status
    session.add(category)
    session.commit()
    session.refresh(category)
    return category

@router.delete("/category/delete/{category_id}")
def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    session.delete(category)
    session.commit()
    return {"message": "Category deleted successfully"}
