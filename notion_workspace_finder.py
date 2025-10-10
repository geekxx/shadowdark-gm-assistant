#!/usr/bin/env python3
"""
Notion workspace finder and simple page creator.
This will find your workspace and create a page without needing a database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def find_workspace_and_create_page():
    """Find the user's workspace and create a test page"""
    print("🔍 Finding your Notion workspace...")
    
    try:
        from notion_client import Client
        
        notion_token = os.getenv('NOTION_TOKEN')
        if not notion_token:
            print("❌ NOTION_TOKEN not set")
            return
        
        client = Client(auth=notion_token)
        
        # Search for pages to find the workspace
        print("📄 Searching for pages in your workspace...")
        search_results = client.search()
        
        if not search_results.get('results'):
            print("❌ No pages found. You may need to create a page in your Notion workspace first.")
            print("\n📝 Manual setup instructions:")
            print("1. Go to your Notion workspace")
            print("2. Create a new page called 'Shadowdark Sessions'") 
            print("3. Create a database with properties: Name, Status, Campaign, Date")
            print("4. Share the database with your integration")
            print("5. Get the database ID from the URL")
            return
        
        print(f"✅ Found {len(search_results['results'])} pages/databases in your workspace:")
        
        for i, result in enumerate(search_results['results'][:5]):  # Show first 5
            object_type = result.get('object', 'unknown')
            title = "Untitled"
            
            if object_type == 'page':
                props = result.get('properties', {})
                if 'title' in props and props['title'].get('title'):
                    title = props['title']['title'][0]['text']['content']
                elif result.get('parent', {}).get('type') == 'workspace':
                    title = "Root page in workspace"
            elif object_type == 'database':
                title_prop = result.get('title', [])
                if title_prop:
                    title = title_prop[0]['text']['content']
            
            print(f"  {i+1}. {object_type.title()}: {title}")
            print(f"     ID: {result['id']}")
            
        # Try to create a page in workspace root (if possible)
        print("\n🎯 Let's try to create a test page...")
        
        # Find a page that's in the workspace root
        workspace_pages = [r for r in search_results['results'] 
                         if r.get('parent', {}).get('type') == 'workspace']
        
        if workspace_pages:
            print("✅ Found workspace root access. Testing page creation...")
            
            # Try to create a child page under workspace
            try:
                test_content = """# Test Session Notes

This is a test page created by the Shadowdark GM Assistant.

## Next Steps
1. Create a database called "Shadowdark Sessions"  
2. Add properties: Name (Title), Status (Select), Campaign (Select), Date (Date)
3. Share the database with your integration
4. Copy the database ID and set NOTION_DATABASE_ID environment variable

You can delete this test page after setup is complete.
"""
                
                blocks = []
                for line in test_content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('# '):
                        blocks.append({
                            "object": "block",
                            "type": "heading_1", 
                            "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                        })
                    elif line.startswith('## '):
                        blocks.append({
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
                        })
                    else:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
                        })
                
                page = client.pages.create(
                    parent={"type": "workspace", "workspace": True},
                    properties={
                        "title": {"title": [{"text": {"content": "Shadowdark GM Test Page"}}]}
                    },
                    children=blocks
                )
                
                print("🎉 SUCCESS! Created test page in your workspace!")
                print(f"   Page URL: {page.get('url', 'N/A')}")
                print("\n✅ Your Notion integration is working!")
                print("\n📋 To complete setup:")
                print("1. Visit the test page in Notion")
                print("2. Create a database called 'Shadowdark Sessions'")
                print("3. Share it with your integration")  
                print("4. Set NOTION_DATABASE_ID environment variable")
                
            except Exception as create_error:
                print(f"❌ Could not create page: {create_error}")
                print("\n📋 Manual database setup required:")
                print("1. Create a new database in Notion called 'Shadowdark Sessions'")
                print("2. Add properties: Name (Title), Status (Select), Campaign (Select), Date (Date)")
                print("3. Share the database with your integration")
                print("4. Copy database ID from URL and set NOTION_DATABASE_ID")
        else:
            print("❌ No workspace root access found.")
            print("   You may need to create content manually in Notion first.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    find_workspace_and_create_page()