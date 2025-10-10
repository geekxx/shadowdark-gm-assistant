# Changelog

All notable changes to the Shadowdark GM Assistant project will be documented in this file.

## [Unreleased]

### Planned
- Golden dataset creation and evaluation framework
- Basic Notion integration
- Audio transcription with Diarizer agent

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