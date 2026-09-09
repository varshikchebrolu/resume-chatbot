"""Endpoints for managing the current session resume."""
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from core.logging import get_logger
from features.resume import source as rs

logger = get_logger(__name__)

router = APIRouter(tags=["resume"], prefix="/resume")

# Guard against oversized uploads (bytes) before parsing.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


class ResumeTextRequest(BaseModel):
    resume: str = Field(..., min_length=1, description="Resume text")


class ResumeStatus(BaseModel):
    has_custom_resume: bool
    length: int
    preview: str


def _status() -> ResumeStatus:
    text = rs.get_current_resume()
    return ResumeStatus(
        has_custom_resume=rs.has_custom_resume(),
        length=len(text),
        preview=text[:400],
    )


@router.get("", response_model=ResumeStatus)
def get_resume():
    return _status()


@router.post("/text", response_model=ResumeStatus)
def set_resume_text(payload: ResumeTextRequest):
    try:
        rs.set_current_resume(payload.resume)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _status()


@router.post("/upload", response_model=ResumeStatus)
async def upload_resume(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB).")

    try:
        text = rs.parse_upload(file.filename or "", data)
        rs.set_current_resume(text)
    except rs.UnsupportedFileType as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Failed to parse uploaded resume")
        raise HTTPException(status_code=400, detail="Could not read the uploaded file.")

    return _status()


@router.delete("", response_model=ResumeStatus)
def clear_resume():
    rs.clear_current_resume()
    return _status()
