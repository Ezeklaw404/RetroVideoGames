from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    address: str



class UserUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None



class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    address: str