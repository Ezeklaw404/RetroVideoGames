from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    address: str



class UserUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None



class User(BaseModel):
    id: Optional[str]
    name: str
    email: EmailStr
    address: str
    links: Dict[str, str] = {}