
# Shadowdark GM Assistant

A multi-agent AI assistant for running Shadowdark RPG campaigns end-to-end. This tool helps GMs capture sessions, generate notes, manage knowledge bases, and maintain campaign continuity using modern AI and RAG (Retrieval-Augmented Generation) techniques.

## 🎯 Features

- **Session Scribe**: Generate Shadowdark-style session notes from transcripts
- **RAG Librarian**: Build and query a private knowledge base from PDFs and notes
- **CLI Tools**: Command-line interface for all major functions
- **REST API**: HTTP endpoints for integration with other tools
- **Database Integration**: PostgreSQL with vector similarity search

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (via Docker)
- OpenAI API key (optional, has mock mode for testing)

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
   # Edit .env with your OpenAI API key (optional)
   ```

4. **Make CLI executable:**
   ```bash
   chmod +x gm
   ```

## 📖 Usage

### CLI Commands

**Generate session notes from transcript:**
```bash
./gm session summarize my_transcript.md --use-rag --out session_notes.md
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
# Summarize a session
curl -X POST "http://localhost:8000/sessions/summarize" \
  -H "Content-Type: application/json" \
  -d '{"text": "GM: You enter the dungeon...", "use_rag": true}'

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
│   ├── agents/           # AI agents (Session Scribe, RAG Librarian)
│   ├── data/             # Database models and vector store
│   ├── prompts/          # LLM prompts and style guides
│   └── tools/            # Utility functions and integrations
├── infra/
│   └── docker-compose.yml  # Database and services
└── tests/
    ├── golden/           # Golden dataset for evaluation
    ├── integration/      # Integration tests
    ├── unit/            # Unit tests
    └── test_golden_dataset.py  # Evaluation framework
```

### Core Components

- **Session Scribe**: Transforms raw transcripts into structured Shadowdark-style notes
- **RAG Librarian**: Manages document ingestion, chunking, and semantic search
- **Vector Store**: PostgreSQL + pgvector for embedding similarity search
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

## 🔮 Roadmap

### Sprint 1 (MVP) ✅
- [x] Session Scribe with Shadowdark styling
- [x] RAG Librarian with smart chunking
- [x] CLI interface
- [x] REST API endpoints
- [ ] Golden dataset and evaluation framework
- [ ] Basic Notion integration

### Sprint 2 (Audio)
- [ ] Diarizer agent (WhisperX integration)
- [ ] Audio file upload and processing
- [ ] Speaker identification and mapping

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
- **OpenAI** for GPT models

## Endpoints
- `POST /rag/ingest` {text, title?, source_id?, doctype?} → {document_id}
- `POST /rag/query` {query, k?} → top-k chunks

## Dev
1. `cp .env.example .env` and edit if needed.
2. `docker compose -f infra/docker-compose.yml up -d`
3. `pip install -r requirements.txt`
4. `uvicorn apps.api.main:app --reload`
