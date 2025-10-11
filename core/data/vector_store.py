
import os, re, hashlib
from typing import List, Dict, Tuple
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from .models import Chunk, Document, EMBED_DIM

def _hash_token(token: str, dim: int) -> int:
    h = int(hashlib.sha1(token.encode('utf-8')).hexdigest(), 16)
    return h % dim

def embed_local(text: str, dim: int = EMBED_DIM) -> List[float]:
    vec = np.zeros(dim, dtype=np.float32)
    tokens = re.findall(r"\w+", text.lower())
    for t in tokens:
        idx = _hash_token(t, dim)
        vec[idx] += 1.0
    n = np.linalg.norm(vec) or 1.0
    return (vec / n).tolist()

def upsert_chunks(sess: Session, doc: Document, chunks: List[Tuple[str, Dict]], classify_content: bool = True):
    """
    Upsert text chunks with optional intelligent content classification
    
    Args:
        sess: Database session
        doc: Parent document 
        chunks: List of (text, metadata) tuples
        classify_content: Whether to auto-classify chunk content types
    """
    from core.agents.rag_librarian import _classify_chunk_content
    
    for txt, meta in chunks:
        emb = embed_local(txt)
        
        # Determine chunk type
        chunk_type = meta.get('chunk_type')
        if classify_content and not chunk_type:
            chunk_type = _classify_chunk_content(txt, doc.doctype)
        
        c = Chunk(
            document_id=doc.id, 
            text=txt, 
            page=meta.get('page'), 
            section=meta.get('section'),
            chunk_type=chunk_type,
            embedding=emb, 
            meta=meta
        )
        sess.add(c)
    sess.commit()

def query(sess: Session, qtext: str, k: int = 5, chunk_types: List[str] = None) -> List[Chunk]:
    """
    Query chunks with optional filtering by content types
    
    Args:
        sess: Database session
        qtext: Query text 
        k: Number of results to return
        chunk_types: Optional list of chunk types to filter by (e.g., ['monster', 'spell'])
    
    Returns:
        List of most relevant chunks
    """
    qvec = embed_local(qtext)
    
    # Convert to string format that PostgreSQL can parse as a vector
    vec_str = '[' + ','.join(map(str, qvec)) + ']'
    
    # Build query with optional type filtering
    if chunk_types:
        type_filter = "AND c.chunk_type = ANY(:types)"
        stmt = text(f"""
            SELECT c.id FROM chunk c
            WHERE 1=1 {type_filter}
            ORDER BY c.embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """).bindparams(qvec=vec_str, k=k, types=chunk_types)
    else:
        stmt = text("""
            SELECT c.id FROM chunk c
            ORDER BY c.embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """).bindparams(qvec=vec_str, k=k)
    
    result = sess.exec(stmt)
    ids = [r[0] for r in result]
    
    if not ids:
        return []
    
    # Load chunks with document relationships
    chunks = sess.exec(
        select(Chunk)
        .options(selectinload(Chunk.document))
        .where(Chunk.id.in_(ids))
    ).all()
    
    return list(chunks)
