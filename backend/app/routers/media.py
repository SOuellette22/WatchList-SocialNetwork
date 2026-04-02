import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.models.users import User
from backend.app.schemas.media import MovieDetail, SearchResponse, TVDetail
from backend.app.services import tmdb
from backend.app.services.auth import get_current_user

router = APIRouter(prefix="/api/media", tags=["media"])

def _http_error_to_http_exception(exc: httpx.HTTPStatusError):
    """Translate a TMDB error into a FastAPI HTTPException."""
    
    # Checks if the error type was user side and returns that 404 error
    if exc.response.status_code  == 404:
        raise HTTPException(
            status_code=404,
            detail="Not found on TMDB"
        )
    
    # Since not user side return 502 error for server side
    raise HTTPException(
        status_code=502,
        detail="TMDB request failed"
    )
    

@router.get("/search", response_model=SearchResponse)
def search_media(
    search_query: str = Query(min_length=1, description="Search query"),
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(get_current_user),
):
    """
    Search for movies and TV shows by name.
    
    Requires authentication so random internet traffic can't hammer TMDB via your key.
    
    Results are served from cache when available.
    """
    
    # This searches the TMDB API endpoint for movies/shows with matching keywords
    try:
        raw = tmdb.search(search_query, page=page)
    except httpx.HTTPStatusError as exc:
        _http_error_to_http_exception(exc) # error out if needed
        
    results = []
    for item in raw.get("results", []): # loop through list returned by endpoint
        
        # save off media type 'movie' or 'tv'
        media_type = item.get("media_type")
        
        # Check if it is one of the two excepted media types skip if not
        if media_type not in ("movie", "tv"):
            continue
        
        # add all the medias data to the list through a python dictionary
        results.append({
            "tmdb_id": item["id"],
            "media_type": media_type,
            "title": item.get("title") or item.get("name", ""),
            "overview": item.get("overview", ""),
            "poster_url": item.get("poster_url"),
            "release_date": item.get("release_date") or item.get("first_air_date"),
        })
        
    # After looping through al media return all the relevant media to the user
    return {
        "page": raw["page"],
        "total_results": raw["total_results"],
        "total_pages": raw["total_pages"],
        "results": results,
    }
    
@router.get("/movie/{tmdb_id}", response_model=MovieDetail)
def get_movie(
    tmdb_id: int,
    current_user: User = Depends(get_current_user),
):
    """Fetch full details for a movie by its TMDB ID. Served from cache when available."""
    
    # This searches the TMDB API endpoint for the movie that matched the given TMDB ID
    try:
        data = tmdb.get_movie(tmdb_id)
    except httpx.HTTPStatusError as exc:
        _http_error_to_http_exception(exc) # error out if not found

    # return that found tv show data to the user
    return {
        "tmdb_id": data["id"],
        "title": data["title"],
        "overview": data["overview"],
        "poster_url": data["poster_url"],
        "release_date": data.get("release_date"),
        "runtime": data.get("runtime"),
        "vote_average": data["vote_average"],
    }


@router.get("/tv/{tmdb_id}", response_model=TVDetail)
def get_tv_show(
    tmdb_id: int,
    current_user: User = Depends(get_current_user),
):
    """Fetch full details for a TV show by its TMDB ID. Served from cache when available."""
    
    # This searches the TMDB API endpoint for the tv show that matched the given TMDB ID
    try:
        data = tmdb.get_tv_show(tmdb_id)
    except httpx.HTTPStatusError as exc:
        _http_error_to_http_exception(exc) # error out if not found


    return {
        "tmdb_id": data["id"],
        "title": data["name"],
        "overview": data["overview"],
        "poster_url": data["poster_url"],
        "first_air_date": data.get("first_air_date"),
        "number_of_seasons": data.get("number_of_seasons", 0),
        "vote_average": data["vote_average"],
    }