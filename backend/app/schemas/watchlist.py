from pydantic import BaseModel, ConfigDict, field_validator

SUGGESTED_EMOJIS: list[str] = ["🔥", "😂", "💩", "😢", "😍"]

class WatchlistEntryCreate(BaseModel):
    tmdb_id: int
    media_type: str     # 'movie' or 'tv'
    
    
# TODO add the class that will take in the users emoji for the rating

class WatchlistEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tmdb_id: int
    media_type: str     # 'movie or 'tv'
    list_type: str      # 'want-to-watch' or 'watched'
    emoji: str | None = None
    
class WatchlistOut(BaseModel):
    want_to_watch: list[WatchlistEntryOut]
    watched: list[WatchlistEntryOut]
    
class FriendEmoji(BaseModel):  # NEW
    model_config = ConfigDict(from_attributes=True)

    username: str
    emoji: str


class WatchlistEntryWithFriendEmojis(WatchlistEntryOut):  # NEW
    friend_emojis: list[FriendEmoji] = []
    
class EmojiRatingCreate(BaseModel):  # NEW
    tmdb_id: int
    media_type: str
    emoji: str

    @field_validator("emoji")
    @classmethod
    def must_be_valid_emoji(cls, v: str) -> str:
        if len(v.strip()) == 0:
            raise ValueError("emoji cannot be empty")
        if len(v) > 10:
            raise ValueError("emoji value too long")
        return v.strip()


class EmojiRatingOut(BaseModel):  # NEW
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    tmdb_id: int
    media_type: str
    emoji: str


class EmojiCount(BaseModel):  # NEW
    emoji: str
    count: int