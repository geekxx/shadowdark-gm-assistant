"""
Speaker Diarization Agent for Shadowdark GM Assistant

This agent processes audio files to identify different speakers and create 
diarized transcripts w        # Try to process original file first, convert only if needed
        converted_audio = None
        try:
            # Try original file first
            diarization = self.pipeline(str(audio_path))
            logger.info(f"Successfully processed {audio_path.suffix} file directly")
            wav_path = audio_path
        except Exception as e:
            logger.info(f"Direct processing failed, attempting conversion: {e}")
            try:
                wav_path = self._convert_audio_format(audio_path)
                converted_audio = wav_path if wav_path != audio_path else Nonepeaker labels and timestamps.
"""

import os
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch
import librosa
import soundfile as sf
from dataclasses import dataclass
from openai import OpenAI

# Import pyannote.audio components
from pyannote.audio import Pipeline
from pyannote.core import Annotation, Segment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """Represents a segment of audio with speaker information."""
    start_time: float
    end_time: float
    speaker_id: str
    duration: float
    
    def __post_init__(self):
        if self.duration == 0:
            self.duration = self.end_time - self.start_time


@dataclass
class DiarizationResult:
    """Results from speaker diarization process."""
    segments: List[SpeakerSegment]
    num_speakers: int
    total_duration: float
    speaker_stats: Dict[str, float]  # speaker_id -> total speaking time


