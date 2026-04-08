# WatchTogether — Project Roadmap

This document tracks everything that still needs to be built to realize the full WatchTogether vision. It is organized by area and roughly ordered by priority within each section.

For context on what is already implemented, see the feature docs in `docs/backend/`.

---

## Current State (as of April 2026)

### What is Built

| Area | Status |
|---|---|
| User registration, login, JWT auth | Done |
| Watchlist (want-to-watch, watched, CRUD) | Done |
| Friends system (request, accept, decline, unfriend, cooldown) | Done |
| TMDB integration (search, movie/TV detail, caching) | Done |
| Tests (~87 tests across 6 files) | Done |
| Feature documentation | Done |
| CI/CD (GitHub Actions on PRs to main) | Done |

### What is Not Built

Everything below.

---

## Backend

### 1. Emoji Ratings

**Priority: Next up** — implementation is fully planned in `docs/backend/temp/emoji_ratings.md`. TODOs exist in `backend/app/models/watchlist.py` (line 25) and `backend/app/schemas/watchlist.py` (lines 8 and 18). GitHub issue: #22.

**What it does:** Users can attach a single emoji reaction to any item on their watched list. Each user gets one emoji per piece of media; submitting again replaces the previous one. The emoji is automatically removed if the entry is deleted or moved back to want-to-watch.

**Scope:**

- New `emoji_ratings` table: `user_id`, `tmdb_id`, `media_type`, `emoji` (max 10 chars), unique per `(user_id, tmdb_id, media_type)`
- `POST /api/watchlist/{entry_id}/emoji` — set or replace an emoji (must own the entry, entry must be on watched list)
- `GET /api/media/{media_type}/{tmdb_id}/emojis` — get aggregated emoji counts for a movie or show (public, no auth required)
- `DELETE /api/watchlist/{entry_id}/emoji` — remove own emoji
- Auto-delete emoji on watched-entry deletion and on demotion back to want-to-watch
- Full test suite (see planning doc for the complete test outline)

**Friend Emojis on Want-to-Watch (subfeature):** When a user fetches their own want-to-watch list, the response should include the emoji reactions their friends have left on those same items. This requires the friends system (already done) and the emoji ratings table. Implementation detail: for each item in the user's want-to-watch list, query `emoji_ratings` joined with `friendships` to find accepted friends who have rated that item.

See `docs/backend/temp/emoji_ratings.md` for full schema, endpoint specs, and a complete test file.

---

### 2. Refresh Tokens

**Priority: High** — the current access token expires after 30 minutes with no way to refresh silently. Users must log in again. This is essential before building any frontend.

Implementation is fully planned in `docs/backend/temp/refresh_tokens.md`.

**What it does:** Issues a long-lived refresh token at login. The client uses it to get a new access token without prompting for credentials. Old refresh tokens are rotated (invalidated) on each use to prevent reuse after theft.

**Scope:**

- Two new columns on the `users` table: `refresh_token` (string, nullable) and `refresh_token_expires_at` (datetime, nullable)
- Updated `Token` schema to include `refresh_token` and `refresh_token_type`
- Updated login endpoint (`POST /api/users/token`) to issue both tokens
- New `POST /api/users/refresh` — accepts a refresh token, returns a new access token + rotated refresh token; invalidates the old one
- New `POST /api/users/logout` — invalidates the current refresh token
- Refresh tokens stored as secure random strings (not JWTs) so they can be revoked server-side
- Client-side: store in `expo-secure-store` on mobile, `httpOnly` cookie on web

See `docs/backend/temp/refresh_tokens.md` for full implementation detail including code snippets for every change.

---

### 3. User Profile Management

**Priority: High** — users need to be able to update their profile before the app goes live.

**What it does:** Lets authenticated users update their own account details.

**Scope:**

- `PATCH /api/users/me` — update username and/or email; validate uniqueness, return updated profile
- `POST /api/users/me/password` — change password; requires current password for verification
- `POST /api/users/me/avatar` — upload a profile picture; stores to `backend/media/profile_pics/`, updates `image_file` on the user record
  - Needs file size and MIME type validation (accept JPEG and PNG only, max ~2 MB)
- Corresponding tests for each endpoint covering success paths, uniqueness conflicts, and auth failures

---

### 4. TMDB Metadata Enrichment in Watchlist

**Priority: Medium** — watchlist responses currently return only `tmdb_id` and `media_type`. Clients must make separate media detail calls to display titles and posters. This creates N+1 request patterns.

**What it does:** Embeds title, poster URL, and release year directly in watchlist entry responses so clients can render the list without extra calls.

**Scope:**

- Updated `WatchlistEntryOut` schema to add optional `title`, `poster_url`, and `release_date` fields
- On watchlist fetch, batch-resolve TMDB metadata for all entries using the existing `get_movie()` / `get_tv_show()` service functions (already cached, so repeated calls are cheap)
- Graceful degradation: if TMDB is unavailable, return the entry without metadata rather than failing the whole request

---

### 5. Friends-only Watchlist Visibility

**Priority: Medium** — currently any watchlist is publicly accessible by username with no auth required (`GET /api/watchlist/{username}`). The README implies a more social/private model.

**What it does:** Allows users to make their watchlist visible only to accepted friends.

**Scope:**

- New `is_public` boolean column on `users` table (default `True` for backwards compatibility)
- `PATCH /api/users/me/privacy` — toggle public/private (or include in the profile PATCH above)
- Update `GET /api/watchlist/{username}` to check visibility: if the target user is private, return 403 unless the requester is an accepted friend
- Update `GET /api/friends/{username}` with the same visibility check
- Tests covering each combination (public user no auth, private user no auth, private user as friend, private user as non-friend)

---

