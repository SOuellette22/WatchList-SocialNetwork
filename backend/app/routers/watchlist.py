from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.users import User
from backend.app.models.watchlist import ListType, MediaType, WatchlistEntry
from backend.app.schemas.watchlist import (
    WatchlistEntryCreate,
    WatchlistEntryOut,
    WatchlistOut,
)
from backend.app.services.auth import get_current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

def _get_entry(
    entry_id: int, 
    user_id: int, 
    db: Session
) -> WatchlistEntry:
    """Fetch a single watchlist entry by id and verify it belongs to the requesting user.
    
    Raise 404 if the entry does not exist or belongs to a different user."""
    
    # Queries the database for a watchlist entry under a certain user
    entry = db.query(WatchlistEntry).filter(
        WatchlistEntry.id == entry_id,
        WatchlistEntry.user_id == user_id,
    ).first()
    
    # If it does not exist raise a 404 error
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
        
    return entry


# ------------------------------------------
# Get Endpoints
# ------------------------------------------

@router.get("/", response_model=WatchlistOut)
def get_my_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the current user's want-to-watch and watched lists."""
    
    # Gets all the entries to the watchlist db for a given user
    all_entries = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.user_id == current_user.id
        )
        .all()
    )
    
    # Returns two lists the watched and want-to-watch list as separate lists to the user
    return WatchlistOut(
        want_to_watch = [wtw for wtw in all_entries if wtw.list_type == ListType.want_to_watch],
        watched = [w for w in all_entries if w.list_type == ListType.watched],
    )
    
    
@router.get("/{username}", response_model=WatchlistOut)
def get_user_watchlist(
    username: str,
    db: Session = Depends(get_db),
):
    """Returns any user's want-to-watch and watched lists. No auth required."""
    
    # Gets the username provided from the db
    target = db.query(User).filter(User.username == username).first()
    
    # If that user does not exist raise of 404 error
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    # Get the watched and want-to-watch list for that inputted user
    all_entries = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.user_id == target.id,
        )
        .all()
    )
    
    # Return the watched and want-to-watch list of the inputted user
    return WatchlistOut(
        want_to_watch = [wtw for wtw in all_entries if wtw.list_type == ListType.want_to_watch],
        watched = [w for w in all_entries if w.list_type == ListType.watched],
    ) 
    
# ------------------------------------------
# POST Endpoints
# ------------------------------------------
    
@router.post("/want-to-watch", response_model=WatchlistEntryOut, status_code=status.HTTP_201_CREATED)
def add_to_want_to_watch(
    body: WatchlistEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a movie or TV show to the current user's want-to-watch list."""
    
    # If the inputted media is not of type movie or tv than raise 400 error
    if body.media_type not in (MediaType.movie, MediaType.tv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Media type must be 'movie' or 'tv'."
        )
        
    # Get the watchlist entry that matches the inputted media fo that user
    existing = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.user_id == current_user.id,
            WatchlistEntry.tmdb_id == body.tmdb_id,
            WatchlistEntry.media_type == body.media_type,
        )
        .first()
    )
    
    # Check if that media exists in the watchlist db for that user
    if existing:
        
        # If already in want-to-watch list raise 409 error
        if existing.list_type == ListType.want_to_watch:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already on want-to-watchlist"
            )
        
        # If already in watched list move to want-to-watch list and return it to the user
        if existing.list_type == ListType.watched:
            existing.list_type = ListType.want_to_watch
            db.commit()
            db.refresh(existing)
            return existing
        
    # Create the new entry to add to the db
    entry = WatchlistEntry(
        user_id=current_user.id,
        tmdb_id=body.tmdb_id,
        media_type=body.media_type,
        list_type=ListType.want_to_watch,
    )
    
    # Add the new entry to the db then return it to the user
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
        

@router.post("/watched", response_model=WatchlistEntryOut, status_code=status.HTTP_201_CREATED)
def add_to_watched(
    body: WatchlistEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a movie or TV show to the current user's watched list.
    If the item is already on the want-to-watch list it is promoted in place —
    the same row is updated so the entry id remains stable."""
    
    # If the inputted media is not of type movie or tv than raise 400 error
    if body.media_type not in (MediaType.movie, MediaType.tv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_type must be 'movie' or 'tv'",
        )

    # Get the watchlist entry that matches the inputted media fo that user
    existing = db.query(WatchlistEntry).filter(
        WatchlistEntry.user_id == current_user.id,
        WatchlistEntry.tmdb_id == body.tmdb_id,
        WatchlistEntry.media_type == body.media_type,
    ).first()

    # Check if that media exists in the watchlist db for that user
    if existing:
        
        # If the media is already in the watched list raise a 409 error
        if existing.list_type == ListType.watched:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already on watched list",
            )

        # Otherwise change the list type of the movie to watched and return it to the user
        existing.list_type = ListType.watched
        db.commit()
        db.refresh(existing)
        return existing

    # Create the new entry to add to the db
    entry = WatchlistEntry(
        user_id=current_user.id,
        tmdb_id=body.tmdb_id,
        media_type=body.media_type,
        list_type=ListType.watched,
    )
    
    # Add the new entry to the db then return it to the user
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

# ------------------------------------------
# DELETE Endpoints
# ------------------------------------------

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an entry from either list."""
    
    # Gets the entry from the db
    entry = _get_entry(entry_id, current_user.id, db)

    # If found remove it from the db
    db.delete(entry)
    db.commit()