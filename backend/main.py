"""Resume Toolkit backend entrypoint.

Mounts each feature's router under one FastAPI app. Run from the backend/ dir:

    uvicorn main:app --reload --port 8000
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.config import get_settings
from core.logging import configure_logging, get_logger, request_id_var
from core.rate_limit import limiter
from features.chatbot.router import router as chatbot_router
from features.optimizer.router import router as optimizer_router
from features.resume.router import router as resume_router

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on obvious misconfiguration.
    if not settings.google_api_key:
        logger.error("GOOGLE_API_KEY is not set — AI features will fail.")
    else:
        logger.info(
            "Starting Resume Toolkit API (env=%s, chat_model=%s, optimizer_model=%s)",
            settings.environment,
            settings.chat_model,
            settings.optimizer_model,
        )

    # Initialize the database schema (non-fatal if the DB is unavailable so the
    # health endpoint still works and the error is visible in logs).
    try:
        from core.db import init_db

        init_db()
    except Exception:
        logger.exception("Database initialization failed")

    yield
    logger.info("Shutting down Resume Toolkit API")


app = FastAPI(title="Resume Toolkit API", lifespan=lifespan)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request id, log the request, and set security headers."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/health", tags=["ops"])
def health():
    """Liveness: the process is up."""
    return {"status": "ok", "service": "resume-toolkit"}


@app.get("/ready", tags=["ops"])
def ready():
    """Readiness: required config is present."""
    if not settings.google_api_key:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "GOOGLE_API_KEY not set"},
        )
    return {"status": "ready"}


@app.get("/", tags=["ops"])
def root():
    return {"status": "ok", "service": "resume-toolkit"}


app.include_router(chatbot_router)
app.include_router(optimizer_router)
app.include_router(resume_router)
