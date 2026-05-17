"""Verify normalized corpus exists for all allowlisted schemes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ms02_corpus.p1_1_registry.registry import load_registry


def check_corpus_spot(
    *,
    normalized_root: Path,
    allowlist_path: Path,
    expected_schemes: int = 5,
) -> dict[str, Any]:
    registry = load_registry(allowlist_path)
    if len(registry.schemes) != expected_schemes:
        return {
            "ok": False,
            "error": f"allowlist has {len(registry.schemes)} schemes, expected {expected_schemes}",
            "schemes": [],
        }

    schemes: list[dict[str, Any]] = []
    all_ok = True
    for entry in registry.schemes:
        page = normalized_root / entry.id / "page.md"
        manifest = normalized_root / entry.id / "manifest.json"
        row: dict[str, Any] = {
            "scheme_id": entry.id,
            "page_md": str(page),
            "page_exists": page.is_file() and page.stat().st_size > 0,
            "manifest_exists": manifest.is_file(),
            "manifest_ok": None,
        }
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            row["manifest_ok"] = bool(data.get("ok"))
            row["raw_fetched_at"] = data.get("raw_fetched_at")
        scheme_ok = (
            row["page_exists"]
            and row["manifest_exists"]
            and row["manifest_ok"] is True
        )
        row["ok"] = scheme_ok
        if not scheme_ok:
            all_ok = False
        schemes.append(row)

    return {
        "ok": all_ok,
        "normalized_root": str(normalized_root.resolve()),
        "scheme_count": len(schemes),
        "schemes": schemes,
    }


def default_normalized_root(phases_root: Path) -> Path:
    return phases_root / "corpus" / "normalized"
