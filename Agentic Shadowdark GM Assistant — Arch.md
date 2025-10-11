# Agentic Shadowdark GM Assistant — Architecture, Sprints, and Starter Specs

## 1) Vision & Scope

**Goal:** A multi‑agent assistant that helps you run Shadowdark campaigns end‑to‑end: capture/diarize sessions, generate notes, build adventures, spawn NPCs/monsters/spells/items, draw tokens/portraits, sketch dungeons, track factions/clocks/rumors, and act as an encyclopedic (private) rules knowledge base.

**Con## 15) Current Status & Next Actions

### COMPLETED ✅ (Sprints 1-2)
* ✅ **Full MVP Implementation**: Session Scribe + RAG Librarian + GM Chat
* ✅ **Storage Integration**: Notion, PostgreSQL + pgvector implemented
* ✅ **Core Features**:
  * SQLModel models with intelligent chunk classification
  * Advanced RAG with fallback search system
  * Session Scribe with audio processing and Notion sync
  * Natural language chat interface with conversation history
  * Speaker diarization via pyannote.audio
  * Comprehensive test suite with golden dataset

### Current Capabilities
- **Knowledge Base**: Full Shadowdark core rules ingested with intelligent classification
- **Chat Interface**: Natural language Q&A about Shadowdark rules with accurate citations
- **Session Processing**: Audio → transcript → structured session notes → Notion
- **CLI Tools**: `gm chat`, `gm session`, `gm rag` commands for all functionality

### Next Sprint Priorities (Sprint 3)
* **Enhanced Embedding System**: Replace hash-based embeddings with proper semantic embeddings
* **NPC/Monster/Spell Smith**: Structured generators for game entities
* **Web UI**: Basic web interface for non-CLI users
* **API Improvements**: Enhanced FastAPI endpoints for external integrations

---

## 16) Implementation Details & Lessons Learned

### Key Technical Decisions Made

**Intelligent Chunk Classification**
* Implemented pattern-based detection for 12+ document types (monster, spell, rule, table, etc.)
* Uses regex patterns to identify stat blocks, spell lists, and structured content
* Enables targeted searches by content type for improved accuracy

**Fallback Search System**
* Hash-based embeddings have semantic limitations for certain queries
* Implemented intelligent fallback terms for problematic searches (death/dying → "d4 + con", ancestry traits → "Common and Orcish languages")
* Automatically triggers when initial search doesn't find relevant content
* Critical for production accuracy with limited embedding systems

**Natural Language Chat Interface**
* `GMChatAgent` provides ChatGPT-like conversational experience
* Anti-hallucination system prompts prioritize official Shadowdark knowledge
* Conversation history with context management
* RAG integration with knowledge base citations and page references

**Audio Processing Pipeline**
* WhisperX for speech recognition with high accuracy
* PyAnnote.audio for speaker diarization when HuggingFace token available
* Graceful degradation to transcription-only when diarization unavailable
* Integrated directly into Session Scribe workflow

### Production Readiness Features
* **Error Handling**: Comprehensive error handling with graceful degradation
* **Configuration Management**: Environment-based configuration for API keys and database connections
* **Testing**: Golden dataset with expected outputs for regression testing
* **Database Migrations**: Proper Alembic migrations for schema changes
* **Integration Testing**: End-to-end tests for critical workflows

### Known Limitations & Future Improvements
* **Embedding System**: Current hash-based approach has semantic limitations; semantic embeddings recommended for Sprint 3
* **Chunk Size**: Large chunks (1000+ chars) containing multiple concepts can confuse extraction
* **Content Extraction**: Some detailed information gets truncated in AI responses despite being in source chunks ethics:**

* Use your **privately owned sources** for rules/content. Do not reproduce large verbatim copyrighted text. Summarize/quote minimally when necessary, with citations to your private library.
* All art generation should be **opt‑in** and tagged with provenance metadata.
* Support Shadowdark’s **terse, easy‑to‑run** formatting and your preferences (zone ranges, no saves, etc.).

---

## 2) High‑Level Architecture

