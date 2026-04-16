from collections import defaultdict, Counter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.status import HTTP_204_NO_CONTENT

from backend.app.database import get_db
from backend.app.models.users import User
from backend.app.models.watchlist import EmojiRating, ListType, MediaType, WatchlistEntry
from backend.app.schemas.watchlist import (
    EmojiCount,
    EmojiRatingCreate,
    EmojiRatingOut,
    FriendEmoji,
    SUGGESTED_EMOJIS,
    WatchlistEntryWithFriendEmojis,
    WatchlistEntryCreate,
    WatchlistEntryOut,
    WatchlistOut,
)
from backend.app.services.auth import get_current_user, get_optional_current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

def _get_friends_for_user(db: Session, user_id: int):
    """Compatibility wrapper for friend lookup used by watchlist routes.
    This avoids a direct module-level import of a private helper from another
    router while preserving the existing behavior until the shared logic can
    be moved into a dedicated service module.
    """
    from backend.app.routers import friends as friends_router
    
    return friends_router._get_friends_for_user(db, user_id)

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
    """Returns the current user's want-to-watch and watched lists.
    Want-to-watch entries include emojis left by friends on the same items.
    Watched entries include the user's own emoji rating."""

    all_entries = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.user_id == current_user.id)
        .all()
    )

    # Saves all the want to watch and watched movies/shows for the current user into there receptive lists.
    want_to_watch = [e for e in all_entries if e.list_type == ListType.want_to_watch]
    watched = [e for e in all_entries if e.list_type == ListType.watched]

    # --- Below handles friends emoji ratings showing up in users want-to-watch list ---
    friends = _get_friends_for_user(db, current_user.id)
    friend_ids = [f.id for f in friends]

    # Makes a list of the want to watch list with only the tmdb_id and the media_type
    wtw_pairs = [(e.tmdb_id, e.media_type) for e in want_to_watch]
    wtw_tmdb_ids = [tmdb_id for tmdb_id, _ in wtw_pairs]          
                                                                                                                                                
    friend_emoji_rows = (                                                                                                                       
        db.query(EmojiRating, User.username)                                                                                                    
        .join(User, User.id == EmojiRating.user_id)                                                                                             
        .filter(                                                                                 
            EmojiRating.user_id.in_(friend_ids),    
            EmojiRating.tmdb_id.in_(wtw_tmdb_ids),
        )                                                                                                                                       
        .all()
        if friend_ids and wtw_tmdb_ids else []                                                                                                  
    )

    # this process makes sure that only friends username and emoji are added to the friend_emoji_map for later use
    friend_emoji_map: dict[tuple, list] = defaultdict[tuple, list](list)
    wtw_pairs_set = set[tuple[int , MediaType]](wtw_pairs)
    for rating, username in friend_emoji_rows:
        if (rating.tmdb_id, rating.media_type) in wtw_pairs_set:
            friend_emoji_map[(rating.tmdb_id, rating.media_type)].append(
                FriendEmoji(username=username, emoji=rating.emoji)
            )

    # Puts the friends username and emoji data into a more useful format along with making ready be be returned to the user
    wtw_with_friends = [
        WatchlistEntryWithFriendEmojis(
            id=entry.id,
            tmdb_id=entry.tmdb_id,
            media_type=entry.media_type,
            list_type=entry.list_type,
            emoji=None,
            friend_emojis=friend_emoji_map.get((entry.tmdb_id, entry.media_type), []),
        )
        for entry in want_to_watch
    ]

    # --- Below handles user's own emoji on watched list ---
    
    # Gets the emojis the current users has on there watched list
    my_ratings = (
        db.query(EmojiRating)
        .filter(
            EmojiRating.user_id == current_user.id,
            EmojiRating.tmdb_id.in_([e.tmdb_id for e in watched]),
        )
        .all()
    )
    my_emoji_map = {(r.tmdb_id, r.media_type): r.emoji for r in my_ratings}

    # Puts the emoji the current user has on their watched list into a useful format along with making it ready to return
    watched_with_emoji = [
        WatchlistEntryOut(
            id=entry.id,
            tmdb_id=entry.tmdb_id,
            media_type=entry.media_type,
            list_type=entry.list_type,
            emoji=my_emoji_map.get((entry.tmdb_id, entry.media_type)),
        )
        for entry in watched
    ]

    # Returns the wanted to watch list and watched list with emojis of friends and self included
    return WatchlistOut(want_to_watch=wtw_with_friends, watched=watched_with_emoji)
    
    
