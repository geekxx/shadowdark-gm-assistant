
import os, re, hashlib
from typing import List, Dict, Tuple
import numpy as np
from sqlalchemy import text
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

def upsert_chunks(sess: Session, doc: Document, chunks: List[Tuple[str, Dict]]):
    for txt, meta in chunks:
        emb = embed_local(txt)
        c = Chunk(document_id=doc.id, text=txt, page=meta.get('page'), section=meta.get('section'), embedding=emb, meta=meta)
        sess.add(c)
    sess.commit()

def query(sess: Session, qtext: str, k: int = 5) -> List[Chunk]:
    qvec = embed_local(qtext)
    
    # Convert to string format that PostgreSQL can parse as a vector
    vec_str = '[' + ','.join(map(str, qvec)) + ']'
    
    stmt = text("""
        SELECT id FROM chunk 
        ORDER BY embedding <=> CAST(:qvec AS vector)
        LIMIT :k
    """).bindparams(qvec=vec_str, k=k)
    result = sess.exec(stmt)
    ids = [r[0] for r in result]
    
    if not ids:
        return []
    return list(sess.exec(select(Chunk).where(Chunk.id.in_(ids))))
