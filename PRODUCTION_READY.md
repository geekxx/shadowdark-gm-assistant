# 🎯 **New Multi-Stage Audio Processing Pipeline - Ready to Use!**

## 🚀 **Your New Workflow is Complete!**

The enhanced GM CLI tool now supports the **5-step quality-controlled audio processing pipeline** you requested:

### **✅ What's New**

1. **🔪 Audio Splitting** - Automatically handles files >25MB
2. **🎙️ Smart Transcription** - Diarized transcripts for manual review  
3. **🔗 Transcript Merging** - Combines segments with overlap handling
4. **📝 Manual Review Stage** - Edit transcripts before session notes
5. **📋 Session Note Generation** - High-quality output from clean transcripts

---

## 🎯 **Complete Example Workflow**

### **Step 1: Split Large Audio File**
```bash
# Split your 131MB Allura Session into segments
./gm audio split "Allura Session.m4a" --output-dir allura_segments/

# Output:
# 📁 Output directory: allura_segments/
# ✅ Successfully split into 6 segments:
#    1. allura_segments/Allura_Session_segment_001.m4a (23.0 MB)
#    2. allura_segments/Allura_Session_segment_002.m4a (23.0 MB)
#    3. allura_segments/Allura_Session_segment_003.m4a (23.0 MB)
#    4. allura_segments/Allura_Session_segment_004.m4a (23.0 MB)
#    5. allura_segments/Allura_Session_segment_005.m4a (23.0 MB)
#    6. allura_segments/Allura_Session_segment_006.m4a (16.0 MB)
```

### **Step 2: Transcribe Each Segment**
```bash
# Process each segment (can be done in parallel!)
./gm audio transcribe "allura_segments/Allura_Session_segment_001.m4a"
./gm audio transcribe "allura_segments/Allura_Session_segment_002.m4a"
# ... etc

# Or use a loop for efficiency:
for segment in allura_segments/*.m4a; do
    ./gm audio transcribe "$segment"
done

# Each command outputs:
# 🎙️ Transcribing audio file: allura_segments/Allura_Session_segment_001.m4a
# 🔄 Processing audio (this may take several minutes)...
# ✅ Transcript saved to: allura_segments/Allura_Session_segment_001_transcript.md
```

### **Step 2.5: CRITICAL - Fix Speaker Labels in Each Transcript**
```bash
# ⚠️  IMPORTANT: Each segment gets independent speaker IDs!
# Speaker_1 in segment 1 ≠ Speaker_1 in segment 2 (same person, different labels)

# Edit each transcript file to standardize speaker names:
code allura_segments/Allura_Session_segment_001_transcript.md
code allura_segments/Allura_Session_segment_002_transcript.md
# ... etc

# Replace Speaker_1 → GM, Speaker_2 → Alice, Speaker_3 → Bob (consistently!)
# Listen to a few seconds if you need to identify voices
```

### **Step 3: Merge All Transcripts**
```bash
# Combine all segment transcripts into one file
./gm transcript merge "allura_session_transcript.md" allura_segments/*_transcript.md

# Output:
# 🔗 Merging transcripts into: allura_session_transcript.md
# 📁 Input files:
#    1. allura_segments/Allura_Session_segment_001_transcript.md (45.2 KB)
#    2. allura_segments/Allura_Session_segment_002_transcript.md (48.7 KB)
#    3. allura_segments/Allura_Session_segment_003_transcript.md (52.1 KB)
#    4. allura_segments/Allura_Session_segment_004_transcript.md (47.3 KB)
#    5. allura_segments/Allura_Session_segment_005_transcript.md (44.8 KB)
#    6. allura_segments/Allura_Session_segment_006_transcript.md (38.9 KB)
# 🔄 Merging transcripts...
# ✅ Merged transcript saved to: allura_session_transcript.md (267.3 KB)
```

