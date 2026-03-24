from pydantic import BaseModel, ConfigDict

from backend.app.models import friends
from backend.app.schemas.users import UserPublic

class FriendListOut(BaseModel):
    friends: list[UserPublic]
    total: int
    
class FriendRequestOut(BaseModel):
    """Represents a pending incoming friend request"""
    
    model_config = ConfigDict(from_attributes=True)
    
    requester: UserPublic