"""SQLAlchemy models for the Resume Toolkit."""
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class AppState(Base):
    """Simple key/value store for small pieces of persisted app state
    (e.g. the current session resume)."""

    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Optimization(Base):
    """A saved optimizer run: an optimized resume for a specific JD."""

    __tablename__ = "optimizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled optimization")

    jd: Mapped[str] = mapped_column(Text)
    original_resume: Mapped[str] = mapped_column(Text)
    optimized_resume: Mapped[str] = mapped_column(Text)

    ats_score: Mapped[float] = mapped_column(Float, default=0)
    iterations: Mapped[int] = mapped_column(Integer, default=0)

    matched_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    unmatched_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    jd_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    resume_keywords: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def summary(self) -> dict:
        """Lightweight representation for list views."""
        return {
            "id": self.id,
            "title": self.title,
            "ats_score": self.ats_score,
            "iterations": self.iterations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def detail(self) -> dict:
        return {
            **self.summary(),
            "jd": self.jd,
            "original_resume": self.original_resume,
            "optimized_resume": self.optimized_resume,
            "matched_keywords": self.matched_keywords or [],
            "unmatched_keywords": self.unmatched_keywords or [],
            "jd_keywords": self.jd_keywords or [],
            "resume_keywords": self.resume_keywords or [],
        }
