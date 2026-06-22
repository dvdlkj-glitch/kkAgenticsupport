# kkAgentic Support — 1st Achievement SOP (Demo Online)

Goal: get the **introduction page + live chat intake + file upload** online on
Streamlit Community Cloud as a working early demo, as fast as possible.

The order below is the fastest path. You can do **Step A (GitHub)** and
**Step B (get keys)** in parallel; both must be done before **Step C (deploy)**.

---

## Step A — Push the project to GitHub

You do **not** need any keys for this step. Secrets never go in the repo.

### A1. Files that MUST be in the repo (the demo depends on them)
```
core/__init__.py
core/config.py
core/openrouter.py        # the LLM client the chat agent uses
core/drive.py             # Google Drive upload
streamlit_app/intro.py        # <-- Streamlit entry point
streamlit_app/intake_agent.py # the AI intake agent logic
web/introduction.html         # the page UI
customer_support_script.txt   # the agent reads this at runtime — REQUIRED
requirements.txt
.gitignore
.env.example                  # template only (safe — no real secrets)
```

### A2. Nice to include (not needed for the demo)
```
README.md  FLOW.md  flow.mermaid
core/db.py  core/embeddings.py  core/pipeline.py  core/router_agent.py  core/answer_agent.py
api/  telegram_bot/  ingest/  supabase/   # other channels — for later
web/bg-agentic.jpg  web/bg-agentic.png
streamlit_app/app.py
```

### A3. NEVER upload these
```
.env                       # your real secrets (already in .gitignore)
service-account JSON key   # goes in Streamlit Secrets, NOT the repo
__pycache__/  .venv/       # caches (already in .gitignore)
```

### A4. Requirements (already done)
`requirements.txt` has been slimmed to just what the demo needs (Streamlit,
OpenRouter client, Drive client) so the Streamlit Cloud build is fast:
```
streamlit>=1.36.0
openai>=1.40.0
python-dotenv>=1.0.1
google-api-python-client>=2.130.0
google-auth>=2.30.0
```
The full set (Supabase, embeddings/torch, Telegram, FastAPI) is preserved in
`requirements-full.txt` for when you wire up the other channels later.

### A5. Commands
```bash
cd "kkAgentic Support"
git init
git add .
git commit -m "kkAgentic Support — intro page + live intake demo"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

---

## Step B — Get the keys (do this while A is running)

### B1. OpenRouter (powers the AI chat agent) — REQUIRED for the demo
1. Sign up at https://openrouter.ai and add a little credit (or use a free model).
2. Create an API key → copy it (starts with `sk-or-...`).
3. Pick the answer model slug, e.g. `google/gemma-3-27b-it` (or any model your
   account exposes). This becomes `ANSWER_MODEL`.

> The AI agent is **already built** (`streamlit_app/intake_agent.py`): it greets
> users, collects Name / Company / Project / Project Code, runs the STL branch,
> and decides when details are ready to save. It just needs `OPENROUTER_API_KEY`
> to come alive — no extra coding required.

### B2. Google Drive service account (powers screenshot / client-project upload) — REQUIRED for upload
You already created the folder:
`https://drive.google.com/drive/folders/1n85znNakl_5A_kkuC52faUbPQIUmL0Xj`
Now create credentials that can write to it:
1. Go to https://console.cloud.google.com → create/select a project.
2. **APIs & Services → Library →** enable **Google Drive API**.
3. **APIs & Services → Credentials → Create credentials → Service account.**
4. Open the service account → **Keys → Add key → Create new key → JSON** → download it.
5. Open the JSON, copy the `client_email` (looks like
   `name@project.iam.gserviceaccount.com`).
6. In Google Drive, open your folder → **Share** → paste that `client_email` →
   give **Editor** → Share.

> Heads-up: a service account writing into a **personal "My Drive"** folder can
> fail with a storage-quota error (the file ends up owned by the quota-less
> service account). If that happens, move the folder to a **Shared Drive** and
> share that with the `client_email`. Tell me and I'll guide you.

### B3. Supabase — NOT needed for this demo
The intake chat does not use the document/RAG search, so you can skip Supabase
entirely for now. We'll wire it in for the "answer-from-docs" feature later.

---

## Step C — Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io → **Create app** → pick your GitHub repo.
2. **Main file path:** `streamlit_app/intro.py`
3. **Advanced settings → Secrets:** paste the block below (fill in your values),
   then Deploy.

```toml
OPENROUTER_API_KEY = "sk-or-...your key..."
ANSWER_MODEL = "google/gemma-3-27b-it"
GDRIVE_UPLOAD_FOLDER_ID = "1n85znNakl_5A_kkuC52faUbPQIUmL0Xj"

[gcp_service_account]
# paste these fields straight from your downloaded JSON key:
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n....\n-----END PRIVATE KEY-----\n"
client_email = "name@your-project.iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

Notes:
- Keep the `private_key` exactly as in the JSON, including the `\n` sequences.
- You can edit Secrets after deploy (**Manage app → Settings → Secrets**); the app reboots automatically.

---

## Step D — Smoke test the live demo

On the deployed page, scroll to **kkAgentic Support intake** and check:
- [ ] Page loads; the marketing section shows; the old preview chat is hidden.
- [ ] Status line shows **✅ Assistant online** and **✅ Google Drive configured**.
- [ ] Chat: type a name/company/project/code — the assistant collects them; the
      "Details collected" panel fills in.
- [ ] Click **Save my details to support** → confirms saved as
      `<name> and <project>.txt`; the file appears in your Drive folder.
- [ ] Say "I'm an STL member" + give name & project → record saves as
      `STL member request.txt`.
- [ ] Upload a screenshot / `client request.txt` → confirms upload; appears in Drive.

If the status line shows ⚠️ for either, re-check the matching secret in Step C.

---

## What this 1st step delivers vs. what's deferred
- **Delivered:** public intro page, live LLM chat intake following your script,
  Name/Company/Project/Code capture, STL branch, record + file uploads to Drive.
- **Deferred (next milestone):** answer-from-docs RAG (Supabase + pgvector),
  Telegram + FastAPI channels, conversation analytics.
