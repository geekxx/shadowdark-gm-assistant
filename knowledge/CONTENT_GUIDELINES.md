# Knowledge Base Content Guidelines

## Content Authority Levels

### 🏆 **Tier 1: Official Content (Highest Priority)**
- Shadowdark RPG Core Rules
- Official supplements (Cursed Scroll, etc.)
- Licensed adventures and modules
- **Document Types**: `rule`, `supplement`, `adventure`

### 🥈 **Tier 2: Semi-Official Content**
- Community-approved content
- Popular house rules
- Well-tested homebrew
- **Document Types**: `supplement`, `reference`

### 🥉 **Tier 3: Utility Content (Generic)**
- Random generation tables
- Generic RPG tools
- Campaign organization helpers
- **Document Types**: `table`, `reference`, `other`

### 📝 **Tier 4: Campaign-Specific Content**
- Your house rules
- Custom NPCs and locations
- Campaign notes and lore
- **Document Types**: `note`, `setting`, `lore`

## 🧠 Intelligent Content Classification

The RAG system now includes **intelligent chunk classification** that automatically categorizes content based on patterns, regardless of the parent document type.

### How It Works
When ingesting documents (especially multi-category ones like core rulebooks), the system:

1. **Splits content** into logical chunks
2. **Analyzes each chunk** using pattern matching
3. **Assigns content types** based on detected patterns:
   - `monster` - Stat blocks with AC, HP, abilities, attacks
   - `spell` - Spells with level, casting time, range, components
   - `rule` - Game rules, mechanics, procedures
   - `table` - Random generators, lookup tables, dice results
   - `equipment` - Weapons, armor, gear with stats

### Multi-Category Documents
Perfect for documents like the **Shadowdark Core Rules** that contain:

```bash
# Ingest entire core rulebook as 'rule' type
./gm rag ingest shadowdark-core.pdf --doctype rule

# Query specific content types within it
./gm rag query "shadow rat stats" --types monster     # Find monster stats
./gm rag query "light cantrip" --types spell          # Find spell descriptions  
./gm rag query "random encounters" --types table      # Find random tables
./gm rag query "advantage rolls" --types rule         # Find game rules
```

### Query Filtering
Use `--types` parameter to filter results by content classification:
- `--types monster` - Only monster stat blocks
- `--types spell,rule` - Spells and rules only  
- `--types table` - Random tables and generators

## 📋 Ingestion Best Practices

### Content Authority Hierarchy
1. **Official Sources** (Highest Authority)
   - Official Shadowdark Core Rulebook
   - Official supplements from The Arcane Library
   - Published adventures and materials

2. **Semi-Official Sources** 
   - Community-approved content
   - Popular third-party supplements
   - Well-regarded homebrew rules

3. **Utility Content**
   - Random generators and tables
   - GM tools and quick references  
   - Session planning aids

4. **Campaign-Specific Content** (Lowest Authority)
   - House rules and custom mechanics
   - Campaign-specific lore and modifications
   - Player-created content

## Avoiding Conflicts

- **Use specific document types** for better categorization
- **Name files clearly** (e.g., `shadowdark-core-v1.0.pdf` not `rules.pdf`)
- **Check for duplicates** before ingesting new content
- **Query test** after ingesting to ensure good results

## Content Quality

- **Official sources** are always preferred
- **Cite sources** in document metadata
- **Version control** rule changes and updates
- **Remove outdated** content when rules change