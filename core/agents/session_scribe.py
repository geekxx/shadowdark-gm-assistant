
import os
import re
from datetime import datetime
from textwrap import dedent
from typing import List, Optional, Dict
from openai import OpenAI
from dotenv import load_dotenv
from sqlmodel import Session
from ..data.models import Session as SessionModel, Event, NPC
from .diarizer import SpeakerDiarizer, DiarizationResult

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

STAT BLOCKS: For abilities, only display the ability score bonus, not the score. 
- Example STR = 16 would be shown as "S +3"

Use the following formatfor stat blocks:
<MONSTER NAME>  
*<Monster Description>*  
**AC** <AC>, **HP** <HP>, **ATK** <Attacks>, **MV** <Movement>, **S** <STR>, **D** <DEX>, **C** <CON>, **I** <INT>, **W** <WIS>, **Ch** <CHA>, **AL** <Alignment>, **LV** <Level>  
**<Ability 1 name>.** <Ability 1 description>  
**<Ability 2 name>.** <Ability 2 description>  
<Etc.>

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

Scenes & Encounters — numbered; each has: What happened, loot, clocks advanced, NPC changes.

Treasure & XP — bullet list.

Rumors & Leads — bullet list.
                  
Notable Quotes & Moments — 3–5 items.
                  
Character Development - bullet list.
                  
Plot Threads & Foreshadowing — bullet list.

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

