"""Integration tests for /api/friends endpoints."""
from datetime import datetime, timedelta

import pytest

from backend.app.models.friends import Friendship
from backend.tests.conftest import TEST_USER

SECOND_USER = {
    "username": "frienduser",
    "email": "friend@example.com",
    "password": "securepassword456",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def second_user(client):
    resp = client.post("/api/users/register", json=SECOND_USER)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def second_auth_headers(client, second_user):
    resp = client.post(
        "/api/users/token",
        data={"username": SECOND_USER["username"], "password": SECOND_USER["password"]},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def accepted_friendship(client, registered_user, second_user, auth_headers, second_auth_headers):
    """Send and accept a friend request so both users are friends."""
    resp_request = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
    assert resp_request.status_code == 201
    resp_request = client.post(f"/api/friends/{TEST_USER['username']}/accept", headers=second_auth_headers)
    assert resp_request.status_code == 200


# ---------------------------------------------------------------------------
# Send friend request
# ---------------------------------------------------------------------------

class TestSendFriendRequest:
    def test_success_returns_201(self, client, registered_user, second_user, auth_headers):
        resp = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["username"] == SECOND_USER["username"]

    def test_password_and_email_not_in_response(self, client, registered_user, second_user, auth_headers):
        resp = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        body = resp.json()
        assert "password" not in body
        assert "pass_hash" not in body
        assert "email" not in body

    def test_duplicate_request_returns_409(self, client, registered_user, second_user, auth_headers):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 409

    def test_request_to_nonexistent_user_returns_404(self, client, registered_user, auth_headers):
        resp = client.post("/api/friends/doesnotexist", headers=auth_headers)
        assert resp.status_code == 404

    def test_request_to_self_returns_400(self, client, registered_user, auth_headers):
        resp = client.post(f"/api/friends/{TEST_USER['username']}", headers=auth_headers)
        assert resp.status_code == 400

    def test_no_token_returns_401(self, client, second_user):
        resp = client.post(f"/api/friends/{SECOND_USER['username']}")
        assert resp.status_code == 401

    def test_request_when_other_user_already_requested_returns_409(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        # Second user requests first user
        client.post(f"/api/friends/{TEST_USER['username']}", headers=second_auth_headers)
        # First user tries to also send a request — should be told to just accept instead
        resp = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 409

    def test_request_after_decline_cooldown_passes(
        self, client, registered_user, second_user, auth_headers, second_auth_headers, db_session
    ):
        # Send and decline
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        client.post(f"/api/friends/{TEST_USER['username']}/decline", headers=second_auth_headers)

        # Manually backdate declined_at to simulate cooldown expiry
        row = db_session.query(Friendship).first()
        row.declined_at = datetime.now() - timedelta(minutes=31)
        db_session.commit()

        resp = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 201

    def test_request_during_cooldown_returns_429(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        client.post(f"/api/friends/{TEST_USER['username']}/decline", headers=second_auth_headers)
        resp = client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Accept friend request
# ---------------------------------------------------------------------------

class TestAcceptFriendRequest:
    def test_success_returns_200_with_requester(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.post(f"/api/friends/{TEST_USER['username']}/accept", headers=second_auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == TEST_USER["username"]

    def test_both_users_appear_in_each_others_list_after_accept(
        self, client, registered_user, second_user, auth_headers, second_auth_headers, accepted_friendship
    ):
        resp1 = client.get("/api/friends/", headers=auth_headers)
        resp2 = client.get("/api/friends/", headers=second_auth_headers)
        assert resp1.json()["total"] == 1
        assert resp2.json()["total"] == 1
        assert resp1.json()["friends"][0]["username"] == SECOND_USER["username"]
        assert resp2.json()["friends"][0]["username"] == TEST_USER["username"]

    def test_accept_nonexistent_request_returns_404(
        self, client, registered_user, second_user, second_auth_headers
    ):
        resp = client.post(f"/api/friends/{TEST_USER['username']}/accept", headers=second_auth_headers)
        assert resp.status_code == 404

    def test_no_token_returns_401(self, client, registered_user, second_user, auth_headers):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.post(f"/api/friends/{TEST_USER['username']}/accept")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Decline friend request
# ---------------------------------------------------------------------------

class TestDeclineFriendRequest:
    def test_success_returns_204(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.post(f"/api/friends/{TEST_USER['username']}/decline", headers=second_auth_headers)
        assert resp.status_code == 204

    def test_declined_user_not_in_friends_list(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        client.post(f"/api/friends/{TEST_USER['username']}/decline", headers=second_auth_headers)
        resp = client.get("/api/friends/", headers=second_auth_headers)
        assert resp.json()["total"] == 0

    def test_decline_nonexistent_request_returns_404(
        self, client, registered_user, second_user, second_auth_headers
    ):
        resp = client.post(f"/api/friends/{TEST_USER['username']}/decline", headers=second_auth_headers)
        assert resp.status_code == 404

    def test_no_token_returns_401(self, client, registered_user, second_user, auth_headers):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.post(f"/api/friends/{TEST_USER['username']}/decline")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get friends list (own)
# ---------------------------------------------------------------------------

class TestGetMyFriends:
    def test_empty_list_when_no_friends(self, client, registered_user, auth_headers):
        resp = client.get("/api/friends/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"friends": [], "total": 0}

    def test_pending_request_not_in_friends_list(
        self, client, registered_user, second_user, auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.get("/api/friends/", headers=auth_headers)
        assert resp.json()["total"] == 0

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/friends/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get incoming requests
# ---------------------------------------------------------------------------

class TestGetIncomingRequests:
    def test_shows_pending_request(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.get("/api/friends/requests", headers=second_auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["requester"]["username"] == TEST_USER["username"]

    def test_empty_when_no_requests(self, client, registered_user, auth_headers):
        resp = client.get("/api/friends/requests", headers=auth_headers)
        assert resp.json() == []

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/friends/requests")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get another user's friends list
# ---------------------------------------------------------------------------

class TestGetUserFriends:
    def test_returns_accepted_friends(
        self, client, registered_user, second_user, accepted_friendship
    ):
        resp = client.get(f"/api/friends/{TEST_USER['username']}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["friends"][0]["username"] == SECOND_USER["username"]

    def test_no_auth_required(self, client, registered_user):
        resp = client.get(f"/api/friends/{TEST_USER['username']}")
        assert resp.status_code == 200

    def test_nonexistent_user_returns_404(self, client):
        resp = client.get("/api/friends/doesnotexist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Remove friend / cancel request
# ---------------------------------------------------------------------------

class TestRemoveFriend:
    def test_remove_accepted_friend_returns_204(
        self, client, registered_user, second_user, auth_headers, accepted_friendship
    ):
        resp = client.delete(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_friend_gone_after_removal(
        self, client, registered_user, second_user, auth_headers, accepted_friendship
    ):
        client.delete(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.get("/api/friends/", headers=auth_headers)
        assert resp.json()["total"] == 0

    def test_cancel_outgoing_request_returns_204(
        self, client, registered_user, second_user, auth_headers
    ):
        client.post(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.delete(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_cannot_cancel_request_you_did_not_send(
        self, client, registered_user, second_user, auth_headers, second_auth_headers
    ):
        # Second user sends request to first user; first user tries to cancel it
        client.post(f"/api/friends/{TEST_USER['username']}", headers=second_auth_headers)
        resp = client.delete(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 403

    def test_remove_non_friend_returns_404(
        self, client, registered_user, second_user, auth_headers
    ):
        resp = client.delete(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        assert resp.status_code == 404

    def test_remove_nonexistent_user_returns_404(self, client, registered_user, auth_headers):
        resp = client.delete("/api/friends/doesnotexist", headers=auth_headers)
        assert resp.status_code == 404

    def test_no_token_returns_401(self, client, second_user):
        resp = client.delete(f"/api/friends/{SECOND_USER['username']}")
        assert resp.status_code == 401

    def test_removal_is_mutual(
        self, client, registered_user, second_user, auth_headers, second_auth_headers, accepted_friendship
    ):
        """Removing a friend removes them from both sides."""
        client.delete(f"/api/friends/{SECOND_USER['username']}", headers=auth_headers)
        resp = client.get("/api/friends/", headers=second_auth_headers)
        assert resp.json()["total"] == 0