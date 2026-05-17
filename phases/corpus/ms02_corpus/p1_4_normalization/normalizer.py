"""
Phase 1.4 — Normalization (phased-architecture.md).

Reads Phase 1.3 `extracted.html`, converts to Markdown, verifies allowlisted
`source_url` and raw snapshot alignment, writes `normalized/<scheme_id>/`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from markdownify import markdownify as html_to_md

from ms02_corpus.p1_1_registry.registry import Registry, SchemeEntry, load_registry

DOC_TYPE = "groww_scheme_page"


@dataclass(frozen=True)
class NormalizeManifest:
    scheme_id: str
    scheme_name: str
    source_url: str
    doc_type: str
    raw_content_sha256: str
    raw_fetched_at: str
    intermediate_extracted_sha256: str
    intermediate_extracted_at: str
    normalized_at: str
    normalized_sha256: str
    normalized_size_bytes: int
    ok: bool
    error: str | None


def _default_intermediate_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "intermediate"


def _default_normalized_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "normalized"


def _default_raw_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "raw"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collapse_blank_lines(text: str) -> str:
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def html_fragment_to_markdown(html: str) -> str:
    """Turn cleaned HTML fragment into readable Markdown (no network)."""
    md = html_to_md(
        html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
    )
    return _collapse_blank_lines(md)


def normalize_scheme(
    entry: SchemeEntry,
    *,
    allowlist_urls: frozenset[str],
    intermediate_root: Path,
    normalized_root: Path,
    raw_root: Path | None = None,
) -> NormalizeManifest:
    inter_dir = intermediate_root / entry.id
    html_path = inter_dir / "extracted.html"
    inter_man_path = inter_dir / "manifest.json"
    out_dir = normalized_root / entry.id
    out_md = out_dir / "page.md"
    out_man = out_dir / "manifest.json"

    def _fail(msg: str) -> NormalizeManifest:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        m = NormalizeManifest(
            scheme_id=entry.id,
            scheme_name=entry.scheme_name,
            source_url=entry.url,
            doc_type=DOC_TYPE,
            raw_content_sha256="",
            raw_fetched_at="",
            intermediate_extracted_sha256="",
            intermediate_extracted_at="",
            normalized_at=ts,
            normalized_sha256="",
            normalized_size_bytes=0,
            ok=False,
            error=msg,
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_man.write_text(json.dumps(asdict(m), indent=2, ensure_ascii=False), encoding="utf-8")
        if out_md.exists():
            out_md.unlink()
        return m

    if not html_path.is_file() or not inter_man_path.is_file():
        return _fail(f"Missing intermediate snapshot under {inter_dir}")

    inter = _read_json(inter_man_path)
    if not inter.get("ok"):
        return _fail("Intermediate manifest ok=false; run Phase 1.3 first.")

    source_url = str(inter.get("source_url", ""))
    if source_url not in allowlist_urls:
        return _fail(f"source_url not in allowlist: {source_url!r}")
    if source_url != entry.url:
        return _fail(f"source_url mismatch for {entry.id}: {source_url!r} vs {entry.url!r}")

    raw_sha = str(inter.get("raw_content_sha256", ""))
    raw_fetched = str(inter.get("raw_fetched_at", ""))
    ex_sha_expected = str(inter.get("extracted_sha256", ""))
    ex_at = str(inter.get("extracted_at", ""))

    if not ex_sha_expected:
        return _fail("Intermediate manifest missing extracted_sha256")

    got_ex_sha = _sha256_file(html_path)
    if got_ex_sha != ex_sha_expected:
        return _fail(
            f"extracted.html sha256 mismatch: disk={got_ex_sha!r} manifest={ex_sha_expected!r}"
        )

    raw_r = raw_root or _default_raw_dir()
    raw_html = raw_r / entry.id / "latest.html"
    if raw_html.is_file():
        raw_disk = _sha256_file(raw_html)
        if raw_disk != raw_sha:
            return _fail(
                f"Raw snapshot no longer matches intermediate provenance: "
                f"disk={raw_disk!r} expected={raw_sha!r}"
            )
    else:
        return _fail(f"Missing raw snapshot for alignment check: {raw_html}")

    try:
        html = html_path.read_text(encoding="utf-8", errors="replace")
        md = html_fragment_to_markdown(html)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Normalization failed: {exc}")

    out_bytes = md.encode("utf-8")
    n_digest = _sha256_bytes(out_bytes)
    normalized_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_bytes(out_bytes)
    m = NormalizeManifest(
        scheme_id=entry.id,
        scheme_name=entry.scheme_name,
        source_url=source_url,
        doc_type=DOC_TYPE,
        raw_content_sha256=raw_sha,
        raw_fetched_at=raw_fetched,
        intermediate_extracted_sha256=ex_sha_expected,
        intermediate_extracted_at=ex_at,
        normalized_at=normalized_at,
        normalized_sha256=n_digest,
        normalized_size_bytes=len(out_bytes),
        ok=True,
        error=None,
    )
    out_man.write_text(json.dumps(asdict(m), indent=2, ensure_ascii=False), encoding="utf-8")
    return m


def normalize_all(
    registry: Registry,
    *,
    intermediate_root: Path | None = None,
    normalized_root: Path | None = None,
    raw_root: Path | None = None,
) -> list[NormalizeManifest]:
    allow = registry.url_set()
    inter = intermediate_root or _default_intermediate_dir()
    norm = normalized_root or _default_normalized_dir()
    raw_r = raw_root or _default_raw_dir()
    norm.mkdir(parents=True, exist_ok=True)
    return [
        normalize_scheme(
            e,
            allowlist_urls=allow,
            intermediate_root=inter,
            normalized_root=norm,
            raw_root=raw_r,
        )
        for e in registry.schemes
    ]


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    inter: Path | None = None
    norm: Path | None = None
    raw: Path | None = None
    if len(argv) >= 1:
        inter = Path(argv[0]).resolve()
    if len(argv) >= 2:
        norm = Path(argv[1]).resolve()
    if len(argv) >= 3:
        raw = Path(argv[2]).resolve()

    reg = load_registry()
    results = normalize_all(
        reg,
        intermediate_root=inter,
        normalized_root=norm,
        raw_root=raw,
    )
    summary = {
        "intermediate_root": str(inter or _default_intermediate_dir()),
        "normalized_root": str(norm or _default_normalized_dir()),
        "raw_root": str(raw or _default_raw_dir()),
        "results": [asdict(m) for m in results],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not all(m.ok for m in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
