"""
Log sanitization — redact PII patterns before writing user text to logs.
"""

from __future__ import annotations

import re

_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
_OTP = re.compile(r"\b(?:otp|one[- ]time)\s*(?:is|:)?\s*\d{4,8}\b", re.IGNORECASE)

_REDACTED = "[REDACTED]"


def sanitize_for_log(text: str, *, max_len: int = 200) -> str:
    """Return a log-safe snippet with common PII patterns masked."""
    s = (text or "").strip()
    if not s:
        return ""
    s = _PAN.sub(_REDACTED, s)
    s = _AADHAAR.sub(_REDACTED, s)
    s = _EMAIL.sub(_REDACTED, s)
    s = _PHONE.sub(_REDACTED, s)
    s = _OTP.sub(_REDACTED, s)
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s
