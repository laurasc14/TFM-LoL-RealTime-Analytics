from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class Position(BaseModel):
    x: float
    y: float

class EventModel(BaseModel):
    match_id: str
    timestamp: datetime
    event_type: str
    player: str
    target: Optional[str] = None
    position: Optional[Position] = None
    extra: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
