from fastapi import FastAPI

from backend.app.database import Base, engine
from backend.app.routers import (
    users,
    friends,
    media,
    watchlist
)

# Sets the sqlalchemy database as the backends db
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WatchTogether API") # Initializes the app

app.include_router(users.router)
app.include_router(friends.router)
app.include_router(media.router)
app.include_router(watchlist.router)

@app.get("/")
def root():
    return {"message": "WatchTogether API"}