### 6. Recommendations

**Priority: Medium** — a core social feature from the README: "see how the community feels about a show at a glance, and get a more personal view from friends."

**What it does:** Lets users send a movie or TV show recommendation directly to one or more friends.

**Scope:**

- New `recommendations` table: `id`, `sender_id` (FK users), `recipient_id` (FK users), `tmdb_id`, `media_type`, `message` (optional text), `sent_at`, `seen_at` (nullable)
- `POST /api/recommendations` — send a recommendation to a friend (must be accepted friends)
- `GET /api/recommendations` — list recommendations received by the current user (unread first)
- `PATCH /api/recommendations/{id}/seen` — mark a recommendation as seen
- `DELETE /api/recommendations/{id}` — dismiss a recommendation (recipient) or retract (sender)
- A user should not be able to spam the same recommendation repeatedly — enforce a unique constraint or cooldown on `(sender_id, recipient_id, tmdb_id, media_type)`

---

### 7. Comments / Discussions

**Priority: Lower** — gated discussion threads are a differentiating feature but depend on emoji ratings and a mature watchlist first.

**What it does:** Each movie or show has a discussion thread. Only users who have that item on their watched list can post. Anyone (including non-watchers) can read.

**Scope:**

- New `comments` table: `id`, `user_id` (FK), `tmdb_id`, `media_type`, `body` (text, max ~500 chars), `created_at`, `edited_at` (nullable)
- `GET /api/media/{media_type}/{tmdb_id}/comments` — list comments, paginated (no auth required)
- `POST /api/media/{media_type}/{tmdb_id}/comments` — post a comment (auth required; user must have the item on their watched list — 403 otherwise)
- `PATCH /api/comments/{id}` — edit own comment (auth required; within a time window, e.g., 15 minutes)
- `DELETE /api/comments/{id}` — delete own comment (auth required)
- No nested replies for now — keep it flat

---

### 8. Notifications

**Priority: Lower** — depends on emoji ratings and recommendations being built first, as those are the trigger events.

**What it does:** Alerts users when friends react to something on their want-to-watch list, or when they receive a recommendation.

**Scope:**

- New `notifications` table: `id`, `user_id` (FK, recipient), `type` (enum: `friend_emoji`, `recommendation`, `friend_request`), `payload` (JSON or structured columns), `created_at`, `read_at` (nullable)
- `GET /api/notifications` — list unread notifications, newest first (auth required)
- `PATCH /api/notifications/{id}/read` — mark as read
- `PATCH /api/notifications/read-all` — mark all as read
- Notifications are created server-side as a side effect of the triggering action (emoji rating on a want-to-watch item, recommendation sent, friend request received)
- No push notifications yet — polling from the client is fine for an initial version

---

## Infrastructure / DevOps

### 9. Database Migrations (Alembic)

**Priority: High** — currently using `Base.metadata.create_all()` which only creates missing tables; it cannot add columns to existing tables. As soon as emoji ratings or refresh tokens are built, the existing development database will be out of sync.

**Scope:**

- Add `alembic` to `requirements.txt`
- Run `alembic init alembic` and configure `alembic.ini` + `env.py` to use the project's `DATABASE_URL` and `Base`
- Create an initial migration that captures the current schema as a baseline
- All future model changes must include a corresponding Alembic migration file
- CI should run `alembic upgrade head` before tests to ensure migrations are valid

---

### 10. HTTPS and Deployment

**Priority: Medium** — required before the app can be used on a real device.

A step-by-step guide is already written in `docs/backend/temp/https_setup.md`. It covers running Uvicorn behind Caddy as a reverse proxy with automatic Let's Encrypt TLS certificates.

**Remaining work:**

- Follow the guide to provision a server, configure DNS, and deploy
- Write a `systemd` service file for the Uvicorn process (template is in the guide)
- Decide on the production database (SQLite works for a single server; consider PostgreSQL if multiple processes or higher concurrency is needed)
- Set up environment variable management for the production `.env`

---

### 11. `.env.example`

**Priority: Low** — quick win. There is currently no example environment file, making it harder for new contributors to get set up.

Create `backend/.env.example`:

```
SECRET_KEY=replace-with-a-long-random-string
TMDB_API_TOKEN=replace-with-your-tmdb-bearer-token
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Frontend

### 12. React Native App

**Priority: Parallel with backend completion** — the frontend is currently an empty placeholder (`frontend/index.html`). The full frontend needs to be built with React Native targeting both mobile (iOS/Android) and web (React Native Web).

This is a large workload. A rough screen list based on the feature set:

| Screen | Depends On |
|---|---|
| Login / Register | Auth (done) |
| My Profile + Edit | Profile management (#3) |
| My Watchlist | Watchlist (done) |
| Search (browse TMDB) | TMDB integration (done) |
| Movie / Show Detail | TMDB integration (done), Emoji ratings (#1), Comments (#7) |
| Friends list | Friends system (done) |
| Friend Requests | Friends system (done) |
| User Profile (other) | Watchlist visibility (#5) |
| Want-to-Watch with Friend Emojis | Emoji ratings (#1, subfeature) |
| Recommendations inbox | Recommendations (#6) |
| Notifications | Notifications (#8) |

Authentication should use the refresh token flow (#2) with tokens stored in `expo-secure-store`.

---

## Housekeeping

### Minor Code Issues

These are small bugs/inconsistencies found in the existing codebase:

- **Cache typo** (`backend/app/services/cache.py`, line 9): `self._tll` should be `self._ttl`. The code works because the typo is used consistently, but it should be corrected.
- **Duplicate dependency** (`backend/requirements.txt`, lines 3 and 20): `httpx == 0.28.1` appears twice. Remove the duplicate.
