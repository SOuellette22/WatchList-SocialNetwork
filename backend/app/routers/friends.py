from datetime import datetime, timedelta, timezone
from webbrowser import get

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import ReturnsRows

from backend.app.database import get_db
from backend.app.models.friends import Friendship, FriendshipStatus
from backend.app.models.users import User
from backend.app.schemas.friends import FriendListOut, FriendRequestOut
from backend.app.schemas.users import UserPublic
from backend.app.services.auth import get_current_user

router = APIRouter(prefix="/api/friends", tags=["friends"])

DECLINE_COOLDOWN_MINUTES = 30

# --------------------------------------------------------------
# Internal Methods
# --------------------------------------------------------------

def _get_friendship(db: Session, user_a_id: int, user_b_id: int) -> Friendship | None:
    """Returns the friendship row between two users regardless of whi initiated it."""
    
    return (
        db.query(Friendship)
        .filter(
            or_( # This query checks if the user name combination is in one or the other
                (Friendship.requester_id == user_a_id) & (Friendship.addressee_id == user_b_id),
                (Friendship.requester_id == user_b_id) & (Friendship.addressee_id == user_a_id),
            )
        )
        .first()
    )
    
def _get_friends_for_user(db: Session, user_id: int) -> list[User]:
    """Returns all accepted friends for a given user id."""
    
    # Query to find if the username is part of any accepted friendships in the database
    rows = (
        db.query(Friendship)
        .filter(
            or_(Friendship.requester_id == user_id, 
                Friendship.addressee_id == user_id),
            Friendship.status == FriendshipStatus.accepted,
        )
        .all()
    )
    
    # This puts the list of all users friends into a list of user id's
    friends_ids = [
        row.addressee_id if row.requester_id == user_id else row.requester_id
        for row in rows
    ]
    
    # If the user does not have any friends return an empty list :(
    if not friends_ids:
        return []
    
    # return the query of all the user id's at are in the users friends list
    return db.query(User).filter(User.id.in_(friends_ids)).all()

# --------------------------------------------------------------
# Get API Endpoints
# --------------------------------------------------------------

@router.get("/", response_model=FriendListOut)
def get_my_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the current user's accepted friends list."""
    
    # Gets all the friends of the current user
    friends = _get_friends_for_user(db, current_user.id)
    
    # Returns the schema for the friends list out format
    return FriendListOut(friends=friends, total=len(friends))

@router.get("/requests", response_model=list[FriendRequestOut])
def get_incoming_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all the pending friend requests sent to the current user."""
    
    # This query checks if the current user has any pending friend requests
    rows = (
        db.query(Friendship)
        .filter(
            Friendship.addressee_id == current_user.id,
            Friendship.status == FriendshipStatus.pending,
        )
        .all()
    )
    
    # This returns all the user information of the users that have sent friend requests
    requesters = (
        db.query(User)
        .filter(
            User.id.in_(
                [r.requester_id for r in rows]
                )
            )
        .all()
    )
    
    # Returns a list of all the people that have requested to friend a user in the correct format
    return [FriendRequestOut(requester=u) for u in requesters]

# --------------------------------------------------------------
# Post API Endpoints
# --------------------------------------------------------------

@router.post("/{username}", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def send_friend_request(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a friend request to another user."""
    
    # Queries the User db to see if the inputted username is in the database
    target = db.query(User).filter(User.username == username).first()
    
    # If username not found return 404 error
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    # If the id of the target matches the current user return a 400 error
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add yourself as a friend"
        )
      
    # Get the row in the Friendship table with both the current user and the target  
    existing = _get_friendship(db, current_user.id, target.id)
    
    # Checks if the current user has friends
    if existing:
        
        # If the user friendship with the target is already excepted return a 409 error
        if existing.status == FriendshipStatus.accepted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already friends"
            )
        
        # Checks if the users friendship request is pending    
        if existing.status == FriendshipStatus.pending:
            
            if existing.requester_id == target.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This user has already sent you a friend request"
                )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Friend request already sent"
            )
            
        if existing.status == FriendshipStatus.declined:
            
            if existing.requester_id == current_user.id and existing.declined_at:
                cooldown_ends = existing.declined_at + timedelta(minutes=DECLINE_COOLDOWN_MINUTES)
                
                if datetime.now(timezone.utc).replace(tzinfo=None) < cooldown_ends:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"You must wait {DECLINE_COOLDOWN_MINUTES} minutes before sending another request to this user",
                    )
                    
            existing.requester_id = current_user.id
            existing.addressee_id = target.id
            existing.status = FriendshipStatus.pending
            existing.declined_at = None
            db.commit()
            return target
    
    db.add(Friendship(requester_id=current_user.id, addressee_id=target.id))
    db.commit()
    return target


@router.post("/{username}/accept", response_model=UserPublic)
def accept_friend_request(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept a pending friend request from another user."""
    
    requester = db.query(User).filter(User.username == username).first()
    
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    row = (
        db.query(Friendship)
        .filter(
            Friendship.requester_id == requester.id,
            Friendship.addressee_id == current_user.id,
            Friendship.status == FriendshipStatus.pending,
        )
        .first()
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending friend request from this user",
        )
        
    row.status = FriendshipStatus.accepted
    db.commit()
    return requester

@router.post("/{username}/decline",
             status_code=status.HTTP_204_NO_CONTENT
             )
def decline_friend_request(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Decline a pending friend request. The requester may retry after 30 minutes."""
    
    requester = db.query(User).filter(User.username == username).first()
    
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    row = (
        db.query(Friendship)
        .filter(
            Friendship.requester_id == requester.id,
            Friendship.addressee_id == current_user.id,
            Friendship.status == FriendshipStatus.pending,
        )
        .first()
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending friend request from this user",
        )
        
    row.status = FriendshipStatus.declined
    row.declined_at = datetime.now()
    db.commit()
    
# --------------------------------------------------------------
# Delete API Endpoints
# --------------------------------------------------------------

@router.delete("/{username}",
               status_code=status.HTTP_204_NO_CONTENT,
               )
def remove_friend(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an accepted friend, or cancel an outgoing pending request."""
    
    target = db.query(User).filter(User.username == username).first()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    row = _get_friendship(db, current_user.id, target.id)
    
    if not row or row.status == FriendshipStatus.declined:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No friendship or pending request found",
        )
        
    if row.status == FriendshipStatus.pending and row.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Cannot cancel a request you did not send",
        )
        
    db.delete(row)
    db.commit()