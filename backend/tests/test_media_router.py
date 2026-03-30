import httpx
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Shared test payloads
# ---------------------------------------------------------------------------

MOVIE_PAYLOAD = {
    "id": 550,
    "title": "Fight Club",
    "overview": "An insomniac office worker...",
    "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "poster_url": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "release_date": "1999-10-15",
    "runtime": 139,
    "vote_average": 8.4,
}

TV_PAYLOAD = {
    "id": 1396,
    "name": "Breaking Bad",
    "overview": "A chemistry teacher turned drug manufacturer...",
    "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
    "poster_url": "https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
    "first_air_date": "2008-01-20",
    "number_of_seasons": 5,
    "vote_average": 8.9,
}

SEARCH_PAYLOAD = {
    "page": 1,
    "total_results": 1,
    "total_pages": 1,
    "results": [
        {
            "id": 550,
            "media_type": "movie",
            "title": "Fight Club",
            "overview": "An insomniac office worker...",
            "poster_url": "https://image.tmdb.org/t/p/w500/abc.jpg",
            "release_date": "1999-10-15",
        }
    ],
}


def _tmdb_error(status_code: int) -> httpx.HTTPStatusError:
    """Build a fake httpx.HTTPStatusError with the given status code."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    return httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

def test_search_requires_auth(client):
    response = client.get("/api/media/search?q=fight+club")
    assert response.status_code == 401


def test_search_empty_query_rejected(client, auth_headers):
    # q has min_length=1 — empty string should be rejected before hitting TMDB
    response = client.get("/api/media/search?q=", headers=auth_headers)
    assert response.status_code == 422


def test_search_returns_results(client, auth_headers):
    with patch("backend.app.routers.media.tmdb.search", return_value=SEARCH_PAYLOAD):
        response = client.get("/api/media/search?q=fight+club", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert data["results"][0]["title"] == "Fight Club"
    assert data["results"][0]["tmdb_id"] == 550


def test_search_filters_out_person_results(client, auth_headers):
    # TMDB multi-search returns people too — the router should silently drop them
    payload = {
        "page": 1,
        "total_results": 2,
        "total_pages": 1,
        "results": [
            {
                "id": 550,
                "media_type": "movie",
                "title": "Fight Club",
                "overview": "",
                "poster_url": None,
                "release_date": "1999-10-15",
            },
            {
                "id": 819,
                "media_type": "person",
                "name": "Edward Norton",
                "poster_url": None,
            },
        ],
    }
    with patch("backend.app.routers.media.tmdb.search", return_value=payload):
        response = client.get("/api/media/search?q=norton", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["media_type"] == "movie"


def test_search_tmdb_404_returns_404(client, auth_headers):
    with patch(
        "backend.app.routers.media.tmdb.search",
        side_effect=_tmdb_error(404),
    ):
        response = client.get("/api/media/search?q=nothing", headers=auth_headers)
    assert response.status_code == 404


def test_search_tmdb_error_returns_502(client, auth_headers):
    with patch(
        "backend.app.routers.media.tmdb.search",
        side_effect=_tmdb_error(500),
    ):
        response = client.get("/api/media/search?q=nothing", headers=auth_headers)
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# Movie detail tests
# ---------------------------------------------------------------------------

def test_get_movie_requires_auth(client):
    response = client.get("/api/media/movie/550")
    assert response.status_code == 401


def test_get_movie(client, auth_headers):
    with patch("backend.app.routers.media.tmdb.get_movie", return_value=MOVIE_PAYLOAD):
        response = client.get("/api/media/movie/550", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Fight Club"
    assert data["tmdb_id"] == 550
    assert data["runtime"] == 139
    assert data["vote_average"] == 8.4
    assert "poster_url" in data


def test_get_movie_not_found(client, auth_headers):
    with patch(
        "backend.app.routers.media.tmdb.get_movie",
        side_effect=_tmdb_error(404),
    ):
        response = client.get("/api/media/movie/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_movie_tmdb_error_returns_502(client, auth_headers):
    with patch(
        "backend.app.routers.media.tmdb.get_movie",
        side_effect=_tmdb_error(500),
    ):
        response = client.get("/api/media/movie/550", headers=auth_headers)
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# TV show detail tests
# ---------------------------------------------------------------------------

def test_get_tv_show_requires_auth(client):
    response = client.get("/api/media/tv/1396")
    assert response.status_code == 401


def test_get_tv_show(client, auth_headers):
    with patch("backend.app.routers.media.tmdb.get_tv_show", return_value=TV_PAYLOAD):
        response = client.get("/api/media/tv/1396", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Breaking Bad"
    assert data["tmdb_id"] == 1396
    assert data["number_of_seasons"] == 5
    assert data["vote_average"] == 8.9
    assert "poster_url" in data


def test_get_tv_show_not_found(client, auth_headers):
    with patch(
        "backend.app.routers.media.tmdb.get_tv_show",
        side_effect=_tmdb_error(404),
    ):
        response = client.get("/api/media/tv/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_tv_show_tmdb_error_returns_502(client, auth_headers):
    with patch(
        "backend.app.routers.media.tmdb.get_tv_show",
        side_effect=_tmdb_error(500),
    ):
        response = client.get("/api/media/tv/1396", headers=auth_headers)
    assert response.status_code == 502
