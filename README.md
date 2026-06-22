# kkAgentic Support

A two-agent AI support system. Each project gets its own dedicated agent, and a router
agent decides which one should answer.

- **Agent 1 — Router** (`ROUTER_MODEL` on OpenRouter): reads the question, decides which
  project it belongs to, returns a confidence score. If unsure, it asks the user to choose.
- **Agent 2 — Project answer agent** (`ANSWER_MODEL` on OpenRouter): retrieves that
  project's most relevant doc/FAQ chunks from Supabase (pgvector) and answers, grounded in
  those chunks only — with sources.

Channels: an **Apple-style web page**, a **Telegram bot**, and a **Streamlit console** —
all share the same pipeline.

```
You ──▶ Router (Gemma A) ──▶ Project Agent (Gemma B) ──▶ grounded answer + sources
                │                        │
          which project?         vector search in Supabase (per-project docs/FAQ)
```

See `flow.mermaid` for the full diagram (renders on GitHub), or open `web/index.html` which
visualizes the same flow.

---

## Project layout

```
kkAgentic Support/
├── core/                 # shared brain
│   ├── config.py         # env settings
│   ├── openrouter.py     # OpenRouter chat client (OpenAI-compatible)
│   ├── embeddings.py     # local sentence-transformers (or OpenAI) embeddings
│   ├── db.py             # Supabase: projects, vector search, logging
│   ├── router_agent.py   # Agent 1
│   ├── answer_agent.py   # Agent 2 (RAG)
│   └── pipeline.py       # orchestration used by every channel
├── api/main.py           # FastAPI /chat + /projects (called by the web page)
├── telegram_bot/bot.py   # Telegram front-end
├── streamlit_app/app.py  # Streamlit support console
├── web/index.html        # Apple-style support landing + chat (static)
├── ingest/
│   ├── ingest_docs.py     # load docs/FAQ -> embeddings -> Supabase
│   └── data/<project>/    # project.json + .md/.txt/.pdf knowledge files
├── supabase/schema.sql    # database schema (run in Supabase SQL editor)
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Install
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env
```

### 2. Supabase
1. Create a project at supabase.com.
2. Open **SQL Editor** and run the contents of `supabase/schema.sql`.
   (The vector dimension is **384**, matching `all-MiniLM-L6-v2`. If you change the
   embedding model, update both the SQL `vector(384)` and `EMBEDDING_DIM` in `.env`.)
3. Put your project URL and a key in `.env` (`SUPABASE_URL`, `SUPABASE_KEY`).
   Use the **service-role** key for ingestion; the anon key is fine for chat.

### 3. OpenRouter (your 2 agents)
Set `OPENROUTER_API_KEY`, and pick the two models:
```
ROUTER_MODEL=google/gemma-3-12b-it
ANSWER_MODEL=google/gemma-3-27b-it
```
Use whatever exact Gemma slugs your OpenRouter account exposes (swap in your "Gemma 4"
slug when available). The two agents can use the same or different models.

### 4. Add a project's knowledge
Create `ingest/data/<project_key>/project.json`:
```json
{
  "name": "Billing Portal",
  "description": "Invoices, payments, refunds, subscriptions.",
  "keywords": ["invoice", "refund", "payment"],
  "persona": "Be careful with money questions; point to the exact button."
}
```
Drop `.md`, `.txt`, or `.pdf` files (docs + FAQ) in the same folder, then:
```bash
python -m ingest.ingest_docs --all --replace
```
Two sample projects (`billing-portal`, `mobile-app`) are included to start.

---

## Run each channel

**API (for the web page):**
```bash
uvicorn api.main:app --reload --port 8000
```

**Web page:** open `web/index.html` (or host it on GitHub Pages). Edit the three
constants at the top of its `<script>`: `API_BASE`, `TELEGRAM`, `STREAMLIT`.

**Telegram bot:** create a bot with @BotFather, set `TELEGRAM_BOT_TOKEN`, then:
```bash
python -m telegram_bot.bot
```

**Streamlit console:**
```bash
streamlit run streamlit_app/app.py
```

---

## Deploy (Supabase + GitHub + Streamlit)

- **Supabase** hosts the database, knowledge base (pgvector) and conversation logs.
- **GitHub** stores this repo. Add a `.env`-equivalent as repo/Actions secrets — never
  commit `.env` (already in `.gitignore`).
- **Streamlit Community Cloud**: point it at `streamlit_app/app.py` and add the same
  variables under **App → Settings → Secrets**.
- **FastAPI `/chat`** can run on any host (Render, Railway, Fly.io, a VPS, or a Supabase
  Edge Function rewrite). Point the web page's `API_BASE` at it and set `CORS_ALLOW_ORIGINS`
  to your web page's origin.
- **Telegram bot** runs as a long-lived worker (Railway/Fly/VPS), or switch `run_polling`
  to a webhook for serverless.

---

## How routing decides

1. **Keyword shortcut** — if a project keyword appears in the question, route instantly
   (confidence 0.9).
2. **Router model** — otherwise the router model returns `{project_key, confidence, reason}`.
3. **Confidence gate** — below `ROUTER_MIN_CONFIDENCE` (default 0.45) or `unknown`, the user
   is asked to pick a project instead of getting a guessed answer.
4. **Context stickiness** — Telegram and the web chat remember the last project so follow-up
   questions stay with the same agent.

## Recommendations / ideas beyond your sketch

- **Confidence gate + clarify** (built in) avoids the router silently sending a question to
  the wrong project.
- **Grounded answers with sources** reduce hallucination — the answer agent is told to say
  "I don't have that yet" and offer escalation rather than invent.
- **Conversation logging** in Supabase gives you analytics (most-asked topics, low-confidence
  questions to add to FAQs) and a path to human escalation.
- **One pipeline, many channels** means Telegram, web, and Streamlit never drift apart.
- Future: add a `human_handoff` flag, per-project analytics dashboard, and feedback 👍/👎
  buttons that write back to `conversations`.

## Security notes
- Keep `SUPABASE_KEY` (service role) and `OPENROUTER_API_KEY` server-side only — never in
  `web/index.html`. The web page only talks to your FastAPI `/chat`.
- Row Level Security is enabled in the schema: public can read active projects/documents;
  writes go through your backend's key.
