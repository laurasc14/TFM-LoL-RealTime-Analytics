from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class Ban(BaseModel):
    champion_id: int
    pick_turn: int

class Objectives(BaseModel):
    barons: int
    dragons: int
    towers: int
    inhibitors: int

class Team(BaseModel):
    team_id: int
    win: bool
    bans: List[Ban]
    objectives: Objectives

class MatchModel(BaseModel):
    match_id: str
    game_mode: str
    map_id: int
    duration: int
    start_time: datetime
    end_time: datetime
    teams: List[Team]
    created_at: datetime = Field(default_factory=datetime.utcnow)
