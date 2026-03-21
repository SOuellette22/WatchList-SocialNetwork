from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# This file holds the pydantic models for easy interaction with needed user data

# The basic user information that is needed
class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)

# The information that is needed to create a new user
class UserCreate(UserBase):
    password: str = Field(min_length=8)

# This is the information that a user will see if they are searching for a user that is not themself
class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    image_file: str | None
    image_path: str

# This extends UserPublic  and adds email since this is what a user will see observing their own page
class UserPrivate(UserPublic):
    email: EmailStr

# This is the information needed for the user to login
class UserLogin(BaseModel):
    username: str
    password: str