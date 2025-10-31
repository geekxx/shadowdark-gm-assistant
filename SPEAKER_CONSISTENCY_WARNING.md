# ⚠️ Critical: Speaker Label Consistency Across Audio Segments

## 🎯 The Problem

When processing large audio files in segments, **each segment gets independent speaker diarization**. This means:

- **Speaker_1** in segment 1 ≠ **Speaker_1** in segment 2
- The same person might be labeled differently in each segment
- **Alice** could be Speaker_1 in segment 1, but Speaker_3 in segment 2
- **Bob** could be Speaker_2 in segment 1, but Speaker_1 in segment 2

## 🚨 Why This Matters

If you don't fix speaker labels before merging:
- **Confusing session notes** with inconsistent speaker attribution
- **Wrong dialogue attribution** making it hard to follow conversations
- **Broken narrative flow** in the final session summary
- **Wasted time** having to fix the merged transcript later

## ✅ The Solution: Fix Labels Per Segment

### **Step-by-Step Process:**

1. **Transcribe all segments first:**
   ```bash
   for segment in segments/*.m4a; do
       ./gm audio transcribe "$segment"
   done
   ```

2. **Edit EACH segment transcript individually:**
   ```bash
   # Open each transcript file
   code segments/session_segment_001_transcript.md
   code segments/session_segment_002_transcript.md
   # etc.
   ```

3. **Standardize speaker names in each file:**
   - Replace `Speaker_1` → `GM` (if GM is speaking)
   - Replace `Speaker_2` → `Alice` (if Alice is speaking)  
   - Replace `Speaker_3` → `Bob` (if Bob is speaking)
   - **Use the SAME names across ALL segments**

4. **Listen to a few seconds if needed:**
   - If you can't tell who's who from context
   - Play a bit of the audio to identify voices
   - Be consistent with your naming choices

5. **Only THEN merge the transcripts:**
   ```bash
   ./gm transcript merge final_transcript.md segments/*_transcript.md
   ```

## 🔍 How to Identify Speaker Issues

The transcript merger will warn you about potential issues:

```
⚠️  POTENTIAL SPEAKER CONSISTENCY ISSUES DETECTED:
   Found AI-generated speaker labels that may be inconsistent:
   - Speaker_1
   - Speaker_2
   - Speaker_3
   
   🎯 RECOMMENDATION: Review transcripts before merging!
```

If you see this warning, **STOP** and fix the speaker labels before proceeding.

## 📝 Example: Before and After

### ❌ Before (Inconsistent):

**Segment 1:**
- Speaker_1: "I cast magic missile"
- Speaker_2: "Roll for damage"

**Segment 2:**  
- Speaker_1: "That hits for 3 damage"
- Speaker_2: "I want to cast a spell too"

### ✅ After (Consistent):

**Segment 1:**
- Alice: "I cast magic missile"
- GM: "Roll for damage"

**Segment 2:**
- GM: "That hits for 3 damage"
- Alice: "I want to cast a spell too"

## 🎯 Best Practices

1. **Create a speaker mapping** before you start:
   - Write down who is who: "Alice = Player 1, Bob = Player 2, etc."
   
2. **Be consistent with names:**
   - Use the same exact spelling/capitalization
   - **GM** (not "Game Master" or "DM")
   - **Alice** (not "alice" or "Player Alice")

3. **Use context clues:**
   - Look for character names, spell names, GM-specific language
   - Check who's asking questions vs. answering them

4. **When in doubt:**
   - Listen to a few seconds of the audio segment
   - Better to spend 30 seconds identifying than fix wrong attribution later

## 🚀 Tools to Help

The system provides several aids:
- **Speaker statistics** showing talk time percentages
- **Clear warnings** when inconsistent labels are detected  
- **Structured editing instructions** in each transcript
- **Timestamps** to help you locate specific sections in audio

Remember: **5 minutes of careful speaker labeling per segment** saves hours of confusion later!

---

*This is a fundamental limitation of speaker diarization technology - segment independence is unavoidable, but easily manageable with proper workflow.*