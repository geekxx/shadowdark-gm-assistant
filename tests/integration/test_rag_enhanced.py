#!/usr/bin/env python3

"""
Test script for enhanced RAG Librarian functionality
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import create_engine, Session
from core.agents.rag_librarian import ingest_text, ingest_file, search
from core.data.models import SQLModel

# Test database setup
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/shadowdark"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Sample Shadowdark rule text
SAMPLE_RULES = """
# Combat

## Initiative
At the start of combat, each side rolls 1d6. The side with the higher result goes first.

## Attack Rolls
Roll 1d20 + ability modifier + proficiency bonus vs target's AC.

### Critical Hits
Natural 20 always hits and deals maximum damage plus one additional damage die.

## Damage and Death
When you reach 0 HP, make a death check:
- Roll 1d20
- 1-10: You die
- 11-15: You're unconscious and stable
- 16-20: You revive with 1 HP

## Spellcasting

### Spell Slots
Clerics and wizards have spell slots that refresh after a full rest.

### Spell DC
Spell save DC = 10 + ability modifier + proficiency bonus

# Equipment

## Light Sources
- Torch: 1 hour of bright light in Near range
- Candle: 2 hours of dim light in Close range
- Lantern: 3 hours of bright light in Near range (requires oil)

## Armor
- Leather: AC 11 + DEX modifier
- Chain: AC 13 + DEX modifier (max 2)
- Plate: AC 15
"""

SAMPLE_SESSION_NOTES = """
# Session 5: The Cursed Library

## What Happened
The party entered the abandoned library beneath Ravenshollow. Kira (elf wizard) detected magical auras throughout the building. Thane (human fighter) triggered a trap while searching the archives.

## NPCs Met
- **Erasmus the Scribe**: Ghostly librarian, helpful but melancholy
- **Shadow Rats**: Corrupted creatures in the basement

## Treasure Found
- Spell scroll: Magic Missile
- 40 gold pieces in a hidden drawer
- Ancient tome: "Rituals of the Moon Court" (worth 100gp to collectors)

## Clocks Advanced
- **Cult Activity**: 2/6 segments (they're getting bolder)
- **Winter's Approach**: 4/6 segments (supplies running low)
"""

def test_enhanced_rag():
    print("Testing Enhanced RAG Librarian...")
    print("=" * 50)
    
    try:
        with Session(engine) as sess:
            # Test text ingestion with smart chunking
            print("1. Ingesting sample rules...")
            rules_doc_id = ingest_text(
                sess, 
                SAMPLE_RULES, 
                title="Shadowdark Core Rules", 
                doctype="rule"
            )
            print(f"   Created document ID: {rules_doc_id}")
            
            print("2. Ingesting session notes...")
            session_doc_id = ingest_text(
                sess,
                SAMPLE_SESSION_NOTES,
                title="Session 5 Notes",
                doctype="note"
            )
            print(f"   Created document ID: {session_doc_id}")
            
            # Test search functionality
            print("\n3. Testing search queries...")
            
            queries = [
                "How do death saves work?",
                "What light sources are available?",
                "Tell me about the cursed library session",
                "What treasure did they find?"
            ]
            
            for query in queries:
                print(f"\nQuery: '{query}'")
                results = search(sess, query, k=2)
                print(f"Found {len(results)} results:")
                for i, chunk in enumerate(results, 1):
                    preview = chunk.text[:100].replace('\n', ' ')
                    print(f"   {i}. [{chunk.page or 'N/A'}] {preview}...")
            
            print("\n" + "=" * 50)
            print("✅ Enhanced RAG Librarian test completed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_rag()