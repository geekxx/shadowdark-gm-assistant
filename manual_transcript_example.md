# Manual Speaker Assignment Example

This demonstrates how to use the new manual transcript generation modes when diarization is unreliable.

## Usage Options

### 1. No Diarization (Simple Transcript)
```bash
gm audio transcribe your_audio.wav --no-diarization --output simple_transcript.md
```
This generates a basic Whisper transcript without any speaker diarization attempts.

### 2. Manual Segments (Split by Word Count)
```bash
gm audio transcribe your_audio.wav --manual-segments 5 --output segmented_transcript.md
```
This splits the transcript into 5 roughly equal segments for easier manual speaker assignment.

### 3. Time-Based Segments
```bash
gm audio transcribe your_audio.wav --time-segments 5 --output time_transcript.md
```
This creates segments every 5 minutes (estimated) for chronological speaker assignment.

## Example Output Format

When using manual modes, you'll get a transcript like this:

---

# Manual Speaker Assignment Required

**Instructions:** Replace `[ASSIGN SPEAKER]` with the actual speaker name (e.g., GM, Player 1, Player 2, etc.)

### Segment 1 of 3

**[ASSIGN SPEAKER]:** Welcome everyone to tonight's session. Last time you were exploring the ancient tower and discovered the mysterious glowing orb in the central chamber.

---

### Segment 2 of 3

**[ASSIGN SPEAKER]:** I want to examine the orb more closely. Can I roll an investigation check? Okay that's a fifteen plus my bonus makes it eighteen.

---

### Segment 3 of 3

**[ASSIGN SPEAKER]:** As you approach the orb you notice strange runes carved into its surface. They seem to pulse with the same rhythm as your heartbeat. Make a wisdom saving throw.

---

## Editing Instructions

1. Listen to your audio while reading the transcript
2. Replace each `[ASSIGN SPEAKER]` with the correct speaker:
   - GM for game master narration and NPC dialogue
   - Player 1, Player 2, etc. for player characters
   - Use consistent names throughout
3. You can also split segments further if needed
4. Once edited, you can process with: `gm session summarize your_edited_transcript.md`

## Benefits of Manual Assignment

- **Accuracy**: You know who's speaking better than any AI
- **Context**: You can handle cross-talk and interruptions properly  
- **Flexibility**: Split or merge segments as needed
- **Gaming-Specific**: Handle character voices, NPC dialogue, and meta-game discussion correctly