```mermaid
flowchart TD
    A[Frontend: CLI / Notion / Web UI / Foundry export] --> B[Orchestrator (LangGraph/Custom)];
    subgraph Agents
      B --> C1[RAG Librarian];
      B --> C2[Session Scribe];
      B --> C3[Diarizer];
      B --> C4[NPC/Monster/Spell Smith];
      B --> C5[Cartographer];
      B --> C6[Portrait & Token Artist];
      B --> C7[Faction Keeper];
      B --> C8[Module Crafter];
      B --> C9[Rules Explainer];
    end
    C1 <---> D[(Vector DB: pgvector/Weaviate/Pinecone)];
    B <---> E[(Postgres: canonical campaign DB)];
    B <---> F[(Object Store: art, audio, maps)];
    B <--> G[Tools via MCP: Notion, Google Drive, Git, Foundry export, WhisperX];
    B <--> H[Queue/Workers: Redis + Celery/Arq];
    I[Observability: Traces/Evals] --> B;
```

**Core pieces:**

* **Orchestrator:** A graph of tools/agents (LangGraph or your own runner).
* **Data:** Postgres (campaign state), Vector DB (chunks), Object store (S3/Cloudflare R2/local).
* **Tools via MCP:** Turn Notion, Drive, Git, local FS, Foundry exporters, and WhisperX into tools the LLM can call safely.
* **Workers:** Long jobs (diarization, image/gen map rendering) offloaded to background workers; orchestrator keeps state.
* **Observability:** Trace every run; store prompts/IO; add offline evals.

---

## 3) Agents & Responsibilities

1. **RAG Librarian** — IMPLEMENTED ✅

   * ✅ Build & query private knowledge base from PDFs (Shadowdark core rules), house rules, session notes
   * ✅ Intelligent chunk classification with 12+ document types (monster, spell, rule, table, equipment, etc.)
   * ✅ Content-aware ingestion with pattern-based detection for stat blocks, spells, and rules
   * ✅ Fallback search system for embedding limitations (death/dying, ancestry traits)
   * ✅ Policies: retrieve → synthesize → cite with page references

2. **Session Scribe** — IMPLEMENTED ✅

   * ✅ Input: transcript (raw or diarized), chat logs, DM notes, handouts, audio files
   * ✅ Output: Shadowdark‑style session notes with scene lists, NPC ledger, treasure, clocks, rumors, XP hooks
   * ✅ Side‑effects: creates `Session`, `Document`, `Chunk` entities in Postgres
   * ✅ Audio processing integration with automatic diarization
   * ✅ Notion sync with structured database entries

3. **Diarizer** — IMPLEMENTED ✅

   * ✅ WhisperX for ASR with PyAnnote.audio for speaker diarization
   * ✅ Produces timestamped segments + speaker maps
   * ✅ Integrated into Session Scribe workflow for audio files
   * ✅ Exports clean transcript with speaker identification

4. **GM Chat Agent** — IMPLEMENTED ✅ (NEW)

   * ✅ Natural language conversational interface for Shadowdark rules
   * ✅ RAG-enhanced responses with knowledge base integration
   * ✅ Conversation history and context management
   * ✅ Anti-hallucination system prompts prioritizing official knowledge
   * ✅ Fallback search for complex queries

4. **NPC/Monster/Spell Smith**

   * Structured generators that respect Shadowdark stat blocks and your house style.
   * Outputs JSON conforming to schemas (below) and Markdown blocks for quick reading.

5. **Cartographer**

   * Dungeon map drafts from seeds (graph layout → tile/wavefunction options → export PNG + Foundry scene JSON).
   * Optionally calls image model for styled render; maintains a text‑first room index that matches the map.

6. **Portrait & Token Artist**

   * Prompts from stat lines + vibe tags; outputs 512–1024px webp/png, round‑cropped tokens; writes EXIF/user data with provenance.

7. **Faction Keeper**

   * Maintains factions, relationships, clocks, fronts, tags; suggests moves, rumors, entanglements; generates weekly “state of the world.”

8. **Module Crafter**

   * Takes seeds (theme, constraint budget, tier, biome) → produces 5‑room or multi‑zone adventures in Shadowdark terse format; outputs Notion‑ready and Foundry‑ready artifacts.

9. **Rules Explainer**

   * Answers rules Qs citing your private corpus; shows page pointers; avoids long verbatim text.

---

## 4) Data Model (selected)

**Core tables (Postgres)**

