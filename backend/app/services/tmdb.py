import httpx
from backend.app.config import settings
from backend.app.services.cache import TTLCache

_BASE_URL = "https://api.themoviedb.org/3"
_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # w500 = 500px wide poster

_detail_cache = TTLCache(ttl_seconds=86400)  # 24 hours — movie/TV metadata is stable
_search_cache = TTLCache(ttl_seconds=300)    # 5 minutes — search results change occasionally

def _headers() -> dict[str, str]:
    """Build the auth header's TMDB expects."""
    token = settings.tmdb_api_token.get_secret_value()
    return {"Authorization": f"Bearer {token}", "accept": "application/json"}

def _poster_url(path: str | None) -> str | None:
    """Convert a TMDB poster_path like '/abc.jpg' to a full URL."""

    if not path:
        return None
    
    return f"{_IMAGE_BASE}{path}"

def search(query: str, page: int = 1) -> dict:
    """
    Search for movies and TV shows by name.
    
    Return TMDB's raw multi-search response (results list + pagination info).
    Each result includes media_type: 'movie' | 'tv'.
    Results are cached for 5 minutes per (query, page) pair.
    """
    key = f"search:{query}:{page}"
    cached = _search_cache.get(key)
    
    if cached is not None:
        return cached
    
    response = httpx.get(
        f"{_BASE_URL}/search/multi",
        headers=_headers(),
        params={"query": query, "page": page, "include_adult": False},
    )
    response.raise_for_status()
    data = response.json()
    
    for item in data.get("results", []):
        item["poster_url"] = _poster_url(item.get("poster_path"))
        
    _search_cache.set(key, data)
    
    return data

def get_movie(movie_id: int) -> dict:
    """
    Fetch full details for a single movie by its TMDB ID.
    Response is cached for 24 hours.
    """
    key = f"movie:{movie_id}"
    cached = _detail_cache.get(key)
    
    if cached is not None:
        return cached
    
    response = httpx.get(
        f"{_BASE_URL}/movie/{movie_id}",
        headers = _headers(),
    )
    
    response.raise_for_status()
    data = response.json()
    data["poster_url"] = _poster_url(data.get("poster_path"))
    
    _detail_cache.set(key, data)
    
    
    return data

def get_tv_show(show_id: int) -> dict:
    """
    Fetch full detail for a single TV show by its TMDB ID.
    Response is cached for 24 hours.
    """
    key = f"tv:{show_id}"
    cached = _detail_cache.get(key)
    
    if cached is not None:
        return cached
    
    response = httpx.get(
        f"{_BASE_URL}/tv/{show_id}",
        headers=_headers(),
    )
    
    response.raise_for_status()
    data = response.json()
    data["poster_url"] = _poster_url(data.get("poster_path"))
    
    _detail_cache.set(key, data)
    
    return data