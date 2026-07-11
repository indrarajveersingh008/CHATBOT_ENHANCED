# AI Nexus

An AI chatbot with persistent conversation memory, file uploads, and message search, built with a FastAPI backend and a vanilla JS frontend.

## Project structure

```
AI-Chatbot/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app entrypoint
│       ├── config/          # env-based settings
│       ├── database/        # SQLAlchemy engine/session
│       ├── models/          # Conversation, Message, UploadedFile
│       ├── routes/          # /chat, /memory/*, /files/*
│       ├── ai/              # OpenRouter client wrapper
│       └── utils/           # small helpers
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
│       ├── api.js           # all fetch() calls to the backend
│       ├── chat.js          # chat rendering + sending
│       ├── memory.js        # conversation history panel
│       ├── ui.js            # panel switching, Files & Search panels
│       ├── voice.js         # "Hi Nexus" voice input
│       └── app.js           # bootstrap
├── requirements.txt
└── runtime.txt              # pins Python version for Render
```

## Backend setup (local)

1. Create a `.env` file in the project root:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```
2. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the server from the project root:
   ```bash
   uvicorn backend.app.main:app --reload
   ```
   This creates a local `ai_nexus.db` SQLite file automatically on first run.

## Frontend setup (local)

Open `frontend/index.html` directly, or serve the folder with any static server
(e.g. the VS Code "Live Server" extension). Update `API_BASE_URL` in
`frontend/js/api.js` if your backend isn't running on Render.

## Deploying

- **Backend (Render):** start command `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
  Set `OPENROUTER_API_KEY` in Render's environment variables — don't commit `.env`.
  Render's free-tier disk is wiped on every redeploy, so the SQLite DB and any
  uploaded files reset then too. For anything you need to keep long-term, point
  `DATABASE_URL` at a managed Postgres instance instead.
- **Frontend (Vercel):** deploy the `frontend/` folder as a static site.

## Features

- 💬 **Chat** — talks to an LLM via OpenRouter, with conversation memory sent as context.
- 🧠 **Memory** — past conversations are saved server-side and browsable/deletable.
- 📂 **Files** — upload, list, download, and delete files (stored on the server).
- 🌐 **Search** — full-text search across every message you've ever sent/received.
- 🎤 **Voice** — say "Hi Nexus" to activate voice input.
