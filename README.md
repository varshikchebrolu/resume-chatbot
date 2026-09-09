# resume-toolkit

A collection of resume tools backed by a FastAPI service and a Next.js frontend.

## Features

- **Advisor chatbot** — chat grounded in your resume and (optionally) a target job
  description. Ask about fit, gaps, weak spots, and what to build/learn for a specific
  role. Uses RAG over your resume plus the JD you attach.
- **Optimizer** — optimize a resume against a JD (keyword match, ATS scoring, iterative
  rewrite). Each run is **saved to Postgres** so you can revisit past optimized resumes.
- **Resume source** — use the default resume file, paste text, or upload a PDF/DOCX/TXT.
  The current resume is shared by both the chat and the optimizer, and is persisted in
  Postgres so it survives restarts.

## Layout

```
resume-toolkit/
  backend/
    main.py            FastAPI app: CORS, logging, rate limiting, health/ready
    config.py          env-driven settings (pydantic-settings)
    logging_config.py  structured logging + request IDs
    db.py, models.py   SQLAlchemy engine + Optimization model (Postgres)
    resume_source.py   parse uploads, hold current session resume
    resume_api.py      /resume endpoints
    chatbot/           advisor chat (app.py) + RAG (rag_pipeline.py)
    optimizer/         resume_optimizer.py (LangGraph) + api.py (endpoints)
    data/              default resume.txt / jd.txt
  frontend/            Next.js UI (chat, optimizer, saved optimizations)
```

## Prerequisites

- Python 3.13+, Node 18+
- PostgreSQL running locally. Create the database once:

  ```bash
  createdb resume_toolkit
  ```

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
cp .env.example .env        # set GOOGLE_API_KEY and DATABASE_URL
uvicorn main:app --reload --port 8000
```

Tables are created automatically on startup.

Key env vars (`backend/.env`):
- `GOOGLE_API_KEY` — Google AI Studio key (required).
- `DATABASE_URL` — e.g. `postgresql+psycopg://USER:PASS@localhost:5432/resume_toolkit`.
- Optional: `CHAT_MODEL`, `OPTIMIZER_MODEL`, `CORS_ORIGINS`, `ACCEPTABLE_ATS_SCORE`,
  `MAX_ITERATIONS`, `OPTIMIZER_TIMEOUT_SECONDS`, rate limits — see `.env.example`.

### Endpoints

Ops:
- `GET /health` — liveness · `GET /ready` — readiness (checks config)

Resume source:
- `GET /resume` — current resume status (custom vs default, length, preview)
- `POST /resume/text` — set resume from `{ resume }`
- `POST /resume/upload` — upload a PDF/DOCX/TXT/MD file
- `DELETE /resume` — revert to the default resume file

Chatbot:
- `POST /getAIResponse` — streaming chat. Body: `{ messages, jd?, resume? }`.
  If `jd` is provided, answers focus on fit/gaps for that role.

Optimizer:
- `POST /optimize` — Body: `{ jd, resume?, title?, save? }`. `resume` defaults to the
  current session resume. Returns the result and (if `save`) its saved `id`.
- `GET /optimizations` — list saved optimizations
- `GET /optimizations/{id}` — full detail (JD, original + optimized resume, keywords)
- `DELETE /optimizations/{id}` — delete one

### Optimizer CLI (standalone)

```bash
cd backend
python -m optimizer.resume_optimizer      # reads data/resume.txt + data/jd.txt
```

## Frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:3000
```

Routes: `/` (home), `/chat` (advisor chat), `/optimize` (run + save),
`/optimize/saved` (list), `/optimize/saved/[id]` (detail).

Optional `frontend/.env.local`:
- `NEXT_PUBLIC_API_BASE_URL` — backend base URL. Defaults to `http://localhost:8000`.

## Notes

- The optimizer runs several sequential AI passes, so a request can take a minute or two.
- Pure learning experiments unrelated to the toolkit live in `../Notebooks/`.
