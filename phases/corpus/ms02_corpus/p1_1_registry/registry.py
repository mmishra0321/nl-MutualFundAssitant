"""
Phase 1.1 — Allowlist & registry (phased-architecture.md).

Loads `phases/foundations/allowlist.yaml`, validates exactly the five Phase 0
Groww URLs, and exposes a single immutable `Registry` for later subphases.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, FrozenSet, Mapping, Sequence

import yaml

# Canonical set from phased-architecture.md Phase 0 (order not significant).
CANONICAL_URLS: FrozenSet[str] = frozenset(
    {
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    }
)

_EXPECTED_COUNT = len(CANONICAL_URLS)


class RegistryError(ValueError):
    """Allowlist violates Phase 0 / Phase 1.1 invariants."""


@dataclass(frozen=True)
class SchemeEntry:
    id: str
    scheme_name: str
    slug: str
    url: str


@dataclass(frozen=True)
class Registry:
    """Validated closed allowlist. Use as the single source for fetchers (1.2+)."""

    version: int
    amc: str
    description: str
    schemes: tuple[SchemeEntry, ...]
    allowlist_path: Path

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(s.url for s in self.schemes)

    def url_set(self) -> FrozenSet[str]:
        return frozenset(self.urls)


def _default_allowlist_path() -> Path:
    # registry.py -> p1_1_registry -> ms02_corpus -> corpus -> phases
    return Path(__file__).resolve().parents[3] / "foundations" / "allowlist.yaml"


def _require_non_empty_str(value: Any, field: str, *, entry_id: str | None) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{field} must be a string{_ctx(entry_id)}.")
    text = value.strip()
    if not text:
        raise RegistryError(f"{field} is empty{_ctx(entry_id)}.")
    return text


def _ctx(entry_id: str | None) -> str:
    return f" (entry id={entry_id!r})" if entry_id else ""


def _parse_entries(raw_urls: Any) -> list[SchemeEntry]:
    if raw_urls is None:
        raise RegistryError("Missing top-level key 'urls'.")
    if not isinstance(raw_urls, list):
        raise RegistryError("'urls' must be a list.")
    entries: list[SchemeEntry] = []
    for i, item in enumerate(raw_urls):
        if not isinstance(item, Mapping):
            raise RegistryError(f"urls[{i}] must be a mapping/object.")
        try:
            eid = _require_non_empty_str(item.get("id"), "id", entry_id=None)
            name = _require_non_empty_str(item.get("scheme_name"), "scheme_name", entry_id=eid)
            slug = _require_non_empty_str(item.get("slug"), "slug", entry_id=eid)
            url = _require_non_empty_str(item.get("url"), "url", entry_id=eid)
        except RegistryError as exc:
            raise RegistryError(f"urls[{i}]: {exc}") from exc
        expected_prefix = f"https://groww.in/mutual-funds/{slug}"
        if url != expected_prefix:
            raise RegistryError(
                f"url must equal https://groww.in/mutual-funds/{{slug}} for id={eid!r}: "
                f"expected {expected_prefix!r}, got {url!r}"
            )
        entries.append(SchemeEntry(id=eid, scheme_name=name, slug=slug, url=url))
    return entries


def load_raw_allowlist_dict(allowlist_path: Path) -> dict[str, Any]:
    if not allowlist_path.is_file():
        raise RegistryError(f"Allowlist file not found: {allowlist_path}")
    try:
        data = yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"Invalid YAML in {allowlist_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("Root YAML document must be a mapping/object.")
    return data


def build_registry(data: Mapping[str, Any], *, allowlist_path: Path) -> Registry:
    version = data.get("version")
    if type(version) is not int:
        raise RegistryError("'version' must be an integer.")
    amc = _require_non_empty_str(data.get("amc"), "amc", entry_id=None)
    description = _require_non_empty_str(data.get("description"), "description", entry_id=None)

    entries = _parse_entries(data.get("urls"))
    if len(entries) != _EXPECTED_COUNT:
        raise RegistryError(
            f"Expected exactly {_EXPECTED_COUNT} allowlisted schemes; got {len(entries)}."
        )

    ids = [e.id for e in entries]
    if len(set(ids)) != len(ids):
        raise RegistryError(f"Duplicate entry ids: {ids}")

    urls = [e.url for e in entries]
    if len(set(urls)) != len(urls):
        raise RegistryError("Duplicate urls in allowlist.")

    url_set = frozenset(urls)
    if url_set != CANONICAL_URLS:
        missing = sorted(CANONICAL_URLS - url_set)
        extra = sorted(url_set - CANONICAL_URLS)
        parts = []
        if missing:
            parts.append(f"missing canonical urls: {missing}")
        if extra:
            parts.append(f"unknown or disallowed urls: {extra}")
        raise RegistryError("Allowlist URLs do not match Phase 0 canonical set. " + "; ".join(parts))

    return Registry(
        version=version,
        amc=amc,
        description=description,
        schemes=tuple(entries),
        allowlist_path=allowlist_path.resolve(),
    )


def load_registry(allowlist_path: Path | None = None) -> Registry:
    """
    Load and validate the closed allowlist.

    Fails fast if count ≠ 5, URLs are not exactly the Phase 0 set, duplicates,
    or required fields/slug-url consistency are violated.
    """
    path = allowlist_path or _default_allowlist_path()
    data = load_raw_allowlist_dict(path)
    return build_registry(data, allowlist_path=path)


def registry_to_jsonable(reg: Registry) -> dict[str, Any]:
    """Stable dict for logging / CLI output (not used as config source)."""
    return {
        "version": reg.version,
        "amc": reg.amc,
        "description": reg.description,
        "allowlist_path": str(reg.allowlist_path),
        "schemes": [
            {"id": s.id, "scheme_name": s.scheme_name, "slug": s.slug, "url": s.url}
            for s in reg.schemes
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    path = Path(argv[0]).resolve() if argv else _default_allowlist_path()
    reg = load_registry(path)
    print(json.dumps(registry_to_jsonable(reg), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