* `campaign(id, title, style_prefs, rulesets[], house_rules[])`
* `session(id, campaign_id, date, audio_uri, transcript_uri, summary_md, gm_notes_md)`
* `event(id, session_id, ts, type, payload_jsonb)`  // atomic facts (kill, loot, reaction, rumor)
* `npc(id, name, tags[], stat_jsonb, portrait_uri, token_uri)`
* `monster(id, name, stat_jsonb, token_uri, source_ref)`
* `faction(id, name, tags[], attitude_jsonb, clocks_jsonb)`
* `location(id, name, region, map_uri, notes_md)`
* `item(id, name, rarity, props_jsonb)`
* `rumor(id, text, source, truthiness, first_seen_session_id)`
* `export_job(id, type, status, output_uri, metadata_jsonb)`

**Vector DB (chunks) — IMPLEMENTED ✅**

* ✅ `chunk_type` classification with 12+ types: monster, spell, rule, table, equipment, monster_stat, spell_list, etc.
* ✅ `document_id`, `page`, `text`, `embedding` (hash-based), `chunk_type`
* ✅ Intelligent content classification using pattern matching
* ✅ PostgreSQL + pgvector implementation

---

## 5) File & Schema Contracts

**NPC JSON (Shadowdark‑style, tersified)**

```json
{
  "name": "Yrsa Smoke‑Eye",
  "tags": ["Moon Elf", "ranger", "Norwood"],
  "attitude": "wary but fair",
  "hook": "Seeks proof settlers poison the creek",
  "stat_block": {
    "HD": 3,
    "AC": 15,
    "Attacks": ["bow +4 (1d6)", "dagger +3 (1d4)"],
    "Moves": 30,
    "Morale": 9,
    "Special": ["Near‑silent in woods", "Knows old stone circles"],
    "DCs": {"track intruders": 12}
  },
  "portrait_uri": "s3://.../yrsa.png",
  "token_uri": "s3://.../yrsa_token.png"
}
```

**Monster JSON**

```json
{
  "name": "Saltmarsh Lurker",
  "tier": 2,
  "traits": ["amphibious", "ambush"],
  "stat_block": {
    "HD": 4,
    "AC": 13,
    "Attack": "+5 (1d8) grasp",
    "Morale": 8,
    "Special": ["drag prey into water"],
    "DCs": {"escape grasp (STR)": 13, "resist brine sting (CON)": 12}
  },
  "lore": "Legends say...",
  "treasure": "2d6 gp, brine‑etched ring",
  "token_uri": "..."
}
```

**CSV/Excel ingestion**

* Spells and monsters can be ingested from **CSV/XLSX** into canonical tables; parser maps headers to the JSON contracts above.

**Faction YAML**

```yaml
name: Trollbane Clan
region: Bay Ridge Mountains
attitude:
  Red Death: hostile
  Tangol Crown: wary
clocks:
  - name: Dragonrider Tribute
    segments: 6
    filled: 2
    consequence: "Kalaxtha riders demand oaths"
rumors:
  - text: "Trollbane trade in red dragon scales"
    truthiness: plausible
```

**Foundry export (concept)**

* Scenes: JSON with walls/lights/tiles; image in `/scenes/`.
* Actors: compendium of NPC/Monsters from JSON above; items separate.

---

## 6) Prompts & Style Guides (excerpts)

**Shadowdark Terse Style (assistant system hint)**

* Prioritize brevity and runnable text.
* Use **Close/Near/Far** distances. Avoid feet unless measuring map scale.
* **No saving throws.** Use **ability checks vs DC** appropriate to the threat (e.g., CON check vs poison DC) instead of saves/resistance/avoidance jargon.
* Format stat blocks compactly (HD, AC, Attack, Moves, Morale, Special). Add **DCs** inline where relevant (e.g., “Poison thorn: CON DC 12 or poisoned”).

**Session Scribe Template (output skeleton)** (output skeleton)**

```
[Date]

Session Summary — 1–2 short paragraphs.

Cast of Characters
- PCs: name — ancestry/class, one‑line descriptor
- Notable NPCs: name — role, attitude

Locations Visited — list with quick details

Scenes & Encounters — numbered; each has: What happened, stakes, loot, clocks advanced, NPC changes.

Treasure & XP Hooks — bullet list.

Rumors & Leads — bullet list.

Prep For Next — 3–5 items.
```

