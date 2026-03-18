from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.users import User
from backend.app.schemas.token import Token
from backend.app.schemas.users import UserCreate, UserPrivate, UserPublic
from backend.app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password, 
    verify_password,
)
from backend.app.config import settings

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/register", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db :Session = Depends(get_db)):
    """Registers a new user and returns the created user with there email and not password"""
    
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
        
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
        
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        pass_hash=hash_password(user_in.password),
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2 login endpoint. Accept form fields: username and password
    Returns a JWT access token on success
    """
    
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.pass_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserPrivate)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user"""
    return current_user