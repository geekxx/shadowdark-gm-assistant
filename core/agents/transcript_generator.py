"""
Transcript Generator Agent for Shadowdark GM Assistant

This agent generates clean diarized transcripts from audio files
for manual review and editing before session note generation.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from .diarizer import SpeakerDiarizer, DiarizationResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptGenerator:
    """
    Generates clean diarized transcripts suitable for manual review.
    
    Outputs structured transcripts with speaker labels, timestamps,
    and clear formatting for easy editing and quality control.
    """
    
    def __init__(self, huggingface_token: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.huggingface_token = huggingface_token
        self.openai_api_key = openai_api_key
    
    def generate_transcript(
        self, 
        audio_path: str, 
        output_path: Optional[str] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        quality: str = 'balanced'
    ) -> str:
        """
        Generate a clean diarized transcript from audio file.
        
        Args:
            audio_path: Path to the audio file
            output_path: Path to save transcript (optional)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            
        Returns:
            Path to the generated transcript file
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"🎙️  Generating transcript from: {audio_path.name}")
        
        # Initialize diarizer
        diarizer = SpeakerDiarizer(
            huggingface_token=self.huggingface_token,
            openai_api_key=self.openai_api_key
        )
        
        # Set quality parameters
        quality_settings = {
            'fast': {'min_segment_duration': 0.5, 'merge_threshold': 0.3},
            'balanced': {'min_segment_duration': 1.5, 'merge_threshold': 0.8},
            'precise': {'min_segment_duration': 2.5, 'merge_threshold': 1.2}
        }
        
        settings = quality_settings.get(quality, quality_settings['balanced'])
        logger.info(f"🎛️  Using '{quality}' quality settings: {settings}")
        
        # Perform diarization and transcription with quality-based settings
        logger.info("📊 Step 1/3: Performing speaker diarization and transcription...")
        diarization_result, transcript_text = diarizer.diarize_and_transcribe(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            min_segment_duration=settings['min_segment_duration'],
            merge_threshold=settings['merge_threshold']
        )
        
        # Create speaker mapping
        logger.info("📊 Step 2/3: Creating speaker mapping...")
        speaker_mapping = diarizer.get_speaker_mapping(diarization_result)
        logger.info(f"🏷️  Identified speakers: {list(speaker_mapping.values())}")
        
        # Generate formatted transcript
        logger.info("📊 Step 3/3: Generating formatted transcript...")
        formatted_transcript = self._create_formatted_transcript(
            diarization_result, 
            transcript_text, 
            speaker_mapping,
            audio_path
        )
        
        # Save to file if output path provided
        if output_path is None:
            output_path = audio_path.parent / f"{audio_path.stem}_transcript.md"
        else:
            output_path = Path(output_path)
        
        # Write transcript
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_transcript)
        
        logger.info(f"✅ Transcript saved to: {output_path}")
        return str(output_path)
    
    def _create_formatted_transcript(
        self,
        diarization_result: DiarizationResult,
        transcript_text: Optional[str],
        speaker_mapping: dict,
        audio_file: Path
    ) -> str:
        """
        Create a well-formatted transcript for manual review.
        
        Args:
            diarization_result: Results from speaker diarization
            transcript_text: Full transcript text from Whisper
            speaker_mapping: Mapping of technical speaker IDs to readable names
            audio_file: Original audio file path
            
        Returns:
            Formatted transcript string
        """
        lines = []
        
        # Header with metadata
        lines.append(f"# Session Transcript")
        lines.append(f"")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Source Audio:** {audio_file.name}")
        lines.append(f"**Duration:** {diarization_result.total_duration:.1f} seconds ({diarization_result.total_duration/60:.1f} minutes)")
        lines.append(f"**Speakers:** {len(diarization_result.speaker_stats)} detected")
        lines.append("")
        
        # Speaker summary
        lines.append("## Speaker Summary")
        lines.append("")
        for speaker_id, readable_name in speaker_mapping.items():
            if speaker_id in diarization_result.speaker_stats:
                stats = diarization_result.speaker_stats[speaker_id]
                percentage = (stats / diarization_result.total_duration) * 100
                lines.append(f"- **{readable_name}** ({speaker_id}): {stats:.1f}s ({percentage:.1f}%)")
        lines.append("")
        
        # Instructions for editing
        lines.append("## ⚠️ CRITICAL: Speaker Label Consistency")
        lines.append("")
        lines.append("**🎯 IMPORTANT: Each segment gets independent speaker IDs!**")
        lines.append("")
        lines.append("- Speaker_1 in this segment ≠ Speaker_1 in other segments")
        lines.append("- The same person might be Speaker_1 here, Speaker_3 elsewhere")
        lines.append("- **YOU MUST standardize names before merging transcripts**")
        lines.append("")
        lines.append("**✏️ Fix Speaker Names NOW (before merging):**")
        lines.append("1. Replace Speaker_1, Speaker_2, etc. with consistent names:")
        lines.append("   - GM → GM (always the same)")
        lines.append("   - Speaker_1 → Alice (if Alice is speaking)")
        lines.append("   - Speaker_2 → Bob (if Bob is speaking)")
        lines.append("   - etc.")
        lines.append("2. Listen to a few seconds if you need to identify voices")
        lines.append("")
        lines.append("## Additional Editing Instructions")
        lines.append("")
        lines.append("**After fixing speaker names, also review:**")
        lines.append("")
        lines.append("1. **Fix Transcription Errors**: Correct any misheard words or phrases")
        lines.append("2. **Add Context**: Include important non-verbal actions in [brackets]")
        lines.append("3. **Clean Up**: Remove filler words, false starts, and off-topic conversation")
        lines.append("4. **Preserve Game Content**: Keep all in-character dialogue and game mechanics")
        lines.append("")
        lines.append("**Formatting Guidelines:**")
        lines.append("- Use consistent names: **GM**, **Alice**, **Bob**, etc.")
        lines.append("- Use [dice roll], [pause], [laughter] for non-verbal content")
        lines.append("- Mark unclear sections with [unclear] for follow-up")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Main transcript
        lines.append("## Transcript")
        lines.append("")
        
        if not diarization_result.segments:
            lines.append("*No speaker segments detected in audio*")
            if transcript_text:
                lines.append("")
                lines.append("**Raw Transcript (no speaker diarization):**")
                lines.append("")
                lines.append(transcript_text)
            return "\n".join(lines)
        
        # Merge consecutive short segments to reduce over-segmentation
        logger.info("🔗 Merging consecutive short segments...")
        merged_segments = self._merge_consecutive_segments(diarization_result.segments)
        
        # Update diarization result with merged segments
        diarization_result.segments = merged_segments
        
        # Align transcript text with speaker segments if available
        aligned_segments = {}
        if transcript_text:
            logger.info("📝 Aligning transcript with speaker segments...")
            aligned_segments = self._align_transcript_with_speakers(transcript_text, merged_segments)
        
        # Create structured transcript with speaker segments
        for i, segment in enumerate(diarization_result.segments):
            # Get speaker name
            speaker_name = speaker_mapping.get(segment.speaker_id, segment.speaker_id)
            
            # Format timestamp
            start_time = self._format_timestamp(segment.start_time)
            end_time = self._format_timestamp(segment.end_time)
            
            # Add speaker and timestamp
            lines.append(f"### {start_time} - {end_time}")
            
            # Add aligned transcript content if available
            if i in aligned_segments and aligned_segments[i].strip():
                lines.append(f"**{speaker_name}:** {aligned_segments[i].strip()}")
            else:
                lines.append(f"**{speaker_name}:** *[Edit this section with the actual speech content]*")
            lines.append("")
        
        # Add raw transcript for reference
        if transcript_text:
            lines.append("---")
            lines.append("")
            lines.append("## Raw Transcript (for reference while editing)")
            lines.append("")
            lines.append("Use this text to fill in the speaker sections above:")
            lines.append("")
            lines.append("```")
            lines.append(transcript_text.strip())
            lines.append("```")
        
        # Footer with next steps
        lines.append("---")
        lines.append("")
        lines.append("## Next Steps")
        lines.append("")
        lines.append("After reviewing and editing this transcript:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Generate session notes from reviewed transcript")
        lines.append(f"./gm session summarize {audio_file.stem}_transcript.md --out {audio_file.stem}_session_notes.md")
        lines.append("```")
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _merge_consecutive_segments(self, segments: List, min_duration: float = 2.0, max_gap: float = 1.0):
        """
        Merge consecutive segments from the same speaker to reduce over-segmentation.
        
        Args:
            segments: List of speaker segments
            min_duration: Minimum duration to keep segments separate (seconds)
            max_gap: Maximum gap between segments to merge (seconds)
            
        Returns:
            List of merged segments
        """
        if not segments:
            return segments
        
        from .diarizer import SpeakerSegment  # Import here to avoid circular imports
        
        merged = []
        current_segment = None
        
        for segment in segments:
            if current_segment is None:
                current_segment = segment
                continue
            
            # Check if we should merge with the previous segment
            should_merge = (
                # Same speaker
                current_segment.speaker_id == segment.speaker_id and
                # Close in time (within max_gap)
                (segment.start_time - current_segment.end_time) <= max_gap and
                # At least one segment is short (under min_duration)
                (current_segment.duration < min_duration or segment.duration < min_duration)
            )
            
            if should_merge:
                # Merge segments by extending the current one
                current_segment = SpeakerSegment(
                    start_time=current_segment.start_time,
                    end_time=segment.end_time,
                    speaker_id=current_segment.speaker_id,
                    duration=segment.end_time - current_segment.start_time
                )
            else:
                # Add the completed segment and start a new one
                merged.append(current_segment)
                current_segment = segment
        
        # Add the final segment
        if current_segment:
            merged.append(current_segment)
        
        logger.info(f"📊 Segment merging: {len(segments)} → {len(merged)} segments")
        return merged
    
    def _align_transcript_with_speakers(self, transcript: str, segments: List) -> Dict[int, str]:
        """
        Align transcript text with speaker segments using simple word distribution.
        
        This is a basic implementation that distributes words proportionally
        across speaker segments based on duration.
        
        Args:
            transcript: Full transcript text
            segments: List of speaker segments with timing
            
        Returns:
            Dictionary mapping segment index to transcript text
        """
        if not transcript or not segments:
            return {}
        
        # Split transcript into words
        words = transcript.strip().split()
        if not words:
            return {}
        
        # Calculate total duration
        total_duration = sum(segment.duration for segment in segments)
        if total_duration == 0:
            return {}
        
        # Distribute words proportionally based on segment duration
        aligned_segments = {}
        current_word_idx = 0
        
        for i, segment in enumerate(segments):
            # Calculate proportion of words for this segment
            duration_ratio = segment.duration / total_duration
            words_for_segment = max(1, int(len(words) * duration_ratio))
            
            # Get words for this segment
            start_idx = current_word_idx
            end_idx = min(current_word_idx + words_for_segment, len(words))
            
            if start_idx < len(words):
                segment_words = words[start_idx:end_idx]
                aligned_segments[i] = " ".join(segment_words)
                current_word_idx = end_idx
            else:
                aligned_segments[i] = ""
        
        # If there are remaining words, add them to the last segment
        if current_word_idx < len(words):
            remaining_words = words[current_word_idx:]
            last_segment_idx = len(segments) - 1
            if last_segment_idx in aligned_segments:
                aligned_segments[last_segment_idx] += " " + " ".join(remaining_words)
            else:
                aligned_segments[last_segment_idx] = " ".join(remaining_words)
        
        return aligned_segments
    
    def generate_simple_transcript(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        manual_segments: Optional[int] = None,
        time_segments: Optional[int] = None
    ) -> str:
        """
        Generate a simple transcript without speaker diarization.
        
        This mode is useful when diarization is unreliable and you want to 
        manually assign speakers to the transcript segments.
        
        Args:
            audio_path: Path to the audio file
            output_path: Path to save transcript (optional)
            manual_segments: Number of segments to split transcript into for manual assignment
            
        Returns:
            Path to the generated transcript file
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"🎙️  Generating simple transcript from: {audio_path.name}")
        
        # Initialize diarizer (we only need it for transcription)
        from openai import OpenAI
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required for transcription")
        
        openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Step 1: Get speech-to-text transcription only
        logger.info("🎙️  Step 1/2: Performing speech-to-text transcription...")
        
        # Check file size (Whisper has 25MB limit)
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 25:
            raise ValueError(f"Audio file is {file_size_mb:.1f}MB (Whisper limit: 25MB). "
                           "Please split the file into smaller segments first.")
        
        # Transcribe the audio
        with open(audio_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        logger.info("✅ Speech-to-text transcription completed")
        
        # Step 2: Format the transcript
        logger.info("📝 Step 2/2: Formatting transcript for manual speaker assignment...")
        
        formatted_transcript = self._create_simple_formatted_transcript(
            transcript, Path(audio_path), manual_segments, time_segments
        )
        
        # Save to file if output path provided
        if output_path is None:
            output_path = audio_path.parent / f"{audio_path.stem}_transcript.md"
        else:
            output_path = Path(output_path)
        
        # Write transcript
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_transcript)
        
        logger.info(f"✅ Simple transcript saved to: {output_path}")
        return str(output_path)
    
    def _create_simple_formatted_transcript(
        self,
        transcript_text: str,
        audio_file: Path,
        manual_segments: Optional[int] = None,
        time_segments: Optional[int] = None
    ) -> str:
        """Create a simple formatted transcript for manual speaker assignment."""
        lines = []
        
        # Header with metadata
        lines.append(f"# Session Transcript (Manual Speaker Assignment)")
        lines.append(f"")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Source Audio:** {audio_file.name}")
        lines.append(f"**Mode:** Simple transcription (no speaker diarization)")
        lines.append("")
        
        # Instructions for manual assignment
        lines.append("## 📝 Manual Speaker Assignment Instructions")
        lines.append("")
        lines.append("**This transcript was generated WITHOUT speaker diarization.**")
        lines.append("")
        lines.append("To assign speakers manually:")
        lines.append("1. **Listen to the audio** while reading the transcript")
        lines.append("2. **Add speaker labels** in the format: `**Speaker Name:** text`")
        lines.append("3. **Use consistent names**: GM, Alice, Bob, etc.")
        lines.append("4. **Add timestamps** if needed: `[12:34]` for reference points")
        lines.append("5. **Mark unclear sections** with `[unclear]` for follow-up")
        lines.append("")
        lines.append("**Editing Guidelines:**")
        lines.append("- Break long paragraphs at natural speaker changes")
        lines.append("- Use [dice roll], [pause], [laughter] for non-verbal content")
        lines.append("- Remove filler words and false starts as needed")
        lines.append("- Preserve all game-relevant content")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Main transcript
        lines.append("## Raw Transcript")
        lines.append("")
        lines.append("*Assign speakers by adding `**Speaker Name:**` before each speaker's text:*")
        lines.append("")
        
        if manual_segments and manual_segments > 1:
            # Split transcript into segments for easier manual assignment
            words = transcript_text.split()
            words_per_segment = len(words) // manual_segments
            
            for i in range(manual_segments):
                start_idx = i * words_per_segment
                end_idx = (i + 1) * words_per_segment if i < manual_segments - 1 else len(words)
                segment_text = " ".join(words[start_idx:end_idx])
                
                lines.append(f"### Segment {i + 1} of {manual_segments}")
                lines.append("")
                lines.append("**[ASSIGN SPEAKER]:** " + segment_text.strip())
                lines.append("")
                lines.append("---")
                lines.append("")
        elif time_segments and time_segments > 0:
            # Split transcript by estimated time intervals
            # Rough estimate: ~150 words per minute of speech
            words = transcript_text.split()
            words_per_minute = 150
            words_per_time_segment = words_per_minute * time_segments
            
            num_segments = max(1, len(words) // words_per_time_segment)
            
            for i in range(num_segments):
                start_idx = i * words_per_time_segment
                end_idx = min((i + 1) * words_per_time_segment, len(words))
                segment_text = " ".join(words[start_idx:end_idx])
                
                start_time_est = int(i * time_segments)
                end_time_est = int(min((i + 1) * time_segments, len(words) // words_per_minute))
                
                lines.append(f"### ~{start_time_est:02d}:00 - ~{end_time_est:02d}:00 (Estimated)")
                lines.append("")
                lines.append("**[ASSIGN SPEAKER]:** " + segment_text.strip())
                lines.append("")
                lines.append("---")
                lines.append("")
        else:
            # Single transcript block
            lines.append("**[ASSIGN SPEAKERS]:** " + transcript_text.strip())
            lines.append("")
        
        # Footer with next steps
        lines.append("---")
        lines.append("")
        lines.append("## Next Steps")
        lines.append("")
        lines.append("After manually assigning speakers:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Generate session notes from your edited transcript")
        lines.append(f"./gm session summarize {audio_file.stem}_transcript.md --out {audio_file.stem}_session_notes.md")
        lines.append("```")
        lines.append("")
        
        return "\n".join(lines)


def generate_transcript(
    audio_path: str,
    output_path: Optional[str] = None,
    huggingface_token: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None
) -> str:
    """
    Convenience function to generate a transcript from audio.
    
    Args:
        audio_path: Path to the audio file
        output_path: Path to save transcript (optional)
        huggingface_token: HuggingFace token for diarization
        openai_api_key: OpenAI API key for transcription
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        
    Returns:
        Path to the generated transcript file
    """
    generator = TranscriptGenerator(huggingface_token, openai_api_key)
    return generator.generate_transcript(
        audio_path, 
        output_path, 
        min_speakers, 
        max_speakers
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python transcript_generator.py <audio_file> [output_file]")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        transcript_path = generate_transcript(
            audio_path, 
            output_path,
            huggingface_token,
            openai_api_key
        )
        print(f"\n✅ Transcript generated: {transcript_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)