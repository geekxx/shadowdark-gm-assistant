# 🎯 Multi-Stage Audio Processing Update - October 2025

## 🚀 What's New

Your Shadowdark GM Assistant now supports a **quality-controlled multi-stage workflow** for processing large audio files that exceed the Whisper API's 25MB limit.

## ✨ New Workflow Benefits

### ✅ **Quality Control**
- **Manual transcript review** catches AI transcription errors
- **Speaker verification** ensures correct attribution  
- **Context addition** improves session note quality
- **Content curation** removes irrelevant conversation

### ✅ **No Size Limits** 
- **Automatic segmentation** handles files of any size
- **Intelligent overlap** prevents speech cutoff at boundaries
- **Parallel processing** - work on multiple segments simultaneously
- **Whisper compatibility** - all segments stay under 25MB

### ✅ **Flexible Workflow**
- **Pausable process** - stop and resume at any step
- **Collaborative editing** - multiple people can review transcripts
- **Version control** - track transcript changes over time
- **Reusable transcripts** - generate session notes multiple times

## 🎯 New Commands

```bash
# Split large audio files into manageable segments
./gm audio split "large_session.m4a" --output-dir segments/

# Transcribe segments to reviewable transcripts
./gm audio transcribe "segment.m4a"

# Merge segment transcripts into one cohesive file
./gm transcript merge "final_transcript.md" segments/*_transcript.md

# Generate session notes from reviewed transcript  
./gm session summarize "final_transcript.md" --out "session_notes.md" --use-rag
```

## 🎲 Perfect for Your Gaming Sessions

This workflow is ideal for:
- **Long sessions** (2+ hours) that exceed file size limits
- **Important campaigns** where accuracy is crucial
- **Multiple speakers** needing clear attribution
- **Sessions requiring** detailed review and editing

## 🔄 Migration Guide

### Before (Limited to 25MB files):
```bash
./gm session summarize "large_session.m4a" --use-rag
# Error: Request entity too large
```

### After (Any file size):
```bash
./gm audio split "large_session.m4a" --output-dir segments/
for segment in segments/*.m4a; do ./gm audio transcribe "$segment"; done
./gm transcript merge "session_transcript.md" segments/*_transcript.md
# Edit transcript for accuracy
./gm session summarize "session_transcript.md" --out "session_notes.md" --use-rag
```

## 📋 Implementation Details

### New Agents Added:
- **AudioSplitter**: Handles file segmentation with overlap
- **TranscriptGenerator**: Creates reviewable diarized transcripts  
- **TranscriptMerger**: Combines segments with speaker continuity

### CLI Enhancement:
- New command groups: `audio` and `transcript`
- Improved error handling and user guidance
- Robust file path and dependency management

The system maintains full backward compatibility - small files (<25MB) continue to work exactly as before, while large files now have a clear path to successful processing.

---

*Updated October 15, 2025 - Version 0.4.0*