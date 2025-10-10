
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, select
from typing import Optional, List
import os
import tempfile
from pathlib import Path

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
    play_group: Optional[str] = "Online"  # Default to Online

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
                        "Play Group": {"select": {"name": payload.play_group or "Online"}},
                        "Status": {"select": {"name": "Draft"}}        # Start as draft for review
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

# --- Audio processing endpoints ---

@app.post("/sessions/summarize-audio")
async def summarize_audio_endpoint(
    audio_file: UploadFile = File(...),
    campaign_id: Optional[int] = None,
    use_rag: bool = False,
    save_to_db: bool = False,
    sync_to_notion: bool = False,
    session_title: Optional[str] = None,
    play_group: Optional[str] = "Online",
    huggingface_token: Optional[str] = None
):
    """
    Process audio file for speaker diarization and generate session notes.
    
    Upload an audio file (WAV, MP3, M4A, FLAC, OGG) and get back session notes
    with speaker identification and timeline.
    """
    # Validate file type
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
    file_extension = Path(audio_file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format: {file_extension}. "
                   f"Supported formats: {', '.join(allowed_extensions)}"
        )
    
    # Create temporary file for processing
    temp_file = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            content = await audio_file.read()
            tmp.write(content)
            temp_file = tmp.name
        
        # Get RAG context if requested
        context_chunks = None
        if use_rag:
            from core.agents.rag_librarian import search
            with Session(engine) as sess:
                # Use filename as initial search query
                search_query = f"session audio recording {Path(audio_file.filename).stem}"
                chunks = search(sess, search_query, k=3)
                context_chunks = [chunk.text for chunk in chunks]
        
        # Process audio and generate notes
        from core.agents.session_scribe import summarize_audio
        
        # Use environment variable if token not provided
        token = huggingface_token or os.getenv("HUGGINGFACE_TOKEN")
        
        with Session(engine) as sess:
            notes = summarize_audio(
                audio_path=temp_file,
                campaign_id=campaign_id,
                context_chunks=context_chunks,
                db_session=sess if save_to_db else None,
                huggingface_token=token,
                use_mock=not bool(os.getenv("OPENAI_API_KEY", "").startswith("sk-"))
            )
        
        # Handle Notion sync if requested
        notion_page_url = None
        if sync_to_notion:
            try:
                from core.integrations.notion_sync import NotionSync
                
                notion = NotionSync()
                if notion.test_connection():
                    title = session_title or f"Audio Session - {Path(audio_file.filename).stem}"
                    
                    page = notion.create_session_page(
                        title=title,
                        content=notes,
                        properties={
                            "Play Group": {"select": {"name": play_group or "Online"}},
                            "Status": {"select": {"name": "Draft"}}
                        }
                    )
                    notion_page_url = page.get('url')
                else:
                    raise Exception("Failed to connect to Notion API")
                    
            except Exception as e:
                return {
                    "notes": notes,
                    "notion_error": str(e),
                    "notion_page_url": None,
                    "audio_filename": audio_file.filename
                }
        
        return {
            "notes": notes,
            "notion_page_url": notion_page_url,
            "audio_filename": audio_file.filename
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful error messages for common issues
        if "gated repo" in error_msg.lower() or "access" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "HuggingFace model access required",
                    "message": error_msg,
                    "instructions": [
                        "Visit: https://huggingface.co/pyannote/speaker-diarization-community-1",
                        "Click 'Agree and access repository'",
                        "Create a token at: https://huggingface.co/settings/tokens", 
                        "Provide token via huggingface_token parameter or HUGGINGFACE_TOKEN env var"
                    ]
                }
            )
        else:
            raise HTTPException(status_code=500, detail=f"Audio processing failed: {error_msg}")
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

@app.post("/audio/diarize")
async def diarize_audio(
    audio_file: UploadFile = File(...),
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    huggingface_token: Optional[str] = None
):
    """
    Perform speaker diarization only (no session note generation).
    
    Returns speaker timeline and statistics.
    """
    # Validate file type
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
    file_extension = Path(audio_file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_extension}. "
                   f"Supported formats: {', '.join(allowed_extensions)}"
        )
    
    temp_file = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            content = await audio_file.read()
            tmp.write(content)
            temp_file = tmp.name
        
        # Perform diarization
        from core.agents.diarizer import SpeakerDiarizer
        
        token = huggingface_token or os.getenv("HUGGINGFACE_TOKEN")
        diarizer = SpeakerDiarizer(huggingface_token=token)
        
        result = diarizer.diarize_audio(
            temp_file,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )
        
        # Create speaker mapping
        speaker_mapping = diarizer.get_speaker_mapping(result)
        
        # Format response
        return {
            "filename": audio_file.filename,
            "duration": result.total_duration,
            "num_speakers": result.num_speakers,
            "speaker_stats": result.speaker_stats,
            "speaker_mapping": speaker_mapping,
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "duration": seg.duration,
                    "speaker_id": seg.speaker_id,
                    "speaker_name": speaker_mapping.get(seg.speaker_id, seg.speaker_id)
                }
                for seg in result.segments
            ]
        }
        
    except Exception as e:
        error_msg = str(e)
        
        if "gated repo" in error_msg.lower() or "access" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "HuggingFace model access required",
                    "message": error_msg,
                    "instructions": [
                        "Visit: https://huggingface.co/pyannote/speaker-diarization-community-1",
                        "Click 'Agree and access repository'",
                        "Create a token at: https://huggingface.co/settings/tokens",
                        "Provide token via huggingface_token parameter or HUGGINGFACE_TOKEN env var"
                    ]
                }
            )
        else:
            raise HTTPException(status_code=500, detail=f"Diarization failed: {error_msg}")
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
