from pydantic import BaseModel, ConfigDict, Field

class WatchlistEntryCreate(BaseModel):
    tmdb_id: int
    media_type: str
    
    
# TODO add the class that will take in the users emoji for the rating

class WatchlistEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tmdb_id: int
    media_type: str
    list_type: str
    
    # TODO add emoji support to this part of the schema
    
class WatchlistOut(BaseModel):
    want_to_watch: list[WatchlistEntryOut]
    watched: list[WatchlistEntryOut]