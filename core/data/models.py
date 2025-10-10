
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import String, Integer
from pgvector.sqlalchemy import Vector

# --- Core domain tables ---
class Campaign(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    style_prefs: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    rulesets: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    house_rules: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: Optional[int] = Field(default=None, foreign_key="campaign.id")
    date: Optional[str] = None
    audio_uri: Optional[str] = None
    transcript_uri: Optional[str] = None
    summary_md: Optional[str] = None
    gm_notes_md: Optional[str] = None

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id")
    ts: Optional[float] = 0.0
    type: str
    payload_json: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

class NPC(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    stat_json: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    portrait_uri: Optional[str] = None
    token_uri: Optional[str] = None

class Monster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    stat_json: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    token_uri: Optional[str] = None
    source_ref: Optional[str] = None

# --- RAG tables ---
EMBED_DIM = 384  # keep in sync with embedder

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[str] = None         # path, notion page id, etc.
    doctype: Optional[str] = None           # 'rule' | 'note' | 'transcript' | 'compendium' | 'csv'
    title: Optional[str] = None
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

class Chunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    embedding: List[float] = Field(sa_column=Column(Vector(EMBED_DIM)))
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
