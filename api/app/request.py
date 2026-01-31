from pydantic import BaseModel
from typing import Optional


class RequestCreate(BaseModel):
    requesterId: str
    requestedGameId: str
    offeredGameId: str
    clientId: str



class Request(BaseModel):
    id: Optional[str] = None
    requester: str
    requestedGame: str
    offeredGame: str
    client: str  
    accepted: Optional[bool] = False

class AcceptRequest(BaseModel):
    accepted: bool = False