# Changelog

All notable changes to the Shadowdark GM Assistant project will be documented in this file.

## [Unreleased]

### Planned
- NPC/Monster Smith for content generation
- Spell and item generators
- Foundry VTT export functionality

## [0.4.0] - 2025-10-15

### 🎯 Multi-Stage Audio Processing Pipeline

#### NEW Quality-Controlled Workflow
- **Audio Splitter Agent**: Automatically segments large audio files (>25MB) with intelligent overlap handling
- **Transcript Generator Agent**: Creates diarized transcripts optimized for manual review and editing
- **Transcript Merger Agent**: Seamlessly combines multiple segment transcripts with speaker continuity
- **Manual Review Stage**: Edit transcripts for accuracy before generating session notes
- **Quality Control**: Manual verification of speaker labels and content before final processing

#### Enhanced CLI Commands
- `./gm audio split <file> --output-dir <dir>` - Split large audio files into segments
- `./gm audio transcribe <file>` - Generate reviewable diarized transcripts  
- `./gm transcript merge <output> <transcripts...>` - Merge multiple transcript segments
- Enhanced session summarize to work with reviewed transcripts

#### Large File Support
- **No Size Limits**: Handle any audio file size by automatic segmentation
- **Whisper API Compatibility**: Keeps segments under 25MB limit automatically
- **Overlap Handling**: 30-second overlap between segments prevents speech cutoff
- **Parallel Processing**: Process multiple segments simultaneously for efficiency

#### Workflow Benefits
- **Accuracy Improvement**: Manual transcript review catches AI transcription errors
- **Speaker Verification**: Fix speaker labels before session note generation
- **Context Addition**: Add [dice roll], [laughter], [pause] annotations for better session notes
- **Collaborative Editing**: Multiple people can review transcripts before processing
- **Version Control**: Track transcript changes and improvements

### Added
- AudioSplitter class with intelligent file size detection and segmentation
- TranscriptGenerator class with structured markdown output and editing guidelines
- TranscriptMerger class with overlap detection and speaker mapping consistency
- Complete CLI integration for new multi-stage workflow
- Comprehensive documentation and usage examples

### Changed
- CLI architecture enhanced with new command groups (audio, transcript)
- Database connection handling made more robust with lazy initialization
- Error handling improved for missing files and processing failures

### Fixed
- Database connection timeout issues in CLI
- Path handling bugs in audio processing agents
- String vs Path object compatibility in file operations

### Performance
- **Predictable Processing**: Know exactly how long each step will take
- **Pausable Workflow**: Stop and resume processing at any stage
- **Flexible Quality**: Choose between fast processing or thorough review

## [0.3.0] - 2025-10-14

### 🚀 Major Performance & AI Upgrades

#### GPT-5 Integration
- **Upgraded to GPT-5**: Massive 500k token context window (vs previous 128k limit)
- **Enhanced Session Processing**: Can now handle 2-4 hour gaming sessions without chunking
- **Improved Reasoning**: Better session summaries and rule analysis with GPT-5's enhanced capabilities
- **Smart Token Management**: Conservative 400k token limits with intelligent chunking fallback
- **API Compatibility**: Fixed parameter compatibility (max_completion_tokens, removed temperature)

#### Apple Silicon Optimization  
- **MPS Acceleration**: Added Metal Performance Shaders support for 3-5x faster audio processing
- **Intelligent Device Detection**: Automatically uses best available compute (MPS > CUDA > CPU)
- **Progress Reporting**: Duration-aware time estimates for long audio processing
- **Memory Optimization**: Enhanced memory management for Apple Silicon architecture

#### Fast Processing Mode
- **Fast Mode Flag**: Added `--fast` option to skip speaker diarization
- **80-90% Speed Improvement**: Process audio in minutes instead of tens of minutes
- **Flexible Workflow**: Choose between full diarization or fast transcription-only mode
- **Smart Defaults**: Maintains high-quality transcription while dramatically reducing processing time

#### Audio Processing Enhancements
- **Robust Format Support**: Enhanced .m4a, .mp3, .wav processing with automatic conversion
- **Large File Handling**: Graceful handling of 25MB+ audio files with clear guidance
- **Error Recovery**: Improved fallback strategies for audio format compatibility
- **Better Logging**: Enhanced progress reporting and error diagnostics

