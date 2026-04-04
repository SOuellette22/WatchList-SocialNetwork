"""Unit tests for backend.app.services.auth (no HTTP layer)."""
from datetime import timedelta

import jwt
import pytest

from backend.app.config import settings
from backend.app.services.auth import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"

    def test_verify_correct_password_returns_true(self):
        hashed = hash_password("mysecretpassword")
        assert verify_password("mysecretpassword", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("mysecretpassword")
        assert verify_password("totallyWrong!", hashed) is False

    def test_same_password_produces_different_hashes(self):
        # The hashing algorithm uses a random salt, so two hashes must differ.
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2


class TestJWTTokens:
    def test_valid_token_returns_subject(self):
        token = create_access_token(data={"sub": "42"})
        assert verify_access_token(token) == "42"

    def test_expired_token_returns_none(self):
        token = create_access_token(
            data={"sub": "42"}, expires_delta=timedelta(seconds=-1)
        )
        assert verify_access_token(token) is None

    def test_token_signed_with_wrong_key_returns_none(self):
        bad_token = jwt.encode(
            {"sub": "42", "exp": 9_999_999_999},
            "completely-wrong-secret-key-used-for-testing",
            algorithm="HS256",
        )
        assert verify_access_token(bad_token) is None

    def test_garbage_string_returns_none(self):
        assert verify_access_token("not.a.valid.jwt.token") is None

    def test_token_missing_sub_claim_returns_none(self):
        # options={"require": ["exp", "sub"]} should reject tokens without sub.
        token = jwt.encode(
            {"exp": 9_999_999_999},
            settings.secret_key.get_secret_value(),
            algorithm="HS256",
        )
        assert verify_access_token(token) is None

    def test_token_missing_exp_claim_returns_none(self):
        token = jwt.encode(
            {"sub": "42"},
            settings.secret_key.get_secret_value(),
            algorithm="HS256",
        )
        assert verify_access_token(token) is None
