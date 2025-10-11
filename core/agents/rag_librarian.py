
import os
import re
from pathlib import Path
from typing import List, Dict, Union, Optional
import fitz  # PyMuPDF
import tiktoken
from sqlmodel import Session
from core.data.models import Document
from core.data.vector_store import upsert_chunks, query as vs_query

def _count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens for a given text using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to rough character-based estimation (1 token ≈ 4 chars)
        return len(text) // 4

def _smart_split_text(
    text: str, 
    max_tokens: int = 300, 
    overlap_tokens: int = 30,
    preserve_paragraphs: bool = True
) -> List[str]:
    """
    Intelligent text chunking that respects document structure
    
    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
        preserve_paragraphs: Try to keep paragraphs intact
    
    Returns:
        List of text chunks
    """
    if preserve_paragraphs:
        # Split by double newlines (paragraphs) first
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
    else:
        # Split by sentences
        paragraphs = re.split(r'(?<=[.!?])\s+', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for paragraph in paragraphs:
        para_tokens = _count_tokens(paragraph)
        
        # If single paragraph exceeds max_tokens, split it further
        if para_tokens > max_tokens:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            # Split large paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            temp_chunk = []
            temp_tokens = 0
            
            for sentence in sentences:
                sent_tokens = _count_tokens(sentence)
                if temp_tokens + sent_tokens > max_tokens and temp_chunk:
                    chunks.append(' '.join(temp_chunk))
                    # Add overlap
                    if len(temp_chunk) > 1:
                        overlap_text = ' '.join(temp_chunk[-2:])
                        if _count_tokens(overlap_text) <= overlap_tokens:
                            temp_chunk = temp_chunk[-2:] + [sentence]
                            temp_tokens = _count_tokens(' '.join(temp_chunk))
                        else:
                            temp_chunk = [sentence]
                            temp_tokens = sent_tokens
                    else:
                        temp_chunk = [sentence]
                        temp_tokens = sent_tokens
                else:
                    temp_chunk.append(sentence)
                    temp_tokens += sent_tokens
            
            if temp_chunk:
                chunks.append(' '.join(temp_chunk))
            continue
        
        # Normal paragraph processing
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
            # Add overlap from previous chunk
            if len(current_chunk) > 0:
                overlap_text = current_chunk[-1]
                if _count_tokens(overlap_text) <= overlap_tokens:
                    current_chunk = [overlap_text, paragraph]
                    current_tokens = _count_tokens('\n\n'.join(current_chunk))
                else:
                    current_chunk = [paragraph]
                    current_tokens = para_tokens
            else:
                current_chunk = [paragraph]
                current_tokens = para_tokens
        else:
            current_chunk.append(paragraph)
            current_tokens += para_tokens
    
    # Add final chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return [chunk for chunk in chunks if chunk.strip()]

def _extract_pdf_text(pdf_path: str) -> Dict[str, str]:
    """Extract text from PDF with page information"""
    doc = fitz.open(pdf_path)
    pages = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            pages[f"page_{page_num + 1}"] = text
    
    doc.close()
    return pages

def _read_markdown_file(md_path: str) -> str:
    """Read markdown file"""
    with open(md_path, 'r', encoding='utf-8') as f:
        return f.read()

def ingest_text(
    sess: Session, 
    text: str, 
    title: str = None, 
    source_id: str = None, 
    doctype: str = None, 
    meta: Dict = None,
    classify_chunks: bool = True
) -> int:
    """Ingest plain text into the knowledge base"""
    doc = Document(title=title, source_id=source_id, doctype=doctype, meta=meta or {})
    sess.add(doc)
    sess.commit()
    sess.refresh(doc)
    
    pieces = _smart_split_text(text)
    metas = [{"page": meta.get("page") if meta else None, "section": None} for _ in pieces]
    upsert_chunks(sess, doc, list(zip(pieces, metas)), classify_content=classify_chunks)
    return doc.id

def ingest_file(
    sess: Session,
    file_path: Union[str, Path],
    title: str = None,
    doctype: str = None,
    meta: Dict = None,
    classify_chunks: bool = True
) -> int:
    """
    Ingest a file (PDF or Markdown) into the knowledge base
    
    Args:
        sess: Database session
        file_path: Path to the file to ingest
        title: Optional title (defaults to filename)
        doctype: Document type (rule, note, transcript, etc.)
        meta: Additional metadata
    
    Returns:
        Document ID
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    title = title or file_path.stem
    source_id = str(file_path)
    file_meta = meta or {}
    file_meta.update({
        "filename": file_path.name,
        "file_size": file_path.stat().st_size,
        "file_type": file_path.suffix.lower()
    })
    
    # Create document record
    doc = Document(
        title=title,
        source_id=source_id,
        doctype=doctype or _infer_doctype(file_path),
        meta=file_meta
    )
    sess.add(doc)
    sess.commit()
    sess.refresh(doc)
    
    # Extract and chunk content
    if file_path.suffix.lower() == '.pdf':
        pages = _extract_pdf_text(str(file_path))
        all_chunks = []
        
        for page_key, page_text in pages.items():
            page_num = int(page_key.split('_')[1])
            chunks = _smart_split_text(page_text)
            
            for chunk in chunks:
                chunk_meta = {
                    "page": page_num,
                    "section": None,
                    "source_file": file_path.name
                }
                all_chunks.append((chunk, chunk_meta))
        
        upsert_chunks(sess, doc, all_chunks, classify_content=classify_chunks)
        
    elif file_path.suffix.lower() in ['.md', '.markdown', '.txt']:
        text = _read_markdown_file(str(file_path))
        chunks = _smart_split_text(text, preserve_paragraphs=True)
        
        chunk_metas = []
        for i, chunk in enumerate(chunks):
            # Try to extract section headers from markdown
            section = _extract_section_header(chunk)
            chunk_meta = {
                "page": None,
                "section": section,
                "chunk_index": i,
                "source_file": file_path.name
            }
            chunk_metas.append(chunk_meta)
        
        upsert_chunks(sess, doc, list(zip(chunks, chunk_metas)), classify_content=classify_chunks)
    
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    return doc.id

def _classify_chunk_content(text: str, fallback_type: str = None) -> str:
    """
    Classify a chunk based on its content patterns
    
    Args:
        text: The chunk text to analyze
        fallback_type: Default type if no specific pattern matches
    
    Returns:
        Classified chunk type (monster, spell, rule, table, etc.)
    """
    text_lower = text.lower()
    
    # Monster stat block patterns
    monster_patterns = [
        r'\b(?:ac|armor class)\s*[\d\+\-]+',
        r'\b(?:hp|hit points)\s*\d+',
        r'\b(?:str|dex|con|int|wis|cha)\s*[\d\+\-]+',
        r'\b(?:melee|ranged)\s+attack\s*[:\+]',
        r'\b(?:damage|dmg)\s*[\dd\+\-\s]+',
        r'\b(?:cr|challenge rating)\s*[\d\/]+',
        r'\barmor class\b.*\bhit points\b',
        r'\bspeed\s*\d+\s*ft',
        r'\bsaving throws?\b',
        r'\bskills?\s*:',
        r'\bactions?\s*$',
        r'\blegendary actions?\b'
    ]
    
    # Spell patterns
    spell_patterns = [
        r'\b(?:level|lvl)\s*[0-9]\s*(?:spell|cantrip)',
        r'\bschool\s*:?\s*(?:abjuration|conjuration|divination|enchantment|evocation|illusion|necromancy|transmutation)',
        r'\bcasting time\s*:',
        r'\brange\s*:?\s*(?:\d+\s*ft|self|touch|sight)',
        r'\bcomponents\s*:?\s*[vsm]',
        r'\bduration\s*:',
        r'\bconcentration\b',
        r'\bat higher levels\b',
        r'\bupcasting\b',
        r'\bspell attack\b',
        r'\bsave\s*(?:dc|difficulty)',
        r'\bcantrip\b'
    ]
    
    # Table patterns  
    table_patterns = [
        r'\b(?:roll|d\d+)\s+(?:result|effect|outcome)',
        r'^\s*\d+[-–]\d+\s+',  # Range entries like "01-10"
        r'^\s*\d+\s+[^\d]',    # Numbered entries like "1 Goblin"
        r'\| *[^\|]+ *\| *[^\|]+ *\|',  # Markdown table format
        r'\b(?:random|encounter|treasure|loot)\s+table\b',
        r'\bgenerator\b.*\btable\b',
        r'^\s*\d{1,2}[\.:]',   # Numbered list entries
        r'\bdice\s*roll\b'
    ]
    
    # Equipment patterns
    equipment_patterns = [
        r'\b(?:weapon|armor|shield|tool|gear)\b',
        r'\b(?:damage|dmg)\s*[\dd\+\-\s]+',
        r'\b(?:light|heavy|medium)\s+armor\b',
        r'\b(?:one-handed|two-handed|versatile)\b',
        r'\b(?:finesse|reach|thrown)\b',
        r'\b(?:studded leather|chain mail|plate armor)\b',
        r'\bgp\s*(?:cost|price)\b',
        r'\bweight\s*\d+\s*lb'
    ]
    
    # Rule patterns
    rule_patterns = [
        r'\bmake\s+(?:a|an)\s+.*\s+(?:check|roll|save)\b',
        r'\badvantage\s+(?:on|or)\s+disadvantage\b',
        r'\bdc\s*\d+\b',
        r'\bdifficulty\s+class\b',
        r'\brolling\s+(?:dice|d\d+)\b',
        r'\binitiative\s+order\b',
        r'\bturns?\s+(?:and|&)\s+rounds?\b'
    ]
    
    import re
    
    # Count matches for each category
    monster_score = sum(1 for pattern in monster_patterns if re.search(pattern, text_lower))
    spell_score = sum(1 for pattern in spell_patterns if re.search(pattern, text_lower))
    table_score = sum(1 for pattern in table_patterns if re.search(pattern, text_lower))
    equipment_score = sum(1 for pattern in equipment_patterns if re.search(pattern, text_lower))
    rule_score = sum(1 for pattern in rule_patterns if re.search(pattern, text_lower))
    
    # Determine the best match
    scores = {
        'monster': monster_score,
        'spell': spell_score,
        'table': table_score,
        'equipment': equipment_score,
        'rule': rule_score
    }
    
    # Find the highest scoring category
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # Only classify if we have a strong signal (2+ pattern matches)
    if best_score >= 2:
        return best_type
    
    # Special cases for single strong indicators
    if monster_score >= 1 and any(keyword in text_lower for keyword in ['ac ', 'hp ', 'hit points', 'armor class']):
        return 'monster'
    
    if spell_score >= 1 and any(keyword in text_lower for keyword in ['casting time', 'spell attack', 'cantrip']):
        return 'spell'
    
    if table_score >= 1 and ('d' in text_lower and 'roll' in text_lower):
        return 'table'
    
    # Fallback to document type or generic
    return fallback_type or 'content'

def _infer_doctype(file_path: Path) -> str:
    """Infer document type from filename and path"""
    name_lower = file_path.name.lower()
    parent_lower = file_path.parent.name.lower()
    
    # Check parent directory for type hints
    if parent_lower in ['rules', 'rule']:
        return 'rule'
    elif parent_lower in ['monsters', 'monster', 'bestiary', 'creatures']:
        return 'monster'
    elif parent_lower in ['spells', 'spell', 'magic']:
        return 'spell'
    elif parent_lower in ['equipment', 'items', 'gear', 'treasure']:
        return 'equipment'
    elif parent_lower in ['settings', 'setting', 'world', 'lore']:
        return 'setting'
    elif parent_lower in ['supplements', 'supplement', 'expansion']:
        return 'supplement'
    elif parent_lower in ['tables', 'generators', 'random']:
        return 'table'
    elif parent_lower in ['adventures', 'adventure', 'modules']:
        return 'adventure'
    
    # Check filename for type hints
    if any(word in name_lower for word in ['rule', 'core', 'manual', 'guide', 'basic']):
        return 'rule'
    elif any(word in name_lower for word in ['session', 'transcript', 'log', 'notes']):
        return 'transcript'
    elif any(word in name_lower for word in ['monster', 'creature', 'beast', 'undead', 'dragon']):
        return 'monster'
    elif any(word in name_lower for word in ['spell', 'magic', 'wizard', 'cleric', 'cantrip']):
        return 'spell'
    elif any(word in name_lower for word in ['weapon', 'armor', 'equipment', 'gear', 'treasure']):
        return 'equipment'
    elif any(word in name_lower for word in ['setting', 'world', 'city', 'dungeon', 'region']):
        return 'setting'
    elif any(word in name_lower for word in ['table', 'random', 'generator', 'encounter']):
        return 'table'
    elif any(word in name_lower for word in ['adventure', 'module', 'scenario', 'quest']):
        return 'adventure'
    elif any(word in name_lower for word in ['supplement', 'expansion', 'cursed', 'scroll']):
        return 'supplement'
    elif any(word in name_lower for word in ['lore', 'history', 'background', 'culture']):
        return 'lore'
    elif any(word in name_lower for word in ['reference', 'quick', 'summary', 'cheat']):
        return 'reference'
    else:
        return 'other'

def _extract_section_header(text: str) -> Optional[str]:
    """Extract section header from markdown chunk"""
    lines = text.split('\n')
    for line in lines[:3]:  # Check first few lines
        if line.startswith('#'):
            return line.strip('#').strip()
    return None

def search(sess: Session, query: str, k: int = 5):
    return vs_query(sess, query, k=k)
