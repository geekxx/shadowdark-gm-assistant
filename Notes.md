## To run your application in the future:
1. Make sure Docker is running
2. Start the database: docker-compose -f [docker-compose.yml](http://_vscodecontentref_/2) up -d
3. Start the API: /Users/jeffrey.heinen/projects/shadowdark-gm/.venv/bin/uvicorn apps.api.main:app --reload

# Session Notes Generator CLI Usage
./gm session summarize sample_transcript.md --use-rag --out session_notes.md
./gm rag ingest my_rules.pdf --doctype rule
./gm rag query "How do spells work?"

# API Server
uvicorn apps.api.main:app --reload
# Then use /docs for interactive API testing