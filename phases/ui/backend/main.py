"""
Phase 4 optional REST API — Thin HTTP wrapper around Phase 3 AnswerEngine.

Primary UI is Streamlit: ``phases/ui/app.py`` (``./phases/ui/scripts/run_app.sh``).
This module also serves the legacy static UI at ``/`` for local API testing.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Optional

# Resolve Phase 3 / 2 / 1 packages before importing answer engine code.
_PHASES_ROOT = Path(__file__).resolve().parents[2]
for _subdir in ("corpus", "index", "answer_engine"):
    _p = str(_PHASES_ROOT / _subdir)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ms02_answer.engine import AnswerEngine
from ms02_answer.models import AnswerResult

try:
    from ms02_hardening.logging_policy import sanitize_for_log
except ImportError:

    def sanitize_for_log(text: str, *, max_len: int = 200) -> str:  # type: ignore[misc]
        s = (text or "").strip()
        return s[:max_len] + ("..." if len(s) > max_len else "")


_LOGGER = logging.getLogger("ms02_api")

_BACKEND_DIR = Path(__file__).resolve().parent
_DEFAULT_FRONTEND_DIR = _BACKEND_DIR.parent / "frontend"


class AskBody(BaseModel):
    """Inbound question only — no auth or PII fields."""

    question: str = Field(..., min_length=1, max_length=2000)
    model_config = ConfigDict(extra="ignore")

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("question cannot be blank")
        return s


class AskResponse(BaseModel):
    answer: str
    source_url: Optional[str] = None
    last_updated: Optional[str] = None
    route: str


def _resolve_hf_home() -> Path:
    explicit = os.environ.get("HF_HOME", "").strip()
    if explicit:
        return Path(explicit)
    return _PHASES_ROOT / "index" / ".cache" / "huggingface"


def _cors_allow_origins() -> List[str]:
    raw = os.environ.get("MS02_API_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [x.strip() for x in raw.split(",") if x.strip()]


def get_answer_engine(request: Request) -> AnswerEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        err = getattr(request.app.state, "startup_error", None)
        detail = (
            err
            if err
            else "Answer engine is not available. Ensure Phase 2 index is built (run_index_build.sh)."
        )
        raise HTTPException(status_code=503, detail=detail)
    return engine


def _result_to_response(result: AnswerResult) -> AskResponse:
    return AskResponse(
        answer=result.answer,
        source_url=result.source_url,
        last_updated=result.last_updated,
        route=result.route,
    )


def _attach_frontend(application: FastAPI, *, frontend_dir: Optional[Path] = None) -> None:
    root = frontend_dir if frontend_dir is not None else _DEFAULT_FRONTEND_DIR
    static_dir = root / "static"
    index_path = root / "index.html"

    if static_dir.is_dir():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    if index_path.is_file():

        @application.get("/", include_in_schema=False)
        def serve_index() -> FileResponse:
            return FileResponse(index_path, media_type="text/html")


def create_app(
    *,
    answer_engine: Optional[AnswerEngine] = None,
    frontend_dir: Optional[Path] = None,
) -> FastAPI:
    """Build FastAPI app. Tests may pass ``answer_engine`` to skip real index load."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        hf = _resolve_hf_home()
        os.environ.setdefault("HF_HOME", str(hf))

        app.state.engine = None  # type: ignore[attr-defined]
        app.state.startup_error = None  # type: ignore[attr-defined]
        try:
            if answer_engine is not None:
                app.state.engine = answer_engine
                _LOGGER.info("Using injected AnswerEngine.")
            else:
                app.state.engine = AnswerEngine()
                _LOGGER.info("AnswerEngine started.")
        except Exception as e:
            app.state.engine = None
            app.state.startup_error = str(e)
            _LOGGER.exception("AnswerEngine failed to start: %s", e)
            # Allow process to boot so /health and OpenAPI respond; POST /api/ask returns 503.
        yield

    application = FastAPI(
        title="MS02 Mutual Fund FAQ API",
        description="Facts-only Phase 4 API (phased-architecture.md). No PII fields.",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(),
        allow_credentials=False,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )

    _attach_frontend(application, frontend_dir=frontend_dir)

    @application.get("/health")
    def health(request: Request) -> dict:
        eng = getattr(request.app.state, "engine", None)
        return {
            "status": "ok" if eng is not None else "degraded",
            "startup_error": getattr(request.app.state, "startup_error", None),
        }

    @application.post("/api/ask", response_model=AskResponse)
    def ask(
        body: AskBody,
        engine: AnswerEngine = Depends(get_answer_engine),
    ) -> AskResponse:
        result = engine.ask(body.question)
        _LOGGER.debug(
            "ask route=%s has_source=%s q_len=%d q_preview=%s",
            result.route,
            bool(result.source_url),
            len(body.question),
            sanitize_for_log(body.question),
        )
        return _result_to_response(result)

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("MS02_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("MS02_API_PORT", "8000")),
    )
