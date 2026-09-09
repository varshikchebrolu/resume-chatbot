"""Resume source: parse uploaded files and hold the current resume.

Single-user app. The "current resume" is persisted in Postgres (app_state table)
so it survives restarts. It starts from the default file (data/resume.txt) and can
be replaced by an upload or pasted text. An in-memory cache avoids a DB read on
every request; it's invalidated whenever the resume changes.
"""
import io
import os

from sqlalchemy import delete, select

from core.config import DATA_DIR, get_settings
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

DEFAULT_RESUME_PATH = os.path.join(DATA_DIR, "resume.txt")
_RESUME_KEY = "current_resume"

# Sentinel: cache not yet loaded. None means "no custom resume set".
_UNSET = object()
_cache = _UNSET  # type: ignore[assignment]


class UnsupportedFileType(ValueError):
    pass


def parse_upload(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded resume file (PDF / DOCX / TXT)."""
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    elif name.endswith(".docx"):
        import docx2txt

        text = docx2txt.process(io.BytesIO(data)) or ""
    elif name.endswith(".txt") or name.endswith(".md"):
        text = data.decode("utf-8", errors="replace")
    else:
        raise UnsupportedFileType(
            "Unsupported file type. Upload a PDF, DOCX, TXT, or MD file."
        )

    text = text.strip()
    if not text:
        raise ValueError("Could not extract any text from the file.")
    return text


def _load_from_db() -> str | None:
    """Read the persisted current resume from the DB, or None if unset/unavailable."""
    from core.db import get_sessionmaker
    from core.models import AppState

    try:
        with get_sessionmaker()() as session:
            row = session.scalar(select(AppState).where(AppState.key == _RESUME_KEY))
            return row.value if row else None
    except Exception:
        logger.exception("Could not read current resume from DB")
        return None


def _ensure_cache() -> None:
    global _cache
    if _cache is _UNSET:
        _cache = _load_from_db()


def set_current_resume(text: str) -> str:
    """Set the current resume from raw text, persisting it. Returns the stored text."""
    global _cache
    text = (text or "").strip()
    if not text:
        raise ValueError("Resume text is empty.")
    if len(text) > settings.max_resume_chars:
        raise ValueError(
            f"Resume too long (max {settings.max_resume_chars} characters)."
        )

    from core.db import get_sessionmaker
    from core.models import AppState

    with get_sessionmaker()() as session:
        row = session.get(AppState, _RESUME_KEY)
        if row:
            row.value = text
        else:
            session.add(AppState(key=_RESUME_KEY, value=text))
        session.commit()

    _cache = text
    logger.info("Current resume set and persisted (%d chars)", len(text))
    return _cache


def clear_current_resume() -> None:
    """Remove the persisted current resume; revert to the default file."""
    global _cache
    from core.db import get_sessionmaker
    from core.models import AppState

    with get_sessionmaker()() as session:
        session.execute(delete(AppState).where(AppState.key == _RESUME_KEY))
        session.commit()

    _cache = None
    logger.info("Current resume cleared; using default file")


def get_current_resume() -> str:
    """Return the current resume, or the default file if none is set."""
    _ensure_cache()
    if _cache:
        return _cache
    if os.path.exists(DEFAULT_RESUME_PATH):
        with open(DEFAULT_RESUME_PATH) as f:
            return f.read().strip()
    return ""


def has_custom_resume() -> bool:
    _ensure_cache()
    return bool(_cache)
