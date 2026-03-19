from pydantic import BaseModel

# This is the token pydantic model to allow for easy use of JWT tokens throughout the backend
class Token(BaseModel):
    access_token: str
    token_type: str