"""Integration tests for /api/users endpoints."""
from datetime import timedelta

import jwt
import pytest

from backend.app.config import settings
from backend.app.services.auth import create_access_token
from backend.tests.conftest import TEST_USER


class TestRegister:
    def test_success_returns_201_with_user_data(self, client):
        resp = client.post("/api/users/register", json=TEST_USER)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == TEST_USER["username"]
        assert data["email"] == TEST_USER["email"]
        assert "id" in data

    def test_password_never_returned(self, client):
        resp = client.post("/api/users/register", json=TEST_USER)
        assert resp.status_code == 201
        body = resp.json()
        assert "password" not in body
        assert "pass_hash" not in body

    def test_default_image_path_returned(self, client):
        resp = client.post("/api/users/register", json=TEST_USER)
        assert resp.status_code == 201
        assert resp.json()["image_path"] == "/static/profile_pics/default.jpg"

    def test_duplicate_username_returns_409(self, client, registered_user):
        resp = client.post(
            "/api/users/register",
            json={**TEST_USER, "email": "other@example.com"},
        )
        assert resp.status_code == 409
        assert "username" in resp.json()["detail"].lower()

    def test_duplicate_email_returns_409(self, client, registered_user):
        resp = client.post(
            "/api/users/register",
            json={**TEST_USER, "username": "otheruser"},
        )
        assert resp.status_code == 409
        assert "email" in resp.json()["detail"].lower()

    def test_password_too_short_returns_422(self, client):
        resp = client.post(
            "/api/users/register",
            json={**TEST_USER, "password": "short"},
        )
        assert resp.status_code == 422

    def test_invalid_email_format_returns_422(self, client):
        resp = client.post(
            "/api/users/register",
            json={**TEST_USER, "email": "not-an-email"},
        )
        assert resp.status_code == 422

    def test_missing_required_fields_returns_422(self, client):
        resp = client.post("/api/users/register", json={"username": "onlyname"})
        assert resp.status_code == 422


class TestLogin:
    def test_success_returns_bearer_token(self, client, registered_user):
        resp = client.post(
            "/api/users/token",
            data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_token_contains_correct_user_id(self, client, registered_user):
        resp = client.post(
            "/api/users/token",
            data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        assert payload["sub"] == str(registered_user["id"])

    def test_wrong_password_returns_401(self, client, registered_user):
        resp = client.post(
            "/api/users/token",
            data={"username": TEST_USER["username"], "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_nonexistent_user_returns_401(self, client):
        resp = client.post(
            "/api/users/token",
            data={"username": "nobody", "password": "irrelevant123"},
        )
        assert resp.status_code == 401

    def test_missing_password_field_returns_422(self, client):
        resp = client.post("/api/users/token", data={"username": TEST_USER["username"]})
        assert resp.status_code == 422


class TestGetMe:
    def test_success_returns_user_profile(self, client, registered_user, auth_token):
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == TEST_USER["username"]
        assert data["email"] == TEST_USER["email"]
        assert data["id"] == registered_user["id"]

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/users/me")
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, client):
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, registered_user):
        expired_token = create_access_token(
            data={"sub": str(registered_user["id"])},
            expires_delta=timedelta(seconds=-1),
        )
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_token_signed_with_wrong_secret_returns_401(self, client):
        bad_token = jwt.encode(
            {"sub": "1", "exp": 9_999_999_999},
            "completely-wrong-secret",
            algorithm="HS256",
        )
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401

    def test_valid_token_for_deleted_user_returns_401(
        self, client, registered_user, auth_token, db_session
    ):
        from backend.app.models.users import User

        user = db_session.get(User, registered_user["id"])
        db_session.delete(user)
        db_session.commit()

        resp = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 401
