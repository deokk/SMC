from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from db.database import Base


class Friend(Base):
    __tablename__ = 'friends'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    friend_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationship to the User who initiated the friendship
    user = relationship("User", foreign_keys=[user_id], back_populates="friends")
    
    # Relationship to the User who was added as a friend
    friend_user = relationship("User", foreign_keys=[friend_id], back_populates="friend_of")

    # Ensure a user cannot add the same friend twice
    __table_args__ = (UniqueConstraint('user_id', 'friend_id', name='_user_friend_uc'),)

    def __repr__(self):
        return f"<Friend(user_id={self.user_id}, friend_id={self.friend_id})>"
