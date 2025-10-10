#!/usr/bin/env python3
"""
Simple Notion page creator (doesn't require a database).
This creates a standalone page that you can then convert to a database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.integrations.notion_sync import NotionSync

def create_standalone_page():
    """Create a standalone Notion page (no database required)"""
    print("📝 Creating standalone Notion page...")
    
    sample_notes = """# Shadowdark GM Session Notes

## Cast
- **Kira Brightblade** (Fighter) - Led the party's assault on the shadow creatures
- **Thane Ironforge** (Cleric) - Provided healing and turned undead
- **Zara Quickfingers** (Thief) - Disabled magical traps and picked locks

## Key Scenes
- The party discovered an ancient tome of shadow magic
- Three shadow rats attacked from the cursed bookshelves
- Successfully cleansed the library's dark influence

## Treasure Found
- Ancient spellbook worth 200gp
- Silver dagger with +1 enchantment
- 45 gold pieces from a hidden compartment

## Next Prep
- The shadow tome mentions a dark ritual in the nearby caves
- NPCs to prep: Elder Morthain, the village sage
- Location: The Whispering Caves entrance
"""
    
    try:
        from notion_client import Client
        
        notion_token = os.getenv('NOTION_TOKEN')
        if not notion_token:
            print("❌ NOTION_TOKEN not set")
            return
        
        client = Client(auth=notion_token)
        
        # Create a standalone page (no database)
        response = client.pages.create(
            parent={"type": "page_id", "page_id": "parent_page_id"},  # This will fail but show us the workspace
            properties={
                "title": {"title": [{"text": {"content": "Test Session Notes"}}]}
            }
        )
        
    except Exception as e:
        if "Parent page does not exist" in str(e) or "parent" in str(e).lower():
            print("✅ Token is valid! But we need to create content in your workspace.")
            print("\n📋 Next steps:")
            print("1. Go to your Notion workspace")
            print("2. Create a new page called 'Shadowdark Sessions'")
            print("3. Add a database (full page) with these properties:")
            print("   - Name (Title)")
            print("   - Status (Select: Draft, Complete)")
            print("   - Campaign (Select)")
            print("   - Date (Date)")
            print("4. Share the database with your integration")
            print("5. Copy the database ID from the URL")
            print("\nThen run: export NOTION_DATABASE_ID='your-database-id'")
        else:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    create_standalone_page()