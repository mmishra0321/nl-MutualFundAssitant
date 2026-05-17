"""
Phase 1.5 — End-to-end corpus job (phased-architecture.md).

Runs allowlist shell check, then 1.1 registry → 1.2 fetch → 1.3 extract → 1.4
normalize in order. Idempotent re-runs overwrite artifacts under raw/
intermediate/ normalized/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ms02_corpus.p1_1_registry.registry import Registry, load_registry
from ms02_corpus.p1_2_fetcher.fetcher import fetch_all
from ms02_corpus.p1_3_extraction.extractor import extract_all
from ms02_corpus.p1_4_normalization.normalizer import normalize_all

EXPECTED_SCHEME_COUNT = 5


def _compact_fetch_manifests(manifests: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "scheme_id": getattr(m, "scheme_id", None),
            "ok": bool(getattr(m, "ok", False)),
            "error": getattr(m, "error", None),
            "http_status": getattr(m, "http_status", None),
        }
        for m in manifests
    ]


def _compact_extract_manifests(manifests: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "scheme_id": getattr(m, "scheme_id", None),
            "ok": bool(getattr(m, "ok", False)),
            "error": getattr(m, "error", None),
        }
        for m in manifests
    ]


def _compact_normalize_manifests(manifests: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "scheme_id": getattr(m, "scheme_id", None),
            "ok": bool(getattr(m, "ok", False)),
            "error": getattr(m, "error", None),
            "normalized_sha256": getattr(m, "normalized_sha256", None),
        }
        for m in manifests
    ]


class PipelineError(RuntimeError):
    """A pipeline step failed."""


def _phases_dir() -> Path:
    # pipeline.py -> p1_5_pipeline -> ms02_corpus -> corpus -> phases
    return Path(__file__).resolve().parents[3]


def _one_corpus_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_normalized_dir() -> Path:
    return _one_corpus_dir() / "normalized"


def _postflight_normalized(
    registry: Registry, normalized_root: Path
) -> tuple[bool, dict[str, Any]]:
    """Verify five schemes have non-empty page.md with allowlisted source_url."""
    schemes_out: list[dict[str, Any]] = []
    all_ok = True
    for entry in registry.schemes:
        page = normalized_root / entry.id / "page.md"
        manifest_path = normalized_root / entry.id / "manifest.json"
        row: dict[str, Any] = {
            "scheme_id": entry.id,
            "page_md": str(page.resolve()) if page.is_file() else None,
            "ok": False,
            "error": None,
        }
        if not page.is_file():
            row["error"] = "missing page.md"
            all_ok = False
        elif page.stat().st_size < 100:
            row["error"] = "page.md too small"
            all_ok = False
        elif manifest_path.is_file():
            man = json.loads(manifest_path.read_text(encoding="utf-8"))
            if man.get("source_url") != entry.url:
                row["error"] = "source_url mismatch in manifest"
                all_ok = False
            elif man.get("source_url") not in registry.url_set():
                row["error"] = "source_url not in allowlist"
                all_ok = False
            else:
                row["ok"] = True
                row["normalized_sha256"] = man.get("normalized_sha256")
                row["raw_fetched_at"] = man.get("raw_fetched_at")
        else:
            row["error"] = "missing manifest.json"
            all_ok = False
        schemes_out.append(row)
    return all_ok, {"schemes": schemes_out, "scheme_count": len(schemes_out)}


def _write_corpus_build_manifest(
    steps: list[StepResult],
    *,
    ok: bool,
    paths: dict[str, str],
) -> Path:
    out = _one_corpus_dir() / "corpus_build.json"
    payload = {
        "ok": ok,
        "corpus_root": str(_one_corpus_dir().resolve()),
        "phases_root": str(_phases_dir().resolve()),
        "paths": paths,
        "steps": _serialize_steps(steps),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def run_validate_allowlist_sh() -> str:
    """Shell parity check (CI). Returns stdout on success."""
    script = _phases_dir() / "foundations" / "validate_allowlist.sh"
    if not script.is_file():
        raise PipelineError(f"Missing validate_allowlist.sh: {script}")
    proc = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise PipelineError(err or out or f"validate_allowlist.sh exit {proc.returncode}")
    return out or "allowlist OK"


def run_unittests() -> None:
    """Discover tests under phases/corpus/tests (optional CI step)."""
    root = _one_corpus_dir()
    env = {**os.environ, "PYTHONPATH": str(root)}
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        msg = proc.stderr or proc.stdout or "unittest failed"
        raise PipelineError(msg)


@dataclass
class StepResult:
    step: str
    ok: bool
    detail: dict[str, Any]


def run_phase1_pipeline(
    *,
    raw_root: Path | None = None,
    intermediate_root: Path | None = None,
    normalized_root: Path | None = None,
    skip_validate_sh: bool = False,
    run_tests: bool = False,
) -> tuple[list[StepResult], bool]:
    """
    Execute 1.1→1.4 in order. Returns (steps, all_ok).
    Raises PipelineError on hard failures before subphase manifests exist.
    """
    steps: list[StepResult] = []

    if not skip_validate_sh:
        msg = run_validate_allowlist_sh()
        steps.append(StepResult("0_validate_allowlist_sh", True, {"message": msg}))

    if run_tests:
        run_unittests()
        steps.append(StepResult("0_unittest_discover", True, {}))

    registry = load_registry()
    reg_ok = len(registry.schemes) == EXPECTED_SCHEME_COUNT
    steps.append(
        StepResult(
            "1.1_registry",
            reg_ok,
            {
                "allowlist_path": str(registry.allowlist_path),
                "schemes": len(registry.schemes),
                "expected_schemes": EXPECTED_SCHEME_COUNT,
            },
        )
    )
    if not reg_ok:
        return steps, False

    fetch_manifests = fetch_all(registry, raw_root=raw_root)
    fetch_ok = all(m.ok for m in fetch_manifests)
    steps.append(
        StepResult(
            "1.2_fetch",
            fetch_ok,
            {"results": _compact_fetch_manifests(fetch_manifests)},
        )
    )
    if not fetch_ok:
        return steps, False

    extract_manifests = extract_all(
        registry, raw_root=raw_root, intermediate_root=intermediate_root
    )
    ext_ok = all(m.ok for m in extract_manifests)
    steps.append(
        StepResult(
            "1.3_extract",
            ext_ok,
            {"results": _compact_extract_manifests(extract_manifests)},
        )
    )
    if not ext_ok:
        return steps, False

    norm_manifests = normalize_all(
        registry,
        intermediate_root=intermediate_root,
        normalized_root=normalized_root,
        raw_root=raw_root,
    )
    norm_ok = all(m.ok for m in norm_manifests)
    steps.append(
        StepResult(
            "1.4_normalize",
            norm_ok,
            {"results": _compact_normalize_manifests(norm_manifests)},
        )
    )
    if not norm_ok:
        return steps, False

    norm_r = normalized_root or _default_normalized_dir()
    post_ok, post_detail = _postflight_normalized(registry, norm_r)
    steps.append(StepResult("1.5_postflight", post_ok, post_detail))
    if not post_ok:
        return steps, False

    return steps, True


def _serialize_steps(steps: list[StepResult]) -> list[dict[str, Any]]:
    return [{"step": s.step, "ok": s.ok, "detail": s.detail} for s in steps]


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Phase 1.5 — full corpus pipeline (1.1–1.4).")
    p.add_argument(
        "--skip-validate-sh",
        action="store_true",
        help="Skip phases/foundations/validate_allowlist.sh (not recommended for CI).",
    )
    p.add_argument(
        "--with-tests",
        action="store_true",
        help="Run python -m unittest discover -s tests before ingestion.",
    )
    p.add_argument("raw_dir", nargs="?", default=None, help="Override raw/ root")
    p.add_argument("intermediate_dir", nargs="?", default=None, help="Override intermediate/ root")
    p.add_argument("normalized_dir", nargs="?", default=None, help="Override normalized/ root")
    args = p.parse_args(list(argv) if argv is not None else None)

    raw = Path(args.raw_dir).resolve() if args.raw_dir else None
    inter = Path(args.intermediate_dir).resolve() if args.intermediate_dir else None
    norm = Path(args.normalized_dir).resolve() if args.normalized_dir else None

    try:
        steps, ok = run_phase1_pipeline(
            raw_root=raw,
            intermediate_root=inter,
            normalized_root=norm,
            skip_validate_sh=args.skip_validate_sh,
            run_tests=args.with_tests,
        )
    except PipelineError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    paths = {
        "raw_root": str((raw or _one_corpus_dir() / "raw").resolve()),
        "intermediate_root": str((inter or _one_corpus_dir() / "intermediate").resolve()),
        "normalized_root": str((norm or _default_normalized_dir()).resolve()),
    }
    manifest_path = _write_corpus_build_manifest(steps, ok=ok, paths=paths)

    summary: dict[str, Any] = {
        "ok": ok,
        "phases_root": str(_phases_dir()),
        "corpus_root": str(_one_corpus_dir()),
        "manifest_path": str(manifest_path),
        "paths": paths,
        "steps": _serialize_steps(steps),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
