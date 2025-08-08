from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class PlayerModel(BaseModel):
    match_id: str
    summoner_id: str
    summoner_name: str
    team_id: int
    champion_id: int
    role: str
    kills: int
    deaths: int
    assists: int
    gold_earned: int
    cs: int
    items: List[int]
    runes: List[int]
    spells: List[int]
    performance_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
