#!/usr/bin/env python3
"""
Inspect the actual properties of the Notion database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def inspect_database():
    """Inspect the actual database schema"""
    print("🔍 Inspecting your Notion database schema...")
    
    try:
        from notion_client import Client
        
        notion_token = os.getenv('NOTION_TOKEN')
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not notion_token or not database_id:
            print("❌ Missing NOTION_TOKEN or NOTION_DATABASE_ID")
            return
        
        client = Client(auth=notion_token)
        
        # Get database details
        database = client.databases.retrieve(database_id=database_id)
        
        print(f"✅ Database: {database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
        print(f"   ID: {database_id}")
        print("\n📋 Properties:")
        
        properties = database.get('properties', {})
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get('type', 'unknown')
            print(f"   - {prop_name}: {prop_type}")
            
            # Show options for select/multi_select
            if prop_type in ['select', 'multi_select']:
                options = prop_info.get(prop_type, {}).get('options', [])
                if options:
                    option_names = [opt.get('name', 'Unknown') for opt in options]
                    print(f"     Options: {', '.join(option_names)}")
        
        print(f"\n🎯 To fix the integration, update NotionSync to use these exact property names and types.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    inspect_database()