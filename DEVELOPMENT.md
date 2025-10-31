# Development Guide

## Getting Started

1. **Clone and setup:**
   ```bash
   git clone <repo-url>
   cd shadowdark-gm
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start services:**
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```

## Development Workflow

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/new-agent
   ```

2. Make your changes and test:
   ```bash
   # Run unit tests
   python tests/unit/test_session_scribe.py
   
   # Run integration tests
   python tests/integration/test_rag_enhanced.py
   python tests/integration/test_api.py
   
   # Run golden dataset evaluation
   python tests/test_golden_dataset.py
   
   # Test CLI
   ./gm session summarize sample_transcript.md
   ```

3. Commit and push:
   ```bash
   git add .
   git commit -m "Add new feature: description"
   git push origin feature/new-agent
   ```

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings for public functions
- Keep functions focused and testable

### Testing

- Add tests for new agents in `test_*.py` files
- Use mock LLM mode for CI/automated testing
- Include golden datasets for evaluation

### Database Changes

- Update `core/data/models.py` for schema changes
- Future: Add Alembic migrations
- Test with fresh database: `docker-compose down -v && docker-compose up -d`

## Architecture Patterns

### Adding a New Agent

1. Create `core/agents/new_agent.py`:
   ```python
   def process_input(text: str, **kwargs) -> str:
       """Process input and return result"""
       # Your agent logic here
       pass
   ```

2. Add CLI commands in `gm` script
3. Add API endpoints in `apps/api/main.py`
4. Add tests in `test_new_agent.py`

### Multi-Stage Processing Agents

The project includes several agents that work together for complex workflows:

#### AudioSplitter Agent (`core/agents/audio_splitter.py`)
- **Purpose**: Split large audio files (>25MB) into segments for API compatibility
- **Key Methods**: `should_split()`, `calculate_segment_duration()`, `split_audio()`
- **Dependencies**: ffmpeg for audio processing
- **Usage**: `./gm audio split large_file.m4a --output-dir segments/`

#### TranscriptGenerator Agent (`core/agents/transcript_generator.py`)  
- **Purpose**: Generate diarized transcripts optimized for manual review
- **Key Methods**: `generate_transcript()`, `_create_formatted_transcript()`
- **Dependencies**: SpeakerDiarizer integration, markdown formatting
- **Usage**: `./gm audio transcribe segment.m4a`

#### TranscriptMerger Agent (`core/agents/transcript_merger.py`)
- **Purpose**: Merge multiple transcript segments with overlap handling
- **Key Methods**: `merge_transcripts()`, `_remove_overlap()`, `_merge_parsed_transcripts()`  
- **Dependencies**: Regex parsing for transcript structure, timestamp manipulation
- **Usage**: `./gm transcript merge final.md segment1.md segment2.md`

These agents follow the pattern of:
1. **Input validation** and file existence checks
2. **Processing logic** specific to the agent's purpose  
3. **Error handling** with user-friendly messages
4. **Progress reporting** for long-running operations
5. **Output formatting** appropriate for the next step in workflow

### Adding Database Models

1. Add to `core/data/models.py`:
   ```python
   class NewModel(SQLModel, table=True):
       id: Optional[int] = Field(default=None, primary_key=True)
       # ... other fields
   ```

2. Update vector store if needed
3. Add to API schemas if needed

## Debugging

### Common Issues

**Database connection errors:**
```bash
# Check if containers are running
docker-compose -f infra/docker-compose.yml ps

# Recreate database
docker-compose -f infra/docker-compose.yml down -v
docker-compose -f infra/docker-compose.yml up -d
```

**Import errors:**
```bash
# Check Python path
export PYTHONPATH=/path/to/shadowdark-gm:$PYTHONPATH
```

**Vector search errors:**
```bash
# Check pgvector extension
docker exec -it infra-db-1 psql -U postgres -d shadowdark -c "\dx"
```

### Useful Commands

```bash
# View database contents
docker exec -it infra-db-1 psql -U postgres -d shadowdark

# Check API docs
# Visit http://localhost:8000/docs when server is running

# Reset everything
docker-compose -f infra/docker-compose.yml down -v
rm -rf core/**/__pycache__
```