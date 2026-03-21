from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base

## This is the sqlachemy model that allows for easy access of the sqlite database
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    pass_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # This is the field for the users profile picture
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None
    )

    @property
    def image_path(self) -> str:
        """Gets the users profile picture or gets the default profile picture."""
        
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"
        return "/static/profile_pics/default.jpg"
