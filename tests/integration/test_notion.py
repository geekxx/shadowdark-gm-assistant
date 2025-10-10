#!/usr/bin/env python3
"""
Test script for Notion integration.

This script demonstrates how to use the Notion sync functionality.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.integrations.notion_sync import NotionSync

def test_notion_connection():
    """Test basic Notion API connection"""
    print("🔗 Testing Notion API connection...")
    
    # Check environment variables
    notion_token = os.getenv('NOTION_TOKEN')
    notion_db_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token:
        print("❌ NOTION_TOKEN environment variable not set")
        print("   Please set your Notion integration token:")
        print("   export NOTION_TOKEN='your_token_here'")
        return False
    
    if not notion_db_id:
        print("⚠️  NOTION_DATABASE_ID not set - you'll need to specify database_id in function calls")
    
    try:
        notion = NotionSync()
        
        if notion.test_connection():
            print("✅ Notion API connection successful!")
            return True
        else:
            print("❌ Notion API connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Notion: {e}")
        return False

def test_notion_page_creation():
    """Test creating a Notion page with sample session notes"""
    print("\n📝 Testing Notion page creation...")
    
    sample_notes = """# Session 5: The Haunted Library

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
        notion = NotionSync()
        
        page = notion.create_session_page(
            title="Test Session - Haunted Library",
            content=sample_notes,
            properties={
                "Status": {"select": {"name": "Draft"}},
                "Play Group": {"select": {"name": "Online"}}
            }
        )
        
        print("✅ Test page created successfully!")
        print(f"   Page URL: {page.get('url', 'N/A')}")
        return True
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error creating page: {e}")
        return False

def main():
    """Run Notion integration tests"""
    print("🧪 Notion Integration Test Suite")
    print("=" * 40)
    
    # Test 1: Connection
    if not test_notion_connection():
        print("\n❌ Connection test failed. Cannot proceed with page creation test.")
        return
    
    # Test 2: Page creation
    print("\nWould you like to test creating a sample Notion page? (y/n): ", end="")
    response = input().strip().lower()
    
    if response in ['y', 'yes']:
        test_notion_page_creation()
    else:
        print("📝 Skipping page creation test.")
    
    print("\n🎉 Test suite completed!")
    print("\nTo use Notion sync in the CLI:")
    print("  ./gm session summarize sample_transcript.md --out notion")
    print("\nTo use Notion sync in the API:")
    print('  curl -X POST "http://localhost:8000/sessions/summarize" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"text": "Your transcript here", "sync_to_notion": true}\'')

if __name__ == '__main__':
    main()