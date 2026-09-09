import hashlib
from functools import lru_cache

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

from core.config import get_settings
from core.logging import get_logger
from core.rate_limit import limiter
from features.resume import source as rs
from features.chatbot import rag

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["chatbot"])


@lru_cache
def _get_client() -> genai.Client:
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
        )
    return genai.Client(api_key=settings.google_api_key)


@lru_cache(maxsize=8)
def _index_for(resume_hash: str, resume_text: str):
    """Chunk + embed a resume once, cached by content hash so a changed
    session resume gets a fresh index."""
    chunks = rag.loadAndChunkText(resume_text, max_chunk_size=100)
    embeddings = rag.embedChunks(chunks)
    logger.info("Built resume index (%d chunks, hash=%s)", len(chunks), resume_hash[:8])
    return chunks, embeddings


def _resume_index(resume_text: str):
    resume_hash = hashlib.sha256(resume_text.encode("utf-8")).hexdigest()
    return _index_for(resume_hash, resume_text)


ADVISOR_SYSTEM = """You are a candid, experienced career advisor and technical resume coach.
You are given the candidate's RESUME context (retrieved snippets) and, optionally, a target JOB DESCRIPTION.

Answer the user's question using ONLY the resume context and the job description provided.
- If a job description is present, focus on fit: strengths, gaps, missing skills/keywords, and
  concrete suggestions (what to learn, build, or highlight) to become a stronger candidate.
- Be specific and honest about weaknesses; do not invent experience the resume doesn't show.
- If the resume context doesn't contain the answer, say you don't have that information.
- Keep answers practical and concise."""


def _extract_text(msg: dict) -> str:
    return "".join(
        part.get("text", "")
        for part in msg.get("parts", [])
        if part.get("type") == "text"
    )


def build_context_prompt(query: str, resume_text: str, jd_text: str | None) -> str:
    chunks, embeddings = _resume_index(resume_text)
    results = rag.findClosestChunks(
        query, chunks, embeddings, top_n=5, similarity_threshold=0.40
    )
    resume_context = "\n\n".join(chunk for _score, chunk in results)

    parts = [ADVISOR_SYSTEM, "\n\nRESUME CONTEXT:\n" + (resume_context or "(none)")]
    if jd_text:
        parts.append("\n\nTARGET JOB DESCRIPTION:\n" + jd_text)
    return "\n".join(parts)


async def generate_ai_stream(messages: list, resume_text: str, jd_text: str | None):
    query_text = _extract_text(messages[-1])
    system_prompt = build_context_prompt(query_text, resume_text, jd_text)

    contents = [types.Content(role="model", parts=[types.Part(text=system_prompt)])]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        text = _extract_text(msg)
        if text:
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))

    try:
        response = _get_client().models.generate_content_stream(
            model=settings.chat_model, contents=contents
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception:
        logger.exception("Chat generation failed")
        yield "\n[The assistant hit an error generating a response. Please try again.]"


@router.post("/getAIResponse")
@limiter.limit(settings.rate_limit_chat)
async def get_ai_response(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    # Optional per-request context passed by the frontend.
    jd_text = (body.get("jd") or "").strip() or None
    resume_override = (body.get("resume") or "").strip()

    if not messages:
        raise HTTPException(status_code=422, detail="No messages provided.")

    query_text = _extract_text(messages[-1])
    if not query_text.strip():
        raise HTTPException(status_code=422, detail="Empty message.")
    if len(query_text) > settings.max_chat_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Message too long (max {settings.max_chat_chars} characters).",
        )

    resume_text = resume_override or rs.get_current_resume()
    if not resume_text:
        raise HTTPException(
            status_code=422,
            detail="No resume available. Upload or paste a resume first.",
        )
    if jd_text and len(jd_text) > settings.max_jd_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Job description too long (max {settings.max_jd_chars} characters).",
        )

    return StreamingResponse(
        generate_ai_stream(messages, resume_text, jd_text),
        media_type="text/plain; charset=utf-8",
    )
