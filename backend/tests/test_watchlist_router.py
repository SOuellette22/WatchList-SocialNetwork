"""Integration tests for /api/watchlist endpoints."""
import pytest

from backend.tests.conftest import TEST_USER

SECOND_USER = {
    "username": "otherwatchuser",
    "email": "other@example.com",
    "password": "securepassword456",
}

MOVIE_ENTRY = {"tmdb_id": 550, "media_type": "movie"}
TV_ENTRY = {"tmdb_id": 1396, "media_type": "tv"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def second_user(client):
    resp = client.post("/api/users/register", json=SECOND_USER)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def second_auth_headers(client, second_user):
    resp = client.post(
        "/api/users/token",
        data={"username": SECOND_USER["username"], "password": SECOND_USER["password"]},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def want_to_watch_entry(client, registered_user, auth_headers):
    """Add a movie to the current user's want-to-watch list and return the entry."""
    resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def watched_entry(client, registered_user, auth_headers):
    """Add a movie to the current user's watched list and return the entry."""
    resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Add to want-to-watch
# ---------------------------------------------------------------------------

class TestAddToWantToWatch:
    def test_success_returns_201(self, client, registered_user, auth_headers):
        resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.status_code == 201

    def test_entry_has_correct_fields(self, client, registered_user, auth_headers):
        resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        body = resp.json()
        assert body["tmdb_id"] == MOVIE_ENTRY["tmdb_id"]
        assert body["media_type"] == MOVIE_ENTRY["media_type"]
        assert body["list_type"] == "want_to_watch"

    def test_tv_show_can_be_added(self, client, registered_user, auth_headers):
        resp = client.post("/api/watchlist/want-to-watch", json=TV_ENTRY, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["media_type"] == "tv"

    def test_duplicate_returns_409(self, client, registered_user, auth_headers):
        client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.status_code == 409

    def test_already_watched_item_demotes_to_want_to_watch(
        self, client, registered_user, auth_headers, watched_entry
    ):
        resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["list_type"] == "want_to_watch"

    def test_demotion_preserves_entry_id(
        self, client, registered_user, auth_headers, watched_entry
    ):
        original_id = watched_entry["id"]
        resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.json()["id"] == original_id

    def test_invalid_media_type_returns_400(self, client, registered_user, auth_headers):
        resp = client.post(
            "/api/watchlist/want-to-watch",
            json={"tmdb_id": 550, "media_type": "book"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_no_token_returns_401(self, client, registered_user):
        resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Add to watched
# ---------------------------------------------------------------------------

class TestAddToWatched:
    def test_success_returns_201(self, client, registered_user, auth_headers):
        resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.status_code == 201

    def test_entry_has_correct_fields(self, client, registered_user, auth_headers):
        resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        body = resp.json()
        assert body["tmdb_id"] == MOVIE_ENTRY["tmdb_id"]
        assert body["media_type"] == MOVIE_ENTRY["media_type"]
        assert body["list_type"] == "watched"

    def test_tv_show_can_be_added(self, client, registered_user, auth_headers):
        resp = client.post("/api/watchlist/watched", json=TV_ENTRY, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["media_type"] == "tv"

    def test_duplicate_returns_409(self, client, registered_user, auth_headers):
        client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.status_code == 409

    def test_want_to_watch_item_promotes_to_watched(
        self, client, registered_user, auth_headers, want_to_watch_entry
    ):
        resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["list_type"] == "watched"

    def test_promotion_preserves_entry_id(
        self, client, registered_user, auth_headers, want_to_watch_entry
    ):
        original_id = want_to_watch_entry["id"]
        resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        assert resp.json()["id"] == original_id

    def test_invalid_media_type_returns_400(self, client, registered_user, auth_headers):
        resp = client.post(
            "/api/watchlist/watched",
            json={"tmdb_id": 550, "media_type": "book"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_no_token_returns_401(self, client, registered_user):
        resp = client.post("/api/watchlist/watched", json=MOVIE_ENTRY)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Delete entry
# ---------------------------------------------------------------------------

class TestDeleteEntry:
    def test_delete_want_to_watch_entry_returns_204(
        self, client, registered_user, auth_headers, want_to_watch_entry
    ):
        resp = client.delete(f"/api/watchlist/{want_to_watch_entry['id']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_watched_entry_returns_204(
        self, client, registered_user, auth_headers, watched_entry
    ):
        resp = client.delete(f"/api/watchlist/{watched_entry['id']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_entry_gone_after_deletion(
        self, client, registered_user, auth_headers, want_to_watch_entry
    ):
        client.delete(f"/api/watchlist/{want_to_watch_entry['id']}", headers=auth_headers)
        resp = client.get("/api/watchlist/", headers=auth_headers)
        assert resp.json()["want_to_watch"] == []

    def test_delete_another_users_entry_returns_404(
        self, client, registered_user, auth_headers, second_user, second_auth_headers
    ):
        entry_resp = client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        entry_id = entry_resp.json()["id"]
        resp = client.delete(f"/api/watchlist/{entry_id}", headers=second_auth_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_entry_returns_404(self, client, registered_user, auth_headers):
        resp = client.delete("/api/watchlist/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_no_token_returns_401(self, client, registered_user, want_to_watch_entry):
        resp = client.delete(f"/api/watchlist/{want_to_watch_entry['id']}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get own watchlist
# ---------------------------------------------------------------------------

class TestGetMyWatchlist:
    def test_empty_lists_on_new_user(self, client, registered_user, auth_headers):
        resp = client.get("/api/watchlist/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"want_to_watch": [], "watched": []}

    def test_entry_appears_in_correct_list(self, client, registered_user, auth_headers):
        client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        client.post("/api/watchlist/watched", json=TV_ENTRY, headers=auth_headers)
        resp = client.get("/api/watchlist/", headers=auth_headers)
        body = resp.json()
        assert len(body["want_to_watch"]) == 1
        assert len(body["watched"]) == 1
        assert body["want_to_watch"][0]["tmdb_id"] == MOVIE_ENTRY["tmdb_id"]
        assert body["watched"][0]["tmdb_id"] == TV_ENTRY["tmdb_id"]

    def test_promoted_entry_moves_to_watched_list(
        self, client, registered_user, auth_headers, want_to_watch_entry
    ):
        client.post("/api/watchlist/watched", json=MOVIE_ENTRY, headers=auth_headers)
        resp = client.get("/api/watchlist/", headers=auth_headers)
        body = resp.json()
        assert body["want_to_watch"] == []
        assert len(body["watched"]) == 1

    def test_demoted_entry_moves_to_want_to_watch_list(
        self, client, registered_user, auth_headers, watched_entry
    ):
        client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        resp = client.get("/api/watchlist/", headers=auth_headers)
        body = resp.json()
        assert body["watched"] == []
        assert len(body["want_to_watch"]) == 1

    def test_users_lists_are_isolated(
        self, client, registered_user, auth_headers, second_user, second_auth_headers
    ):
        client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        resp = client.get("/api/watchlist/", headers=second_auth_headers)
        assert resp.json()["want_to_watch"] == []

    def test_no_token_returns_401(self, client, registered_user):
        resp = client.get("/api/watchlist/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get another user's watchlist
# ---------------------------------------------------------------------------

class TestGetUserWatchlist:
    def test_returns_200_with_correct_entries(
        self, client, registered_user, auth_headers, second_user
    ):
        client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        resp = client.get(f"/api/watchlist/{TEST_USER['username']}")
        assert resp.status_code == 200
        assert resp.json()["want_to_watch"][0]["tmdb_id"] == MOVIE_ENTRY["tmdb_id"]

    def test_no_auth_required(self, client, registered_user):
        resp = client.get(f"/api/watchlist/{TEST_USER['username']}")
        assert resp.status_code == 200

    def test_returns_empty_lists_for_user_with_no_entries(self, client, registered_user):
        resp = client.get(f"/api/watchlist/{TEST_USER['username']}")
        assert resp.json() == {"want_to_watch": [], "watched": []}

    def test_nonexistent_user_returns_404(self, client):
        resp = client.get("/api/watchlist/doesnotexist")
        assert resp.status_code == 404

    def test_only_returns_target_users_entries(
        self, client, registered_user, auth_headers, second_user, second_auth_headers
    ):
        client.post("/api/watchlist/want-to-watch", json=MOVIE_ENTRY, headers=auth_headers)
        client.post("/api/watchlist/watched", json=TV_ENTRY, headers=second_auth_headers)
        resp = client.get(f"/api/watchlist/{SECOND_USER['username']}")
        body = resp.json()
        assert body["want_to_watch"] == []
        assert len(body["watched"]) == 1
        assert body["watched"][0]["tmdb_id"] == TV_ENTRY["tmdb_id"]