@router.get("/emoji/suggestions", response_model=list[str])
def get_emoji_suggestions():
    """Return the list of suggested emojis for the quick-pick UI. No auth required."""
    return SUGGESTED_EMOJIS
    
    
@router.get("/emoji/{tmdb_id}/{media_type}", response_model=list[EmojiCount])
def get_emoji_ratings(
    tmdb_id: int,
    media_type: str,
    db: Session = Depends(get_db),
):
    """Return aggregated emoji counts for a specific movie or show. No auth required."""
    
    # Makes sure that the media type inputted is valid
    if media_type not in (MediaType.movie, MediaType.tv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_type must be 'movie' or 'tv'",
        )

    # Gets the emoji ratings of a specific movie/show
    rows = db.query(EmojiRating).filter(
        EmojiRating.tmdb_id == tmdb_id,
        EmojiRating.media_type == media_type,
    ).all()
    
    # Saves the emoji into a counter to allow for easy display according to spec
    counts = Counter(r.emoji for r in rows)
    return [EmojiCount(emoji=emoji, count=count) for emoji, count in counts.items()]
    
    
@router.get("/{username}", response_model=WatchlistOut)
def get_user_watchlist(
    username: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Returns any user's want-to-watch and watched lists.
    If the requester is authenticated, want-to-watch entries include their friends' emojis.
    Watched entries always include the target user's own emoji ratings."""

    # Gets the searched user from the database and makes sure they exist
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Gets all the watchlist entries for the searched user
    all_entries = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.user_id == target.id)
        .all()
    )

    # Saves all the want to watch and watched movies/shows for the searched user into there receptive lists.
    want_to_watch = [e for e in all_entries if e.list_type == ListType.want_to_watch]
    watched = [e for e in all_entries if e.list_type == ListType.watched]

    # --- Friend emojis: only if the requester is logged in ---
    
    # Checks to make sure that the current user is friends with the searched user
    if current_user:
        friends = _get_friends_for_user(db, current_user.id)
        friend_ids = [f.id for f in friends]
    else:
        friend_ids = []
        
    # Makes a list of the want to watch list with only the tmdb_id and the media_type
    wtw_pairs = [(e.tmdb_id, e.media_type) for e in want_to_watch]
    wtw_tmdb_ids = [tmdb_id for tmdb_id, _ in wtw_pairs]          
                                                                                                                                              
    friend_emoji_rows = (                                                                                                                       
        db.query(EmojiRating, User.username)                                                                                                    
        .join(User, User.id == EmojiRating.user_id)                                                                                             
        .filter(                                                                                 
            EmojiRating.user_id.in_(friend_ids),    
            EmojiRating.tmdb_id.in_(wtw_tmdb_ids),
        )                                                                                                                                       
        .all()
        if friend_ids and wtw_tmdb_ids else []                                                                                                  
    )

    # this process makes sure that only friends username and emoji are added to the friend_emoji_map for later use
    friend_emoji_map: dict[tuple, list] = defaultdict[tuple, list](list)
    wtw_pairs_set = set[tuple[int, MediaType]](wtw_pairs)
    for rating, uname in friend_emoji_rows:
        if (rating.tmdb_id, rating.media_type) in wtw_pairs_set:
            friend_emoji_map[(rating.tmdb_id, rating.media_type)].append(
                FriendEmoji(username=uname, emoji=rating.emoji)
            )

    # Puts the friends username and emoji data into a more useful format along with making ready be be returned to the user
    wtw_with_friends = [
        WatchlistEntryWithFriendEmojis(
            id=entry.id,
            tmdb_id=entry.tmdb_id,
            media_type=entry.media_type,
            list_type=entry.list_type,
            emoji=None,
            friend_emojis=friend_emoji_map.get((entry.tmdb_id, entry.media_type), []),
        )
        for entry in want_to_watch
    ]

    # --- Target user's own emoji on their watched entries ---
    
    # Gets the targets emojis that they have left on their watched list
    target_ratings = (
        db.query(EmojiRating)
        .filter(
            EmojiRating.user_id == target.id,
            EmojiRating.tmdb_id.in_([e.tmdb_id for e in watched]),
        )
        .all()
    )
    target_emoji_map = {(r.tmdb_id, r.media_type): r.emoji for r in target_ratings}

    # Puts the watched emoji of the searched user into a usable format for easy display later
    watched_with_emoji = [
        WatchlistEntryOut(
            id=entry.id,
            tmdb_id=entry.tmdb_id,
            media_type=entry.media_type,
            list_type=entry.list_type,
            emoji=target_emoji_map.get((entry.tmdb_id, entry.media_type)),
        )
        for entry in watched
    ]

    # return the searched user want-to-watch list along with their watched list and the emojis needed
    return WatchlistOut(want_to_watch=wtw_with_friends, watched=watched_with_emoji) 
    