def _estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)"""
    return len(text) // 4

def _enhance_transcript_with_speakers(transcript: str, speaker_mapping: Dict[str, str]) -> str:
    """
    Enhance a transcript with speaker labels based on diarization results.
    
    Args:
        transcript: Original transcript text
        speaker_mapping: Mapping from technical speaker IDs to readable names
        
    Returns:
        Enhanced transcript with speaker labels
    """
    # Apply speaker mapping to transcript
    enhanced = transcript
    for tech_id, readable_name in speaker_mapping.items():
        # Replace patterns like "SPEAKER_00" with "GM"
        enhanced = re.sub(rf'\b{tech_id}\b', readable_name, enhanced)
    
    return enhanced

def _clean_vtt_transcript(transcript: str) -> str:
    """
    Clean VTT transcript by removing system messages, timestamps, and non-game content.
    This significantly reduces token count while preserving the essential game narrative.
    """
    lines = transcript.split('\n')
    cleaned_lines = []
    
    # Patterns to skip (common VTT system messages)
    skip_patterns = [
        r'^\d{2}:\d{2}:\d{2}',  # Timestamps
        r'^\[.*\]',  # System messages in brackets
        r'^(.*) has joined the game',
        r'^(.*) has left the game',
        r'^(.*) is now controlling',
        r'^Rolling \d+d\d+',
        r'^Roll: \d+',
        r'^Initiative:',
        r'^.*rolled.*for.*',
        r'^.*whispers.*',
        r'^OOC:',  # Out of character
        r'^\s*$',  # Empty lines
        r'^.*\(GM\).*has joined',
        r'^.*\(GM\).*has left',
        r'^System:',
        r'^<.*>',  # HTML tags
        r'^\*\*.*\*\*$',  # Action text in asterisks (sometimes just formatting)
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip lines matching system patterns
        skip_line = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                skip_line = True
                break
        
        if skip_line:
            continue
            
        # Clean up the line
        # Convert "Player Name:" to more consistent format
        line = re.sub(r'^([^:]+?)(\s*\([^)]*\))?\s*:', r'\1:', line)
        
        # Remove excessive whitespace
        line = re.sub(r'\s+', ' ', line)
        
        # Only keep lines that seem to contain actual game content
        if ':' in line or line.startswith('GM') or line.startswith('DM'):
            cleaned_lines.append(line)
        elif len(line.split()) > 3:  # Keep substantial non-dialogue lines
            cleaned_lines.append(f"Narrative: {line}")
    
    cleaned_transcript = '\n'.join(cleaned_lines)
    
    # Calculate reduction
    original_tokens = _estimate_tokens(transcript)
    cleaned_tokens = _estimate_tokens(cleaned_transcript)
    reduction_pct = ((original_tokens - cleaned_tokens) / original_tokens) * 100
    
    print(f"   Cleaned transcript: {original_tokens:,} → {cleaned_tokens:,} tokens ({reduction_pct:.1f}% reduction)")
    
    return cleaned_transcript

def _chunk_transcript(transcript: str, max_tokens: int = 8000) -> List[str]:
    """
    Break large transcripts into smaller chunks that fit within token limits.
    
    Args:
        transcript: Full transcript text
        max_tokens: Maximum tokens per chunk (default 8000 to leave room for system prompt)
    
    Returns:
        List of transcript chunks
    """
    estimated_tokens = _estimate_tokens(transcript)
    
    # If transcript is small enough, return as-is
    if estimated_tokens <= max_tokens:
        return [transcript]
    
    # Split by logical breaks (GM/Player turns, then paragraphs, then sentences)
    chunks = []
    
    # First try splitting by speaker turns
    turns = re.split(r'\n(?=(?:GM|DM|Player)(?:\s*\([^)]*\))?\s*:)', transcript)
    
    current_chunk = ""
    current_tokens = 0
    
    for turn in turns:
        turn = turn.strip()
        if not turn:
            continue
            
        turn_tokens = _estimate_tokens(turn)
        
        # If this single turn is too big, we need to split it further
        if turn_tokens > max_tokens:
            # Split by sentences
            sentences = re.split(r'(?<=[.!?])\s+', turn)
            for sentence in sentences:
                sentence_tokens = _estimate_tokens(sentence)
                
                if current_tokens + sentence_tokens > max_tokens and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
                    current_tokens += sentence_tokens
        else:
            # Check if adding this turn would exceed the limit
            if current_tokens + turn_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = turn
                current_tokens = turn_tokens
            else:
                current_chunk += "\n" + turn if current_chunk else turn
                current_tokens += turn_tokens
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def _merge_session_notes(chunk_notes: List[str]) -> str:
    """
    Merge session notes from multiple chunks into a single cohesive summary.
    
    Args:
        chunk_notes: List of session notes from each chunk
        
    Returns:
        Merged session notes
    """
    if len(chunk_notes) == 1:
        return chunk_notes[0]
    
    # This is a simplified merge - in practice, you might want more sophisticated merging
    merged = f"[{datetime.now().strftime('%Y-%m-%d')}]\n\n"
    merged += "Session Summary — Multi-part session covering various encounters and roleplay.\n\n"
    
    all_characters = set()
    all_locations = set()
    all_scenes = []
    all_treasure = []
    all_rumors = []
    all_quotes = []
    all_character_dev = []
    all_plot_threads = []
    all_prep = []
    
    # Extract information from each chunk
    for i, notes in enumerate(chunk_notes):
        lines = notes.split('\n')
        section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('Cast of Characters'):
                section = 'characters'
                continue
            elif line.startswith('Locations Visited'):
                section = 'locations'
                continue
            elif line.startswith('Scenes & Encounters'):
                section = 'scenes'
                continue
            elif line.startswith('Treasure & XP'):
                section = 'treasure'
                continue
            elif line.startswith('Rumors & Leads'):
                section = 'rumors'
                continue
            elif line.startswith('Notable Quotes & Moments'):
                section = 'quotes'
                continue
            elif line.startswith('Character Development'):
                section = 'character_dev'
                continue
            elif line.startswith('Plot Threads & Foreshadowing'):
                section = 'plot_threads'
                continue
            elif line.startswith('Prep For Next'):
                section = 'prep'
                continue
            elif line.startswith('##') or line.startswith('['):
                section = None
                continue
            
            if line and line.startswith('- ') and section:
                if section == 'characters':
                    all_characters.add(line)
                elif section == 'locations':
                    all_locations.add(line)
                elif section == 'scenes':
                    all_scenes.append(f"{len(all_scenes)+1}. {line[2:]}")
                elif section == 'treasure':
                    all_treasure.append(line)
                elif section == 'rumors':
                    all_rumors.append(line)
                elif section == 'quotes':
                    all_quotes.append(line)
                elif section == 'character_dev':
                    all_character_dev.append(line)
                elif section == 'plot_threads':
                    all_plot_threads.append(line)
                elif section == 'prep':
                    all_prep.append(line)
    
    # Build merged sections
    if all_characters:
        merged += "Cast of Characters\n"
        for char in sorted(all_characters):
            merged += f"{char}\n"
        merged += "\n"
    
    if all_locations:
        merged += "Locations Visited — " + ", ".join([loc[2:] for loc in sorted(all_locations)]) + "\n\n"
    
    if all_scenes:
        merged += "Scenes & Encounters\n"
        for scene in all_scenes[:10]:  # Limit to avoid too long
            merged += f"{scene}\n"
        merged += "\n"
    
    if all_treasure:
        merged += "Treasure & XP\n"
        for treasure in all_treasure[:10]:
            merged += f"{treasure}\n"
        merged += "\n"
    
    if all_rumors:
        merged += "Rumors & Leads\n"
        for rumor in all_rumors[:10]:
            merged += f"{rumor}\n"
        merged += "\n"
    
    if all_quotes:
        merged += "Notable Quotes & Moments\n"
        for quote in all_quotes[:5]:
            merged += f"{quote}\n"
        merged += "\n"
    
    if all_character_dev:
        merged += "Character Development\n"
        for dev in all_character_dev[:10]:
            merged += f"{dev}\n"
        merged += "\n"
    
    if all_plot_threads:
        merged += "Plot Threads & Foreshadowing\n"
        for thread in all_plot_threads[:10]:
            merged += f"{thread}\n"
        merged += "\n"
    
    if all_prep:
        merged += "Prep For Next\n"
        for prep in all_prep[:5]:
            merged += f"{prep}\n"
    
    return merged

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

Treasure & XP
- 30 gold pieces divided among party
- Silver amulet with moon symbol (faint divination magic)
- XP awarded for clever tactics and brave actions

Rumors & Leads
- The tower contains deeper levels accessed by stairs
- Draconic wards suggest ancient magical protection
- Moon symbol amulet may have significance to local cults

Notable Quotes & Moments
- "These runes are older than anything I've seen" - Kira examining the tower
- Party's clever use of climbing gear to bypass the main entrance
- Thane's strategic positioning during the skeleton combat

Character Development
- Kira showing increased knowledge of ancient languages
- Thane displaying tactical leadership in combat situations

Plot Threads & Foreshadowing
- The moon symbol amulet connects to local cult activities
- Draconic ward runes suggest deeper magical history in the region
- The tower's lower levels may contain greater treasures or dangers

Prep For Next
- Map the deeper levels of the tower
- Research the moon symbol amulet's properties
- Determine what the draconic wards were protecting
- Consider what other dangers lurk below"""

    return mock_response

