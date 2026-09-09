import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.logging import get_logger
from core.rate_limit import limiter
from core.db import get_db
from core.models import Optimization
from features.resume import source as rs
from features.optimizer.workflow import run_optimizer

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["optimizer"])


class OptimizeRequest(BaseModel):
    # Resume is optional: falls back to the current session resume.
    resume: str | None = Field(default=None, description="Resume text (optional)")
    jd: str = Field(..., min_length=1, description="Full job description text")
    title: str | None = Field(default=None, description="Label for the saved result")
    save: bool = Field(default=True, description="Persist the result")


class OptimizeResponse(BaseModel):
    id: int | None = None
    saved: bool
    title: str
    ats_score: float
    iterations: int
    matched_keywords: list[str]
    unmatched_keywords: list[str]
    jd_keywords: list[str]
    resume_keywords: list[str]
    updated_resume: str
    original_resume: str
    jd: str


class OptimizationSummary(BaseModel):
    id: int
    title: str
    ats_score: float
    iterations: int
    created_at: str | None


def _derive_title(jd: str) -> str:
    """Best-effort title from the JD's first non-empty line."""
    for line in jd.splitlines():
        line = line.strip()
        if line:
            return line[:80]
    return "Untitled optimization"


@router.post("/optimize", response_model=OptimizeResponse)
@limiter.limit(settings.rate_limit_optimize)
async def optimize(request: Request, payload: OptimizeRequest, db: Session = Depends(get_db)):
    resume = (payload.resume or rs.get_current_resume() or "").strip()
    jd = payload.jd.strip()

    if not resume:
        raise HTTPException(
            status_code=422,
            detail="No resume provided and no session resume is set. Upload or paste a resume first.",
        )
    if not jd:
        raise HTTPException(status_code=422, detail="Job description is required.")
    if len(resume) > settings.max_resume_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Resume too long (max {settings.max_resume_chars} characters).",
        )
    if len(jd) > settings.max_jd_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Job description too long (max {settings.max_jd_chars} characters).",
        )

    thread_id = f"api-{uuid.uuid4()}"
    logger.info(
        "Optimize request (resume=%d chars, jd=%d chars, save=%s, thread=%s)",
        len(resume), len(jd), payload.save, thread_id,
    )

    try:
        result = await asyncio.wait_for(
            run_optimizer(resume, jd, thread_id=thread_id),
            timeout=settings.optimizer_timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("Optimizer timed out after %ss", settings.optimizer_timeout_seconds)
        raise HTTPException(
            status_code=504,
            detail="Optimization timed out. Please try again with shorter input.",
        )
    except RuntimeError as exc:
        logger.error("Optimizer configuration error: %s", exc)
        raise HTTPException(status_code=503, detail="Service is not configured correctly.")
    except Exception:
        logger.exception("Optimizer failed")
        raise HTTPException(status_code=502, detail="Optimization failed upstream.")

    title = (payload.title or "").strip() or _derive_title(jd)
    saved_id: int | None = None

    if payload.save:
        try:
            record = Optimization(
                title=title,
                jd=jd,
                original_resume=resume,
                optimized_resume=result.get("updated_resume", ""),
                ats_score=result.get("ats_score", 0),
                iterations=result.get("iterations", 0),
                matched_keywords=result.get("matched_keywords", []),
                unmatched_keywords=result.get("unmatched_keywords", []),
                jd_keywords=result.get("jd_keywords", []),
                resume_keywords=result.get("resume_keywords", []),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            saved_id = record.id
            logger.info("Saved optimization id=%s", saved_id)
        except Exception:
            db.rollback()
            logger.exception("Failed to save optimization (returning result anyway)")

    return OptimizeResponse(
        id=saved_id,
        saved=saved_id is not None,
        title=title,
        original_resume=resume,
        jd=jd,
        **result,
    )


@router.get("/optimizations", response_model=list[OptimizationSummary])
def list_optimizations(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Optimization).order_by(Optimization.created_at.desc())
    ).all()
    return [row.summary() for row in rows]


@router.get("/optimizations/{opt_id}")
def get_optimization(opt_id: int, db: Session = Depends(get_db)):
    row = db.get(Optimization, opt_id)
    if not row:
        raise HTTPException(status_code=404, detail="Optimization not found.")
    return row.detail()


@router.delete("/optimizations/{opt_id}", status_code=204)
def delete_optimization(opt_id: int, db: Session = Depends(get_db)):
    row = db.get(Optimization, opt_id)
    if not row:
        raise HTTPException(status_code=404, detail="Optimization not found.")
    db.delete(row)
    db.commit()
    return None