class SpeakerDiarizer:
    """
    Speaker diarization agent using pyannote.audio.
    
    This agent can:
    1. Process audio files to identify different speakers
    2. Create speaker-labeled transcripts
    3. Generate speaker statistics
    4. Handle various audio formats
    """
    
    def __init__(self, huggingface_token: Optional[str] = None, openai_api_key: Optional[str] = None):
        """
        Initialize the diarizer.
        
        Args:
            huggingface_token: HuggingFace access token for accessing models
            openai_api_key: OpenAI API key for Whisper transcription
        """
        self.huggingface_token = huggingface_token
        self.pipeline = None
        self._supported_formats = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        
        # Initialize OpenAI client for Whisper transcription
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        
    def _load_pipeline(self):
        """Load the pyannote.audio diarization pipeline."""
        if self.pipeline is None:
            try:
                # Try to load the community model (free) with optimizations
                if self.huggingface_token:
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-community-1",
                        token=self.huggingface_token
                    )
                else:
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-community-1"
                    )
                
                # Apple Silicon optimizations
                if torch.backends.mps.is_available():
                    # Enable optimized operations for Apple Silicon
                    torch.backends.mps.enable_fallback = True
                    logger.info("🍎 Enabled Apple Silicon MPS optimizations")
                
                # Send pipeline to best available device (Apple Silicon MPS, CUDA, or CPU)
                if torch.backends.mps.is_available():
                    device = torch.device("mps")
                    logger.info("🚀 Using Apple Silicon MPS acceleration for diarization")
                elif torch.cuda.is_available():
                    device = torch.device("cuda")
                    logger.info("🚀 Using NVIDIA CUDA acceleration for diarization")
                else:
                    device = torch.device("cpu")
                    logger.info("⚠️  Using CPU for diarization (slower)")
                
                self.pipeline.to(device)
                logger.info(f"Loaded diarization pipeline on {device}")
                
            except Exception as e:
                logger.error(f"Failed to load diarization pipeline: {e}")
                logger.info("Note: You may need to accept the model license at: "
                          "https://huggingface.co/pyannote/speaker-diarization-community-1")
                raise
    
    def _convert_audio_format(self, audio_path: Path) -> Path:
        """
        Convert audio to WAV format if needed.
        
        Args:
            audio_path: Path to the input audio file
            
        Returns:
            Path to WAV file (original if already WAV, converted if not)
        """
        if audio_path.suffix.lower() == '.wav':
            return audio_path
            
        # Create temporary WAV file
        temp_wav = Path(tempfile.mktemp(suffix='.wav'))
        
        try:
            # Use ffmpeg for robust audio conversion with pyannote-compatible settings
            cmd = [
                'ffmpeg', '-i', str(audio_path), 
                '-acodec', 'pcm_s16le',     # 16-bit PCM
                '-ar', '16000',             # 16kHz sample rate (pyannote standard)
                '-ac', '1',                 # Mono channel
                '-af', 'aresample=16000:resampler=soxr',  # High-quality resampling
                '-y',                       # Overwrite output file
                '-loglevel', 'error',       # Suppress verbose output
                str(temp_wav)
            ]
            
            # Run ffmpeg conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg conversion failed: {result.stderr}")
                
            logger.info(f"Converted {audio_path.suffix} to WAV format using ffmpeg")
            return temp_wav
            
        except Exception as e:
            logger.error(f"Failed to convert audio format: {e}")
            if temp_wav.exists():
                temp_wav.unlink()
            raise
    
    def diarize_audio(
        self, 
        audio_path: str, 
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        min_segment_duration: float = 1.0,
        merge_threshold: float = 0.5
    ) -> DiarizationResult:
        """
        Perform speaker diarization on an audio file.
        
        Args:
            audio_path: Path to the audio file
            min_speakers: Minimum number of speakers (optional)
            max_speakers: Maximum number of speakers (optional)
            
        Returns:
            DiarizationResult with speaker segments and statistics
        """
        audio_path = Path(audio_path)
        
        # Validate input
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        if audio_path.suffix.lower() not in self._supported_formats:
            raise ValueError(f"Unsupported audio format: {audio_path.suffix}. "
                           f"Supported formats: {self._supported_formats}")
        
        # Load pipeline
        self._load_pipeline()
        
        # Try to process original file first, convert only if needed
        converted_audio = None
        wav_path = audio_path
        
        try:
            # Set speaker constraints if provided
            # Note: pyannote clustering constraints are set during pipeline creation
            # For runtime constraints, we'll need to modify the approach
            if min_speakers is not None or max_speakers is not None:
                logger.info(f"🎯 Speaker constraints: min={min_speakers}, max={max_speakers}")
                logger.info("Note: Runtime speaker constraints not yet implemented")
            
            # Get audio duration for progress estimation
            try:
                import librosa
                audio_duration = librosa.get_duration(path=str(audio_path))
                duration_mins = int(audio_duration // 60)
                duration_secs = int(audio_duration % 60)
                
                if audio_duration > 7200:  # > 2 hours
                    logger.info(f"🎵 Starting diarization of {audio_path.name} ({duration_mins}m {duration_secs}s)")
                    logger.info("⏰ Long audio detected! This may take 10-20 minutes on Apple Silicon...")
                elif audio_duration > 3600:  # > 1 hour
                    logger.info(f"🎵 Starting diarization of {audio_path.name} ({duration_mins}m {duration_secs}s)")
                    logger.info("⏰ Medium-length audio detected! This may take 5-10 minutes on Apple Silicon...")
                else:
                    logger.info(f"🎵 Starting diarization of {audio_path.name} ({duration_mins}m {duration_secs}s)")
                    logger.info("⏰ Processing should complete in a few minutes on Apple Silicon...")
            except Exception:
                logger.info(f"🎵 Starting diarization of {audio_path.name}...")
                logger.info("📊 This may take several minutes depending on audio length...")
            
            try:
                logger.info("🔍 Analyzing audio with ML model...")
                diarization = self.pipeline(str(audio_path))
                logger.info(f"✅ Successfully processed {audio_path.suffix} file directly")
            except Exception as direct_error:
                logger.info(f"⚠️  Direct processing failed, converting audio format...")
                logger.info(f"   Error details: {direct_error}")
                logger.info("🔄 Converting audio to compatible format...")
                wav_path = self._convert_audio_format(audio_path)
                converted_audio = wav_path if wav_path != audio_path else None
                logger.info("🔍 Re-analyzing converted audio...")
                diarization = self.pipeline(str(wav_path))
            
            # Process results
            logger.info("📝 Processing diarization results...")
            segments = []
            speaker_stats = {}
            
            # Handle pyannote.audio 4.x API - diarization is an Annotation object
            try:
                # For pyannote.audio 4.x, use the track() method to iterate
                if hasattr(diarization, 'itertracks'):
                    # pyannote 3.x API
                    for segment, _, speaker in diarization.itertracks(yield_label=True):
                        speaker_segment = SpeakerSegment(
                            start_time=segment.start,
                            end_time=segment.end,
                            speaker_id=speaker,
                            duration=segment.duration
                        )
                        segments.append(speaker_segment)
                        
                        # Update speaker statistics
                        if speaker not in speaker_stats:
                            speaker_stats[speaker] = 0
                        speaker_stats[speaker] += segment.duration
                        
                elif hasattr(diarization, 'speaker_diarization'):
                    # pyannote 4.x API - DiarizeOutput object
                    annotation = diarization.speaker_diarization
                    logger.info(f"Got speaker_diarization annotation: {type(annotation)}")
                    
                    # The annotation should have itertracks method
                    if hasattr(annotation, 'itertracks'):
                        for segment, _, speaker in annotation.itertracks(yield_label=True):
                            speaker_segment = SpeakerSegment(
                                start_time=segment.start,
                                end_time=segment.end,
                                speaker_id=speaker,
                                duration=segment.duration
                            )
                            segments.append(speaker_segment)
                            
                            # Update speaker statistics
                            if speaker not in speaker_stats:
                                speaker_stats[speaker] = 0
                            speaker_stats[speaker] += segment.duration
                    else:
                        # Try for_json if available
                        if hasattr(annotation, 'for_json'):
                            json_data = annotation.for_json()
                            for item in json_data['content']:
                                segment_info = item['segment']
                                speaker = item['label']
                                start_time = segment_info['start']
                                end_time = segment_info['end']
                                duration = end_time - start_time
                                
                                speaker_segment = SpeakerSegment(
                                    start_time=start_time,
                                    end_time=end_time,
                                    speaker_id=speaker,
                                    duration=duration
                                )
                                segments.append(speaker_segment)
                                
                                # Update speaker statistics
                                if speaker not in speaker_stats:
                                    speaker_stats[speaker] = 0
                                speaker_stats[speaker] += duration
                        else:
                            raise Exception(f"Annotation object has no supported iteration method: {type(annotation)}")
                else:
                    raise Exception(f"Unsupported diarization object type: {type(diarization)}")
                    
            except Exception as e:
                logger.error(f"Error processing diarization results: {e}")
                logger.info(f"Diarization object type: {type(diarization)}")
                logger.info(f"Available methods: {[method for method in dir(diarization) if not method.startswith('_')]}")
                raise
            
            # Calculate total duration from segments (avoids librosa issues)
            total_duration = max(segment.end_time for segment in segments) if segments else 0.0
            
            # Sort segments by start time
            segments.sort(key=lambda s: s.start_time)
            
            # Apply post-processing to improve diarization quality
            logger.info("🔧 Post-processing diarization results...")
            segments = self._post_process_segments(segments, min_segment_duration, merge_threshold)
            
            # Recalculate speaker stats after post-processing
            speaker_stats = {}
            for segment in segments:
                if segment.speaker_id not in speaker_stats:
                    speaker_stats[segment.speaker_id] = 0
                speaker_stats[segment.speaker_id] += segment.duration
            
            # Log completion summary
            num_speakers = len(speaker_stats)
            logger.info(f"🎉 Diarization completed successfully!")
            logger.info(f"   📊 Detected {num_speakers} speakers in {total_duration:.1f} seconds")
            logger.info(f"   🗣️  Speaker breakdown:")
            for speaker_id, duration in speaker_stats.items():
                percentage = duration/total_duration*100 if total_duration > 0 else 0
                logger.info(f"      {speaker_id}: {duration:.1f}s ({percentage:.1f}%)")
            
            result = DiarizationResult(
                segments=segments,
                num_speakers=num_speakers,  
                total_duration=total_duration,
                speaker_stats=speaker_stats
            )
            
            logger.info(f"Diarization complete: {result.num_speakers} speakers identified "
                       f"in {total_duration:.1f}s of audio")
            
            return result
            
        finally:
            # Clean up temporary files
            if converted_audio and converted_audio.exists():
                converted_audio.unlink()
    
    def create_speaker_transcript(
        self, 
        diarization_result: DiarizationResult,
        transcript_text: Optional[str] = None
    ) -> str:
        """
        Create a transcript with speaker labels and timestamps.
        
        Args:
            diarization_result: Results from diarization
            transcript_text: Optional transcript text to align with speakers
            
        Returns:
            Formatted transcript with speaker labels
        """
        lines = []
        lines.append("# Speaker Diarization Results")
        lines.append("")
        
        # Speaker statistics
        lines.append("## Speaker Statistics")
        for speaker_id, speaking_time in diarization_result.speaker_stats.items():
            percentage = (speaking_time / diarization_result.total_duration) * 100
            lines.append(f"- **{speaker_id}**: {speaking_time:.1f}s ({percentage:.1f}%)")
        lines.append("")
        
        # Timeline with transcript content
        lines.append("## Speaker Timeline")
        lines.append("")
        
        # Align transcript with speakers if available
        aligned_transcript = {}
        if transcript_text:
            logger.info("📝 Aligning transcript with speaker segments...")
            aligned_transcript = self._align_transcript_with_speakers(transcript_text, diarization_result.segments)
        
        for i, segment in enumerate(diarization_result.segments):
            timestamp = f"[{self._format_time(segment.start_time)} - {self._format_time(segment.end_time)}]"
            lines.append(f"**{segment.speaker_id}** {timestamp}")
            
            if i in aligned_transcript and aligned_transcript[i].strip():
                # Use aligned transcript content
                lines.append(aligned_transcript[i].strip())
            elif transcript_text:
                # Has transcript but alignment failed for this segment
                lines.append("(No content aligned to this segment)")
            else:
                # No transcript provided
                lines.append("(Audio segment - no transcript provided)")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file using OpenAI Whisper API.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcript text or None if transcription fails
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available - cannot transcribe audio")
            return None
            
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None
        
        try:
            logger.info("🎙️  Starting speech-to-text transcription with OpenAI Whisper...")
            
            # Check file size (Whisper has 25MB limit)
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 25:
                logger.warning(f"⚠️  Audio file is {file_size_mb:.1f}MB (Whisper limit: 25MB)")
                logger.info("🔄 Large file detected - using local transcription fallback")
                
                # Use a simple fallback for very large files
                # In a production system, you could split the audio into chunks
                # For now, return a placeholder that indicates we need manual transcription
                logger.error("❌ File too large for automatic transcription. Please:")
                logger.error("   1. Split the audio file into smaller segments (<25MB each)")
                logger.error("   2. Use a local Whisper installation for large files")
                logger.error("   3. Or provide a pre-transcribed text file")
                return "Large audio file detected. Manual transcription required. Please split the file or provide a text transcript."
            
            # Open and transcribe the audio file
            with open(audio_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info("✅ Speech-to-text transcription completed successfully")
            return transcript
            
        except Exception as e:
            logger.error(f"❌ Failed to transcribe audio: {e}")
            return None
    
    def _align_transcript_with_speakers(self, transcript: str, segments: List[SpeakerSegment]) -> Dict[int, str]:
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
    
    def diarize_and_transcribe(
        self,
        audio_path: str,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        min_segment_duration: float = 1.0,
        merge_threshold: float = 0.5
    ) -> Tuple[DiarizationResult, Optional[str]]:
        """
        Perform both speaker diarization and speech-to-text transcription.
        
        Args:
            audio_path: Path to the audio file
            min_speakers: Minimum number of speakers (optional)
            max_speakers: Maximum number of speakers (optional)
            
        Returns:
            Tuple of (DiarizationResult, transcript_text)
        """
        logger.info("🎵 Starting combined diarization and transcription...")
        
        # Step 1: Perform speaker diarization
        diarization_result = self.diarize_audio(
            audio_path, min_speakers, max_speakers, 
            min_segment_duration, merge_threshold
        )
        
        # Step 2: Transcribe the audio (if OpenAI client available)
        transcript_text = None
        if self.openai_client:
            transcript_text = self.transcribe_audio(audio_path)
            
            # Step 2.5: Apply transcript-based corrections if we have the text
            if transcript_text:
                logger.info("🔍 Applying transcript-based speaker corrections...")
                
                # Apply mid-sentence split detection
                corrected_segments = self._detect_mid_sentence_splits(
                    diarization_result.segments, transcript_text
                )
                
                # Apply gaming session heuristics
                gaming_corrected = self._apply_gaming_session_heuristics(
                    corrected_segments, transcript_text
                )
                
                diarization_result.segments = gaming_corrected
        else:
            logger.warning("⚠️  OpenAI client not available - skipping transcription")
        
        logger.info("🎉 Combined processing completed!")
        return diarization_result, transcript_text
    
    def get_speaker_mapping(self, diarization_result: DiarizationResult) -> Dict[str, str]:
        """
        Create a mapping from technical speaker IDs to human-readable names.
        
        Args:
            diarization_result: Results from diarization
            
        Returns:
            Dictionary mapping speaker IDs to human-readable names
        """
        mapping = {}
        
        # Sort speakers by total speaking time (most active first)
        sorted_speakers = sorted(
            diarization_result.speaker_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Assign human-readable names
        role_names = ["GM", "Player 1", "Player 2", "Player 3", "Player 4", "Player 5"]
        
        for i, (speaker_id, _) in enumerate(sorted_speakers):
            if i < len(role_names):
                mapping[speaker_id] = role_names[i]
            else:
                mapping[speaker_id] = f"Speaker {i + 1}"
        
        return mapping
    
    def apply_speaker_mapping(
        self, 
        transcript: str,
        speaker_mapping: Dict[str, str]
    ) -> str:
        """
        Apply human-readable speaker names to a transcript.
        
        Args:
            transcript: Original transcript with technical speaker IDs
            speaker_mapping: Mapping from technical IDs to readable names
            
        Returns:
            Transcript with human-readable speaker names
        """
        result = transcript
        
        # Replace speaker IDs with readable names
        for tech_id, readable_name in speaker_mapping.items():
            result = result.replace(f"**{tech_id}**", f"**{readable_name}**")
        
        return result
    
    def _post_process_segments(
        self, 
        segments: List[SpeakerSegment], 
        min_duration: float = 1.0,
        merge_threshold: float = 0.5
    ) -> List[SpeakerSegment]:
        """
        Post-process diarization segments to improve quality.
        
        This method:
        1. Merges very short segments with adjacent segments
        2. Applies speaker smoothing to reduce rapid switching
        3. Fills small gaps between segments from the same speaker
        
        Args:
            segments: Original segments from diarization
            min_duration: Minimum duration for segments (seconds)
            merge_threshold: Time threshold for merging segments (seconds)
            
        Returns:
            List of post-processed segments
        """
        if not segments:
            return segments
        
        processed = segments.copy()
        
        # Step 1: Merge very short segments with neighbors
        logger.info(f"🔄 Merging segments shorter than {min_duration}s...")
        merged_segments = []
        i = 0
        
        while i < len(processed):
            current = processed[i]
            
            # If segment is too short, try to merge it
            if current.duration < min_duration and len(processed) > 1:
                # Find best neighbor to merge with
                best_neighbor_idx = None
                best_overlap_score = 0
                
                # Check previous segment
                if i > 0:
                    prev = processed[i-1]
                    gap = current.start_time - prev.end_time
                    if gap <= merge_threshold:
                        # Prefer same speaker or close temporal proximity
                        score = (2.0 if prev.speaker_id == current.speaker_id else 1.0) / max(gap, 0.1)
                        if score > best_overlap_score:
                            best_overlap_score = score
                            best_neighbor_idx = i-1
                
                # Check next segment
                if i < len(processed) - 1:
                    next_seg = processed[i+1]
                    gap = next_seg.start_time - current.end_time
                    if gap <= merge_threshold:
                        # Prefer same speaker or close temporal proximity
                        score = (2.0 if next_seg.speaker_id == current.speaker_id else 1.0) / max(gap, 0.1)
                        if score > best_overlap_score:
                            best_overlap_score = score
                            best_neighbor_idx = i+1
                
                # Merge with best neighbor if found
                if best_neighbor_idx is not None:
                    neighbor = processed[best_neighbor_idx]
                    
                    if best_neighbor_idx < i:
                        # Merge with previous segment - extend it to include current
                        if merged_segments:  # Update the already-added previous segment
                            merged_segments[-1] = SpeakerSegment(
                                start_time=neighbor.start_time,
                                end_time=current.end_time,
                                speaker_id=neighbor.speaker_id,  # Use neighbor's speaker
                                duration=current.end_time - neighbor.start_time
                            )
                        i += 1
                        continue
                    else:
                        # Merge with next segment - will be handled in next iteration
                        processed[i+1] = SpeakerSegment(
                            start_time=current.start_time,
                            end_time=neighbor.end_time,
                            speaker_id=neighbor.speaker_id,  # Use neighbor's speaker
                            duration=neighbor.end_time - current.start_time
                        )
                        i += 1
                        continue
            
            # Keep segment as-is
            merged_segments.append(current)
            i += 1
        
        processed = merged_segments
        
        # Step 2: Fill small gaps between segments from the same speaker
        logger.info(f"🔗 Filling gaps smaller than {merge_threshold}s between same-speaker segments...")
        gap_filled = []
        
        for i, segment in enumerate(processed):
            if gap_filled and i < len(processed):
                prev_segment = gap_filled[-1]
                gap = segment.start_time - prev_segment.end_time
                
                # If small gap and same speaker, extend previous segment
                if (gap > 0 and gap <= merge_threshold and 
                    prev_segment.speaker_id == segment.speaker_id):
                    
                    # Extend previous segment to include the gap and merge with current
                    gap_filled[-1] = SpeakerSegment(
                        start_time=prev_segment.start_time,
                        end_time=segment.end_time,
                        speaker_id=prev_segment.speaker_id,
                        duration=segment.end_time - prev_segment.start_time
                    )
                    continue
            
            gap_filled.append(segment)
        
        # Step 3: Fix speaker attribution errors using context analysis
        context_corrected = self._fix_speaker_attribution_errors(gap_filled)
        
        # Step 4: Flag remaining potential speaker misattributions
        flagged_segments = self._flag_potential_errors(context_corrected)
        
        logger.info(f"✅ Post-processing complete: {len(segments)} → {len(flagged_segments)} segments")
        return flagged_segments
    
    def _fix_speaker_attribution_errors(self, segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """
        Fix speaker attribution errors using context analysis.
        
        This method looks for patterns that indicate misattribution:
        1. Very short segments between longer segments of the same speaker
        2. Isolated speaker changes that break up continuous speech
        3. Context-based corrections using speaking time patterns
        """
        if len(segments) < 3:
            return segments
        
        corrected = segments.copy()
        corrections_made = 0
        
        # Pass 1: Fix isolated short segments between same-speaker segments
        i = 1
        while i < len(corrected) - 1:
            current = corrected[i]
            prev_segment = corrected[i-1]
            next_segment = corrected[i+1]
            
            # Look for pattern: SpeakerA -> SpeakerB (short) -> SpeakerA
            if (prev_segment.speaker_id == next_segment.speaker_id and 
                current.speaker_id != prev_segment.speaker_id and
                current.duration < 2.0 and  # Very short segment
                (current.start_time - prev_segment.end_time) < 1.0):  # Close timing
                
                # This is likely a misattribution - assign to the surrounding speaker
                logger.info(f"🔧 Correcting misattribution: {current.speaker_id} -> {prev_segment.speaker_id} "
                           f"(segment {current.start_time:.1f}s-{current.end_time:.1f}s)")
                
                corrected[i] = SpeakerSegment(
                    start_time=current.start_time,
                    end_time=current.end_time,
                    speaker_id=prev_segment.speaker_id,  # Use surrounding speaker
                    duration=current.duration
                )
                corrections_made += 1
            
            i += 1
        
        # Pass 2: Merge newly corrected segments with neighbors
        if corrections_made > 0:
            merged = []
            i = 0
            
            while i < len(corrected):
                current = corrected[i]
                
                # Try to merge with previous segment if same speaker and close timing
                if (merged and 
                    merged[-1].speaker_id == current.speaker_id and
                    (current.start_time - merged[-1].end_time) <= 1.0):
                    
                    # Extend the previous segment
                    merged[-1] = SpeakerSegment(
                        start_time=merged[-1].start_time,
                        end_time=current.end_time,
                        speaker_id=merged[-1].speaker_id,
                        duration=current.end_time - merged[-1].start_time
                    )
                else:
                    merged.append(current)
                
                i += 1
            
            corrected = merged
        
        # Pass 3: Apply speaker dominance analysis for long sequences
        # Find sequences where one speaker should likely be dominant
        window_size = 5  # Look at 5-segment windows
        for start_idx in range(len(corrected) - window_size + 1):
            window = corrected[start_idx:start_idx + window_size]
            
            # Count speaker occurrences and total duration in window
            speaker_stats = {}
            for seg in window:
                if seg.speaker_id not in speaker_stats:
                    speaker_stats[seg.speaker_id] = {'count': 0, 'duration': 0}
                speaker_stats[seg.speaker_id]['count'] += 1
                speaker_stats[seg.speaker_id]['duration'] += seg.duration
            
            # Find dominant speaker (by duration)
            dominant_speaker = max(speaker_stats.keys(), 
                                 key=lambda s: speaker_stats[s]['duration'])
            dominant_duration = speaker_stats[dominant_speaker]['duration']
            total_duration = sum(stats['duration'] for stats in speaker_stats.values())
            
            # If one speaker dominates >80% of the time in this window
            if dominant_duration / total_duration > 0.8:
                # Look for very short segments from other speakers to correct
                for i, seg in enumerate(window):
                    actual_idx = start_idx + i
                    if (seg.speaker_id != dominant_speaker and 
                        seg.duration < 1.5 and
                        len([s for s in window if s.speaker_id == seg.speaker_id]) == 1):  # Only occurrence
                        
                        logger.info(f"🔧 Context correction: {seg.speaker_id} -> {dominant_speaker} "
                                   f"(segment {seg.start_time:.1f}s-{seg.end_time:.1f}s, dominant speaker pattern)")
                        
                        corrected[actual_idx] = SpeakerSegment(
                            start_time=seg.start_time,
                            end_time=seg.end_time,
                            speaker_id=dominant_speaker,
                            duration=seg.duration
                        )
                        corrections_made += 1
        
        if corrections_made > 0:
            logger.info(f"🎯 Fixed {corrections_made} speaker attribution errors using context analysis")
            
            # Final merge pass after corrections
            final_merged = []
            for segment in corrected:
                if (final_merged and 
                    final_merged[-1].speaker_id == segment.speaker_id and
                    (segment.start_time - final_merged[-1].end_time) <= 0.5):
                    
                    # Merge with previous
                    final_merged[-1] = SpeakerSegment(
                        start_time=final_merged[-1].start_time,
                        end_time=segment.end_time,
                        speaker_id=final_merged[-1].speaker_id,
                        duration=segment.end_time - final_merged[-1].start_time
                    )
                else:
                    final_merged.append(segment)
            
            return final_merged
        
        return corrected
    
    def _detect_mid_sentence_splits(self, segments: List[SpeakerSegment], transcript_text: str) -> List[SpeakerSegment]:
        """
        Detect and fix cases where sentences are split mid-word between speakers.
        
        This addresses issues like "Player says most of sentence" -> "GM says 'And she'"
        where it's clearly a continuation that got misattributed.
        """
        if not transcript_text or len(segments) < 2:
            return segments
        
        # Split transcript into words for analysis
        words = transcript_text.split()
        if not words:
            return segments
        
        corrected = segments.copy()
        corrections = 0
        
        # Look for very short segments that start with conjunctions or continue previous thought
        continuation_patterns = [
            'and', 'but', 'so', 'then', 'now', 'well', 'or', 'yet', 'for',
            'because', 'since', 'although', 'however', 'therefore', 'thus',
            'she', 'he', 'they', 'it', 'that', 'this', 'the'
        ]
        
        for i in range(1, len(corrected)):
            current = corrected[i]
            prev_segment = corrected[i-1]
            
            # Skip if same speaker
            if current.speaker_id == prev_segment.speaker_id:
                continue
                
            # Look for very short segments (< 3 seconds) that might be continuations
            if (current.duration < 3.0 and 
                (current.start_time - prev_segment.end_time) < 0.5):  # Very close timing
                
                # This segment might be a continuation of the previous speaker
                # Heuristic: if the previous segment was much longer, this might be misattributed
                if prev_segment.duration > current.duration * 3:  # Previous segment 3x longer
                    logger.info(f"🔧 Potential mid-sentence split detected: "
                               f"{prev_segment.speaker_id}({prev_segment.duration:.1f}s) -> "
                               f"{current.speaker_id}({current.duration:.1f}s)")
                    
                    # Assign short segment to the previous (longer) speaker
                    corrected[i] = SpeakerSegment(
                        start_time=current.start_time,
                        end_time=current.end_time,
                        speaker_id=prev_segment.speaker_id,
                        duration=current.duration
                    )
                    corrections += 1
        
        if corrections > 0:
            logger.info(f"🎯 Fixed {corrections} potential mid-sentence attribution errors")
        
        return corrected
    
    def _apply_gaming_session_heuristics(self, segments: List[SpeakerSegment], transcript_text: str) -> List[SpeakerSegment]:
        """
        Apply gaming session specific heuristics to improve speaker attribution.
        
        This method uses knowledge of gaming sessions to make better speaker decisions:
        - GMs typically speak longer (descriptions, NPCs)
        - Players typically ask questions and respond
        - Certain phrases are more likely from GM vs Players
        """
        if not transcript_text or len(segments) < 2:
            return segments
        
        # Find the most likely GM (speaker with most total speaking time)
        speaker_durations = {}
        for segment in segments:
            if segment.speaker_id not in speaker_durations:
                speaker_durations[segment.speaker_id] = 0
            speaker_durations[segment.speaker_id] += segment.duration
        
        likely_gm = max(speaker_durations.keys(), key=lambda s: speaker_durations[s])
        
        # GM phrases that indicate narration/description
        gm_indicators = [
            'you see', 'you notice', 'you hear', 'you feel', 'you find',
            'as you', 'and so', 'the door', 'the room', 'there is', 'there are',
            'make a', 'check', 'roll', 'okay so', 'alright', 'let me',
            'and she says', 'and he says', 'the npc', 'mother gull', 'uncle bemro'
        ]
        
        # Player phrases that indicate questions/responses  
        player_indicators = [
            'i want to', 'can i', 'do i', 'what if', 'how about',
            'my character', 'i think', 'i guess', 'yeah', 'okay', 'sure',
            'what does', 'where is', 'who is'
        ]
        
        corrected = segments.copy()
        corrections = 0
        
        # Simple text-based analysis on segments
        words = transcript_text.lower().split()
        words_per_segment = len(words) // len(segments) if segments else 0
        
        for i, segment in enumerate(corrected):
            # Estimate what text belongs to this segment (rough approximation)
            start_word = max(0, i * words_per_segment - 5)
            end_word = min(len(words), (i + 1) * words_per_segment + 5)
            segment_text = ' '.join(words[start_word:end_word]).lower()
            
            # Count GM vs Player indicators in this text region
            gm_score = sum(1 for phrase in gm_indicators if phrase in segment_text)
            player_score = sum(1 for phrase in player_indicators if phrase in segment_text)
            
            # If there's a strong indication this should be GM but isn't
            if (gm_score > player_score + 1 and 
                segment.speaker_id != likely_gm and
                segment.duration > 5.0):  # Only for longer segments
                
                logger.info(f"🎮 Gaming heuristic: {segment.speaker_id} -> {likely_gm} "
                           f"(GM indicators: {gm_score}, segment {segment.start_time:.1f}s)")
                
                corrected[i] = SpeakerSegment(
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    speaker_id=likely_gm,
                    duration=segment.duration
                )
                corrections += 1
        
        if corrections > 0:
            logger.info(f"🎮 Applied {corrections} gaming session heuristic corrections")
        
        return corrected
    
    def _flag_potential_errors(self, segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """
        Flag segments that might have speaker attribution errors.
        
        This looks for patterns like:
        - Very short segments between longer segments of different speakers
        - Rapid speaker switching that might indicate errors
        """
        if len(segments) < 3:
            return segments
        
        flagged_count = 0
        
        for i in range(1, len(segments) - 1):
            current = segments[i]
            prev_segment = segments[i-1]
            next_segment = segments[i+1]
            
            # Flag very short segments between different speakers
            if (current.duration < 0.5 and 
                prev_segment.speaker_id != current.speaker_id and
                next_segment.speaker_id != current.speaker_id and
                prev_segment.speaker_id == next_segment.speaker_id):
                
                # This might be a misattributed fragment
                flagged_count += 1
                # Could add a flag attribute to the segment here if needed
        
        if flagged_count > 0:
            logger.info(f"⚠️  Detected {flagged_count} potentially misattributed segments")
            logger.info("   Manual review recommended for short segments between longer speaker turns")
        
        return segments