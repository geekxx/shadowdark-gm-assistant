To run your application in the future:
Make sure Docker is running
Start the database: docker-compose -f [docker-compose.yml](http://_vscodecontentref_/2) up -d
Start the API: /Users/jeffrey.heinen/projects/shadowdark-gm/.venv/bin/uvicorn apps.api.main:app --reload
