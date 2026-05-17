"""
Phase 2.1 — Chunking (phased-architecture.md).

Reads Phase 1 normalized Markdown, splits heading-aware (tables intact),
writes JSONL under phases/index/chunks/.
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

# Registry lives in Phase 1 package (PYTHONPATH must include phases/corpus).
from ms02_corpus.p1_1_registry.registry import Registry, SchemeEntry, load_registry

DOC_TYPE = "groww_scheme_page"
MAX_CHUNK_CHARS = 6_000
OVERLAP_CHARS = 250

_HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")
_FOOTER_MARKERS = (
    "\n[Home](/)>",
    "\nDownload the App",
    "\n© 2016-",
    "\nGROWW[About Us]",
)
_FUND_FACT_RE = re.compile(
    r"(NAV:|Min\.\s*for\s*SIP|Expense\s*ratio|Fund\s*size|Exit\s*load|lock-in|Riskometer|benchmark)",
    re.IGNORECASE,
)


class ChunkingError(ValueError):
    """Invalid input or allowlist violation during chunking."""


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    scheme_id: str
    scheme_name: str
    source_url: str
    doc_type: str
    section_heading: str
    text: str
    char_count: int
    chunk_index: int
    raw_fetched_at: str
    raw_content_sha256: str
    normalized_sha256: str
    normalized_at: str


def _default_normalized_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "corpus" / "normalized"


def _default_chunks_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "chunks"


def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def _strip_nav_links(text: str) -> str:
    return _LINK_RE.sub(r"\1", text)


def _trim_trailing_chrome(text: str) -> str:
    cut = len(text)
    for marker in _FOOTER_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return text[:cut].strip()


def _trim_leading_chrome(text: str) -> str:
    """Drop leading site-nav blob; keep fund-fact tail if present on line 1."""
    lines = text.splitlines()
    if not lines:
        return text
    first = lines[0]
    if len(first) > 400 and (first.startswith("Stocks[") or first.count("](/") > 8):
        m = _FUND_FACT_RE.search(first)
        lead = ""
        if m:
            lead = _strip_nav_links(first[m.start() :]).strip()
        rest = "\n".join(lines[1:])
        return (lead + "\n\n" + rest).strip() if lead else rest
    return text


def _paragraphs_outside_tables(body: str) -> list[str]:
    """Split body into blocks; markdown table blocks stay atomic."""
    blocks: list[str] = []
    buf: list[str] = []
    in_table = False

    def flush() -> None:
        if buf:
            blocks.append("\n".join(buf).strip())
            buf.clear()

    for line in body.splitlines():
        if _is_table_line(line):
            if not in_table:
                flush()
                in_table = True
            buf.append(line)
        else:
            if in_table:
                flush()
                in_table = False
            if line.strip() == "":
                flush()
            else:
                buf.append(line)
    flush()
    return [b for b in blocks if b]


def _split_oversized_block(block: str, heading: str) -> list[str]:
    if len(block) <= MAX_CHUNK_CHARS:
        return [block]
    if all(_is_table_line(ln) or ln.strip() == "" or ln.strip().startswith("| ---")
           for ln in block.splitlines() if ln.strip()):
        return [block]
    parts: list[str] = []
    paras = _paragraphs_outside_tables(block)
    current: list[str] = []
    current_len = 0
    prefix = f"{heading}\n\n" if heading else ""

    def emit() -> None:
        nonlocal current, current_len
        if current:
            parts.append("\n\n".join(current).strip())
            current = []
            current_len = 0

    for para in paras:
        if _is_table_line(para.splitlines()[0]):
            emit()
            parts.append(para)
            continue
        plen = len(para)
        if current_len + plen + 2 > MAX_CHUNK_CHARS and current:
            emit()
            if plen > MAX_CHUNK_CHARS:
                start = 0
                while start < plen:
                    end = min(start + MAX_CHUNK_CHARS, plen)
                    slice_text = para[start:end]
                    parts.append(slice_text)
                    start = end - OVERLAP_CHARS if end < plen else end
                continue
        current.append(para)
        current_len += plen + 2
    emit()
    if not parts:
        return [block[:MAX_CHUNK_CHARS]]
    if prefix and parts:
        parts[0] = prefix + parts[0]
    return parts


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    """Return (heading, body) sections from ## / ### / #### boundaries."""
    matches = list(_HEADING_RE.finditer(markdown))
    if not matches:
        return [("", markdown.strip())] if markdown.strip() else []

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preamble = markdown[: matches[0].start()].strip()
        if preamble:
            sections.append(("Fund overview", preamble))

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        heading = f"{'#' * level} {title}"
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        if body or title:
            sections.append((heading, body))
    return sections


