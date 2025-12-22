from sqlalchemy.orm import Session
from ..models.friend import Friend
from ..models.user import User

def get_friends(db: Session, user_id: int) -> list[User]:
    """
    Retrieve a list of friend User objects for a given user.
    """
    # Get all Friend objects where the current user is the initiator
    friend_relationships = db.query(Friend).filter(Friend.user_id == user_id).all()
    # Extract the actual User object from the 'friend_user' relationship
    friends = [relationship.friend_user for relationship in friend_relationships]
    return friends

def add_friend(db: Session, user_id: int, friend_id: int) -> Friend:
    """
    Create a new friendship record in the database.
    """
    if user_id == friend_id:
        raise ValueError("Cannot add yourself as a friend.")
        
    db_friendship = Friend(user_id=user_id, friend_id=friend_id)
    db.add(db_friendship)
    db.commit()
    db.refresh(db_friendship)
    return db_friendship

def check_if_friends(db: Session, user_id: int, friend_id: int) -> bool:
    """
    Check if a friendship already exists between two users.
    """
    return db.query(Friend).filter(Friend.user_id == user_id, Friend.friend_id == friend_id).first() is not None
