from pydantic import BaseModel, Field
from typing import Optional


class Game(BaseModel):
    id: Optional[str] = None
    name: str
    publisher: str
    year: int = Field(ge=1950)
    system: str
    condition: str
    previousOwnerCount: int = Field(ge=0)
    owner_id: str
    owner: str


class GameCreate(BaseModel):
    name: str
    publisher: str
    year: int
    system: str
    condition: str
    previousOwnerCount: int
    owner_id: str

class GameUpdate(BaseModel):
    name: str | None = None
    publisher: str | None = None
    year: int | None = Field(default=None, ge=1950)
    system: str | None = None
    condition: str | None = None

