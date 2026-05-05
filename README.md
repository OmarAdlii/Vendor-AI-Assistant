# Vendor AI Assistant

Brief project overview
- AI-powered chatbot integrated with MCP tools, RAG, and PostgreSQL for conversation memory.
- Web UI is served from `static/chat.html`; API is available via REST and WebSocket.

Key features
- AI agent for message processing (`agent/ai_agent.py`).
- Conversation memory stored in Postgres (`chat_memory`) with indexing and archiving.
- RAG support: upload documents and search the knowledge base.
- MCP utilities for KPI and performance data queries.

Requirements
- Python 3.11+ (virtual environment recommended)
- PostgreSQL for two databases: main (vmbe) and chat memory (chatAi)

Quick start (Linux/macOS)

1) Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies:

```bash
pip install -U pip
pip install -r requirements.txt
```

3) Create a `.env` file in the project root with required variables (minimal):

```
OPENAI_API_KEY=sk-...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=vmbe
POSTGRES_USER=vmbe_user
POSTGRES_PASSWORD=secret

CHAT_DB_HOST=localhost
CHAT_DB_PORT=5432
CHAT_DB_NAME=chatAi
CHAT_DB_USER=chat_user
CHAT_DB_PASSWORD=secret

SUPABASE_URL=...
SUPABASE_KEY=...
```

4) Ensure PostgreSQL databases exist and users have proper privileges. The app will create the `chat_memory` table automatically if missing.

Run the server

```bash
# Option A (simple)
python app/main.py

# Option B (recommended for development)
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

Open the UI

- Visit: http://localhost:8005/ — the file `static/chat.html` will be served if present.
- API docs: http://localhost:8005/docs

Endpoints

WebSocket
- `GET /ws/{vendor_id}` — Real-time chat socket. Send JSON: `{"message":"...","stream":false}`. Responses are streamed or returned as JSON messages.

REST
- `POST /api/chat` — Non-streaming chat. Example payload:

```json
{ "message": "Hello", "vendor_id": "54", "session_id": null }
```

Response: JSON with `response`, `session_id`, and optional `tool_calls`.

- `POST /api/upload-document` — Upload a document to add to the knowledge base. Use a multipart file upload.
- `POST /api/search-knowledge` — Search knowledge base. Provide `{ "query": "...", "top_k": 10, "threshold": 0.7 }`.
- `GET /api/health` — Health check; returns basic service and DB status.

Conversation management
- `DELETE /api/conversation/{session_id}` — Clear conversation (implementation may be no-op).
- `GET /api/conversation/{session_id}` — Get recent conversation (default 20 messages).
- `GET /api/conversation/{session_id}/full` — Get full conversation with optional `start_date` and `end_date` (ISO format).
- `POST /api/conversation/search` — Search conversations (body parameters: `session_id`, `search_text`, `start_date`, `end_date`, `limit`).
- `GET /api/conversation/{session_id}/stats` — Session statistics.
- `POST /api/conversation/archive` — Archive conversations older than `days_old`.

Using this project as a backend

- To integrate the chatbot as a backend for a web or mobile client:
  1. Use the WebSocket endpoint for interactive streaming chat.
  2. Or call `POST /api/chat` from your frontend to get a single response per request.
  3. Store `session_id` on the client to maintain conversational context across requests.

Examples

HTTP chat example (curl):

```bash
curl -X POST http://localhost:8005/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","vendor_id":"54"}'
```

WebSocket example (browser JS):

```js
const ws = new WebSocket('ws://localhost:8005/ws/54');
ws.onopen = () => ws.send(JSON.stringify({ message: 'Hello', stream: false }));
ws.onmessage = (evt) => console.log('recv', JSON.parse(evt.data));
```

Notes

- Configuration is read from `.env` via `app/config.py`.
- Helper scripts are in `scripts/` (for repo maintenance).

Run (single command)

- Make the run script executable and start the app:

```bash
chmod +x scripts/run_all.sh
./scripts/run_all.sh
```

Notes and tips

- `scripts/run_all.sh` will try to activate the local virtualenv at `chatbot/` if present and will load environment variables from `.env`.
- Ensure PostgreSQL instances for `vmbe` and `chatAi` are running and the credentials in `.env` are valid before starting.
- If you prefer using `uvicorn` directly, you can run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```


