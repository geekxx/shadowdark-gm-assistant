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
        max_speakers: Optional[int] = None
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
        max_speakers: Optional[int] = None
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
        diarization_result = self.diarize_audio(audio_path, min_speakers, max_speakers)
        
        # Step 2: Transcribe the audio (if OpenAI client available)
        transcript_text = None
        if self.openai_client:
            transcript_text = self.transcribe_audio(audio_path)
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