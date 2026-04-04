import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base

class ListType(str, enum.Enum):
    want_to_watch = "want_to_watch"
    watched = "watched"

class MediaType(str, enum.Enum):
    movie = "movie"
    tv = "tv"

class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    list_type: Mapped[ListType] = mapped_column(Enum(ListType), nullable=False)
    
    # TODO add in the emoji rating stuff
    
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name = "uq_user_media"),
    )
    