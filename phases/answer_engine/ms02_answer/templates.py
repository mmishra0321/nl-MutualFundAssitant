"""Refusal and insufficient-context copy (no URLs)."""

REFUSAL_ADVISORY = (
    "I can only share objective facts from the five HDFC scheme pages in this assistant, "
    "not investment advice or recommendations. Please ask a factual question such as "
    "expense ratio, minimum SIP, exit load, or benchmark for one of those funds."
)

REFUSAL_PII = (
    "I cannot collect or use personal information such as PAN, Aadhaar, account numbers, "
    "OTP, email, or phone numbers. Please ask a general factual question about the listed "
    "HDFC schemes without sharing private details."
)

REFUSAL_OUT_OF_SCOPE = (
    "I do not have an answer for that fund in this assistant. "
    "I only cover five specific HDFC mutual fund pages on Groww. "
    "Please ask about expense ratio, minimum SIP, exit load, lock-in, or benchmark for one of those schemes."
)

INSUFFICIENT_CONTEXT = (
    "I need a specific factual question to answer. Please ask about expense ratio, "
    "minimum SIP, exit load, lock-in period, benchmark, NAV, or riskometer for one of "
    "the five HDFC schemes in this assistant (for example: \"What is the minimum SIP "
    "for HDFC Mid Cap Fund Direct Growth?\")."
)