# ------------------------------------------
# POST Endpoints
# ------------------------------------------

@router.post("/emoji", response_model=EmojiRatingOut, status_code=status.HTTP_201_CREATED)
def set_emoji_rating(
    body: EmojiRatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit or replace the authenticated user's emoji for a watched item. The item must be on the user's watch list - returns 403 otherwise."""
    
    # Makes sure that the media type inputted is valid
    if body.media_type not in (MediaType.movie, MediaType.tv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_type must be 'movie' or 'tv'",
        )
        
    # Gets the movie/show that are in the current user searched in their watched list
    watched_entry = db.query(WatchlistEntry).filter(
        WatchlistEntry.user_id == current_user.id,
        WatchlistEntry.tmdb_id == body.tmdb_id,
        WatchlistEntry.media_type == body.media_type,
        WatchlistEntry.list_type == ListType.watched,
    ).first()
    
    # If the watched list search does not have anything raise a 403 error
    if not watched_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Item must be on your watch list to rate it.",
        )
        
    # Get the emoji that user has put on that movie/show
    existing = db.query(EmojiRating).filter(
        EmojiRating.user_id == current_user.id,
        EmojiRating.tmdb_id == body.tmdb_id,
        EmojiRating.media_type == body.media_type,
    ).first()
    
    # If that emoji data exists already replace the out emoji with the new one
    if existing:
        existing.emoji = body.emoji
        db.commit()
        db.refresh(existing)
        return existing

    # If the emoji data does not exist add it to the database
    rating = EmojiRating(
        user_id=current_user.id,
        tmdb_id=body.tmdb_id,
        media_type=body.media_type,
        emoji=body.emoji,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating
    
    
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
            db.query(EmojiRating).filter(
                EmojiRating.user_id == current_user.id,
                EmojiRating.tmdb_id == existing.tmdb_id,
                EmojiRating.media_type == existing.media_type,
            ).delete()
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
    
    # Remove the emoji data from the emoji table as well
    db.query(EmojiRating).filter(
        EmojiRating.user_id == current_user.id,
        EmojiRating.tmdb_id == entry.tmdb_id,
        EmojiRating.media_type == entry.media_type,
    ).delete()

    # If found remove it from the db
    db.delete(entry)
    db.commit()
    

@router.delete("/emoji/{tmdb_id}/{media_type}", status_code=HTTP_204_NO_CONTENT)
def delete_emoji_rating(
    tmdb_id: int,
    media_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the authenticated user's emoji for a specific movie or show."""

    # Makes sure that the media type inputted is valid
    if media_type not in (MediaType.movie, MediaType.tv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_type must be 'movie' or 'tv'",
        )

    # Gets the current users emoji date left on the inputted movie/show
    rating = db.query(EmojiRating).filter(
        EmojiRating.user_id == current_user.id,
        EmojiRating.tmdb_id == tmdb_id,
        EmojiRating.media_type == media_type,
    ).first()

    # If that data does not exist raise a 404 error
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No emoji rating found for this item.",
        )

    # If is does delete it from the database
    db.delete(rating)
    db.commit()