from typing import Optional
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from models.user import User

class Subscription(SQLModel, table=True):
    """
    Represents a subscription relationship between two users.
    This acts as the Association Object (or link table) for the self-referencing
    many-to-many relationship on the User table.
    """
    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign Key for the user who is subscribing (the follower)
    subscriber_id: int = Field(foreign_key="users.id", index=True)
    
    # Foreign Key for the user who is being subscribed to (the creator/channel)
    creator_id: int = Field(foreign_key="users.id", index=True)

    # relationship
    # The 'subscriber' who initiated the follow
    subscriber: User = Relationship(back_populates="subscriptions", sa_relationship_kwargs={"foreign_keys": "[Subscription.subscriber_id]"})
    
    # The 'creator' who is being followed
    creator: User = Relationship(back_populates="subscribers", sa_relationship_kwargs={"foreign_keys": "[Subscription.creator_id]"})
    
    # Constraint to ensure a user can only subscribe to a creator once
    __table_args__ = (UniqueConstraint("subscriber_id", "creator_id", name="unique_subscription"),)
