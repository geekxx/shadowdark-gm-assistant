
# Shadowdark GM Assistant

A multi-agent AI assistant for running Shadowdark RPG campaigns end-to-end. This tool helps GMs capture sessions, generate notes, manage knowledge bases, and maintain campaign continuity using modern AI and RAG (Retrieval-Augmented Generation) techniques.

## 🎯 Features

- **Session Scribe**: Generate Shadowdark-style session notes from transcripts or audio
- **Speaker Diarization**: Identify and label different speakers in audio recordings
- **Audio Processing**: Support for .wav, .mp3, .m4a, and other common audio formats
- **RAG Librarian**: Build and query a private knowledge base from PDFs and notes
- **Notion Integration**: Seamlessly sync session notes to your Notion workspace
- **CLI Tools**: Command-line interface for all major functions
- **REST API**: HTTP endpoints for integration with other tools
- **Database Integration**: PostgreSQL with vector similarity search

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (via Docker)
- OpenAI API key (for AI-powered session notes)
- HuggingFace token (for speaker diarization, optional)
- Notion integration token (optional, for workspace sync)

### Installation

1. **Clone and setup environment:**
   ```bash
   git clone <your-repo-url>
   cd shadowdark-gm
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start the database:**
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys:
   # - OPENAI_API_KEY (required for AI features)
   # - HUGGINGFACE_TOKEN (required for audio processing)
   # - NOTION_TOKEN & NOTION_DATABASE_ID (optional, for Notion sync)
   # For Notion integration setup, see NOTION_SETUP.md
   ```

4. **Make CLI executable:**
   ```bash
   chmod +x gm
   ```

### Audio Processing Setup

For audio processing features, you need a HuggingFace token with access to gated repositories:

1. **Create HuggingFace account**: https://huggingface.co/join
2. **Accept model license**: Visit https://huggingface.co/pyannote/speaker-diarization-community-1 and accept terms
3. **Create token**: Go to https://huggingface.co/settings/tokens
   - Create a new fine-grained token
   - Enable "Read access to public gated repositories"
4. **Add to .env file**:
   ```bash
   HUGGINGFACE_TOKEN=hf_your_token_here
   ```

## 📖 Usage

### CLI Commands

**Generate session notes:**
```bash
# From text transcripts
./gm session summarize transcript.txt --out session_notes.md
./gm session summarize notes.md --campaign 1 --use-rag

# From audio files (with speaker diarization)
./gm session summarize session_recording.m4a --campaign 1 --use-rag
./gm session summarize podcast.wav --out notion --play-group "Online"

# Sync directly to Notion
./gm session summarize transcript.txt --out notion --play-group "Post 161"
```

**Build knowledge base:**
```bash
./gm rag ingest shadowdark_rules.pdf --doctype rule
./gm rag ingest campaign_notes.md --doctype note
```

**Query knowledge base:**
```bash
./gm rag query "How do death saves work in Shadowdark?"
```

### API Server

**Start the server:**
```bash
uvicorn apps.api.main:app --reload
```

**Visit interactive docs:**
- http://localhost:8000/docs

**Example API calls:**
```bash
# Summarize a text session
curl -X POST "http://localhost:8000/sessions/summarize" \
  -H "Content-Type: application/json" \
  -d '{"text": "GM: You enter the dungeon...", "use_rag": true}'

# Process audio file with speaker diarization
curl -X POST "http://localhost:8000/sessions/summarize-audio" \
  -F "audio_file=@session_recording.m4a" \
  -F "campaign_id=1" \
  -F "use_rag=true"

# Speaker diarization only
curl -X POST "http://localhost:8000/audio/diarize" \
  -F "audio_file=@recording.wav"

# Query knowledge base
curl -X POST "http://localhost:8000/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "combat rules", "k": 5}'
```

## 🏗️ Architecture

```
shadowdark-gm/
├── apps/
│   ├── api/              # FastAPI REST endpoints
│   └── worker/           # Background job processing (future)
├── core/
│   ├── agents/           # AI agents (Session Scribe, RAG Librarian, Diarizer)
│   ├── data/             # Database models and vector store
│   ├── integrations/     # External service integrations (Notion API)
│   └── prompts/          # LLM prompts and style guides
├── infra/
│   └── docker-compose.yml  # Database and services
└── tests/
    ├── golden/           # Golden dataset for evaluation
    ├── integration/      # Integration tests
    ├── unit/            # Unit tests
    └── test_golden_dataset.py  # Evaluation framework
```

