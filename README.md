# WatchTogether

A social watchlist platform where users react to shows and movies with emojis and discuss them with fellow watchers.

## About

WatchTogether is a watchlist app with a social twist. Track what you've watched and what you want to watch, leave emoji reactions on everything you've seen, and join the conversation with other viewers. See how the community feels about a show at a glance, and get a more personal view from friends on the stuff you're planning to watch next.

---

### How It Works

- **Track Your Watching** — Maintain a *watched* list and a *want-to-watch* list for shows and movies.
- **React to What You've Seen** — When you add something to your watched list, leave an emoji reaction to capture how you felt about it. Every show and movie page displays the reactions from all users, giving you an instant community vibe check.
- **Join the Conversation** — Watched a show? You've earned your spot in the comments. Only users who have a show or movie on their watched list can participate in its discussion, keeping conversations authentic.
- **Friend Insights** — Connect with friends and see the emoji reactions they've left on shows and movies that are on your want-to-watch list. Get a trusted take before you commit.

---

## Tech Stack

- **Frontend:** React Native (with React Native Web for browser support)
- **Backend:** FastAPI (Python)
- **Database:** SQLite (via SQLAlchemy 2.0) — may move to PostgreSQL for production
- **External API:** TMDB (The Movie Database) for show and movie metadata

---

## Installation

1. Clone the repo

```bash
git clone <repo-link>
```

2. Set up python virtual enviornment

**Linux/MacOS**
```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

**Windows**
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

3. Start up the fastapi backend

```bash
cd ..
uvicorn backend.app.main:app --reload 
```