# New Audio Processing Pipeline Demo

## 🚀 **The New 5-Step Workflow**

Your new pipeline is designed to handle large audio files with quality control:

### **Step 1: Auto-Split Large Audio** 🔪
```bash
# Automatically splits files >25MB into segments with overlap
./gm audio split "large_session.m4a" --output-dir segments/
```
**What it does:**
- Detects files over 25MB (Whisper limit)
- Splits into optimal segments (typically 15-20 minutes each)
- Adds 30-second overlap to prevent speech cutoff
- Preserves audio quality with no re-encoding

### **Step 2: Generate Transcripts for Each Segment** 🎙️
```bash
# Process each segment to get diarized transcripts
./gm audio transcribe segments/large_session_segment_001.m4a
./gm audio transcribe segments/large_session_segment_002.m4a
./gm audio transcribe segments/large_session_segment_003.m4a
# ... or use a loop for many segments
```
**What it does:**
- Full speaker diarization for each segment
- Whisper transcription with speaker labels
- Outputs structured markdown transcript for manual review
- Includes timestamps and speaker statistics

### **Step 2.5: CRITICAL - Fix Speaker Labels in Each Transcript** ⚠️
```bash
# IMPORTANT: Each segment gets independent speaker labeling!
# Speaker_1 in segment 1 ≠ Speaker_1 in segment 2 (same person!)

# Edit each transcript file individually:
code segments/large_session_segment_001_transcript.md
code segments/large_session_segment_002_transcript.md
# etc.

# Replace Speaker_1, Speaker_2 with consistent names:
# Speaker_1 → GM (if GM is speaking)
# Speaker_2 → Alice (if Alice is speaking)  
# Speaker_3 → Bob (if Bob is speaking)
```
**Critical Step:**
- Same person must have same name across ALL segments
- Listen to a few seconds if you need to identify voices
- This MUST be done before merging transcripts

### **Step 3: Merge Segment Transcripts** 🔗
```bash
# Combine all segment transcripts into one cohesive transcript
./gm transcript merge merged_session_transcript.md \
  segments/*_transcript.md
```
**What it does:**
- Merges multiple segment transcripts into one file
- Handles speaker ID consistency across segments  
- Removes duplicate content at segment boundaries
- Adjusts timestamps for continuity
- Maintains proper formatting for review

### **Step 4: Manual Review & Editing** 📝
```bash
# Edit the merged transcript in your favorite editor
vim merged_session_transcript.md
# or
code merged_session_transcript.md
# or use any text editor
```
**What you do:**
- Fix transcription errors and unclear sections
- Verify speaker labels are correct
- Add context like [dice roll], [laughter], [pause]
- Remove off-topic conversation
- Preserve all in-game content

### **Step 5: Generate Session Notes** 📋
```bash
# Generate final session notes from reviewed transcript
./gm session summarize merged_session_transcript.md --out final_session_notes.md
```
**What it does:**
- Uses GPT-5 to analyze the cleaned transcript
- Generates structured Shadowdark-style session notes
- No audio processing needed (fast!)
- High quality output from reviewed content

## 🎯 **Complete Example Workflow**

```bash
# Start with a 131MB audio file (your use case!)
./gm audio split "Allura Session.m4a" --output-dir allura_segments/

# This creates: 
#   allura_segments/Allura_Session_segment_001.m4a (23MB)
#   allura_segments/Allura_Session_segment_002.m4a (23MB)
#   allura_segments/Allura_Session_segment_003.m4a (23MB)
#   allura_segments/Allura_Session_segment_004.m4a (23MB)
#   allura_segments/Allura_Session_segment_005.m4a (23MB)
#   allura_segments/Allura_Session_segment_006.m4a (16MB)

# Process each segment (6 segments × 3-8 minutes = 18-48 minutes total)
for segment in allura_segments/*.m4a; do
    ./gm audio transcribe "$segment"
done

# Merge all transcripts
./gm transcript merge allura_session_transcript.md allura_segments/*_transcript.md

# Edit the merged transcript
code allura_session_transcript.md

# Generate final session notes
./gm session summarize allura_session_transcript.md --out allura_final_notes.md --use-rag
```

## ✅ **Benefits of New Pipeline**

### **Quality Control**
- **Manual review** catches AI transcription errors
- **Speaker verification** ensures correct attribution  
- **Context addition** improves session note quality
- **Content curation** removes irrelevant conversation

### **Handles Any Size**
- **No 25MB limit** - can process hours of audio
- **Parallel processing** - work on segments simultaneously
- **Efficient chunking** - optimal segment sizes
- **Quality preservation** - no audio degradation

### **Flexible Workflow**
- **Pausable process** - stop and resume anytime
- **Collaborative editing** - multiple people can review
- **Version control** - track transcript changes
- **Reusable transcripts** - generate notes multiple times

### **Performance**
- **Predictable timing** - know exactly how long each step takes
- **Apple Silicon optimized** - MPS acceleration for diarization
- **GPT-5 powered** - best quality session notes from clean transcripts

## 🚦 **When to Use Each Approach**

### **New Pipeline (Large Files)**
- Files > 25MB
- Important sessions requiring accuracy
- Multiple speakers needing clear attribution
- Time available for manual review

### **Original Pipeline (Small Files)**  
- Files < 25MB
- Quick processing needed
- Simple sessions with clear audio
- Automatic processing preferred

Your 131MB Allura session is **perfect** for the new pipeline! 🎯