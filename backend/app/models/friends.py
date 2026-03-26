import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, null
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"

class Friendship(Base):
    __tablename__ = "friendships"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requester_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    addressee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[FriendshipStatus] = mapped_column(Enum(FriendshipStatus), nullable=False, default=FriendshipStatus.pending)
    declined_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True, default=None)
    
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id",
                         name="uq_requester_addressee"),
    )