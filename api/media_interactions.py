from fastapi import APIRouter, status, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models.user import User
from models.media_interaction import Comment, MediaReaction
from services.auth_service import get_current_user
from schemas.media_interaction import LikeDisLikeRequest, CommentRequest
from schemas.media_response import CommentResponse
from typing import List

router = APIRouter()

@router.post('/media/{media_id}/comments', status_code=status.HTTP_201_CREATED)
def add_comment(media_id: int, payload: CommentRequest, session: Session = Depends(get_session), current_user: User = Depends(get_current_user) ):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty.")
    
    comment = Comment(user_id = current_user.id, media_id=media_id, content=payload.content)
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return {'message': "Comment added successfully."}

@router.get('/media/{media_id}/comments', response_model=List[CommentResponse])
def get_comments(media_id: int, session: Session = Depends(get_session)):
    comments = session.exec(select(Comment).where(Comment.media_id == media_id).order_by(Comment.created_at.desc())).all()
    return comments


@router.post('/media/{media_id}/reaction')
def toggle_reaction(media_id: int, payload: LikeDisLikeRequest, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    existing = session.exec(
        select(MediaReaction).where(
            MediaReaction.media_id == media_id,
            MediaReaction.user_id == current_user.id
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
        reaction = MediaReaction(user_id = current_user.id, media_id=media_id, is_like=payload.is_like)
        session.add(reaction)
        session.commit()
        return {"message": "Reaction added"}
    

@router.get("/media/{media_id}/reactions")
def get__reaction_counts(media_id: int, session: Session = Depends(get_session)):
    likes = session.exec(select(MediaReaction).where(MediaReaction.media_id == media_id, MediaReaction.is_like == True)).all()
    dislikes = session.exec(select(MediaReaction).where(MediaReaction.media_id == media_id, MediaReaction.is_like == False)).all()
    return {"likes": len(likes), "dislikes": len(dislikes)}
