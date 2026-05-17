"""Content-policy and allowlist discipline checks (Phase 0 sign-off)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def check_content_policy_checklist(phases_root: Path) -> dict[str, Any]:
    path = phases_root / "foundations" / "content-policy-checklist.md"
    if not path.is_file():
        return {"ok": False, "error": f"missing {path}"}
    text = path.read_text(encoding="utf-8")
    core = ("## A.", "## B.", "## C.", "## D.", "## E.")
    core_ok = all(marker in text for marker in core)
    disclaimer_ok = "Facts-only. No investment advice." in text
    return {
        "ok": core_ok and disclaimer_ok,
        "path": str(path),
        "core_sections_ok": core_ok,
        "disclaimer_in_checklist": disclaimer_ok,
    }


def check_allowlist_five_urls(phases_root: Path) -> dict[str, Any]:
    path = phases_root / "foundations" / "allowlist.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    urls = data.get("urls") or []
    count = len(urls)
    groww = [
        u
        for u in urls
        if "groww.in/mutual-funds/" in str(u.get("url", ""))
    ]
    return {
        "ok": count == 5 and len(groww) == 5,
        "url_count": count,
        "groww_scheme_urls": len(groww),
    }
