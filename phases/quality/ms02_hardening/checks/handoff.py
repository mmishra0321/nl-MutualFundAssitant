"""Handoff artifacts: disclaimer snippet, UI disclaimer presence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DISCLAIMER_TEXT = "Facts-only. No investment advice."

EDGE_CASE_DOC_NAMES = tuple(
    f"edge-cases-phase-{i}.md" for i in range(6)
)


def check_disclaimer_artifacts(hardening_root: Path) -> dict[str, Any]:
    txt = hardening_root / "disclaimer" / "disclaimer.txt"
    html = hardening_root / "disclaimer" / "disclaimer.html"
    errors: list[str] = []
    if not txt.is_file():
        errors.append(f"missing {txt}")
    elif DISCLAIMER_TEXT not in txt.read_text(encoding="utf-8"):
        errors.append("disclaimer.txt text mismatch")
    if not html.is_file():
        errors.append(f"missing {html}")
    elif DISCLAIMER_TEXT not in html.read_text(encoding="utf-8"):
        errors.append("disclaimer.html text mismatch")
    return {"ok": not errors, "errors": errors}


def check_streamlit_disclaimer(phases_root: Path) -> dict[str, Any]:
    app_py = phases_root / "ui" / "app.py"
    if not app_py.is_file():
        return {"ok": False, "error": f"missing {app_py}"}
    body = app_py.read_text(encoding="utf-8")
    ok = DISCLAIMER_TEXT in body
    return {"ok": ok, "app_py": str(app_py)}


def check_frontend_disclaimer(phases_root: Path) -> dict[str, Any]:
    index_html = phases_root / "ui" / "frontend" / "index.html"
    if not index_html.is_file():
        return {"ok": False, "error": f"missing {index_html}"}
    body = index_html.read_text(encoding="utf-8")
    ok = DISCLAIMER_TEXT in body
    return {"ok": ok, "index_html": str(index_html)}


def check_root_readme(repo_root: Path) -> dict[str, Any]:
    readme = repo_root / "README.md"
    if not readme.is_file():
        return {"ok": False, "error": "missing README.md at repo root"}
    text = readme.read_text(encoding="utf-8").lower()
    required = ("hdfc", "rag", "limitations", "facts-only", "streamlit")
    missing = [k for k in required if k not in text]
    return {"ok": not missing, "missing_keywords": missing}


def check_edge_case_docs(repo_root: Path) -> dict[str, Any]:
    docs_dir = repo_root / "docs" / "edge-cases"
    missing = [name for name in EDGE_CASE_DOC_NAMES if not (docs_dir / name).is_file()]
    return {
        "ok": not missing,
        "docs_dir": str(docs_dir),
        "expected": list(EDGE_CASE_DOC_NAMES),
        "missing": missing,
    }
