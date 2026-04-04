# Friends System

This document explains how the friends system works in WatchTogether — from sending a request, to accepting or declining, to removing a friend.

---

## Overview

Friendships are directional at creation but symmetric once accepted. The `Friendship` table stores a single row per pair, with the user who initiated stored as `requester_id` and the recipient as `addressee_id`. The status field tracks the lifecycle: `pending` → `accepted` or `declined`.

Ratings and list visibility are friend-only — the friend system is the foundation for all social features.

---

## Data Model

**Table:** `friendships`

| Column | Type | Description |
| --- | --- | --- |
| `id` | integer | Primary key |
| `requester_id` | integer (FK → users.id) | User who sent the request |
| `addressee_id` | integer (FK → users.id) | User who received the request |
| `status` | enum | `pending`, `accepted`, or `declined` |
| `declined_at` | datetime (nullable) | Set when a request is declined; used for cooldown enforcement |

A `UniqueConstraint` on `(requester_id, addressee_id)` prevents duplicate rows for the same pair.

---

## Friendship Status Lifecycle

```
[no row]
    │
    │  POST /{username}  (send request)
    ▼
 pending
    │
    ├── POST /{username}/accept  → accepted
    │
    └── POST /{username}/decline → declined
                                       │
                                       │  POST /{username}  (retry after 30 min cooldown)
                                       ▼
                                    pending  (row is reused, not recreated)
```

Once accepted, the friendship is removed entirely by `DELETE /{username}` (unfriend).

---

## Endpoints

### `GET /api/friends/`

Returns the current user's accepted friends list. Requires authentication.

**Success:** `200 OK`

```json
{
  "friends": [
    { "id": 2, "username": "alice", "image_file": null, "image_path": "/static/profile_pics/default.jpg" }
  ],
  "total": 1
}
```

---

### `GET /api/friends/requests`

Returns all pending incoming friend requests for the current user. Requires authentication.

**Success:** `200 OK`

```json
[
  { "requester": { "id": 3, "username": "bob", "image_file": null, "image_path": "..." } }
]
```

---

### `GET /api/friends/{username}`

Returns the accepted friends list of any user by username. No authentication required.

**Errors:**

| Status | Reason |
| --- | --- |
| `404 Not Found` | Username does not exist |

---

### `POST /api/friends/{username}`

Send a friend request to another user. Requires authentication.

**Success:** `201 Created` — returns the target user's public profile.

**Errors:**

| Status | Reason |
| --- | --- |
| `404 Not Found` | Target username does not exist |
| `400 Bad Request` | Cannot send a request to yourself |
| `409 Conflict` | Already friends |
| `409 Conflict` | Request already sent (pending outgoing) |
| `409 Conflict` | That user has already sent you a request |
| `429 Too Many Requests` | Must wait 30 minutes after a decline before retrying |

---

### `POST /api/friends/{username}/accept`

Accept a pending incoming friend request. Requires authentication.

**Success:** `200 OK` — returns the requester's public profile.

**Errors:**

| Status | Reason |
| --- | --- |
| `404 Not Found` | User not found, or no pending request from that user |

---

### `POST /api/friends/{username}/decline`

Decline a pending incoming friend request. The requester must wait 30 minutes before sending another request to this user. Requires authentication.

**Success:** `204 No Content`

**Errors:**

| Status | Reason |
| --- | --- |
| `404 Not Found` | User not found, or no pending request from that user |

---

### `DELETE /api/friends/{username}`

Remove an accepted friend, or cancel an outgoing pending request. Requires authentication.

**Success:** `204 No Content`

**Errors:**

| Status | Reason |
| --- | --- |
| `404 Not Found` | User not found, or no friendship/pending request exists |
| `403 Forbidden` | Attempted to cancel a pending request that you did not send |

---

## Decline Cooldown

When a request is declined, `declined_at` is set to the current time. If the original requester tries to send another request to the same user before 30 minutes have elapsed, they receive a `429 Too Many Requests` error.

After 30 minutes, sending a new request reuses the existing row — `requester_id`, `addressee_id`, `status`, and `declined_at` are all reset in place rather than inserting a new row.

The cooldown constant is `DECLINE_COOLDOWN_MINUTES = 30` in `backend/app/routers/friends.py`.

---

## Where to Look in the Code

| Concern | File |
| --- | --- |
| ORM model and status enum | `backend/app/models/friends.py` |
| All route handlers | `backend/app/routers/friends.py` |
| Response schemas | `backend/app/schemas/friends.py` |
| Public user shape (used in responses) | `backend/app/schemas/users.py` — `UserPublic` |
