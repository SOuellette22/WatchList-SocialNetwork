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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

def hash_password(password: str) -> str:
    return pass_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pass_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token"""

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )

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
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=settings.algorithm,
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get the current user from the JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    
    return user