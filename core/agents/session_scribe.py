
import os
from datetime import datetime
from textwrap import dedent
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
from sqlmodel import Session
from ..data.models import Session as SessionModel, Event, NPC

load_dotenv()

# Initialize OpenAI client if API key is available
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key and openai_api_key.startswith("sk-") else None

SHADOWDARK_STYLE_GUIDE = dedent("""
You are an expert Shadowdark RPG session note taker. Follow these style guidelines:

DISTANCES: Use Close/Near/Far zones only. Never use feet/meters unless measuring map scale.
ABILITY CHECKS: Use "ability check vs DC" format instead of saving throws. Examples:
- "CON check vs DC 12 or poisoned" 
- "STR check vs DC 15 to break free"
- "WIS check vs DC 13 to notice the trap"

STAT BLOCKS: Format compactly as: HD, AC, Attack, Moves, Morale, Special
- Example: "HD 3, AC 15, Attack +4 bow (1d6), Moves 30, Morale 9, Special: Silent in woods"

TONE: Be terse and runnable. Prioritize actionable information over flavor text.
FORMAT: Use the exact template structure provided.
""")

TEMPLATE = dedent("""
[Date]

Session Summary — 1–2 short paragraphs.

Cast of Characters
- PCs: name — ancestry/class, one‑line descriptor
- Notable NPCs: name — role, attitude

Locations Visited — list with quick details

Scenes & Encounters — numbered; each has: What happened, stakes, loot, clocks advanced, NPC changes.

Treasure & XP Hooks — bullet list.

Rumors & Leads — bullet list.

Prep For Next — 3–5 items.
""")

def _build_system_prompt() -> str:
    return SHADOWDARK_STYLE_GUIDE + "\n\nUse this exact template structure:\n\n" + TEMPLATE

def _build_user_prompt(transcript: str, context_chunks: List[str] = None) -> str:
    prompt = f"Please create session notes from this transcript:\n\n{transcript}"
    
    if context_chunks:
        context = "\n\n".join(context_chunks)
        prompt += f"\n\nRelevant context from previous sessions and rules:\n{context}"
    
    prompt += "\n\nPlease format the output exactly according to the template, following Shadowdark style guidelines."
    return prompt

def _mock_llm_response(transcript: str) -> str:
    """Mock LLM response for testing without API key"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Simple parsing to extract some basic info
    lines = transcript.split('\n')
    characters = set()
    locations = set()
    
    for line in lines:
        if ':' in line:
            speaker = line.split(':')[0].strip()
            if speaker in ['GM', 'DM']:
                continue
            characters.add(speaker)
        if 'tower' in line.lower():
            locations.add('Ancient Tower')
        if 'chamber' in line.lower():
            locations.add('Dusty Chamber')
    
    mock_response = f"""[{today}]

Session Summary — The party discovered an ancient tower with draconic ward runes. After finding an alternate entrance, they encountered undead guardians in a dusty chamber and found treasure before discovering stairs leading deeper underground.

Cast of Characters
- PCs: {', '.join(characters) if characters else 'Kira, Thane'} — brave adventurers exploring dangerous ruins
- Notable NPCs: None encountered this session

Locations Visited — {', '.join(locations) if locations else 'Ancient Tower, Upper Chamber'}

Scenes & Encounters 
1) Tower Investigation — Party examined draconic ward runes, found alternate entrance via climbing
2) Undead Combat — Encountered three skeletons in dusty chamber, defeated them in combat
3) Treasure Discovery — Found 30 gp and magical silver amulet with moon symbol

Treasure & XP Hooks
- 30 gold pieces divided among party
- Silver amulet with moon symbol (faint divination magic)
- XP awarded for clever tactics and brave actions

Rumors & Leads
- The tower contains deeper levels accessed by stairs
- Draconic wards suggest ancient magical protection
- Moon symbol amulet may have significance to local cults

Prep For Next
- Map the deeper levels of the tower
- Research the moon symbol amulet's properties
- Determine what the draconic wards were protecting
- Consider what other dangers lurk below"""

    return mock_response

def summarize_text(
    transcript: str, 
    campaign_id: Optional[int] = None,
    context_chunks: List[str] = None,
    db_session: Optional[Session] = None,
    use_mock: bool = False
) -> str:
    """
    Generate Shadowdark-style session notes from a transcript.
    
    Args:
        transcript: Raw session transcript or notes
        campaign_id: Optional campaign ID for context
        context_chunks: Optional RAG context from previous sessions/rules
        db_session: Optional database session for persisting results
        use_mock: If True, use mock LLM instead of OpenAI (for testing)
    
    Returns:
        Formatted session notes following Shadowdark template
    """
    try:
        # Use mock LLM if requested or if no OpenAI client available
        if use_mock or not client:
            notes = _mock_llm_response(transcript)
        else:
            system_prompt = _build_system_prompt()
            user_prompt = _build_user_prompt(transcript, context_chunks)
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            notes = response.choices[0].message.content
            
            # Add today's date if not already present
            if not notes.startswith("["):
                today = datetime.now().strftime("%Y-%m-%d")
                notes = f"[{today}]\n\n" + notes
        
        # If we have a database session, persist the results
        if db_session and campaign_id:
            _persist_session_data(db_session, campaign_id, transcript, notes)
        
        return notes
        
    except Exception as e:
        # Fallback to template with error message
        today = datetime.now().strftime("%Y-%m-%d")
        return f"[{today}]\n\nError generating session notes: {str(e)}\n\n" + TEMPLATE

def _persist_session_data(db_session: Session, campaign_id: int, transcript: str, notes: str):
    """Persist session data to the database"""
    try:
        # Create session record
        session = SessionModel(
            campaign_id=campaign_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            summary_md=notes,
            gm_notes_md=transcript
        )
        
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # TODO: Parse notes and extract structured data (NPCs, events, etc.)
        # This would involve parsing the generated notes and creating Event, NPC records
        
    except Exception as e:
        print(f"Error persisting session data: {e}")
        db_session.rollback()
