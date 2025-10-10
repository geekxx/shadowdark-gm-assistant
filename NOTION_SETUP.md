# Notion Integration Setup

This guide explains how to set up Notion integration for the Shadowdark GM Assistant.

## Prerequisites

1. **Notion Account**: You need a Notion workspace where you want to store session notes
2. **Notion Integration**: Create a Notion integration to get API access

## Step 1: Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Fill out the form:
   - **Name**: "Shadowdark GM Assistant" 
   - **Logo**: Optional
   - **Associated workspace**: Choose your workspace
4. Click "Submit"
5. Copy the **Internal Integration Token** (starts with `secret_`)

## Step 2: Create a Database (Optional)

If you want session notes to go into a specific database:

1. Create a new page in Notion
2. Add a database (full page)
3. Set up these properties:
   - **Name** (Title) - for session titles
   - **Status** (Select) - Draft, Complete, etc.
   - **Type** (Select) - Session Notes, etc.
   - **Campaign** (Select) - Campaign names
   - **Date** (Date) - session date
4. Copy the database ID from the URL:
   - URL: `https://notion.so/workspace/database-id?v=view-id`
   - Database ID is the part after your workspace name

## Step 3: Share with Integration

1. Open your database page in Notion
2. Click "Share" in the top right
3. Click "Invite" and search for your integration name
4. Select your integration and click "Invite"

## Step 4: Set Environment Variables

Add these to your `.env` file or export them:

```bash
# Required - your integration token
export NOTION_TOKEN="secret_your_integration_token_here"

# Optional - specific database ID for session notes
export NOTION_DATABASE_ID="your_database_id_here"
```

## Step 5: Test the Integration

Run the test script to verify everything works:

```bash
python test_notion.py
```

## Usage Examples

### CLI Usage

```bash
# Summarize and sync to Notion
./gm session summarize transcript.txt --out notion

# With campaign and RAG context
./gm session summarize notes.md --campaign 1 --use-rag --out notion
```

### API Usage

```bash
# Summarize with Notion sync
curl -X POST "http://localhost:8000/sessions/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your session transcript here...",
    "sync_to_notion": true,
    "session_title": "Session 5: The Haunted Tower",
    "campaign_id": 1
  }'
```

## Troubleshooting

### Common Issues

1. **"Notion token required" error**
   - Make sure `NOTION_TOKEN` is set correctly
   - Token should start with `secret_`

2. **"Database ID required" error**  
   - Set `NOTION_DATABASE_ID` environment variable
   - Or pass `database_id` parameter to the sync functions

3. **"Failed to create Notion page" error**
   - Check that your integration has access to the database
   - Make sure you've shared the database with your integration
   - Verify the database ID is correct

4. **Page created but content is missing**
   - Check your integration permissions
   - Some Notion accounts have restrictions on content creation

### Getting Help

- Check the integration logs in your Notion integration settings
- Use the test script to isolate issues
- Verify your database structure matches the expected properties

## Features

The Notion integration supports:

- ✅ **Markdown to Notion blocks conversion** (headers, paragraphs, lists, bold text)
- ✅ **Automatic page creation** with session notes content
- ✅ **Custom properties** (campaign, date, status)
- ✅ **Error handling** with fallback to file output
- ✅ **Connection testing** before attempting sync

## Limitations

- Basic markdown conversion (no tables, complex formatting)
- No image/file upload support
- Database properties must be created manually
- Rate limiting may apply for high-volume usage