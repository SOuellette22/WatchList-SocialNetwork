# Authentication

This document explains how authentication works in WatchTogether — from registering a new account, to logging in and getting a JWT, to making authenticated requests.

---

## Overview

WatchTogether uses **JWT (JSON Web Token)** bearer tokens for authentication. There are no sessions or cookies. When a user logs in they receive a token, and every protected endpoint expects that token in an `Authorization: Bearer <token>` header.

Password hashing uses **Argon2** via `pwdlib`, which is the current recommended algorithm for secure password storage.

---

## Endpoints

### `POST /api/users/register`

Registers a new user account.

**Request body (JSON):**

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | Must be unique |
| `email` | string | Must be unique |
| `password` | string | Plaintext — hashed before storage |

**Success:** `201 Created` — returns the created user (id, username, email — no password).

**Errors:**

| Status | Reason |
| --- | --- |
| `409 Conflict` | Username already taken |
| `409 Conflict` | Email already registered |

---

### `POST /api/users/token`

Logs in and returns a JWT access token. This is a standard OAuth2 password flow endpoint.

**Request body (form data — not JSON):**

| Field | Type |
| --- | --- |
| `username` | string |
| `password` | string |

**Success:** `200 OK`
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Errors:**

| Status | Reason |
| --- | --- |
| `401 Unauthorized` | Username not found or password incorrect |

---

### `GET /api/users/me`

Returns the profile of the currently authenticated user. Requires a valid bearer token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success:** `200 OK` — returns the user object (id, username, email).

**Errors:**

| Status | Reason |
| --- | --- |
| `401 Unauthorized` | Token missing, invalid, or expired |

---

## How Tokens Work

### Creating a token (`create_access_token`)

When a user logs in, a JWT is created with:
- **`sub`** — the user's integer ID (as a string)
- **`exp`** — expiry timestamp, calculated as `now + ACCESS_TOKEN_EXPIRE_MINUTES` from config

The token is signed with the app's `SECRET_KEY` using the configured algorithm (HS256 by default).

### Verifying a token (`verify_access_token`)

On every protected request, the token is decoded and validated:
1. Signature must be valid (correct `SECRET_KEY`)
2. Token must not be expired (`exp` claim required)
3. `sub` claim must be present

Returns the user ID string on success, `None` on any failure — no exceptions bubble up.

### Resolving the current user (`get_current_user`)

This is the FastAPI dependency injected into protected routes:
1. Extracts the bearer token from the `Authorization` header
2. Calls `verify_access_token` — raises `401` if it returns `None`
3. Looks up the user by ID in the database — raises `401` if not found
4. Returns the `User` ORM object to the route handler

---

## Password Hashing

Passwords are never stored in plaintext. The flow:

- **On register:** `hash_password(plain)` → Argon2 hash → stored in `pass_hash` column
- **On login:** `verify_password(plain, hash)` → `True/False` → grant or deny access

`pwdlib` handles all Argon2 parameters internally using `PasswordHash.recommended()`, which picks safe defaults automatically.

---

## Where to Look in the Code

| Concern | File |
| --- | --- |
| Route handlers (register, login, /me) | `backend/app/routers/users.py` |
| Password hashing & JWT logic | `backend/app/services/auth.py` |
| Token schema | `backend/app/schemas/token.py` |
| User schema | `backend/app/schemas/users.py` |
| Config (SECRET_KEY, expiry, algorithm) | `backend/app/config.py` |
