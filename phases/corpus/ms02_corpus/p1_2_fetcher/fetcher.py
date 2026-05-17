"""
Phase 1.2 — Raw fetcher (phased-architecture.md).

GET only allowlisted scheme URLs; validate redirects stay on-policy;
write raw HTML + manifest under phases/corpus/raw/.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse, urlunparse

import requests

from ms02_corpus.p1_1_registry.registry import Registry, SchemeEntry, load_registry

DEFAULT_TIMEOUT_S = 45
MAX_ATTEMPTS = 4
BACKOFF_BASE_S = 1.0
USER_AGENT = (
    "MS02CorpusFetcher/1.2 (educational mutual-fund FAQ corpus; local MS02 project)"
)
ALLOWED_HOSTS = frozenset({"groww.in", "www.groww.in"})


class FetcherError(RuntimeError):
    """HTTP, redirect policy, or allowlist violation during fetch."""


@dataclass(frozen=True)
class FetchManifest:
    scheme_id: str
    scheme_name: str
    source_url: str
    final_url: str
    fetched_at: str  # ISO8601 UTC
    http_status: int | None
    ok: bool
    error: str | None
    content_type: str | None
    content_sha256: str | None
    size_bytes: int | None
    etag: str | None
    attempts: int


def _default_raw_dir() -> Path:
    # fetcher.py -> p1_2_fetcher -> ms02_corpus -> corpus
    return Path(__file__).resolve().parents[2] / "raw"


def _canonical_groww_page_url(url: str) -> str:
    """
    Normalize final URL to compare with allowlist: https + groww.in + path, no query/fragment.
    Accepts www.groww.in as equivalent host.
    """
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise FetcherError(f"Redirect left allowed hosts (got host {host!r}).")
    if host == "www.groww.in":
        host = "groww.in"
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if parsed.query or parsed.fragment:
        raise FetcherError("Final URL must not include query or fragment for this closed allowlist.")
    return urlunparse(("https", host, path, "", "", ""))


def _validate_final_url(entry: SchemeEntry, final_url: str, allowlist_urls: frozenset[str]) -> str:
    canonical = _canonical_groww_page_url(final_url)
    if canonical != entry.url:
        raise FetcherError(
            f"After redirects, URL {canonical!r} must match this scheme's allowlist URL {entry.url!r}."
        )
    if canonical not in allowlist_urls:
        raise FetcherError(f"Final URL {canonical!r} is not in the closed allowlist.")
    return canonical


def _should_retry_status(status: int | None) -> bool:
    if status is None:
        return True
    return status in (408, 429, 500, 502, 503, 504)


def fetch_scheme_raw(
    entry: SchemeEntry,
    *,
    allowlist_urls: frozenset[str],
    session: requests.Session,
    raw_root: Path,
) -> FetchManifest:
    """
    GET one scheme page; write raw/<scheme_id>/latest.html and manifest.json on success.
    On failure, writes manifest with ok=false and error message (no HTML body).
    """
    out_dir = raw_root / entry.id
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "latest.html"
    manifest_path = out_dir / "manifest.json"

    attempts = 0
    last_error: str | None = None
    final_status: int | None = None
    final_url_effective: str = entry.url
    body: bytes | None = None
    ctype: str | None = None
    etag: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempts = attempt
        try:
            resp = session.get(
                entry.url,
                timeout=DEFAULT_TIMEOUT_S,
                allow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
            )
            final_status = resp.status_code
            final_url_effective = resp.url
            ctype = resp.headers.get("Content-Type")
            etag = resp.headers.get("ETag")

            _validate_final_url(entry, final_url_effective, allowlist_urls)

            if final_status >= 400:
                raise FetcherError(f"HTTP {final_status}")

            if ctype and "pdf" in ctype.lower():
                raise FetcherError("PDF response not allowed (no PDF branch).")

            body = resp.content
            if not body:
                raise FetcherError("Empty response body.")

            fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            digest = hashlib.sha256(body).hexdigest()

            html_path.write_bytes(body)

            manifest = FetchManifest(
                scheme_id=entry.id,
                scheme_name=entry.scheme_name,
                source_url=entry.url,
                final_url=_canonical_groww_page_url(final_url_effective),
                fetched_at=fetched_at,
                http_status=final_status,
                ok=True,
                error=None,
                content_type=ctype,
                content_sha256=digest,
                size_bytes=len(body),
                etag=etag,
                attempts=attempts,
            )
            manifest_path.write_text(
                json.dumps(_manifest_to_jsonable(manifest), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return manifest

        except (requests.RequestException, FetcherError, ValueError) as exc:
            last_error = str(exc)
            if attempt < MAX_ATTEMPTS and _should_retry_status(
                getattr(getattr(exc, "response", None), "status_code", None) or final_status
            ):
                time.sleep(BACKOFF_BASE_S * (2 ** (attempt - 1)))
                continue
            break

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    manifest = FetchManifest(
        scheme_id=entry.id,
        scheme_name=entry.scheme_name,
        source_url=entry.url,
        final_url=entry.url,
        fetched_at=fetched_at,
        http_status=final_status,
        ok=False,
        error=last_error or "Unknown fetch error",
        content_type=ctype,
        content_sha256=None,
        size_bytes=None,
        etag=etag,
        attempts=attempts,
    )
    manifest_path.write_text(
        json.dumps(_manifest_to_jsonable(manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if html_path.exists():
        html_path.unlink()
    return manifest


def _manifest_to_jsonable(m: FetchManifest) -> dict[str, Any]:
    d = asdict(m)
    return d


def fetch_all(
    registry: Registry,
    raw_root: Path | None = None,
    *,
    delay_between_schemes_s: float = 0.75,
) -> list[FetchManifest]:
    """
    GET each scheme in registry order. Only registry URLs are requested.
    """
    root = raw_root or _default_raw_dir()
    root.mkdir(parents=True, exist_ok=True)
    allow = registry.url_set()
    session = requests.Session()
    results: list[FetchManifest] = []
    for i, entry in enumerate(registry.schemes):
        if i:
            time.sleep(delay_between_schemes_s)
        results.append(
            fetch_scheme_raw(entry, allowlist_urls=allow, session=session, raw_root=root)
        )
    session.close()
    return results


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    raw_dir: Path | None = None
    if argv and not argv[0].startswith("-"):
        raw_dir = Path(argv[0]).resolve()
        rest = argv[1:]
    else:
        rest = argv
    # minimal CLI: optional raw dir as first arg
    _ = rest  # reserved for --allowlist etc.

    reg = load_registry()
    root = raw_dir or _default_raw_dir()
    manifests = fetch_all(reg, raw_root=root)
    summary = {"raw_root": str(root), "results": [_manifest_to_jsonable(m) for m in manifests]}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not all(m.ok for m in manifests):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
