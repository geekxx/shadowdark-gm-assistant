# Agentic Shadowdark GM Assistant — Architecture, Sprints, and Starter Specs

## 1) Vision & Scope

**Goal:** A multi‑agent assistant that helps you run Shadowdark campaigns end‑to‑end: capture/diarize sessions, generate notes, build adventures, spawn NPCs/monsters/spells/items, draw tokens/portraits, sketch dungeons, track factions/clocks/rumors, and act as an encyclopedic (private) rules knowledge base.

**Constraints & ethics:**

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

1. **RAG Librarian**

   * Build & query the private knowledge base from PDFs, SRDs, house rules, past session notes, faction sheets, compendia.
   * Policies: retrieve → synthesize → cite. De‑duplicate and avoid long quotes.

2. **Session Scribe**

   * Input: transcript (raw or diarized), chat logs, DM notes, handouts.
   * Output: Shadowdark‑style session notes, scene lists, NPC ledger, treasure, clocks, rumors, XP hooks, follow‑ups.
   * Side‑effects: creates `Session`, `Encounter`, `NPCRef`, `Treasure` entities in Postgres.

3. **Diarizer**

   * WhisperX/faster‑whisper for ASR; optional PyAnnote for speaker diarization.
   * Produces timestamped segments + speaker maps; exports Word/Markdown + JSON.

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

**Vector DB (chunks)**

* `source_id`, `doctype` (rule, note, transcript, compendium), `campaign_id?`, `embedding`, `text`, `meta{page, section, tags}`

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

## 7) MVP (Sprint 1–2) Scope

**Sprint 1 — Session Scribe + RAG Librarian (baseline)**

* Ingest: your past notes (Markdown/Notion export) + sample transcripts (or text logs).
* Build: RAG pipeline (split rules/notes, embed, store in vector DB).
* Agent: Session Scribe that outputs your preferred template and writes to Postgres, with a Notion sync.
* Deliverables: CLI `gm session summarize input.md --out notion` and an HTTP endpoint `/sessions/:id/notes`.
* Acceptance tests: 5 golden transcripts → expected notes difflib score + human review checklist.

**Sprint 2 — Diarizer**

* Add audio upload; run WhisperX; simple speaker merge UX; export clean transcript.
* Deliverables: `/audio/:id/transcribe` job + webhook + Notion linkback.

---

## 8) Future Sprints (capsule)

* **S3:** NPC/Monster/Spell Smith + Foundry export.
* **S4:** Faction Keeper + clocks and weekly world report.
* **S5:** Module Crafter + dungeon map stubber (graph → grid) + Foundry scene JSON.
* **S6:** Portrait/Token Artist (batch prompts + round cropper) with provenance tags.
* **S7:** Web UI + auth; runbooks; one‑click deployments.
* **S8:** Evals & Observability (prompt/version tracking, task success scoring, red‑team tests).

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

## 10) Minimal Directory Scaffold

```
shadowdark-gm/
  apps/
    api/               # FastAPI service
    worker/            # long jobs (ASR, image)
  core/
    agents/
      orchestrator.py
      session_scribe.py
      rag_librarian.py
      npc_smith.py
      ...
    tools/
      mcp_notion.py
      mcp_gdrive.py
      foundry_export.py
      whisperx.py
    data/
      models.py  # SQLModel
      schemas.py # pydantic IO
      vector_store.py
    prompts/
      styles.md
      session_scribe.md
      npc_smith.md
  infra/
    docker-compose.yml
    alembic/
  tests/
    golden/
      transcripts/
      expected_notes/
    test_session_scribe.py
  README.md
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

## 13) Setup Steps (Day 1)

1. Create repo `shadowdark-gm` and add the scaffold above.
2. Provision Postgres (with pgvector), Redis. `docker-compose up -d`.
3. Add `.env` with LLM keys and DSNs.
4. Implement `data/models.py` and `schemas.py` based on section 4.
5. Implement `rag_librarian.py` with simple ingest (Markdown/PDF → chunks) and query.
6. Implement `session_scribe.py` using the style and template in section 6.
7. Build `/sessions/summarize` endpoint + CLI wrapper.
8. Seed a tiny golden set and run the tests.

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
