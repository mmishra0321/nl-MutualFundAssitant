"""Run Phase 4 API security tests (PII field stripping, response contract)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_api_security_tests(phases_root: Path) -> dict[str, Any]:
    backend = phases_root / "ui" / "backend"
    tests = backend / "tests"
    if not tests.is_dir():
        return {"ok": False, "error": f"missing {tests}"}

    index = phases_root / "index"
    corpus = phases_root / "corpus"
    answer = phases_root / "answer_engine"
    py = index / ".venv" / "bin" / "python"
    if not py.is_file():
        py = Path(sys.executable)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        str(p.resolve())
        for p in (backend, answer, index, corpus)
    )

    proc = subprocess.run(
        [str(py), "-m", "pytest", "tests", "-q", "--tb=no"],
        cwd=str(backend),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }
