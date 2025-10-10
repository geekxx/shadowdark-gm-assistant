"""
Notion integration for Shadowdark GM Assistant.

Handles creating and updating Notion pages with session notes.
"""

import os
from typing import Optional, Dict, Any
from notion_client import Client
from notion_client.errors import APIResponseError


class NotionSync:
    """Handle Notion API integration for session notes."""
    
    def __init__(self, notion_token: Optional[str] = None):
        """
        Initialize Notion client.
        
        Args:
            notion_token: Notion integration token. If not provided, 
                         will look for NOTION_TOKEN environment variable.
        """
        self.token = notion_token or os.getenv('NOTION_TOKEN')
        if not self.token:
            raise ValueError(
                "Notion token required. Set NOTION_TOKEN environment variable "
                "or pass token to constructor."
            )
        
        self.client = Client(auth=self.token)
        self.database_id = os.getenv('NOTION_DATABASE_ID')
    
    def create_session_page(
        self,
        title: str,
        content: str,
        database_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new Notion page with session notes.
        
        Args:
            title: Page title (session name/date)
            content: Session notes content in markdown
            database_id: Notion database ID. If not provided, uses NOTION_DATABASE_ID env var
            properties: Additional page properties (tags, date, etc.)
            
        Returns:
            Created page object from Notion API
        """
        target_db = database_id or self.database_id
        if not target_db:
            raise ValueError(
                "Database ID required. Set NOTION_DATABASE_ID environment variable "
                "or pass database_id parameter."
            )
        
        # Default properties
        page_properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": "Draft"}},
            "Type": {"select": {"name": "Session Notes"}}
        }
        
        # Add custom properties
        if properties:
            page_properties.update(properties)
        
        # Convert markdown content to Notion blocks
        blocks = self._markdown_to_blocks(content)
        
        try:
            response = self.client.pages.create(
                parent={"database_id": target_db},
                properties=page_properties,
                children=blocks
            )
            return response
        except APIResponseError as e:
            raise Exception(f"Failed to create Notion page: {e}")
    
    def update_session_page(
        self,
        page_id: str,
        content: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing Notion page with new session notes.
        
        Args:
            page_id: Notion page ID to update
            content: New session notes content
            properties: Properties to update
            
        Returns:
            Updated page object from Notion API
        """
        blocks = self._markdown_to_blocks(content)
        
        try:
            # Clear existing content
            self._clear_page_content(page_id)
            
            # Add new content
            self.client.blocks.children.append(
                block_id=page_id,
                children=blocks
            )
            
            # Update properties if provided
            if properties:
                self.client.pages.update(
                    page_id=page_id,
                    properties=properties
                )
            
            return self.client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            raise Exception(f"Failed to update Notion page: {e}")
    
    def _markdown_to_blocks(self, content: str) -> list:
        """
        Convert markdown content to Notion blocks.
        
        This is a simplified conversion that handles:
        - Headers (# ## ###)
        - Paragraphs
        - Bullet lists (-)
        - Bold (**text**)
        
        Args:
            content: Markdown content string
            
        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Headers
            if line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            # Bullet lists
            elif line.startswith('- '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            # Regular paragraphs
            else:
                # Handle bold text (**text**)
                rich_text = self._parse_rich_text(line)
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": rich_text
                    }
                })
        
        return blocks
    
    def _parse_rich_text(self, text: str) -> list:
        """
        Parse text for rich formatting (bold, italic).
        
        Currently handles **bold** text.
        """
        rich_text = []
        current_pos = 0
        
        while current_pos < len(text):
            # Find next bold marker
            bold_start = text.find('**', current_pos)
            if bold_start == -1:
                # No more bold text, add remaining as plain text
                if current_pos < len(text):
                    rich_text.append({
                        "type": "text",
                        "text": {"content": text[current_pos:]}
                    })
                break
            
            # Add text before bold marker
            if bold_start > current_pos:
                rich_text.append({
                    "type": "text",
                    "text": {"content": text[current_pos:bold_start]}
                })
            
            # Find closing bold marker
            bold_end = text.find('**', bold_start + 2)
            if bold_end == -1:
                # No closing marker, treat as plain text
                rich_text.append({
                    "type": "text",
                    "text": {"content": text[bold_start:]}
                })
                break
            
            # Add bold text
            bold_content = text[bold_start + 2:bold_end]
            rich_text.append({
                "type": "text",
                "text": {"content": bold_content},
                "annotations": {"bold": True}
            })
            
            current_pos = bold_end + 2
        
        return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]
    
    def _clear_page_content(self, page_id: str):
        """Clear all blocks from a Notion page."""
        try:
            # Get all blocks
            blocks = self.client.blocks.children.list(block_id=page_id)
            
            # Delete each block
            for block in blocks['results']:
                self.client.blocks.delete(block_id=block['id'])
        except APIResponseError as e:
            # If we can't clear content, that's okay - we'll append instead
            pass
    
    def test_connection(self) -> bool:
        """
        Test if Notion API connection is working.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list users (basic API test)
            self.client.users.list()
            return True
        except Exception:
            return False