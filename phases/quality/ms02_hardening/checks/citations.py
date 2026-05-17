"""Verify allowlisted citation URLs are reachable."""

from __future__ import annotations

from typing import Any

import requests

from ms02_corpus.p1_1_registry.registry import load_registry


def check_citation_urls(
    allowlist_path,
    *,
    timeout_sec: float = 20.0,
    skip_network: bool = False,
) -> dict[str, Any]:
    registry = load_registry(allowlist_path)
    if skip_network:
        return {
            "ok": True,
            "skipped": True,
            "results": [{"scheme_id": s.id, "url": s.url, "ok": True} for s in registry.schemes],
        }

    results: list[dict[str, Any]] = []
    all_ok = True
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "MS02-Phase5-CitationCheck/1.0 (+https://github.com; compliance QA)",
            "Accept": "text/html,application/xhtml+xml",
        }
    )
    for entry in registry.schemes:
        row: dict[str, Any] = {"scheme_id": entry.id, "url": entry.url, "ok": False}
        try:
            resp = session.get(entry.url, timeout=timeout_sec, allow_redirects=True)
            row["http_status"] = resp.status_code
            row["ok"] = 200 <= resp.status_code < 400
        except requests.RequestException as exc:
            row["error"] = str(exc)
            row["ok"] = False
        if not row["ok"]:
            all_ok = False
        results.append(row)

    return {"ok": all_ok, "skipped": False, "results": results}
