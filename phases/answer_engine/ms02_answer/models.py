"""Phase 3 response models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    source_url: str | None
    last_updated: str | None
    route: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def display_text(self) -> str:
        """Human-readable block for CLI / UI."""
        lines = [self.answer.strip()]
        if self.source_url:
            lines.append("")
            lines.append(f"Source: {self.source_url}")
            if self.last_updated:
                lines.append(f"Last updated from sources: {self.last_updated}")
        return "\n".join(lines)
