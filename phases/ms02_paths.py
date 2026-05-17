"""
Canonical repository layout paths (Phase folders).

Import from pipeline code instead of hard-coding ``corpus``-style names.
"""

from __future__ import annotations

from pathlib import Path

PHASES_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PHASES_ROOT.parent

FOUNDATIONS_DIR = PHASES_ROOT / "foundations"
CORPUS_DIR = PHASES_ROOT / "corpus"
INDEX_DIR = PHASES_ROOT / "index"
ANSWER_ENGINE_DIR = PHASES_ROOT / "answer_engine"
UI_DIR = PHASES_ROOT / "ui"
QUALITY_DIR = PHASES_ROOT / "quality"
DOCS_DIR = REPO_ROOT / "docs"
EDGE_CASES_DOCS_DIR = DOCS_DIR / "edge-cases"

ALLOWLIST_PATH = FOUNDATIONS_DIR / "allowlist.yaml"
VALIDATE_ALLOWLIST_SH = FOUNDATIONS_DIR / "validate_allowlist.sh"
RED_TEAM_QUERIES_PATH = FOUNDATIONS_DIR / "red-team-queries.yaml"

CORPUS_RAW_DIR = CORPUS_DIR / "raw"
CORPUS_INTERMEDIATE_DIR = CORPUS_DIR / "intermediate"
CORPUS_NORMALIZED_DIR = CORPUS_DIR / "normalized"

INDEX_CHUNKS_DIR = INDEX_DIR / "chunks"
INDEX_EMBEDDINGS_DIR = INDEX_DIR / "embeddings"
INDEX_VECTOR_STORE_DIR = INDEX_DIR / "vector_store"
HF_CACHE_DIR = INDEX_DIR / ".cache" / "huggingface"

STREAMLIT_APP_PATH = UI_DIR / "app.py"
FRONTEND_DIR = UI_DIR / "frontend"
FRONTEND_INDEX_PATH = FRONTEND_DIR / "index.html"
DISCLAIMER_DIR = QUALITY_DIR / "disclaimer"