def summarize_audio(
    audio_path: str,
    campaign_id: Optional[int] = None,
    context_chunks: List[str] = None,
    db_session: Optional[Session] = None,
    huggingface_token: Optional[str] = None,
    use_mock: bool = False
) -> str:
    """
    Generate session notes from an audio file with speaker diarization.
    
    Args:
        audio_path: Path to the audio file
        campaign_id: Optional campaign ID for context
        context_chunks: Optional RAG context from previous sessions/rules
        db_session: Optional database session for persisting results
        huggingface_token: HuggingFace token for accessing diarization models
        use_mock: If True, use mock processing (for testing)
        
    Returns:
        Formatted session notes with speaker identification
    """
    try:
        if use_mock:
            return _mock_llm_response("Audio processing not implemented in mock mode")
        
        # Initialize diarizer
        diarizer = SpeakerDiarizer(huggingface_token=huggingface_token)
        
        # Perform diarization with progress updates
        print(f"🎙️  Processing audio file: {audio_path}")
        print("📊 Step 1/4: Performing speaker diarization...")
        diarization_result = diarizer.diarize_audio(audio_path, min_speakers=2, max_speakers=6)
        
        # Create speaker mapping (GM + Players)
        print("📊 Step 2/4: Creating speaker mapping...")
        speaker_mapping = diarizer.get_speaker_mapping(diarization_result)
        print(f"🏷️  Identified speakers: {list(speaker_mapping.values())}")
        
        # Create diarized transcript
        print("📊 Step 3/4: Generating speaker timeline...")
        diarized_transcript = diarizer.create_speaker_transcript(diarization_result)
        
        # Apply readable speaker names
        enhanced_transcript = diarizer.apply_speaker_mapping(diarized_transcript, speaker_mapping)
        
        # TODO: Integrate with speech-to-text to get actual transcript content
        # For now, we'll use the diarization timeline as the transcript
        transcript_for_notes = enhanced_transcript
        
        # Generate session notes using the enhanced transcript
        print("📊 Step 4/4: Generating AI session notes...")
        print("🤖 Processing with AI to create structured session notes...")
        return summarize_text(
            transcript=transcript_for_notes,
            campaign_id=campaign_id,
            context_chunks=context_chunks,
            db_session=db_session,
            use_mock=use_mock
        )
        
    except Exception as e:
        today = datetime.now().strftime("%Y-%m-%d")
        return f"[{today}]\n\nError processing audio: {str(e)}\n\n" + TEMPLATE

