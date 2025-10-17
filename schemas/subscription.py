from pydantic import BaseModel

class ReadSubscription(BaseModel):
    id: int
    subscriber_id: int
    creator_id: int

    class Config:
        from_attributes = True 