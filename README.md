
# Shadowdark GM Assistant

A multi-agent AI assistant for running Shadowdark campaigns end-to-end. This tool helps GMs capture sessions, generate notes, manage knowledge bases, and maintain campaign continuity using modern AI and RAG (Retrieval-Augmented Generation) techniques.

## 🎯 Features

- **💬 Natural Language Chat**: ChatGPT-like interface for Shadowdark rules and GM advice
- **📝 Session Scribe**: Generate Shadowdark-style session notes from transcripts or audio
- **🎤 Speaker Diarization**: Identify and label different speakers in audio recordings
- **🔊 Audio Processing**: Support for .wav, .mp3, .m4a, and other common audio formats
- **📚 RAG Librarian**: Build and query a private knowledge base from PDFs and notes
- **🧠 Intelligent Knowledge Base**: Automatic content classification with fallback search
- **📋 Notion Integration**: Seamlessly sync session notes to your Notion workspace
- **⚡ CLI Tools**: Comprehensive command-line interface for all functions
- **🌐 REST API**: HTTP endpoints for integration with other tools
- **🗄️ Database Integration**: PostgreSQL with pgvector for semantic search

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

## 🎮 Usage

### 💬 Interactive Chat (Featured!)

Chat naturally with your GM Assistant - like ChatGPT for Shadowdark!

```bash
# Start interactive chat mode
./gm chat

# Ask a single question
./gm chat "What are the stats for a shambling mound?"
./gm chat "What happens when a character drops to 0 hit points?"
./gm chat "Tell me about half-orc ancestry traits"
```

**Example conversation:**
```
👤 You: What are troll stats?
🧙‍♂️ GM Assistant: I don't have specific troll stats in the knowledge base, but I can help 
                   with other monsters or rules. What else can I assist with?

👤 You: What happens at 0 hit points?
🧙‍♂️ GM Assistant: When a character drops to 0 hit points, they enter a dying state:
                   1. Death Timer: Roll 1d4 + CON modifier...
                   (Page 93)
```

### 📝 Session Management

Generate session notes from transcripts or audio recordings:

```bash
# From text transcripts
./gm session summarize transcript.txt --campaign 1 --use-rag

# From audio files (with speaker diarization)
./gm session summarize session_recording.m4a --campaign 1 --use-rag

# Save directly to Notion
NOTION_DATABASE_ID="your-database-id" ./gm session summarize transcript.txt --out notion --campaign 1

# Multiple output options
./gm session summarize transcript.txt --out session_notes.md --use-rag
./gm session summarize transcript.txt --save-to-db --campaign 1
```

### 📚 Knowledge Base Management

```bash
# Ingest documents with automatic content detection
./gm rag ingest shadowdark_rules.pdf --doctype rule
./gm rag ingest campaign_notes.md --doctype note
./gm rag ingest monsters.json --doctype monster

# Batch ingestion with auto-detection
./gm rag ingest-batch knowledge/ --auto-detect

# Query the knowledge base
./gm rag query "death timer"
./gm rag query "shambling mound" --types monster
./gm rag query "half-orc traits"
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

- **GM Chat Agent**: Natural language conversational interface with RAG integration
- **Session Scribe**: Transforms raw transcripts or audio into structured Shadowdark-style notes
- **Speaker Diarizer**: Uses pyannote.audio to identify and label speakers in audio recordings
- **RAG Librarian**: Manages document ingestion with intelligent chunk classification
- **Vector Store**: PostgreSQL + pgvector with intelligent fallback search
- **Content Classification**: Automatic detection of 12+ document types (monster, spell, rule, etc.)
- **Notion Integration**: Syncs session notes directly to Notion workspace pages
- **Audio Processing**: Supports multiple formats with automatic conversion
- **API Layer**: FastAPI with automatic documentation and validation

## ✨ What Makes This Special

### 🧠 Intelligent Knowledge Base
- **Smart Content Classification**: Automatically detects and classifies 12+ document types (monster stats, spells, rules, tables, equipment)
- **Fallback Search System**: When vector search fails, intelligent fallback terms ensure you find what you need
- **Anti-Hallucination**: System prompts prioritize official Shadowdark knowledge over general AI knowledge

### 💬 Natural Conversation
- **ChatGPT-like Experience**: Ask questions naturally and get accurate Shadowdark-specific answers
- **Context Awareness**: Maintains conversation history for follow-up questions
- **Page Citations**: Always includes source page references for rule clarifications

### 🎤 Production-Ready Audio Processing
- **Multiple Formats**: Supports .wav, .mp3, .m4a, and more
- **Speaker Identification**: Automatically identifies and labels different speakers
- **Smart Token Management**: Efficiently processes long transcripts by reducing token usage

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
- [x] RAG Librarian with intelligent chunk classification
- [x] Natural language chat interface (GM Chat Agent)
- [x] Intelligent fallback search system
- [x] CLI interface with comprehensive commands
- [x] REST API endpoints
- [x] Golden dataset and evaluation framework
- [x] Notion integration with proper workspace sync
- [x] Content-aware document ingestion (12+ types)

### Sprint 2 (Audio Processing) ✅
- [x] Speaker Diarizer agent (pyannote.audio integration)
- [x] Audio file upload and processing (.wav, .mp3, .m4a, etc.)
- [x] Speaker identification and timeline generation
- [x] Enhanced session notes with speaker labels
- [x] CLI and API support for audio processing
- [x] HuggingFace integration for ML models
- [x] Graceful degradation for missing tokens

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

**Natural Language Chat:**
- `POST /chat/` - Interactive chat with GM Assistant
- `POST /chat/query` - Single question mode

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
