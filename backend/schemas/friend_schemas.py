from pydantic import BaseModel
from typing import List
from datetime import datetime
from .user_schemas import UserResponse # Return user info without password

class FriendBase(BaseModel):
    friend_username: str

class FriendCreate(FriendBase):
    pass

class Friend(BaseModel):
    id: int
    user_id: int
    friend_id: int

    class Config:
        from_attributes = True

# For the response, we probably want to return the user details of the friends
# So we can define a response model that is a list of users.
class FriendListResponse(BaseModel):
    friends: List[UserResponse]

class FriendLocation(BaseModel):
    username: str
    latitude: float
    longitude: float
    timestamp: datetime