def summarize_text(
    transcript: str, 
    campaign_id: Optional[int] = None,
    context_chunks: List[str] = None,
    db_session: Optional[Session] = None,
    speaker_mapping: Optional[Dict[str, str]] = None,
    use_mock: bool = False
) -> str:
    """
    Generate Shadowdark-style session notes from a transcript.
    
    Args:
        transcript: Raw session transcript or notes
        campaign_id: Optional campaign ID for context
        context_chunks: Optional RAG context from previous sessions/rules
        db_session: Optional database session for persisting results
        speaker_mapping: Optional mapping from technical speaker IDs to readable names
        use_mock: If True, use mock LLM instead of OpenAI (for testing)
    
    Returns:
        Formatted session notes following Shadowdark template
    """
    try:
        # Use mock LLM if requested or if no OpenAI client available
        if use_mock or not client:
            notes = _mock_llm_response(transcript)
        else:
            # Clean the transcript first to reduce token count
            cleaned_transcript = _clean_vtt_transcript(transcript)
            
            # Enhance with speaker labels if provided
            if speaker_mapping:
                cleaned_transcript = _enhance_transcript_with_speakers(cleaned_transcript, speaker_mapping)
            
            # Use GPT-4o for large context window (128k tokens)
            system_prompt = _build_system_prompt()
            user_prompt = _build_user_prompt(cleaned_transcript, context_chunks)
            
            # Estimate tokens and choose model accordingly
            estimated_tokens = _estimate_tokens(system_prompt + user_prompt)
            
            if estimated_tokens > 100000:  # Very large transcript
                print(f"   Very large transcript detected ({estimated_tokens:,} tokens). Using GPT-4o with large context...")
                model = "gpt-4o"
                max_tokens = 4000
            elif estimated_tokens > 50000:  # Large transcript  
                print(f"   Large transcript detected ({estimated_tokens:,} tokens). Using GPT-4o...")
                model = "gpt-4o"
                max_tokens = 3000
            else:  # Normal transcript
                model = "gpt-4o-mini"  # Faster and cheaper for smaller transcripts
                max_tokens = 2000
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens
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