**Module Crafter Seed → Output**

* Inputs: theme, tier, budget, biome, unique twist, constraint list.
* Output: Title, Backdrop, 5 Rooms (Goal/Obstacle/Reward), Encounters, Reaction table, Treasure, Hooks, Front/Clocks, Map index.

---

## 7) MVP (Sprint 1–2) Scope — COMPLETED ✅

**Sprint 1 — Session Scribe + RAG Librarian (baseline) — COMPLETED ✅**

* ✅ Ingest: Implemented RAG pipeline with intelligent chunk classification for rules/notes/monsters/spells
* ✅ Build: RAG pipeline with PostgreSQL + pgvector, hash-based embeddings, content-type detection
* ✅ Agent: Session Scribe with Shadowdark-style output, Postgres persistence, and Notion sync
* ✅ Deliverables: CLI `gm session summarize input.md --out notion` and `gm rag` commands
* ✅ Natural Language Chat: Added `GMChatAgent` with conversational interface via `gm chat`
* ✅ Fallback Search: Implemented intelligent fallback terms for problematic queries (death/dying, ancestry traits)
* ✅ Acceptance tests: Golden dataset with transcript → notes validation

**Sprint 2 — Diarizer — COMPLETED ✅**

* ✅ Audio processing: WhisperX integration with speaker diarization via pyannote.audio
* ✅ Speaker identification: Timeline generation and speaker mapping
* ✅ CLI support: Auto-detection of audio files (.wav, .mp3, .m4a) in session scribe
* ✅ Error handling: Graceful degradation for missing HuggingFace tokens

---

## 8) Future Sprints (capsule)

* **S3:** NPC/Monster/Spell Smith + Foundry export
* **S4:** Faction Keeper + clocks and weekly world report
* **S5:** Module Crafter + dungeon map stubber (graph → grid) + Foundry scene JSON
* **S6:** Portrait/Token Artist (batch prompts + round cropper) with provenance tags
* **S7:** Web UI + auth; runbooks; one‑click deployments
* **S8:** Evals & Observability (prompt/version tracking, task success scoring, red‑team tests)

## 8.1) Current System Capabilities — IMPLEMENTED ✅

**RAG Knowledge Base**
* ✅ Intelligent chunk classification with 12+ document types (monster, spell, rule, table, equipment)
* ✅ Content-aware ingestion with pattern-based detection
* ✅ Fallback search system for problematic queries
* ✅ Full Shadowdark core rules indexed and searchable

**Natural Language Chat Interface**
* ✅ ChatGPT-like conversational interface via CLI (`gm chat`)
* ✅ RAG-enhanced responses with knowledge base integration
* ✅ Conversation history and context management
* ✅ Accurate rule citations with page references
* ✅ Anti-hallucination system prompts prioritizing official knowledge

**Session Processing**
* ✅ Audio and text transcript support
* ✅ Speaker diarization with pyannote.audio
* ✅ Shadowdark-style session note generation
* ✅ Notion integration with database sync
* ✅ PostgreSQL persistence with structured data models

---

## 9) Tech Choices (recommendations)

* **Language:** Python 3.11+
* **Agent graph:** LangGraph (deterministic control + tools); light wrappers for **MCP (Model Context Protocol)** tool calls (Notion, Drive, Git, Foundry exporters).
* **Embeddings/LLM:** OpenAI or local (nomic‑embed, llama‑3.1/3.2, Qwen2.5). Keep a provider interface.
* **Vector DB:** **Postgres + pgvector** (default starting point).
* **DB:** Postgres 15+; SQLModel/SQLAlchemy; Alembic for migrations.
* **Queue:** Redis + Arq/Celery/RQ.
* **Diarization:** WhisperX (ASR + alignment); optional PyAnnote for speakers.
* **Maps/Art:** Image gen API (e.g., SDXL/Flux/22), local ControlNet for layout adherence; Pillow for token crops.
* **Deploy:** Docker Compose local → Fly.io/Render/Modal/AWS.
* **Observability:** OpenTelemetry traces, Arize/Weights&Biases/evals JSON.

---

## 10) Directory Structure — IMPLEMENTED ✅

