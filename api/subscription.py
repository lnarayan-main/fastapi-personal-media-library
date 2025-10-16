from fastapi import FastAPI, HTTPException, APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from services.auth_service import get_current_user
from models.user import User
from models.subscription import Subscription

router = APIRouter()

@router.post("/user/{user_id}/subscribe")
def user_subscribe(user_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    existSubscription = session.exec(select(Subscription).where(Subscription.subscriber_id == current_user.id)).first()
    if existSubscription:
        session.delete(existSubscription)
        session.commit()
        return {'message': "Unsubscribed successfully."}
    else:
        subscription = Subscription(subscriber_id=current_user.id, creator_id = user_id)
        session.add(subscription)
        session.commit()
        return {'message': "Subscribed successfully."}