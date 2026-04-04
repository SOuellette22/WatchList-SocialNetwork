# User Handling

This document covers how users are represented, created, and exposed through the API in WatchTogether. For the login/token flow specifically, see `Authentication_Process.md`.

---

## Overview

A user account has a username, email, and hashed password. Profile pictures are optional — a default image is served when none is set. Users have two different views of their own data: a **public** view (safe to share with other users) and a **private** view (includes email, shown only to the account owner).

---

## Data Model

**Table:** `users`

| Column | Type | Description |
| --- | --- | --- |
| `id` | integer | Primary key, auto-incremented |
| `username` | string (max 50) | Unique, required |
| `email` | string (max 120) | Unique, required |
| `pass_hash` | string (max 200) | Argon2 hash — never the plaintext password |
| `image_file` | string (max 200, nullable) | Filename of the user's uploaded profile picture, or `null` |

### `image_path` property

The `User` model exposes an `image_path` computed property:

- If `image_file` is set: returns `/media/profile_pics/<image_file>`
- Otherwise: returns `/static/profile_pics/default.jpg`

This means callers never need to handle the null case themselves.

---

## Schemas

### `UserCreate`
Used when registering. Accepted in the request body.

| Field | Type | Constraints |
| --- | --- | --- |
| `username` | string | 1–50 characters |
| `email` | EmailStr | max 120 characters |
| `password` | string | min 8 characters (plaintext — hashed before storage) |

### `UserPublic`
Returned when viewing another user's profile or appearing in friends/request lists. Safe to share.

| Field | Type |
| --- | --- |
| `id` | integer |
| `username` | string |
| `image_file` | string or null |
| `image_path` | string (always present — falls back to default) |

### `UserPrivate`
Extends `UserPublic`. Returned only to the authenticated user viewing their own profile.

| Field | Type |
| --- | --- |
| *(all UserPublic fields)* | |
| `email` | string |

### `UserLogin`
Used internally for login validation — not exposed directly as a response schema.

| Field | Type |
| --- | --- |
| `username` | string |
| `password` | string |

---

## Endpoints

### `POST /api/users/register`

Register a new user account.

**Request body (JSON):**

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | 1–50 characters, must be unique |
| `email` | string | Valid email, must be unique |
| `password` | string | Min 8 characters |

**Success:** `201 Created` — returns `UserPrivate` (id, username, email, image fields — no password).

**Errors:**

| Status | Reason |
| --- | --- |
| `409 Conflict` | Username already taken |
| `409 Conflict` | Email already registered |

---

### `POST /api/users/token`

Log in and receive a JWT access token. See `Authentication_Process.md` for full details.

**Request body:** OAuth2 form data (`username`, `password`).

**Success:** `200 OK` — returns `{ "access_token": "<jwt>", "token_type": "bearer" }`.

---

### `GET /api/users/me`

Return the profile of the currently authenticated user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success:** `200 OK` — returns `UserPrivate`.

**Errors:**

| Status | Reason |
| --- | --- |
| `401 Unauthorized` | Token missing, invalid, or expired |

---

## Password Security

Passwords are hashed with **Argon2** via `pwdlib` before being stored. The plaintext password is never persisted anywhere. On login, `verify_password(plain, hash)` compares the submitted password against the stored hash.

See `backend/app/services/auth.py` for `hash_password` and `verify_password`.

---

## Where to Look in the Code

| Concern | File |
| --- | --- |
| ORM model | `backend/app/models/users.py` |
| Pydantic schemas | `backend/app/schemas/users.py` |
| Route handlers | `backend/app/routers/users.py` |
| Password hashing and JWT | `backend/app/services/auth.py` |
| App config (token expiry, secret key) | `backend/app/config.py` |