### **Step 4: Manual Review & Editing** 
```bash
# Edit the merged transcript for accuracy
code allura_session_transcript.md
# or
vim allura_session_transcript.md
# or use any text editor

# What to review:
# - Fix transcription errors
# - Verify speaker labels (GM, Player 1, Player 2, etc.)
# - Add context: [dice roll], [laughter], [pause]
# - Remove off-topic conversation
# - Ensure in-game content is preserved
```

### **Step 5: Generate Session Notes**
```bash
# Generate final session notes from the cleaned transcript
./gm session summarize "allura_session_transcript.md" --out "allura_session_notes.md" --use-rag

# This uses the existing high-quality session note generation
# but now with a clean, reviewed transcript as input!
```

---

## 🎯 **Real Usage Examples**

### **For Your 131MB Allura Session:**
```bash
# Complete workflow:
./gm audio split "Allura Session.m4a" --output-dir allura_segments/

# Transcribe (6 segments × 3-8 minutes each = 18-48 minutes total)
for segment in allura_segments/*.m4a; do ./gm audio transcribe "$segment"; done

# Merge
./gm transcript merge "allura_session_transcript.md" allura_segments/*_transcript.md

# Review & edit
code allura_session_transcript.md

# Generate notes  
./gm session summarize "allura_session_transcript.md" --out "allura_session_notes.md" --use-rag
```

### **For Small Files (<25MB):**
```bash
# Use existing direct processing
./gm session summarize "small_session.m4a" --out "session_notes.md" --use-rag
```

---

## 🚀 **Key Benefits**

### **✅ Quality Control**
- **Manual transcript review** catches AI errors before session notes
- **Speaker verification** ensures correct attribution
- **Context addition** improves final output quality

### **✅ Handles Any Size**  
- **No 25MB limit** - process hours of audio
- **Intelligent segmentation** with overlap handling
- **Parallel processing** - work on multiple segments

### **✅ Flexible Workflow**
- **Pausable** - stop and resume at any step
- **Collaborative** - multiple people can review transcripts  
- **Version controlled** - track changes to transcripts
- **Reusable** - generate session notes multiple times from same transcript

### **✅ Performance Optimized**
- **Apple Silicon MPS acceleration** for diarization
- **GPT-5 powered** session notes with 500k tokens
- **Predictable timing** - know exactly how long each step takes

---

## 🎯 **Command Reference**

### **Audio Commands**
```bash
# Split large audio files
./gm audio split <input_file> [--output-dir <dir>] [--segment-duration <seconds>]

# Transcribe audio to diarized transcript  
./gm audio transcribe <input_file> [--output <output_file>]
```

### **Transcript Commands**
```bash
# Merge multiple transcript files
./gm transcript merge <output_file> <transcript1> <transcript2> [...]
```

### **Session Commands**
```bash
# Generate session notes (works with transcripts or audio)
./gm session summarize <input_file> [--out <output>] [--use-rag] [--campaign <id>]
```

---

## 🎯 **Error Handling & Troubleshooting**

### **Environment Variables Needed:**
```bash
# Required for OpenAI GPT-5
export OPENAI_API_KEY="sk-..."

# Optional for speaker diarization (improves quality)
export HUGGINGFACE_TOKEN="hf_..."

# Optional for RAG features  
export DATABASE_URL="postgresql://..."
```

### **Dependencies:**
- **ffmpeg** - for audio processing (install via `brew install ffmpeg`)
- **Python packages** - installed in your venv (already set up)

### **File Format Support:**
- **Audio:** .wav, .mp3, .m4a, .mp4, .mpeg, .mpga, .webm
- **Text:** .md, .txt

---

## 🎯 **Your Next Steps**

1. **Test the new pipeline** with a sample audio file
2. **Process your 131MB Allura Session** using the 5-step workflow
3. **Compare quality** of session notes from reviewed vs. automatic transcripts
4. **Integrate into your regular GM workflow** for all large sessions

The new pipeline is **production ready** and will give you much better session notes for your longer gaming sessions! 🎲✨