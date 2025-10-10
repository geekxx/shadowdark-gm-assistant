
from pydantic import BaseModel
from typing import List, Dict, Optional

class NPCSchema(BaseModel):
    name: str
    tags: List[str] = []
    attitude: Optional[str] = None
    hook: Optional[str] = None
    stat_block: Dict
    portrait_uri: Optional[str] = None
    token_uri: Optional[str] = None

class MonsterSchema(BaseModel):
    name: str
    tier: Optional[int] = None
    traits: List[str] = []
    stat_block: Dict
    lore: Optional[str] = None
    treasure: Optional[str] = None
    token_uri: Optional[str] = None
