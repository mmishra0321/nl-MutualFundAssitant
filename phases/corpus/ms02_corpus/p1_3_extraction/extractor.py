"""
Phase 1.3 — HTML main-content extraction (phased-architecture.md).

Reads raw snapshots from Phase 1.2, strips script/style/chrome noise without
fetching any outbound URLs, writes cleaned HTML under intermediate/.
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

from bs4 import BeautifulSoup

from ms02_corpus.p1_1_registry.registry import Registry, SchemeEntry, load_registry

# Tags that are never "page content" for our corpus (no outbound fetches).
_DECOMPOSE_TAGS = (
    "script",
    "style",
    "noscript",
    "iframe",
    "template",
    "svg",  # icon noise; factual text lives outside SVG on Groww MF pages
    "link",
    "meta",
    "picture",
    "source",
)
_CHROME_TAGS = ("header", "nav", "footer")


def _strip_aria_landmark_chrome(soup: BeautifulSoup) -> None:
    """Remove common nav/banner/footer regions marked only with ARIA roles (div-based chrome)."""
    chrome_roles = frozenset({"navigation", "banner", "contentinfo"})
    for el in soup.find_all(attrs={"role": True}):
        role = (el.get("role") or "").strip().lower()
        if role in chrome_roles:
            el.decompose()


@dataclass(frozen=True)
class ExtractManifest:
    scheme_id: str
    scheme_name: str
    source_url: str
    raw_content_sha256: str
    raw_fetched_at: str
    extracted_at: str
    ok: bool
    error: str | None
    extracted_sha256: str | None
    extracted_size_bytes: int | None


def _default_raw_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "raw"


def _default_intermediate_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "intermediate"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_noise_from_soup(soup: BeautifulSoup) -> None:
    for name in _DECOMPOSE_TAGS:
        for el in soup.find_all(name):
            el.decompose()
    for name in _CHROME_TAGS:
        for el in soup.find_all(name):
            el.decompose()


def _minimal_head(soup: BeautifulSoup) -> None:
    head = soup.find("head")
    if not head:
        return
    title = head.find("title")
    title_text = title.get_text(strip=True) if title else ""
    head.clear()
    if title_text:
        new_title = soup.new_tag("title")
        new_title.string = title_text
        head.append(new_title)


def extract_main_html_fragment(raw_html: str) -> str:
    """
    Return a cleaned HTML document string: main app shell without scripts,
    stylesheets, meta noise, or common site chrome (header/nav/footer and
    ARIA navigation/banner/contentinfo regions). Does not fetch URLs.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    _strip_noise_from_soup(soup)
    _strip_aria_landmark_chrome(soup)
    _minimal_head(soup)

    root = soup.select_one("#__next")
    if root is None:
        root = soup.body
    if root is None:
        root = soup.find("main")
    if root is None:
        root = soup
    if getattr(root, "name", None) == "html":
        root = root.body or soup.select_one("#__next") or root

    fragment_soup = BeautifulSoup("", "html.parser")
    new_doc = fragment_soup.new_tag("html")
    new_body = fragment_soup.new_tag("body")
    # extract() moves the node out of the original tree
    new_body.append(root.extract())
    new_doc.append(new_body)
    fragment_soup.append(new_doc)

    text = str(fragment_soup)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def extract_scheme(
    entry: SchemeEntry,
    *,
    raw_root: Path,
    intermediate_root: Path,
) -> ExtractManifest:
    raw_dir = raw_root / entry.id
    html_path = raw_dir / "latest.html"
    man_path = raw_dir / "manifest.json"
    out_dir = intermediate_root / entry.id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / "extracted.html"
    out_man = out_dir / "manifest.json"

    def _fail(msg: str) -> ExtractManifest:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        m = ExtractManifest(
            scheme_id=entry.id,
            scheme_name=entry.scheme_name,
            source_url=entry.url,
            raw_content_sha256="",
            raw_fetched_at="",
            extracted_at=ts,
            ok=False,
            error=msg,
            extracted_sha256=None,
            extracted_size_bytes=None,
        )
        out_man.write_text(
            json.dumps(asdict(m), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if out_html.exists():
            out_html.unlink()
        return m

    if not man_path.is_file() or not html_path.is_file():
        return _fail(f"Missing raw snapshot under {raw_dir}")

    raw_man = _read_json(man_path)
    if not raw_man.get("ok"):
        return _fail("Raw manifest reports ok=false; re-run Phase 1.2 first.")

    raw_bytes = html_path.read_bytes()
    digest = _sha256_bytes(raw_bytes)
    expected = raw_man.get("content_sha256")
    if digest != expected:
        return _fail(
            f"Raw HTML sha256 mismatch: disk={digest!r} manifest={expected!r}"
        )

    try:
        raw_html = raw_bytes.decode("utf-8", errors="replace")
        extracted = extract_main_html_fragment(raw_html)
    except Exception as exc:  # noqa: BLE001 — surface parse errors as manifest failures
        return _fail(f"Extraction failed: {exc}")

    out_bytes = extracted.encode("utf-8")
    ex_digest = _sha256_bytes(out_bytes)
    extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    out_html.write_bytes(out_bytes)
    m = ExtractManifest(
        scheme_id=entry.id,
        scheme_name=entry.scheme_name,
        source_url=str(raw_man.get("source_url", entry.url)),
        raw_content_sha256=digest,
        raw_fetched_at=str(raw_man.get("fetched_at", "")),
        extracted_at=extracted_at,
        ok=True,
        error=None,
        extracted_sha256=ex_digest,
        extracted_size_bytes=len(out_bytes),
    )
    out_man.write_text(
        json.dumps(asdict(m), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return m


def extract_all(
    registry: Registry,
    *,
    raw_root: Path | None = None,
    intermediate_root: Path | None = None,
) -> list[ExtractManifest]:
    raw_r = raw_root or _default_raw_dir()
    inter_r = intermediate_root or _default_intermediate_dir()
    inter_r.mkdir(parents=True, exist_ok=True)
    return [extract_scheme(e, raw_root=raw_r, intermediate_root=inter_r) for e in registry.schemes]


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    raw_dir: Path | None = None
    inter_dir: Path | None = None
    if len(argv) >= 1:
        raw_dir = Path(argv[0]).resolve()
    if len(argv) >= 2:
        inter_dir = Path(argv[1]).resolve()

    reg = load_registry()
    raw_r = raw_dir or _default_raw_dir()
    inter_r = inter_dir or _default_intermediate_dir()
    results = extract_all(reg, raw_root=raw_r, intermediate_root=inter_r)
    summary = {
        "raw_root": str(raw_r),
        "intermediate_root": str(inter_r),
        "results": [asdict(m) for m in results],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not all(m.ok for m in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
