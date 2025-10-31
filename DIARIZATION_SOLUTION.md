# Diarization Issues and Solutions

## Problem Summary

The original issue was that speaker diarization was producing many mistakes:
- **Over-segmentation**: Creating tiny 1-2 word fragments instead of natural speech segments
- **Attribution errors**: Misassigning speakers (e.g., Player 1 dialogue attributed to GM)
- **Inconsistent quality**: Some sections worked well, others had "almost random" attribution

## Technical Improvements Made

### 1. Enhanced Post-Processing Pipeline
- **Context Analysis**: Uses 5-segment windows to detect attribution errors
- **Mid-sentence Split Detection**: Identifies and merges fragments split inappropriately
- **Gaming Session Heuristics**: RPG-specific vocabulary analysis for better speaker detection
- **Segment Merging**: Reduces over-segmentation (achieved 68% reduction: 533→171 segments)

### 2. Quality Settings  
- **Fast**: More segments, faster processing (good for quick testing)
- **Balanced**: Default setting with optimal speed/accuracy balance
- **Precise**: Fewer segments, more processing time (best quality)

### 3. Attribution Correction
- Applied 19 automatic corrections using context patterns
- Gaming vocabulary detection (dice rolls, character actions, GM narration)
- Speaker dominance analysis to maintain consistency

## Fundamental Limitation

Despite these improvements, **ML-based diarization has inherent limitations** for gaming sessions:
- Similar voices are hard to distinguish
- Cross-talk and interruptions confuse the models
- Character voices vs. player voices create complexity
- Meta-game discussion mixed with in-character dialogue

## Manual Assignment Solution

### New CLI Options Added

```bash
# No diarization - just Whisper transcription
gm audio transcribe session.wav --no-diarization

# Split into N manual segments  
gm audio transcribe session.wav --manual-segments 5

# Time-based segments (every N minutes)
gm audio transcribe session.wav --time-segments 10
```

### How It Works

1. **Whisper-Only Transcription**: Uses OpenAI Whisper for accurate speech-to-text
2. **Manual Speaker Tags**: Creates `[ASSIGN SPEAKER]` placeholders
3. **Segment Organization**: Splits transcript into manageable chunks
4. **User Editing**: You assign speakers based on your knowledge of the session

### Benefits

- **Perfect Accuracy**: You know who's speaking better than any AI
- **Context Awareness**: Handle character voices, NPCs, and meta-discussion correctly
- **Flexibility**: Split or merge segments as needed
- **Gaming-Specific**: Works great for complex RPG scenarios

## Recommended Workflow

### For Small Files (<25MB)
```bash
# Generate manual transcript
gm audio transcribe session.wav --manual-segments 5 --output manual.md

# Edit the transcript (replace [ASSIGN SPEAKER] with GM, Player 1, etc.)
code manual.md

# Generate session notes
gm session summarize manual.md --out notes.md --use-rag
```

### For Large Files (>25MB)
```bash
# Split large file
gm audio split large_session.m4a --output-dir segments/

# Transcribe segments manually
for segment in segments/*.m4a; do
    gm audio transcribe "$segment" --no-diarization
done

# Edit each segment transcript individually
# Then merge: gm transcript merge final.md segments/*_transcript.md
```

## When to Use Each Approach

### Use Automatic Diarization When:
- Speakers have very distinct voices
- Minimal cross-talk or interruptions  
- Clean audio quality
- Non-gaming content (interviews, meetings)

### Use Manual Assignment When:
- Gaming sessions with similar voices
- Complex character roleplay scenarios
- Poor automatic diarization results
- You need perfect speaker accuracy

## File Changes Made

1. **core/agents/transcript_generator.py**: Added `generate_simple_transcript()` method
2. **core/agents/diarizer.py**: Enhanced post-processing with gaming-specific improvements  
3. **gm (CLI script)**: Added `--no-diarization`, `--manual-segments`, `--time-segments` options
4. **Documentation**: Updated README.md with manual assignment workflow

The solution provides both improved automatic diarization AND manual alternatives for when AI limitations become apparent.