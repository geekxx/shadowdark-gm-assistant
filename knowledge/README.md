# Shadowdark GM Assistant Knowledge Base

This directory contains curated knowledge sources for the Shadowdark GM Assistant's RAG (Retrieval-Augmented Generation) system. These documents provide context and information that AI agents can reference when generating session notes, answering questions, and providing GM assistance.

## 📚 Directory Structure

### `/rules/` - Core Game Rules
- **Purpose**: Official Shadowdark RPG rules and mechanics
- **Content Types**: Core rulebook, player guide, GM guide
- **Document Types**: `rule`, `mechanic`
- **Examples**:
  - `shadowdark-core-rules.pdf` - Main rulebook
  - `combat-rules.md` - Combat mechanics reference
  - `spell-casting.md` - Magic system rules

### `/supplements/` - Official Supplements
- **Purpose**: Official expansions and additional content
- **Content Types**: New classes, spells, monsters, adventures
- **Document Types**: `supplement`, `expansion`
- **Examples**:
  - `cursed-scroll-1.pdf` - Official supplement
  - `new-classes.md` - Additional character classes
  - `advanced-magic.md` - Extended spell rules

### `/settings/` - Campaign Settings
- **Purpose**: World information, locations, NPCs, factions
- **Content Types**: Campaign guides, setting descriptions, lore
- **Document Types**: `setting`, `lore`, `gazetteer`
- **Examples**:
  - `lost-citadel.md` - Default Shadowdark setting
  - `custom-world.md` - Your campaign world
  - `notable-npcs.md` - Important characters

### `/monsters/` - Creature Information
- **Purpose**: Monster stats, behaviors, ecology
- **Content Types**: Stat blocks, bestiaries, creature lore
- **Document Types**: `monster`, `bestiary`, `compendium`
- **Examples**:
  - `shadowdark-monsters.md` - Core monster manual
  - `undead-creatures.md` - Specialized bestiary
  - `boss-monsters.md` - Major antagonists

### `/spells/` - Magic Reference
- **Purpose**: Spell descriptions, magic items, arcane lore
- **Content Types**: Spell lists, magic item catalogs, ritual guides
- **Document Types**: `spell`, `magic`, `item`
- **Examples**:
  - `wizard-spells.md` - Complete spell list
  - `magic-items.md` - Magical equipment
  - `rituals.md` - Special magical procedures

### `/equipment/` - Gear and Items
- **Purpose**: Weapons, armor, tools, treasure
- **Content Types**: Equipment lists, gear descriptions, pricing
- **Document Types**: `equipment`, `item`, `treasure`
- **Examples**:
  - `weapons-armor.md` - Combat equipment
  - `adventuring-gear.md` - Tools and supplies
  - `treasure-tables.md` - Loot generation

### `/tables/` - Random Generation
- **Purpose**: Random tables for generation and inspiration
- **Content Types**: Random encounters, treasure, names, events
- **Document Types**: `table`, `generator`, `random`
- **Examples**:
  - `random-encounters.md` - Encounter tables
  - `treasure-generator.md` - Loot tables
  - `npc-generator.md` - Character creation tables

## 🔧 Usage

### Ingesting Documents

**Single Document:**
```bash
# Ingest a rules PDF
./gm rag ingest knowledge/rules/shadowdark-core.pdf --doctype rule

# Ingest setting information
./gm rag ingest knowledge/settings/lost-citadel.md --doctype setting --title "The Lost Citadel"

# Ingest monster compendium
./gm rag ingest knowledge/monsters/undead.md --doctype monster
```

**Batch Ingestion:**
```bash
# Ingest entire directory
./gm rag ingest-batch knowledge/rules/ --doctype rule

# Ingest all knowledge with auto-detection
./gm rag ingest-batch knowledge/ --auto-detect
```

### Document Types

The system recognizes these document types for better categorization:

- `rule` - Core game mechanics and rules
- `supplement` - Official expansions and additions
- `setting` - World information and campaign details
- `monster` - Creature stats and information
- `spell` - Magic and spells
- `equipment` - Items, weapons, armor
- `table` - Random generation tables
- `lore` - Background information and flavor
- `adventure` - Pre-written adventures and scenarios
- `reference` - Quick reference materials

### Querying Knowledge

```bash
# Search for specific rules
./gm rag query "How does combat initiative work?"

# Find monster information
./gm rag query "Shadow dragon stats and abilities"

# Get setting details
./gm rag query "Lost Citadel districts and locations"
```

## 📋 Best Practices

### Document Format
- **PDF**: Best for official rulebooks and supplements
- **Markdown**: Best for custom content and structured data
- **Plain Text**: Acceptable for simple reference materials

### Metadata
- Use descriptive titles
- Choose appropriate document types
- Include version information in filenames
- Add source attribution in document metadata

### Content Organization
- Keep related content together
- Use consistent naming conventions
- Include page references for official sources
- Maintain clean, searchable text

### File Naming
- Use lowercase with hyphens: `shadowdark-core-rules.pdf`
- Include version numbers: `cursed-scroll-v1.2.pdf`
- Be descriptive: `undead-creatures-bestiary.md`

## 🎲 Content Sources

### Official Sources
- Shadowdark RPG Core Rules (The Arcane Library)
- Cursed Scroll supplements
- Official adventures and modules

### Community Sources
- Fan-created content (with permission)
- Homebrew rules and additions
- Community bestiaries and supplements

### Custom Content
- Your campaign-specific material
- House rules and modifications
- Custom adventures and settings

## 🔍 RAG System Integration

When you ingest documents into this knowledge base, they become available to:

1. **Session Scribe** - References rules during session note generation
2. **Audio Processing** - Provides context for understanding game terms
3. **Query System** - Direct knowledge lookup and answers
4. **Future Agents** - NPC generators, adventure crafters, etc.

The RAG system automatically:
- Chunks documents intelligently
- Creates semantic embeddings
- Enables similarity search
- Provides relevant context to AI agents

## 🚀 Getting Started

1. **Download Official Content**: Obtain Shadowdark RPG materials
2. **Organize Files**: Place them in appropriate directories
3. **Ingest Content**: Use CLI commands to add to knowledge base
4. **Test Queries**: Verify system can find relevant information
5. **Generate Sessions**: Use enhanced context in session notes

Happy gaming! 🎲