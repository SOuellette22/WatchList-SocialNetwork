import httpx
from backend.app.config import settings
from backend.app.services.cache import TTLCache

_BASE_URL = "https://api.themoviedb.org/3"
_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # w500 = 500px wide poster

_detail_cache = TTLCache(ttl_seconds=86400)  # 24 hours — movie/TV metadata is stable
_search_cache = TTLCache(ttl_seconds=300)    # 5 minutes — search results change occasionally

def _headers() -> dict[str, str]:
    """Build the auth header's TMDB expects."""
    
    token = settings.tmdb_api_token.get_secret_value() # Gets the needed api secret
    
    # Returns the properly formatted authorization header
    return {"Authorization": f"Bearer {token}", "accept": "application/json"}

def _poster_url(path: str | None) -> str | None:
    """Convert a TMDB poster_path like '/abc.jpg' to a full URL."""

    # if the path does not exist return None
    if not path:
        return None
    
    # Return the file path if it exists
    return f"{_IMAGE_BASE}{path}"

def search(query: str, page: int = 1) -> dict:
    """
    Search for movies and TV shows by name.
    
    Return TMDB's raw multi-search response (results list + pagination info).
    Each result includes media_type: 'movie' | 'tv'.
    Results are cached for 5 minutes per (query, page) pair.
    """
    
    # Creates the syntax correct key and checks the cache for that key
    key = f"search:{query}:{page}"
    cached = _search_cache.get(key)
    
    # If the cache has it return the item that is in the cache
    if cached is not None:
        return cached
    
    # Query the TMDB API for the multi search with the inputted search
    response = httpx.get(
        f"{_BASE_URL}/search/multi",
        headers=_headers(),
        params={"query": query, "page": page, "include_adult": False},
    )
    response.raise_for_status()
    data = response.json()
    
    # Add the poster data to each row of the search result
    for item in data.get("results", []):
        item["poster_url"] = _poster_url(item.get("poster_path"))
        
    # Add the new data to the cache
    _search_cache.set(key, data)
    
    # Return the data
    return data

def get_movie(movie_id: int) -> dict:
    """
    Fetch full details for a single movie by its TMDB ID.
    Response is cached for 24 hours.
    """
    
    # Creates the syntax correct key and checks the cache for that key
    key = f"movie:{movie_id}"
    cached = _detail_cache.get(key)
    
    # If the cache has it return the item that is in the cache
    if cached is not None:
        return cached
    
    # Query the TMDB API and get the movie based on the movie id
    response = httpx.get(
        f"{_BASE_URL}/movie/{movie_id}",
        headers = _headers(),
    )
    response.raise_for_status()
    data = response.json()
    
    # Add the poster data to the data
    data["poster_url"] = _poster_url(data.get("poster_path"))
    
    # Add the movie to the cache
    _detail_cache.set(key, data)
    
    # Return the data
    return data

def get_tv_show(show_id: int) -> dict:
    """
    Fetch full detail for a single TV show by its TMDB ID.
    Response is cached for 24 hours.
    """
    
    # Creates the syntax correct key and checks the cache for that key
    key = f"tv:{show_id}"
    cached = _detail_cache.get(key)
    
    # If the cache has it return the item that is in the cache
    if cached is not None:
        return cached
    
    # Query the TMDB API and get the show based on the show id
    response = httpx.get(
        f"{_BASE_URL}/tv/{show_id}",
        headers=_headers(),
    )
    response.raise_for_status()
    data = response.json()
    
    # Add poster data to the data
    data["poster_url"] = _poster_url(data.get("poster_path"))
    
    # Add the data to the cache
    _detail_cache.set(key, data)
    
    # Return the data
    return data