def chunk_text(
    markdown: str,
    *,
    scheme_id: str,
    scheme_name: str,
    source_url: str,
    provenance: dict[str, str],
) -> list[ChunkRecord]:
    """Chunk a single page.md string with heading-aware rules."""
    text = _trim_trailing_chrome(_trim_leading_chrome(markdown))
    sections = _split_sections(text)
    pieces: list[tuple[str, str]] = []
    for heading, body in sections:
        if not body and not heading:
            continue
        full = f"{heading}\n\n{body}".strip() if heading else body
        for part in _split_oversized_block(full, heading):
            pieces.append((heading or "Section", part))

    if not pieces and text.strip():
        pieces.append(("Page", text.strip()))

    records: list[ChunkRecord] = []
    for idx, (heading, part) in enumerate(pieces):
        chunk_id = f"{scheme_id}_{idx:04d}"
        records.append(
            ChunkRecord(
                chunk_id=chunk_id,
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                source_url=source_url,
                doc_type=DOC_TYPE,
                section_heading=heading,
                text=part,
                char_count=len(part),
                chunk_index=idx,
                raw_fetched_at=provenance.get("raw_fetched_at", ""),
                raw_content_sha256=provenance.get("raw_content_sha256", ""),
                normalized_sha256=provenance.get("normalized_sha256", ""),
                normalized_at=provenance.get("normalized_at", ""),
            )
        )
    return records


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_normalized_manifest(
    man: dict[str, Any], entry: SchemeEntry, allowlist_urls: frozenset[str]
) -> dict[str, str]:
    if not man.get("ok"):
        raise ChunkingError(f"{entry.id}: normalized manifest ok=false")
    source_url = str(man.get("source_url", ""))
    if source_url not in allowlist_urls:
        raise ChunkingError(f"{entry.id}: source_url not in allowlist")
    if source_url != entry.url:
        raise ChunkingError(f"{entry.id}: source_url mismatch")
    return {
        "raw_fetched_at": str(man.get("raw_fetched_at", "")),
        "raw_content_sha256": str(man.get("raw_content_sha256", "")),
        "normalized_sha256": str(man.get("normalized_sha256", "")),
        "normalized_at": str(man.get("normalized_at", "")),
    }


def chunk_scheme(
    entry: SchemeEntry,
    *,
    allowlist_urls: frozenset[str],
    normalized_root: Path,
    chunks_root: Path,
) -> dict[str, Any]:
    scheme_dir = normalized_root / entry.id
    page_path = scheme_dir / "page.md"
    man_path = scheme_dir / "manifest.json"
    if not page_path.is_file() or not man_path.is_file():
        raise ChunkingError(f"Missing normalized files for {entry.id}")

    man = _read_json(man_path)
    provenance = _verify_normalized_manifest(man, entry, allowlist_urls)
    md = page_path.read_text(encoding="utf-8")
    disk_sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
    expected = provenance["normalized_sha256"]
    if disk_sha != expected:
        raise ChunkingError(
            f"{entry.id}: page.md sha256 mismatch (disk vs manifest)"
        )

    records = chunk_text(
        md,
        scheme_id=entry.id,
        scheme_name=entry.scheme_name,
        source_url=entry.url,
        provenance=provenance,
    )
    if not records:
        raise ChunkingError(f"{entry.id}: produced zero chunks")

    chunks_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = chunks_root / f"{entry.id}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    out_manifest = {
        "scheme_id": entry.id,
        "scheme_name": entry.scheme_name,
        "source_url": entry.url,
        "chunk_count": len(records),
        "chunks_file": str(jsonl_path.name),
        "chunked_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        **provenance,
        "ok": True,
        "error": None,
    }
    man_out = chunks_root / f"{entry.id}.manifest.json"
    man_out.write_text(json.dumps(out_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_manifest


def chunk_all(
    registry: Registry,
    *,
    normalized_root: Path | None = None,
    chunks_root: Path | None = None,
) -> list[dict[str, Any]]:
    norm = normalized_root or _default_normalized_dir()
    chunks = chunks_root or _default_chunks_dir()
    allow = registry.url_set()
    return [
        chunk_scheme(e, allowlist_urls=allow, normalized_root=norm, chunks_root=chunks)
        for e in registry.schemes
    ]


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    norm: Path | None = None
    chunks: Path | None = None
    if len(argv) >= 1:
        norm = Path(argv[0]).resolve()
    if len(argv) >= 2:
        chunks = Path(argv[1]).resolve()

    reg = load_registry()
    norm_r = norm or _default_normalized_dir()
    chunks_r = chunks or _default_chunks_dir()
    try:
        results = chunk_all(reg, normalized_root=norm_r, chunks_root=chunks_r)
    except ChunkingError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    summary = {
        "ok": True,
        "normalized_root": str(norm_r),
        "chunks_root": str(chunks_r),
        "schemes": results,
        "total_chunks": sum(r["chunk_count"] for r in results),
    }
    index_path = chunks_r / "index.json"
    index_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
