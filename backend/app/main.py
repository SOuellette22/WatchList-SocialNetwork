from fastapi import FastAPI

from backend.app.database import Base, engine
from backend.app.routers import (
    users,
    friends
)
from backend.app.models import friends as _friends_model

# Sets the sqlalchemy database as the backends db
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WatchTogether API") # Initializes the app

app.include_router(users.router)
app.include_router(friends.router)

@app.get("/")
def root():
    return {"message": "Hello World"}