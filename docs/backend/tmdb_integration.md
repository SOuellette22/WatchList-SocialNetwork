# TMDB Integration

This document explains how WatchTogether integrates with The Movie Database (TMDB) API to fetch movie and TV show metadata.

---

## Overview

TMDB provides the media catalog — WatchTogether does not store movie or TV show records locally. All media data is fetched on demand from TMDB's REST API and served to clients through three `/api/media` endpoints. An in-process TTL cache sits between the API and TMDB to reduce outbound requests.

All media endpoints require authentication so that random internet traffic cannot exhaust the TMDB API key.

---

## Configuration

TMDB access uses a **Bearer token** (TMDB API Read Access Token), not the older API key style. The token is stored as a secret in the app config and loaded from the environment.

| Config key | Description |
| --- | --- |
| `tmdb_api_token` | TMDB API Read Access Token (stored as `SecretStr`) |

Set this in your `.env` file:
```
TMDB_API_TOKEN=your_token_here
```

The token is read by `settings.tmdb_api_token.get_secret_value()` in `backend/app/services/tmdb.py`.

---

## Caching

Two in-process `TTLCache` instances handle caching (defined in `backend/app/services/cache.py`):

| Cache | TTL | Used for |
| --- | --- | --- |
| `_detail_cache` | 24 hours | Movie and TV show detail lookups by TMDB ID |
| `_search_cache` | 5 minutes | Search results, keyed by `(query, page)` |

Movie and TV metadata changes infrequently, so detail responses are cached aggressively. Search results are kept shorter to reflect new releases.

Cache keys follow the pattern:
- Search: `search:<query>:<page>`
- Movie detail: `movie:<tmdb_id>`
- TV detail: `tv:<tmdb_id>`

The cache is **in-process only** — it is not shared across multiple server instances and does not survive restarts.

---

## TMDB Service Layer

`backend/app/services/tmdb.py` wraps all TMDB HTTP calls.

### `search(query, page=1)`

Calls `GET /search/multi` on TMDB. Returns movies and TV shows together, filtered to `media_type: movie | tv` by the router layer. Adds a `poster_url` field to each result.

### `get_movie(movie_id)`

Calls `GET /movie/{id}` on TMDB. Returns full movie metadata including runtime and vote average. Adds `poster_url`.

### `get_tv_show(show_id)`

Calls `GET /tv/{id}` on TMDB. Returns full TV show metadata including number of seasons and vote average. Adds `poster_url`.

### Poster URLs

TMDB returns poster paths like `/abc123.jpg`. The service converts these to full URLs using the `w500` image size:
```
https://image.tmdb.org/t/p/w500/abc123.jpg
```

If `poster_path` is null, `poster_url` is set to `null`.

---

## Endpoints

All endpoints require a valid bearer token (`Authorization: Bearer <token>`).

### `GET /api/media/search?q=<query>&page=<page>`

Search for movies and TV shows by name.

**Query parameters:**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `q` | string | required | Search term (min length 1) |
| `page` | integer | 1 | Page number (min 1) |

**Success:** `200 OK`

```json
{
  "page": 1,
  "total_results": 42,
  "total_pages": 3,
  "results": [
    {
      "tmdb_id": 550,
      "media_type": "movie",
      "title": "Fight Club",
      "overview": "...",
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "release_date": "1999-10-15"
    }
  ]
}
```

Results with `media_type` values other than `movie` or `tv` (e.g. `person`) are filtered out before the response is returned.

---

### `GET /api/media/movie/{tmdb_id}`

Fetch full details for a movie by its TMDB ID.

**Success:** `200 OK`

```json
{
  "tmdb_id": 550,
  "title": "Fight Club",
  "overview": "...",
  "poster_url": "https://image.tmdb.org/t/p/w500/...",
  "release_date": "1999-10-15",
  "runtime": 139,
  "vote_average": 8.4
}
```

**Note:** `runtime` is in minutes.

---

### `GET /api/media/tv/{tmdb_id}`

Fetch full details for a TV show by its TMDB ID.

**Success:** `200 OK`

```json
{
  "tmdb_id": 1396,
  "title": "Breaking Bad",
  "overview": "...",
  "poster_url": "https://image.tmdb.org/t/p/w500/...",
  "first_air_date": "2008-01-20",
  "number_of_seasons": 5,
  "vote_average": 9.5
}
```

---

## Error Handling

TMDB HTTP errors are caught in the router and translated to appropriate FastAPI responses:

| TMDB status | Response to client |
| --- | --- |
| `404 Not Found` | `404 Not Found` — "Not found on TMDB" |
| Any other error | `502 Bad Gateway` — "TMDB request failed" |

---

## Where to Look in the Code

| Concern | File |
| --- | --- |
| TMDB HTTP calls and caching | `backend/app/services/tmdb.py` |
| TTL cache implementation | `backend/app/services/cache.py` |
| API route handlers | `backend/app/routers/media.py` |
| Response schemas | `backend/app/schemas/media.py` |
| Config (TMDB token) | `backend/app/config.py` |