### Core Components

- **Session Scribe**: Transforms raw transcripts or audio into structured Shadowdark-style notes
- **Speaker Diarizer**: Uses pyannote.audio to identify and label speakers in audio recordings
- **RAG Librarian**: Manages document ingestion, chunking, and semantic search
- **Vector Store**: PostgreSQL + pgvector for embedding similarity search
- **Notion Integration**: Syncs session notes directly to Notion workspace pages
- **Audio Processing**: Supports multiple formats with automatic conversion
- **API Layer**: FastAPI with automatic documentation and validation

## 🎲 Shadowdark Style Guide

This tool follows Shadowdark RPG conventions:

- **Distances**: Uses Close/Near/Far zones instead of feet/meters
- **Ability Checks**: "STR check vs DC 15" instead of saving throws
- **Stat Blocks**: Compact format (HD, AC, Attack, Moves, Morale, Special)
- **Tone**: Terse and runnable, prioritizing actionable information

## 🔧 Development

### Running Tests

```bash
# Run unit tests
python tests/unit/test_session_scribe.py

# Run integration tests  
python tests/integration/test_rag_enhanced.py
python tests/integration/test_api.py

# Run golden dataset evaluation
python tests/test_golden_dataset.py
```

### Adding New Agents

1. Create new agent in `core/agents/`
2. Add database models if needed in `core/data/models.py`
3. Add CLI commands in `gm` script
4. Add API endpoints in `apps/api/main.py`

### Database Migrations

```bash
# Future: Alembic migrations will go here
```

## 📚 Learning Resources

This project demonstrates:

- **RAG Pipeline Architecture**: Document chunking, embedding, retrieval
- **Multi-Agent Systems**: Specialized AI agents for different tasks  
- **FastAPI Development**: REST APIs with automatic documentation
- **CLI Design**: User-friendly command-line interfaces
- **Vector Databases**: Semantic search with PostgreSQL + pgvector
- **LLM Integration**: OpenAI API with fallback strategies
- **External API Integration**: Notion API for seamless workflow integration

## 🔮 Roadmap

### Sprint 1 (MVP) ✅
- [x] Session Scribe with Shadowdark styling
- [x] RAG Librarian with smart chunking
- [x] CLI interface
- [x] REST API endpoints
- [x] Golden dataset and evaluation framework
- [x] Notion integration with proper workspace sync

### Sprint 2 (Audio Processing) ✅
- [x] Speaker Diarizer agent (pyannote.audio integration)
- [x] Audio file upload and processing (.wav, .mp3, .m4a, etc.)
- [x] Speaker identification and timeline generation
- [x] Enhanced session notes with speaker labels
- [x] CLI and API support for audio processing
- [x] HuggingFace integration for ML models

### Sprint 3 (Content Generation)
- [ ] NPC/Monster Smith
- [ ] Spell and item generators
- [ ] Foundry VTT export

### Future Sprints
- [ ] Faction Keeper (relationship tracking)
- [ ] Module Crafter (adventure generation)
- [ ] Portrait & Token Artist
- [ ] Web UI and authentication

## 🤝 Contributing

This is a learning project showcasing modern AI/ML techniques for tabletop RPGs. Feel free to:

- Submit issues and feature requests
- Fork and experiment with new agents
- Share your own Shadowdark campaign data (with proper anonymization)

## 📄 License

[Your chosen license here]

## 🎲 Acknowledgments

- **Shadowdark RPG** by The Arcane Library
- **FastAPI** for the excellent web framework
- **pgvector** for PostgreSQL vector extensions
- **OpenAI** for GPT models and embeddings
- **pyannote.audio** for speaker diarization
- **HuggingFace** for ML model hosting
- **Notion API** for workspace integration

## API Endpoints

**Session Processing:**
- `POST /sessions/summarize` - Process text transcripts into session notes
- `POST /sessions/summarize-audio` - Process audio files with speaker diarization

**Audio Processing:**
- `POST /audio/diarize` - Perform speaker diarization on audio files

**Knowledge Base (RAG):**
- `POST /rag/ingest` - Add documents to the knowledge base
- `POST /rag/query` - Query the knowledge base for relevant information

**Health Check:**
- `GET /health` - System health status

## Dev
1. `cp .env.example .env` and edit if needed.
2. `docker compose -f infra/docker-compose.yml up -d`
3. `pip install -r requirements.txt`
4. `uvicorn apps.api.main:app --reload`
