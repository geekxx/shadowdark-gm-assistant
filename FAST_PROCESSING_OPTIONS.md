# Quick Processing Alternative for Large Segments

## Issue: Long Processing Times

Your 40-minute segments are taking a very long time for speaker diarization (which is normal). Let me suggest a **faster alternative approach**:

## Option 1: Use Fast Mode (Transcription Only)

Instead of full diarization, get transcripts quickly, then add speaker labels manually:

### Step 1: Quick Transcription (No Diarization)
```bash
# Use the original session command with --fast flag for quick processing
./gm session summarize "segments/Allura Session_segment_001.m4a" --fast --out "segment_001_quick_transcript.md"
./gm session summarize "segments/Allura Session_segment_002.m4a" --fast --out "segment_002_quick_transcript.md"
# etc.
```

### Step 2: Add Speaker Labels Manually
Edit each quick transcript and add speaker labels:
```markdown
**GM:** You enter the dark tower...
**Player 1:** I want to cast light spell
**GM:** Roll for it
```

### Step 3: Merge and Process
```bash
./gm transcript merge "allura_merged.md" segment_*_quick_transcript.md
./gm session summarize "allura_merged.md" --out "allura_session_notes.md" --use-rag
```

## Option 2: Create Smaller Segments

Split your segments further for faster diarization:

```bash
# Re-split with shorter duration (20 minutes instead of 40)
./gm audio split "Allura Session.m4a" --output-dir smaller_segments --segment-duration 1200
```

## Option 3: Process One Segment Fully (Test)

Let's try to complete one segment to see the full workflow:
```bash
# Let the first segment finish processing (may take 5-15 minutes)
# Or try the smallest segment first:
./gm audio transcribe "segments/Allura Session_segment_006.m4a"  # Only 19MB
```

## Recommendation: Try Fast Mode First

For immediate results, I recommend **Option 1 (Fast Mode)** to get transcripts quickly, then add speaker labels manually. This gives you:
- ✅ **Immediate transcripts** (2-3 minutes per segment)
- ✅ **Manual quality control** over speaker attribution
- ✅ **Same final result** after manual editing

Which approach would you like to try?