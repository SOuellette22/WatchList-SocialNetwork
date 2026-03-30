from pydantic import BaseModel

class MediaSummary(BaseModel):
    """Compact representation used in search results."""

    tmdb_is: int
    media_type: str           # 'movie' or 'tv'
    title: str
    overview: str
    poster_url: str | None
    release_date: str | None  # "YYYY-MM-DD" or None
    
class MovieDetail(BaseModel):
    """Full movie detail response."""
    tmdb_id: int
    title: str
    overview: str
    poster_url: str | None
    release_date: str | None
    runtime: int | None      # This will be in minutes
    vote_average: float


class TVDetail(BaseModel):
    """Full TV show detail response."""
    tmdb_id: int
    title: str
    overview: str
    poster_url: str | None
    first_air_date: str | None
    number_of_seasons: int
    vote_average: float


class SearchResponse(BaseModel):
    """Paginated search results."""
    page: int
    total_results: int
    total_pages: int
    results: list[MediaSummary]