#### Performance Improvements
- **Token Limit Resolution**: Fixed "Request too large" errors that blocked large session processing
- **Chunking System**: Intelligent transcript splitting for extremely large files
- **Merge Logic**: Sophisticated chunk summary merging for coherent session notes
- **Error Handling**: Comprehensive fallback strategies and user guidance

### Added
- `--fast` flag for session summarize command
- Apple Silicon MPS acceleration detection and configuration
- GPT-5 model integration with proper parameter handling
- Enhanced progress reporting for long audio files
- Intelligent audio format conversion with ffmpeg
- Duration-based processing time estimates

### Changed
- **BREAKING**: Upgraded from GPT-4 to GPT-5 (requires GPT-5 API access)
- Enhanced token limits: 2k → 10k (chat), 3k-6k → 10k-25k (session notes)
- Improved audio processing pipeline with better error recovery
- Updated CLI help text to reflect performance improvements

### Fixed
- Token limit exceeded errors for large gaming sessions
- GPT-5 API parameter compatibility issues
- Audio format processing failures with automatic conversion fallback
- Memory efficiency issues with long audio files
- Progress reporting accuracy for duration estimation

### Performance Benchmarks (Apple Silicon)
- **30 min session**: ~2-3 mins (full) | ~30 secs (fast)
- **2 hour session**: ~10-15 mins (full) | ~2-3 mins (fast)  
- **4 hour session**: ~20-30 mins (full) | ~5-8 mins (fast)

## [0.2.0] - 2025-10-12

### Added
- **Speaker Diarization**: Complete pyannote.audio integration for speaker identification
- **Audio Processing Pipeline**: End-to-end audio → transcript → session notes workflow
- **Natural Language Chat**: ChatGPT-like interface for Shadowdark rules and GM advice
- **Enhanced RAG System**: Intelligent fallback search and improved content classification
- **Notion Integration**: Complete workspace sync with proper page creation
- **Golden Dataset**: Evaluation framework with test transcripts and expected outputs

#### Chat Interface
- Interactive conversation mode with context awareness
- Single question mode for quick queries
- RAG-enhanced responses with official Shadowdark knowledge
- Page citations and source attribution
- Conversation history management

#### Audio Features
- Multi-format support (.wav, .mp3, .m4a, etc.)
- Speaker identification and timeline generation  
- Enhanced session notes with speaker labels
- HuggingFace integration for ML models
- Graceful degradation for missing tokens

#### Knowledge Base Improvements
- Smart content classification (12+ document types)
- Fallback search strategies for better accuracy
- Anti-hallucination prompts prioritizing official content
- Enhanced chunk processing with metadata

### Enhanced
- CLI interface with comprehensive audio and chat commands
- API endpoints for audio processing and chat functionality
- Error handling and user guidance for setup requirements
- Documentation with complete examples and troubleshooting

## [0.1.0] - 2025-10-10

### Added
- **Session Scribe Agent**: Generate Shadowdark-style session notes from transcripts
  - LLM integration with OpenAI GPT-4
  - Mock mode for testing without API keys
  - Shadowdark RPG style guide compliance
  - RAG context integration for enhanced notes
  
- **RAG Librarian Agent**: Knowledge base management
  - Smart text chunking with token counting
  - PDF and Markdown file ingestion
  - PostgreSQL + pgvector semantic search
  - Document type inference and metadata extraction
  
- **CLI Interface**: Command-line tools for all major functions
  - `gm session summarize` with multiple output formats
  - `gm rag ingest` for knowledge base building
  - `gm rag query` for semantic search
  
- **REST API**: HTTP endpoints for web integration
  - `/sessions/summarize` with RAG and database options
  - `/sessions/{id}/notes` for retrieving formatted notes
  - `/sessions` for listing sessions with filtering
  - `/rag/ingest` and `/rag/query` for knowledge base operations
  
- **Database Infrastructure**:
  - SQLModel models for campaigns, sessions, NPCs, monsters
  - Vector storage with pgvector extension
  - Docker Compose setup for development
  
- **Documentation**:
  - Comprehensive README with quick start guide
  - Development guide with contribution guidelines
  - Architecture documentation and roadmap

### Technical Details
- Python 3.11+ with FastAPI framework
- PostgreSQL with pgvector for embeddings
- OpenAI GPT-4 for text generation
- Docker containerization for easy deployment
- Git source control with proper .gitignore

## [0.0.1] - 2025-10-09

### Added
- Initial project structure
- Basic database models
- Placeholder agent stubs