import pytest
from backend.tests.conftest import TEST_USER


WATCHED_ITEM = {"tmdb_id": 550, "media_type": "movie"}
WTW_ITEM = {"tmdb_id": 680, "media_type": "movie"}


@pytest.fixture()
def watched_item(client, auth_headers):
    """Add a movie to the watched list so emoji tests have something to rate."""
    resp = client.post("/api/watchlist/watched", json=WATCHED_ITEM, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def wtw_item(client, auth_headers):
    """Add a movie to the want-to-watch list."""
    resp = client.post("/api/watchlist/want-to-watch", json=WTW_ITEM, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


class TestSuggestedEmojis:

    def test_suggestions_returns_200(self, client):
        resp = client.get("/api/watchlist/emoji/suggestions")
        assert resp.status_code == 200

    def test_suggestions_contains_presets(self, client):
        resp = client.get("/api/watchlist/emoji/suggestions")
        emojis = resp.json()
        assert "🔥" in emojis
        assert "😂" in emojis
        assert "💩" in emojis
        assert "😢" in emojis
        assert "😍" in emojis

    def test_suggestions_no_auth_required(self, client):
        resp = client.get("/api/watchlist/emoji/suggestions")
        assert resp.status_code == 200


class TestSetEmojiRating:

    def test_set_emoji_returns_201(self, client, auth_headers, watched_item):
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": "😂"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["emoji"] == "😂"

    def test_custom_emoji_accepted(self, client, auth_headers, watched_item):
        """Non-suggested emojis are also valid."""
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": "🤯"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["emoji"] == "🤯"

    def test_replace_emoji_returns_201(self, client, auth_headers, watched_item):
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": "🔥"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["emoji"] == "🔥"

    def test_set_emoji_on_want_to_watch_returns_403(self, client, auth_headers, wtw_item):
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WTW_ITEM, "emoji": "😂"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_set_emoji_unauthenticated_returns_401(self, client, watched_item):
        resp = client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"})
        assert resp.status_code == 401

    def test_invalid_media_type_returns_400(self, client, auth_headers, watched_item):
        resp = client.post(
            "/api/watchlist/emoji",
            json={"tmdb_id": 550, "media_type": "book", "emoji": "😂"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_empty_emoji_returns_422(self, client, auth_headers, watched_item):
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_emoji_too_long_returns_422(self, client, auth_headers, watched_item):
        """Pydantic validator rejects emoji strings longer than 10 characters."""
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": "😂" * 11},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_set_emoji_on_item_not_in_watchlist_returns_403(self, client, auth_headers):
        """Rating an item that isn't in the watchlist at all should also 403."""
        resp = client.post(
            "/api/watchlist/emoji",
            json={"tmdb_id": 99999, "media_type": "movie", "emoji": "😂"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_missing_emoji_field_returns_422(self, client, auth_headers, watched_item):
        """Omitting the emoji field entirely should be rejected by Pydantic."""
        resp = client.post(
            "/api/watchlist/emoji",
            json={"tmdb_id": 550, "media_type": "movie"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_non_string_emoji_returns_422(self, client, auth_headers, watched_item):
        """Sending a non-string value for emoji should be rejected by Pydantic."""
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": 123},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_whitespace_only_emoji_returns_422(self, client, auth_headers, watched_item):
        """A whitespace-only emoji string is stripped to empty and should be rejected."""
        resp = client.post(
            "/api/watchlist/emoji",
            json={**WATCHED_ITEM, "emoji": "   "},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_replace_emoji_only_one_rating_persists(self, client, auth_headers, watched_item):
        """Replacing an emoji must not create a second row — the GET should show only one entry."""
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "🔥"}, headers=auth_headers)
        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.status_code == 200
        emojis = {r["emoji"]: r["count"] for r in resp.json()}
        assert emojis.get("🔥") == 1
        assert "😂" not in emojis


class TestGetEmojiRatings:

    def test_get_emojis_returns_200(self, client, auth_headers, watched_item):
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.status_code == 200
        assert any(r["emoji"] == "😂" and r["count"] == 1 for r in resp.json())

    def test_same_emoji_from_multiple_users_is_aggregated(self, client, auth_headers, watched_item):
        second_user = {"username": "user2", "email": "user2@example.com", "password": "securepassword123"}
        client.post("/api/users/register", json=second_user)
        token_resp = client.post("/api/users/token", data={"username": "user2", "password": "securepassword123"})
        headers2 = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}
        client.post("/api/watchlist/watched", json=WATCHED_ITEM, headers=headers2)

        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=headers2)

        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.status_code == 200
        assert any(r["emoji"] == "😂" and r["count"] == 2 for r in resp.json())

    def test_different_emojis_are_returned_as_separate_entries(self, client, auth_headers, watched_item):
        second_user = {"username": "user2", "email": "user2@example.com", "password": "securepassword123"}
        client.post("/api/users/register", json=second_user)
        token_resp = client.post("/api/users/token", data={"username": "user2", "password": "securepassword123"})
        headers2 = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}
        client.post("/api/watchlist/watched", json=WATCHED_ITEM, headers=headers2)

        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "🔥"}, headers=headers2)

        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.status_code == 200
        emojis = {r["emoji"]: r["count"] for r in resp.json()}
        assert emojis["😂"] == 1
        assert emojis["🔥"] == 1

    def test_get_emojis_no_auth_required(self, client):
        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.status_code == 200

    def test_get_emojis_empty_list_when_none(self, client):
        resp = client.get("/api/watchlist/emoji/99999/movie")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_media_type_returns_400(self, client):
        resp = client.get("/api/watchlist/emoji/550/book")
        assert resp.status_code == 400

    def test_tv_media_type_accepted(self, client, auth_headers):
        """Emoji ratings should work for TV shows, not just movies."""
        tv_item = {"tmdb_id": 1399, "media_type": "tv"}
        client.post("/api/watchlist/watched", json=tv_item, headers=auth_headers)
        set_resp = client.post("/api/watchlist/emoji", json={**tv_item, "emoji": "🔥"}, headers=auth_headers)
        assert set_resp.status_code == 201
        get_resp = client.get(f"/api/watchlist/emoji/{tv_item['tmdb_id']}/{tv_item['media_type']}")
        assert get_resp.status_code == 200
        assert any(r["emoji"] == "🔥" and r["count"] == 1 for r in get_resp.json())

    def test_invalid_tmdb_id_type_returns_422(self, client):
        """A non-integer tmdb_id in the URL path should be rejected by FastAPI."""
        resp = client.get("/api/watchlist/emoji/abc/movie")
        assert resp.status_code == 422


class TestDeleteEmojiRating:

    def test_delete_emoji_returns_204(self, client, auth_headers, watched_item):
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        resp = client.delete(
            f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}",
            headers=auth_headers,
        )
        assert resp.status_code == 204
        get_resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert get_resp.json() == []

    def test_delete_nonexistent_emoji_returns_404(self, client, auth_headers):
        resp = client.delete("/api/watchlist/emoji/99999/movie", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_unauthenticated_returns_401(self, client):
        resp = client.delete(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.status_code == 401

    def test_delete_invalid_media_type_returns_400(self, client, auth_headers):
        resp = client.delete("/api/watchlist/emoji/550/book", headers=auth_headers)
        assert resp.status_code == 400

    def test_delete_only_affects_own_emoji(self, client, auth_headers, watched_item):
        """Deleting your own emoji should not remove another user's emoji for the same item."""
        second_user = {"username": "user2", "email": "user2@example.com", "password": "securepassword123"}
        client.post("/api/users/register", json=second_user)
        token_resp = client.post("/api/users/token", data={"username": "user2", "password": "securepassword123"})
        headers2 = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}
        client.post("/api/watchlist/watched", json=WATCHED_ITEM, headers=headers2)

        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "🔥"}, headers=headers2)

        client.delete(
            f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}",
            headers=auth_headers,
        )

        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        emojis = {r["emoji"]: r["count"] for r in resp.json()}
        assert "🔥" in emojis
        assert "😂" not in emojis