```
shadowdark-gm/
  ✅ apps/
    ✅ api/               # FastAPI service
      ✅ main.py          # API endpoints
  ✅ core/
    ✅ agents/
      ✅ session_scribe.py  # Session note generation
      ✅ rag_librarian.py   # Knowledge base RAG
      ✅ gm_chat.py         # Conversational interface
      ✅ diarizer.py        # Audio processing & speaker ID
    ✅ data/
      ✅ models.py          # SQLModel database models
      ✅ schemas.py         # Pydantic IO schemas
      ✅ vector_store.py    # Vector search implementation
    ✅ integrations/
      ✅ notion_sync.py     # Notion database integration
    ✅ prompts/
      ✅ session_scribe.md  # Session note templates
      ✅ styles.md          # Shadowdark style guide
  ✅ infra/
    ✅ docker-compose.yml   # PostgreSQL + pgvector
  ✅ migrations/
    ✅ 001_add_chunk_type.sql  # Database migrations
  ✅ tests/
    ✅ golden/              # Golden dataset
      ✅ expected_*.md      # Expected outputs
      ✅ transcript_*.md    # Test transcripts
    ✅ unit/
      ✅ test_session_scribe.py
    ✅ integration/
      ✅ test_rag_enhanced.py
      ✅ test_notion.py
  ✅ knowledge/            # Shadowdark rules corpus
  ✅ scripts/             # Utility scripts
  ✅ gm                   # CLI entry point
  ✅ README.md
```

---

## 11) Example: Session Scribe (pseudo‑LangGraph)

```python
# orchestrator step
nodes = {
  "ingest": load_transcript,
  "retrieve": rag_retrieve,
  "compose": llm_compose_notes,
  "persist": write_session_and_events,
  "sync": push_to_notion,
}
# edges: ingest -> retrieve -> compose -> persist -> sync
```

**Checklist for quality**

* Matches template; includes PCs, NPCs, loot, clocks, rumors, next prep.
* Cross‑references names consistently; hyperlinks to database entities.
* Citations: rule clarifications cite your corpus (book → page if available).

---

## 12) Evaluation & Guardrails

* **Golden set** for transcripts → notes; require ≥0.7 semantic similarity + pass rubric:

  * Completeness, Terseness, Runnable stat blocks, Correct distances, No saves.
* **Generation caps:** Never exceed N tokens per answer unless “export mode.”
* **Copyright guard:** If response would exceed quote threshold, redirect to a short summary with citation and offer page reference.
* **Safety/Style:** Block disallowed content; keep art prompts SFW unless explicitly flagged.

---

## 13) Setup Steps — COMPLETED ✅

1. ✅ Created repo `shadowdark-gm` with full implementation
2. ✅ Provisioned Postgres (with pgvector) via `docker-compose up -d`
3. ✅ Environment configured with OpenAI keys and database DSNs
4. ✅ Implemented `data/models.py` and `schemas.py` with chunk classification
5. ✅ Implemented `rag_librarian.py` with intelligent chunk classification and fallback search
6. ✅ Implemented `session_scribe.py` with Shadowdark-style output and audio processing
7. ✅ Built CLI interface with `gm session`, `gm rag`, and `gm chat` commands
8. ✅ Created golden dataset with transcript → notes validation tests
9. ✅ Added natural language chat interface with conversation management
10. ✅ Integrated speaker diarization with pyannote.audio
11. ✅ Implemented Notion sync with database integration

---

## 14) Your Preferences (encoded)

* **Distances:** zone (Close/Near/Far) only.
* **Ability checks vs DC** in place of saves/resistances.
* **Foundry** exports preferred over Roll20; Notion as campaign log.
* **World seeds:** Western Reaches, Isles of Andrik, etc. **Exclude Allura** (that is a separate, player-facing campaign not part of this project).

---

## 15) Next Actions

* Confirm your storage targets (Notion, Postgres, Vector DB choice).
* I will generate a **starter repo ZIP** with:

  * SQLModel models, Alembic migration
  * Basic RAG ingest/query
  * Session Scribe agent + HTTP & CLI
  * Tests and a tiny golden dataset
* After MVP compiles, we’ll add Diarizer (Sprint 2) and start the Faction Keeper (Sprint 3).