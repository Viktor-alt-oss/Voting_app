from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PollBase(BaseModel):
    question: str

class PollCreate(PollBase):
    category_id: Optional[int] = None

class PollOut(PollBase):
    id: int
    created_at: datetime
    category_id: Optional[int]

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    description: Optional[str] = None

class CategoryOut(CategoryBase):
    id: int
    description: Optional[str]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str