class TestAutoEmojiRemoval:

    def test_emoji_removed_when_entry_deleted(self, client, auth_headers, watched_item):
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        client.delete(f"/api/watchlist/{watched_item['id']}", headers=auth_headers)
        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.json() == []

    def test_emoji_removed_when_moved_to_want_to_watch(self, client, auth_headers, watched_item):
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😂"}, headers=auth_headers)
        client.post("/api/watchlist/want-to-watch", json=WATCHED_ITEM, headers=auth_headers)
        resp = client.get(f"/api/watchlist/emoji/{WATCHED_ITEM['tmdb_id']}/{WATCHED_ITEM['media_type']}")
        assert resp.json() == []

    def test_moving_wtw_to_watched_does_not_error(self, client, auth_headers, wtw_item):
        """Promoting a WTW entry to watched (no prior emoji) should succeed without errors."""
        resp = client.post("/api/watchlist/watched", json=WTW_ITEM, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["list_type"] == "watched"

    def test_watched_entry_emoji_appears_in_my_watchlist(self, client, auth_headers, watched_item):
        """User's own emoji shows up on watched entries in GET /api/watchlist/."""
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😍"}, headers=auth_headers)
        resp = client.get("/api/watchlist/", headers=auth_headers)
        assert resp.status_code == 200
        watched = resp.json()["watched"]
        rated = next((e for e in watched if e["tmdb_id"] == WATCHED_ITEM["tmdb_id"]), None)
        assert rated is not None
        assert rated["emoji"] == "😍"

    def test_public_watchlist_still_works(self, client, auth_headers):
        """Public endpoint returns 200 without auth after schema changes."""
        client.post("/api/watchlist/watched", json=WATCHED_ITEM, headers=auth_headers)
        resp = client.get(f"/api/watchlist/{TEST_USER['username']}")
        assert resp.status_code == 200
        assert "want_to_watch" in resp.json()
        assert "watched" in resp.json()


_FRIEND_USER = {"username": "frienduser", "email": "friend@example.com", "password": "securepassword123"}


class TestFriendEmojisOnWatchlist:
    """Tests for the friend-emoji feature: friends' reactions on want-to-watch items,
    and the target user's own emoji on watched items in the public endpoint."""

    @pytest.fixture()
    def friend_headers(self, client):
        """Register a second user and return their auth headers."""
        client.post("/api/users/register", json=_FRIEND_USER)
        token_resp = client.post(
            "/api/users/token",
            data={"username": _FRIEND_USER["username"], "password": _FRIEND_USER["password"]},
        )
        return {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    @pytest.fixture()
    def friendship(self, client, auth_headers, friend_headers):
        """Establish an accepted friendship between the test user and the friend user."""
        client.post(f"/api/friends/{_FRIEND_USER['username']}", headers=auth_headers)
        client.post(f"/api/friends/{TEST_USER['username']}/accept", headers=friend_headers)

    def test_want_to_watch_entries_have_friend_emojis_field(self, client, auth_headers, wtw_item):
        """Schema check: every want-to-watch entry includes a friend_emojis list."""
        resp = client.get("/api/watchlist/", headers=auth_headers)
        wtw = resp.json()["want_to_watch"]
        assert len(wtw) > 0
        assert all("friend_emojis" in entry for entry in wtw)

    def test_friend_emoji_appears_on_want_to_watch_item(
        self, client, auth_headers, friend_headers, friendship, wtw_item
    ):
        """If a friend has watched and rated an item on your WTW list, their emoji should appear."""
        client.post("/api/watchlist/watched", json=WTW_ITEM, headers=friend_headers)
        client.post("/api/watchlist/emoji", json={**WTW_ITEM, "emoji": "🔥"}, headers=friend_headers)

        resp = client.get("/api/watchlist/", headers=auth_headers)
        wtw = resp.json()["want_to_watch"]
        entry = next((e for e in wtw if e["tmdb_id"] == WTW_ITEM["tmdb_id"]), None)
        assert entry is not None
        assert any(fe["emoji"] == "🔥" and fe["username"] == _FRIEND_USER["username"] for fe in entry["friend_emojis"])

    def test_non_friend_emoji_does_not_appear_on_want_to_watch(
        self, client, auth_headers, friend_headers, wtw_item
    ):
        """A stranger's emoji should not appear in friend_emojis — no friendship, no emoji."""
        client.post("/api/watchlist/watched", json=WTW_ITEM, headers=friend_headers)
        client.post("/api/watchlist/emoji", json={**WTW_ITEM, "emoji": "🔥"}, headers=friend_headers)

        resp = client.get("/api/watchlist/", headers=auth_headers)
        wtw = resp.json()["want_to_watch"]
        entry = next((e for e in wtw if e["tmdb_id"] == WTW_ITEM["tmdb_id"]), None)
        assert entry is not None
        assert entry["friend_emojis"] == []

    def test_public_watchlist_shows_target_emoji_on_watched(self, client, auth_headers):
        """When viewing someone's public watchlist, their own emoji shows on watched entries."""
        client.post("/api/watchlist/watched", json=WATCHED_ITEM, headers=auth_headers)
        client.post("/api/watchlist/emoji", json={**WATCHED_ITEM, "emoji": "😍"}, headers=auth_headers)

        resp = client.get(f"/api/watchlist/{TEST_USER['username']}")
        watched = resp.json()["watched"]
        entry = next((e for e in watched if e["tmdb_id"] == WATCHED_ITEM["tmdb_id"]), None)
        assert entry is not None
        assert entry["emoji"] == "😍"

    def test_multiple_friends_emojis_all_appear(
        self, client, auth_headers, friend_headers, friendship, wtw_item
    ):
        """All friends who have rated an item should appear in friend_emojis."""
        second_friend = {"username": "frienduser2", "email": "friend2@example.com", "password": "securepassword123"}
        client.post("/api/users/register", json=second_friend)
        token_resp = client.post("/api/users/token", data={"username": "frienduser2", "password": "securepassword123"})
        headers3 = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}
        client.post(f"/api/friends/{second_friend['username']}", headers=auth_headers)
        client.post(f"/api/friends/{TEST_USER['username']}/accept", headers=headers3)

        client.post("/api/watchlist/watched", json=WTW_ITEM, headers=friend_headers)
        client.post("/api/watchlist/emoji", json={**WTW_ITEM, "emoji": "🔥"}, headers=friend_headers)
        client.post("/api/watchlist/watched", json=WTW_ITEM, headers=headers3)
        client.post("/api/watchlist/emoji", json={**WTW_ITEM, "emoji": "😢"}, headers=headers3)

        resp = client.get("/api/watchlist/", headers=auth_headers)
        wtw = resp.json()["want_to_watch"]
        entry = next((e for e in wtw if e["tmdb_id"] == WTW_ITEM["tmdb_id"]), None)
        assert entry is not None
        friend_emoji_set = {fe["username"] for fe in entry["friend_emojis"]}
        assert _FRIEND_USER["username"] in friend_emoji_set
        assert second_friend["username"] in friend_emoji_set

    def test_friend_emoji_disappears_after_unfriending(
        self, client, auth_headers, friend_headers, friendship, wtw_item
    ):
        """After removing a friendship, the ex-friend's emoji should no longer appear in friend_emojis."""
        client.post("/api/watchlist/watched", json=WTW_ITEM, headers=friend_headers)
        client.post("/api/watchlist/emoji", json={**WTW_ITEM, "emoji": "🔥"}, headers=friend_headers)

        client.delete(f"/api/friends/{_FRIEND_USER['username']}", headers=auth_headers)

        resp = client.get("/api/watchlist/", headers=auth_headers)
        wtw = resp.json()["want_to_watch"]
        entry = next((e for e in wtw if e["tmdb_id"] == WTW_ITEM["tmdb_id"]), None)
        assert entry is not None
        assert entry["friend_emojis"] == []

    def test_public_watchlist_unauthenticated_has_empty_friend_emojis(self, client, auth_headers):
        """Unauthenticated requests to the public watchlist get empty friend_emojis on all WTW entries."""
        client.post("/api/watchlist/want-to-watch", json=WTW_ITEM, headers=auth_headers)

        resp = client.get(f"/api/watchlist/{TEST_USER['username']}")
        wtw = resp.json()["want_to_watch"]
        assert all(e["friend_emojis"] == [] for e in wtw)