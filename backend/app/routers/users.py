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

# This is how fastapi allows for easy modularization of the routs.
router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/register", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db :Session = Depends(get_db)):
    """Registers a new user and returns the created user with there email and not password"""
    
    # Checks if the username already exists in the database
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
        
    # Checks if the email already exists in the database
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
        
    # Sets up the new user with the inserted information
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        pass_hash=hash_password(user_in.password),
    )
    
    # Adds the new user to the database
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
    
    # Gets the username that was enterd from the database
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Checks is the username exists in the database while also checking if the passwords has matches
    if not user or not verify_password(form_data.password, user.pass_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Creates the JWT access token in the correct form
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserPrivate)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user"""
    return current_user