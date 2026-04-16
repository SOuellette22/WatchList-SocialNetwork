from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from pwdlib import PasswordHash

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.users import User

pass_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/users/token", auto_error=False)

def hash_password(password: str) -> str:
    """This will hash the password (string) that is given to it"""
    return pass_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """This verifys that the password given matches the hash that is in the database"""
    return pass_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token"""

    to_encode = data.copy()
    
    # Checks if there is a timedelta passed in otherwise uses the default one that is in the config.py file
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )

    # This makes sure that the JWT access token is properly formatted and properly encrypted
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )

    return encode_jwt


def verify_access_token(token: str) -> str | None:
    """Verify a JWT access token and return the subject (user id) if valid"""
    try:
        # Decodes the given token back into the needed information
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    else:
        # Returns the user id if the token is valid
        return payload.get("sub")
    
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get the current user from the JWT token"""
    
    # Expception to through if something goes wrong
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verifys that the token is valid if not raise the exception above
    user_id = verify_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Checks if the user is in the database if not raise the exception above
    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    
    # Return user if token is valid and gave a valid user id
    return user


def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the current user if a valid token is provided, otherwise None."""
    
    # If token does not exist return None
    if not token:
        return None
    
    # Since token exists verify it is a user
    user_id = verify_access_token(token)
    
    # If not user return None
    if user_id is None:
        return None
    
    # Return the user from the database
    return db.get(User, int(user_id))