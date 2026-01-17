from pydantic import BaseModel, Field
from typing import Optional


class Game(BaseModel):
    id: Optional[int] = None
    name: str
    publisher: str
    year: int = Field(ge=1950)
    system: str
    condition: str
    previousOwnerCount: int = Field(ge=0)




