from fastapi import APIRouter, status, HTTPException, Depends
from database import get_session
from sqlmodel import Session, select
from models.user import User
from services.auth_service import get_current_user
from schemas.comment_interaction import LikeDisLikeRequest
from models.comment_interaction import CommentReaction, CommentReply

router = APIRouter()

@router.post("/comment/{comment_id}/reaction")
def toggle_reaction(comment_id: int, payload: LikeDisLikeRequest, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    existing = session.exec(
        select(CommentReaction).where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id
        )
    ).first()

    if existing:
        if existing.is_like == payload.is_like:
            session.delete(existing)
            session.commit()
            return {"message": "Reaction removed"}
        else:
            existing.is_like = payload.is_like
            session.add(existing)
            session.commit()
            return {"message": "Reaction updated"}
    else:
        reaction = CommentReaction(user_id = current_user.id, comment_id=comment_id, is_like=payload.is_like)
        session.add(reaction)
        session.commit()
        return {"message": "Reaction added"}
    

@router.get("/comment/{comment_id}/reactions")
def get__reaction_counts(comment_id: int, session: Session = Depends(get_session)):
    likes = session.exec(select(CommentReaction).where(CommentReaction.comment_id == comment_id, CommentReaction.is_like == True)).all()
    dislikes = session.exec(select(CommentReaction).where(CommentReaction.comment_id == comment_id, CommentReaction.is_like == False)).all()
    return {"likes": len(likes), "dislikes": len(dislikes)}