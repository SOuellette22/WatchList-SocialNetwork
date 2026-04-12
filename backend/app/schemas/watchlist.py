from pydantic import BaseModel, ConfigDict

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