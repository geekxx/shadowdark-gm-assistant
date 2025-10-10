
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, select
from typing import Optional, List
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/shadowdark")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Shadowdark GM API")

@app.on_event("startup")
def startup():
    # Ensure pgvector extension exists
    with engine.connect() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
    from core.data.models import SQLModel as _S  # noqa
    SQLModel.metadata.create_all(engine)

@app.get("/health")
def health():
    return {"ok": True}

class SummarizeIn(BaseModel):
    text: str
    campaign_id: Optional[int] = None
    use_rag: bool = False
    save_to_db: bool = False
    sync_to_notion: bool = False
    session_title: Optional[str] = None

@app.post("/sessions/summarize")
def summarize(payload: SummarizeIn):
    from core.agents.session_scribe import summarize_text
    from core.agents.rag_librarian import search
    
    # Get RAG context if requested
    context_chunks = None
    if payload.use_rag:
        with Session(engine) as sess:
            # Use first part of text as search query
            search_query = payload.text[:500]
            chunks = search(sess, search_query, k=3)
            context_chunks = [chunk.text for chunk in chunks]
    
    # Generate notes
    with Session(engine) as sess:
        notes = summarize_text(
            payload.text,
            campaign_id=payload.campaign_id,
            context_chunks=context_chunks,
            db_session=sess if payload.save_to_db else None,
            use_mock=not bool(os.getenv("OPENAI_API_KEY", "").startswith("sk-"))
        )
    
    # Handle Notion sync if requested
    notion_page_url = None
    if payload.sync_to_notion:
        try:
            from core.integrations.notion_sync import NotionSync
            
            notion = NotionSync()
            if notion.test_connection():
                session_title = payload.session_title or "Session Notes"
                
                page = notion.create_session_page(
                    title=session_title,
                    content=notes,
                    properties={
                        "Campaign": {"multi_select": [{"name": f"Campaign {payload.campaign_id}"}]} if payload.campaign_id else None,
                        "Date": {"date": {"start": "2025-10-10"}}  # TODO: Use actual date
                    }
                )
                notion_page_url = page.get('url')
            else:
                raise Exception("Failed to connect to Notion API")
                
        except Exception as e:
            # If Notion sync fails, we still return the notes but with an error
            return {
                "notes": notes,
                "notion_error": str(e),
                "notion_page_url": None
            }
    
    return {
        "notes": notes,
        "notion_page_url": notion_page_url
    }

@app.get("/sessions/{session_id}/notes")
def get_session_notes(session_id: int):
    """Retrieve formatted session notes by session ID"""
    from core.data.models import Session as SessionModel
    
    with Session(engine) as sess:
        session = sess.get(SessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session.id,
            "campaign_id": session.campaign_id,
            "date": session.date,
            "notes": session.summary_md,
            "raw_transcript": session.gm_notes_md
        }

@app.get("/sessions")
def list_sessions(campaign_id: Optional[int] = None, limit: int = 20, offset: int = 0):
    """List sessions, optionally filtered by campaign"""
    from core.data.models import Session as SessionModel
    
    with Session(engine) as sess:
        query = select(SessionModel)
        if campaign_id:
            query = query.where(SessionModel.campaign_id == campaign_id)
        
        query = query.offset(offset).limit(limit)
        sessions = sess.exec(query).all()
        
        return {
            "sessions": [
                {
                    "id": s.id,
                    "campaign_id": s.campaign_id,
                    "date": s.date,
                    "has_notes": bool(s.summary_md),
                    "has_transcript": bool(s.gm_notes_md)
                } for s in sessions
            ],
            "total": len(sessions)
        }

# --- RAG endpoints ---
class IngestIn(BaseModel):
    text: str
    title: str | None = None
    source_id: str | None = None
    doctype: str | None = None

@app.post("/rag/ingest")
def rag_ingest(payload: IngestIn):
    from core.agents.rag_librarian import ingest_text
    with Session(engine) as sess:
        doc_id = ingest_text(sess, payload.text, title=payload.title, source_id=payload.source_id, doctype=payload.doctype)
    return {"document_id": doc_id}

class QueryIn(BaseModel):
    query: str
    k: int = 5

@app.post("/rag/query")
def rag_query(payload: QueryIn):
    from core.agents.rag_librarian import search
    with Session(engine) as sess:
        chunks = search(sess, payload.query, k=payload.k)
        return {"results": [{"id": c.id, "text": c.text, "page": c.page, "section": c.section, "document_id": c.document_id} for c in chunks]}
