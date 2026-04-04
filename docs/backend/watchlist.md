# Watchlist

This document covers how watchlist entries are stored, validated, and exposed through the API in WatchTogether. Each user has two lists: **want-to-watch** and **watched**. An item (identified by its TMDB id + media type) can only appear on one list at a time.

---

## Overview

A `WatchlistEntry` ties a user to a specific piece of media from TMDB. The same row is reused when an item moves between lists — so the entry id stays stable if, for example, a movie is promoted from want-to-watch to watched.

A user's lists are public. Any visitor can fetch another user's watchlist by username without logging in.

---

## Data Model

**Table:** `watchlist_entries`

| Column | Type | Description |
| --- | --- | --- |
| `id` | integer | Primary key, auto-incremented |
| `user_id` | integer (FK → `users.id`) | Owner of the entry |
| `tmdb_id` | integer | TMDB identifier for the movie or show |
| `media_type` | enum (`movie`, `tv`) | Whether the item is a movie or TV show |
| `list_type` | enum (`want_to_watch`, `watched`) | Which list the item currently sits on |

### Unique constraint

`(user_id, tmdb_id, media_type)` — a user can have at most one row per piece of media. Moving an item between lists updates `list_type` in place rather than inserting a second row.

---

## Schemas

### `WatchlistEntryCreate`
Accepted in the request body when adding an item to either list.

| Field | Type | Description |
| --- | --- | --- |
| `tmdb_id` | integer | TMDB id of the movie or show |
| `media_type` | string | `"movie"` or `"tv"` |

### `WatchlistEntryOut`
Returned when an individual entry is created or updated.

| Field | Type | Description |
| --- | --- | --- |
| `id` | integer | Entry id |
| `tmdb_id` | integer | TMDB id |
| `media_type` | string | `"movie"` or `"tv"` |
| `list_type` | string | `"want_to_watch"` or `"watched"` |

### `WatchlistOut`
Returned when fetching a user's full watchlist. The two lists are separated.

| Field | Type | Description |
| --- | --- | --- |
| `want_to_watch` | list of `WatchlistEntryOut` | Items the user wants to watch |
| `watched` | list of `WatchlistEntryOut` | Items the user has watched |

---

## Endpoints

### `GET /api/watchlist/`

Return the authenticated user's own watchlist.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success:** `200 OK` — returns `WatchlistOut`.

**Errors:**

| Status | Reason |
| --- | --- |
| `401 Unauthorized` | Token missing, invalid, or expired |

---

### `GET /api/watchlist/{username}`

Return any user's watchlist by username. No authentication required.

**Path parameter:** `username` — the username of the target user.

**Success:** `200 OK` — returns `WatchlistOut`.

**Errors:**

| Status | Reason |
| --- | --- |
| `404 Not Found` | No user with that username exists |

---

### `POST /api/watchlist/want-to-watch`

Add a movie or show to the authenticated user's want-to-watch list.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request body (JSON):** `WatchlistEntryCreate`

**Behavior:**

| Existing state | Result |
| --- | --- |
| Item not on any list | New entry created, `list_type = want_to_watch` |
| Item already on want-to-watch | `409 Conflict` |
| Item already on watched | Row updated: `list_type` set to `want_to_watch` |

**Success:** `201 Created` — returns `WatchlistEntryOut`.

**Errors:**

| Status | Reason |
| --- | --- |
| `400 Bad Request` | `media_type` is not `"movie"` or `"tv"` |
| `401 Unauthorized` | Token missing, invalid, or expired |
| `409 Conflict` | Item already on the want-to-watch list |

---

### `POST /api/watchlist/watched`

Add a movie or show to the authenticated user's watched list.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request body (JSON):** `WatchlistEntryCreate`

**Behavior:**

| Existing state | Result |
| --- | --- |
| Item not on any list | New entry created, `list_type = watched` |
| Item already on want-to-watch | Row updated: `list_type` set to `watched` (entry id preserved) |
| Item already on watched | `409 Conflict` |

**Success:** `201 Created` — returns `WatchlistEntryOut`.

**Errors:**

| Status | Reason |
| --- | --- |
| `400 Bad Request` | `media_type` is not `"movie"` or `"tv"` |
| `401 Unauthorized` | Token missing, invalid, or expired |
| `409 Conflict` | Item already on the watched list |

---

### `DELETE /api/watchlist/{entry_id}`

Remove an entry from either list.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path parameter:** `entry_id` — the id of the entry to delete.

**Success:** `204 No Content`

**Errors:**

| Status | Reason |
| --- | --- |
| `401 Unauthorized` | Token missing, invalid, or expired |
| `404 Not Found` | Entry does not exist or belongs to a different user |

---

## What's Not Yet Built

- Emoji ratings on watched entries (model has a `TODO` placeholder for this)
- Friends-only visibility (currently all lists are fully public)
- TMDB metadata enrichment on list responses (currently only ids are stored)

---

## Where to Look in the Code

| Concern | File |
| --- | --- |
| ORM model + enums | `backend/app/models/watchlist.py` |
| Pydantic schemas | `backend/app/schemas/watchlist.py` |
| Route handlers | `backend/app/routers/watchlist.py` |
