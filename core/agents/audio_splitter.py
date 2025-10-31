"""
Audio Splitter Agent for Shadowdark GM Assistant

This agent automatically splits large audio files into smaller segments
suitable for Whisper API processing (< 25MB limit) while maintaining
quality and providing seamless segment boundaries.
"""

import os
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioSplitter:
    """
    Splits large audio files into smaller segments for processing.
    
    Handles the 25MB Whisper API limit by intelligently segmenting audio
    with overlap to prevent speech cutoff at boundaries.
    """
    
    def __init__(self):
        self.max_size_mb = 23  # Stay under 25MB limit with buffer
        self.overlap_seconds = 30  # Overlap between segments for continuity
        self._supported_formats = {'.wav', '.mp3', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm'}
    
    def should_split(self, audio_path: Path) -> bool:
        """
        Check if audio file needs splitting based on size.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            True if file needs splitting, False otherwise
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        logger.info(f"📏 Audio file size: {file_size_mb:.1f}MB")
        
        if file_size_mb > 25:
            logger.info(f"🔄 File exceeds 25MB limit - splitting required")
            return True
        else:
            logger.info(f"✅ File size OK - no splitting needed")
            return False
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """
        Get audio duration in seconds using ffprobe.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                'ffprobe', '-i', str(audio_path),
                '-show_entries', 'format=duration',
                '-v', 'quiet', '-of', 'csv=p=0'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"ffprobe failed: {result.stderr}")
            
            duration = float(result.stdout.strip())
            logger.info(f"⏱️  Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            return duration
            
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            # Fallback to file size estimation (very rough)
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            estimated_duration = file_size_mb * 8  # Very rough estimate
            logger.warning(f"Using estimated duration: {estimated_duration:.1f} seconds")
            return estimated_duration
    
    def calculate_segment_duration(self, total_duration: float, file_size_mb: float) -> float:
        """
        Calculate optimal segment duration to stay under size limit.
        
        Args:
            total_duration: Total audio duration in seconds
            file_size_mb: Total file size in MB
            
        Returns:
            Segment duration in seconds
        """
        # Calculate size per second
        mb_per_second = file_size_mb / total_duration
        
        # Calculate segment duration to stay under limit
        target_segment_duration = self.max_size_mb / mb_per_second
        
        # Round down to nearest 5 minutes for clean segments
        target_minutes = math.floor(target_segment_duration / 300) * 5
        if target_minutes < 5:  # Minimum 5 minutes
            target_minutes = 5
        
        segment_duration = target_minutes * 60
        logger.info(f"📊 Calculated segment duration: {segment_duration/60:.1f} minutes")
        
        return segment_duration
    
    def split_audio(self, audio_path: str, output_dir: Optional[str] = None) -> List[Path]:
        """
        Split audio file into smaller segments.
        
        Args:
            audio_path: Path to the input audio file
            output_dir: Directory to save segments (defaults to same directory as input)
            
        Returns:
            List of paths to the created segment files
        """
        audio_path = Path(audio_path)
        
        # Validate input
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if audio_path.suffix.lower() not in self._supported_formats:
            raise ValueError(f"Unsupported audio format: {audio_path.suffix}")
        
        # Check if splitting is needed
        if not self.should_split(audio_path):
            logger.info("📝 No splitting needed - returning original file")
            return [audio_path]
        
        # Get audio metadata
        total_duration = self.get_audio_duration(audio_path)
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        
        # Calculate segment parameters
        segment_duration = self.calculate_segment_duration(total_duration, file_size_mb)
        
        # Set up output directory
        if output_dir is None:
            output_dir = audio_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filenames
        base_name = audio_path.stem
        extension = audio_path.suffix
        
        segments = []
        segment_num = 0
        current_start = 0.0
        
        logger.info(f"🔪 Starting audio splitting...")
        logger.info(f"   Total duration: {total_duration/60:.1f} minutes")
        logger.info(f"   Segment length: {segment_duration/60:.1f} minutes")
        logger.info(f"   Overlap: {self.overlap_seconds} seconds")
        
        while current_start < total_duration:
            segment_num += 1
            
            # Calculate segment end time
            segment_end = min(current_start + segment_duration, total_duration)
            
            # Generate output filename
            output_filename = f"{base_name}_segment_{segment_num:03d}{extension}"
            output_path = output_dir / output_filename
            
            logger.info(f"📦 Creating segment {segment_num}: {current_start/60:.1f}min - {segment_end/60:.1f}min")
            
            # Use ffmpeg to extract segment
            try:
                cmd = [
                    'ffmpeg', '-i', str(audio_path),
                    '-ss', str(current_start),
                    '-t', str(segment_end - current_start),
                    '-c', 'copy',  # Copy without re-encoding for speed
                    '-avoid_negative_ts', 'make_zero',
                    '-y',  # Overwrite output files
                    str(output_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"ffmpeg failed: {result.stderr}")
                
                segments.append(output_path)
                
                # Verify segment size
                segment_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"   ✅ Segment {segment_num}: {segment_size_mb:.1f}MB")
                
                if segment_size_mb > 25:
                    logger.warning(f"⚠️  Segment {segment_num} still over 25MB - may need further splitting")
                
            except Exception as e:
                logger.error(f"❌ Failed to create segment {segment_num}: {e}")
                # Continue with other segments
                continue
            
            # Move to next segment (with overlap)
            if segment_end >= total_duration:
                break
            current_start = segment_end - self.overlap_seconds
        
        logger.info(f"✅ Audio splitting complete!")
        logger.info(f"   Created {len(segments)} segments")
        logger.info(f"   Total processing time will be approximately {len(segments) * 2:.0f}-{len(segments) * 4:.0f} minutes")
        
        return segments
    
    def estimate_processing_time(self, segments: List[Path]) -> Tuple[int, int]:
        """
        Estimate total processing time for all segments.
        
        Args:
            segments: List of audio segment paths
            
        Returns:
            Tuple of (min_minutes, max_minutes) for estimated processing time
        """
        num_segments = len(segments)
        
        # Rough estimates based on Apple Silicon performance
        min_time_per_segment = 2  # minutes (fast mode)
        max_time_per_segment = 8  # minutes (full diarization)
        
        min_total = num_segments * min_time_per_segment
        max_total = num_segments * max_time_per_segment
        
        return min_total, max_total


def split_audio_file(audio_path: str, output_dir: Optional[str] = None) -> List[Path]:
    """
    Convenience function to split an audio file.
    
    Args:
        audio_path: Path to the input audio file
        output_dir: Directory to save segments (optional)
        
    Returns:
        List of paths to the created segment files
    """
    splitter = AudioSplitter()
    return splitter.split_audio(audio_path, output_dir)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio_splitter.py <audio_file> [output_dir]")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        segments = split_audio_file(audio_path, output_dir)
        print(f"\n✅ Successfully created {len(segments)} segments:")
        for i, segment in enumerate(segments, 1):
            print(f"   {i}. {segment.name}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)