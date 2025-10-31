"""
Transcript Merger for Shadowdark GM Assistant

This tool merges multiple segment transcripts into one cohesive transcript,
handling speaker continuity and removing overlapping content at segment boundaries.
"""

import os
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptMerger:
    """
    Merges multiple segment transcripts into a single cohesive transcript.
    
    Handles speaker ID consistency, removes duplicate content at segment
    boundaries, and maintains proper formatting for manual review.
    """
    
    def __init__(self):
        self.overlap_threshold = 45  # seconds - look for overlaps within this range
    
    def merge_transcripts(self, transcript_files: List[str], output_path: str) -> str:
        """
        Merge multiple transcript files into one cohesive transcript.
        
        Args:
            transcript_files: List of paths to transcript files to merge
            output_path: Path to save the merged transcript
            
        Returns:
            Path to the merged transcript file
        """
        if not transcript_files:
            raise ValueError("No transcript files provided")
        
        logger.info(f"🔗 Merging {len(transcript_files)} transcript files...")
        
        # Parse all transcripts
        parsed_transcripts = []
        for file_path in transcript_files:
            logger.info(f"📄 Parsing: {Path(file_path).name}")
            parsed = self._parse_transcript_file(file_path)
            if parsed:
                parsed_transcripts.append(parsed)
        
        if not parsed_transcripts:
            raise ValueError("No valid transcripts found to merge")
        
        # Validate speaker consistency across transcripts
        self._validate_speaker_consistency(parsed_transcripts)
        
        # Merge transcripts
        merged_transcript = self._merge_parsed_transcripts(parsed_transcripts)
        
        # Write merged transcript
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(merged_transcript)
        
        logger.info(f"✅ Merged transcript saved to: {output_path}")
        return str(output_path)
    
    def _validate_speaker_consistency(self, parsed_transcripts: List[Dict]) -> None:
        """
        Validate that speaker names are consistent across transcripts.
        Issue warnings if inconsistencies are detected.
        """
        all_speakers = set()
        suspicious_speakers = set()
        
        for transcript in parsed_transcripts:
            speakers_in_transcript = set()
            
            for entry in transcript.get('entries', []):
                speaker = entry.get('speaker', '').strip()
                if speaker:
                    speakers_in_transcript.add(speaker)
                    all_speakers.add(speaker)
                    
                    # Check for common AI-generated speaker patterns
                    if 'Speaker_' in speaker or 'speaker_' in speaker:
                        suspicious_speakers.add(speaker)
        
        # Warn about potential consistency issues
        if suspicious_speakers:
            logger.warning("⚠️  POTENTIAL SPEAKER CONSISTENCY ISSUES DETECTED:")
            logger.warning("   Found AI-generated speaker labels that may be inconsistent:")
            for speaker in sorted(suspicious_speakers):
                logger.warning(f"   - {speaker}")
            logger.warning("")
            logger.warning("   🎯 RECOMMENDATION: Review transcripts before merging!")
            logger.warning("   Each segment assigns Speaker_1, Speaker_2 independently.")
            logger.warning("   The same person might have different labels in each segment.")
            logger.warning("")
        
        # Log all unique speakers found
        if len(all_speakers) > 0:
            logger.info(f"📋 Found {len(all_speakers)} unique speakers across all transcripts:")
            for speaker in sorted(all_speakers):
                logger.info(f"   - {speaker}")
            logger.info("")
    
    def _parse_transcript_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse a transcript file and extract structured data.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            Dictionary with parsed transcript data or None if parsing fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"⚠️  Transcript file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata
            metadata = self._extract_metadata(content)
            
            # Extract transcript entries
            entries = self._extract_transcript_entries(content)
            
            return {
                'file_path': file_path,
                'metadata': metadata,
                'entries': entries,
                'raw_content': content
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to parse {file_path}: {e}")
            return None
    
    def _extract_metadata(self, content: str) -> Dict:
        """Extract metadata from transcript content."""
        metadata = {}
        
        # Extract source audio file
        source_match = re.search(r'\\*\\*Source Audio:\\*\\* (.+)', content)
        if source_match:
            metadata['source_audio'] = source_match.group(1).strip()
        
        # Extract duration
        duration_match = re.search(r'\\*\\*Duration:\\*\\* ([0-9.]+) seconds', content)
        if duration_match:
            metadata['duration'] = float(duration_match.group(1))
        
        # Extract speakers
        speaker_pattern = r'- \\*\\*(.+?)\\*\\* \\((.+?)\\): ([0-9.]+)s \\(([0-9.]+)%\\)'
        speakers = {}
        for match in re.finditer(speaker_pattern, content):
            speaker_name = match.group(1)
            speaker_id = match.group(2)
            duration = float(match.group(3))
            percentage = float(match.group(4))
            speakers[speaker_id] = {
                'name': speaker_name,
                'duration': duration,
                'percentage': percentage
            }
        metadata['speakers'] = speakers
        
        return metadata
    
    def _extract_transcript_entries(self, content: str) -> List[Dict]:
        """Extract individual transcript entries with timestamps and speakers."""
        entries = []
        
        # Find the transcript section
        transcript_section_match = re.search(r'## Transcript\\s*\\n\\n(.+)', content, re.DOTALL)
        if not transcript_section_match:
            logger.warning("⚠️  No transcript section found in file")
            return entries
        
        transcript_content = transcript_section_match.group(1)
        
        # Extract timestamp headers and content
        # Pattern: ### MM:SS - MM:SS
        timestamp_pattern = r'### ([0-9]{2}:[0-9]{2}) - ([0-9]{2}:[0-9]{2})\\n\\*\\*(.+?):\\*\\* (.+?)(?=\\n###|\\n---|$)'
        
        for match in re.finditer(timestamp_pattern, transcript_content, re.DOTALL):
            start_time = match.group(1)
            end_time = match.group(2) 
            speaker = match.group(3)
            content_text = match.group(4).strip()
            
            # Convert timestamp to seconds for easier manipulation
            start_seconds = self._timestamp_to_seconds(start_time)
            end_seconds = self._timestamp_to_seconds(end_time)
            
            entries.append({
                'start_time': start_time,
                'end_time': end_time,
                'start_seconds': start_seconds,
                'end_seconds': end_seconds,
                'speaker': speaker,
                'content': content_text
            })
        
        return entries
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert MM:SS timestamp to seconds."""
        try:
            parts = timestamp.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except:
            return 0.0
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS timestamp."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _merge_parsed_transcripts(self, transcripts: List[Dict]) -> str:
        """Merge parsed transcripts into a single cohesive transcript."""
        
        # Sort transcripts by source audio name (assumes chronological naming)
        transcripts.sort(key=lambda t: t['file_path'].name)
        
        # Combine metadata
        merged_metadata = self._combine_metadata(transcripts)
        
        # Combine and deduplicate entries
        all_entries = []
        total_offset = 0.0
        
        for i, transcript in enumerate(transcripts):
            segment_entries = transcript['entries'].copy()
            
            # Adjust timestamps for continuity (except first segment)
            if i > 0:
                for entry in segment_entries:
                    entry['adjusted_start'] = entry['start_seconds'] + total_offset
                    entry['adjusted_end'] = entry['end_seconds'] + total_offset
            else:
                for entry in segment_entries:
                    entry['adjusted_start'] = entry['start_seconds']
                    entry['adjusted_end'] = entry['end_seconds']
            
            # Remove overlapping content from beginning of segment (except first)
            if i > 0 and len(all_entries) > 0:
                segment_entries = self._remove_overlap(all_entries, segment_entries)
            
            all_entries.extend(segment_entries)
            
            # Update offset for next segment
            if segment_entries:
                last_entry = segment_entries[-1]
                total_offset = last_entry['adjusted_end']
        
        # Generate merged transcript
        return self._generate_merged_transcript(merged_metadata, all_entries)
    
    def _combine_metadata(self, transcripts: List[Dict]) -> Dict:
        """Combine metadata from multiple transcripts."""
        combined = {
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_files': [],
            'total_duration': 0.0,
            'speakers': {}
        }
        
        # Collect source files and durations
        for transcript in transcripts:
            metadata = transcript['metadata']
            combined['source_files'].append(metadata.get('source_audio', 'Unknown'))
            combined['total_duration'] += metadata.get('duration', 0.0)
            
            # Merge speaker information
            for speaker_id, speaker_info in metadata.get('speakers', {}).items():
                if speaker_id not in combined['speakers']:
                    combined['speakers'][speaker_id] = {
                        'name': speaker_info['name'],
                        'total_duration': speaker_info['duration']
                    }
                else:
                    combined['speakers'][speaker_id]['total_duration'] += speaker_info['duration']
        
        # Recalculate percentages
        for speaker_info in combined['speakers'].values():
            speaker_info['percentage'] = (speaker_info['total_duration'] / combined['total_duration']) * 100
        
        return combined
    
    def _remove_overlap(self, existing_entries: List[Dict], new_entries: List[Dict]) -> List[Dict]:
        """Remove overlapping content from the beginning of new entries."""
        if not existing_entries or not new_entries:
            return new_entries
        
        # Look for similar content at the end of existing and start of new
        # Simple approach: remove first few entries of new segment if they seem duplicated
        
        # Get last few entries from existing
        last_existing = existing_entries[-3:] if len(existing_entries) >= 3 else existing_entries
        first_new = new_entries[:3] if len(new_entries) >= 3 else new_entries
        
        # Simple overlap detection: if first new entries have very similar content to last existing
        overlap_count = 0
        for new_entry in first_new:
            for existing_entry in last_existing:
                # Check for similar speakers and content
                if (new_entry['speaker'] == existing_entry['speaker'] and 
                    len(new_entry['content']) > 10 and
                    self._content_similarity(new_entry['content'], existing_entry['content']) > 0.7):
                    overlap_count += 1
                    break
        
        # If significant overlap detected, remove overlapping entries
        if overlap_count >= 2:
            logger.info(f"   🔄 Detected overlap - removing first {overlap_count} entries from segment")
            return new_entries[overlap_count:]
        
        return new_entries
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate simple content similarity between two strings."""
        # Simple word-based similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_merged_transcript(self, metadata: Dict, entries: List[Dict]) -> str:
        """Generate the final merged transcript content."""
        lines = []
        
        # Header
        lines.append("# Merged Session Transcript")
        lines.append("")
        lines.append(f"**Generated:** {metadata['generated']}")
        lines.append(f"**Source Files:** {', '.join(metadata['source_files'])}")
        lines.append(f"**Total Duration:** {metadata['total_duration']:.1f} seconds ({metadata['total_duration']/60:.1f} minutes)")
        lines.append(f"**Speakers:** {len(metadata['speakers'])} detected")
        lines.append("")
        
        # Speaker summary
        lines.append("## Speaker Summary")
        lines.append("")
        for speaker_id, speaker_info in metadata['speakers'].items():
            lines.append(f"- **{speaker_info['name']}** ({speaker_id}): {speaker_info['total_duration']:.1f}s ({speaker_info['percentage']:.1f}%)")
        lines.append("")
        
        # Editing instructions
        lines.append("## Editing Instructions")
        lines.append("")
        lines.append("**This is a merged transcript from multiple audio segments. Please review carefully:**")
        lines.append("")
        lines.append("1. **Check Segment Boundaries**: Look for any awkward transitions between segments")
        lines.append("2. **Verify Speaker Continuity**: Ensure speaker labels are consistent throughout")
        lines.append("3. **Fix Transcription Errors**: Correct any misheard words or phrases")
        lines.append("4. **Add Context**: Include important non-verbal actions in [brackets]")
        lines.append("5. **Clean Up**: Remove filler words, false starts, and off-topic conversation")
        lines.append("6. **Preserve Game Content**: Keep all in-character dialogue and game mechanics")
        lines.append("")
        lines.append("**Note:** Some automatic overlap removal was performed, but manual review is recommended.")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Main transcript
        lines.append("## Transcript")
        lines.append("")
        
        if not entries:
            lines.append("*No transcript entries found*")
            return "\\n".join(lines)
        
        # Output entries with adjusted timestamps
        for entry in entries:
            start_time = self._seconds_to_timestamp(entry['adjusted_start'])
            end_time = self._seconds_to_timestamp(entry['adjusted_end'])
            
            lines.append(f"### {start_time} - {end_time}")
            lines.append(f"**{entry['speaker']}:** {entry['content']}")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("## Next Steps")
        lines.append("")
        lines.append("After reviewing and editing this merged transcript:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Generate session notes from reviewed transcript")
        lines.append("./gm session summarize merged_transcript.md --out session_notes.md")
        lines.append("```")
        lines.append("")
        
        return "\\n".join(lines)


def merge_transcript_files(transcript_files: List[str], output_path: str) -> str:
    """
    Convenience function to merge multiple transcript files.
    
    Args:
        transcript_files: List of paths to transcript files
        output_path: Path to save merged transcript
        
    Returns:
        Path to the merged transcript file
    """
    merger = TranscriptMerger()
    return merger.merge_transcripts(transcript_files, output_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python transcript_merger.py <output_file> <transcript1> [transcript2] ...")
        sys.exit(1)
    
    output_path = sys.argv[1]
    transcript_files = sys.argv[2:]
    
    try:
        merged_path = merge_transcript_files(transcript_files, output_path)
        print(f"\\n✅ Merged transcript created: {merged_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)