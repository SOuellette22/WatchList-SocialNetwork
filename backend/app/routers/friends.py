from datetime import datetime, timedelta, timezone
from webbrowser import get

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import ReturnsRows
from starlette.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_429_TOO_MANY_REQUESTS

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
            or_(
                (Friendship.requester_id == user_a_id) & (Friendship.addressee_id == user_b_id),
                (Friendship.requester_id == user_b_id) & (Friendship.addressee_id == user_a_id),
                
            )
        )
        .first()
    )
    
def _get_friends_for_user(db: Session, user_id: int) -> list[User]:
    """Returns all accepted friends for a given user id."""
    
    rows = (
        db.query(Friendship)
        .filter(
            or_(Friendship.requester_id == user_id, 
                Friendship.addressee_id == user_id),
            Friendship.status == FriendshipStatus.accepted,
        )
        .all()
    )
    friends_ids = [
        row.addressee_id if row.requester_id == user_id else row.requester_id
        for row in rows
    ]
    
    if not friends_ids:
        return []
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
    friends = _get_friends_for_user(db, current_user.id)
    return FriendListOut(friends=friends, total=len(friends))

@router.get("/requests", response_model=list[FriendRequestOut])
def get_incoming_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all the pending friend requests sent to the current user."""
    
    rows = (
        db.query(Friendship)
        .filter(
            Friendship.addressee_id == current_user.id,
            Friendship.status == FriendshipStatus.pending,
        )
        .all()
    )
    
    requesters = (
        db.query(User)
        .filter(
            User.id.in_(
                [r.requester_id for r in rows]
                )
            )
        .all()
    )
    
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
    
    target = db.query(User).filter(User.username == username).first()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    if target.id == current_user.id:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Cannot add yourself as a friend"
        )
        
    existing = _get_friendship(db, current_user.id, target.id)
    
    if existing:
        
        if existing.status == FriendshipStatus.accepted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already friends"
            )
            
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
                        status_code=HTTP_429_TOO_MANY_REQUESTS,
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
             status_code=HTTP_204_NO_CONTENT
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