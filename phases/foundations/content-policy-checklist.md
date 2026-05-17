# Content policy checklist (Phase 0)

Use this before merging ingestion, RAG, or UI work. Check **Yes / N/A** and note exceptions in the footer.

## A. Data & allowlist

| # | Item | Yes | N/A |
|---|------|-----|-----|
| A1 | Corpus sources are **only** URLs listed in `allowlist.yaml` (exactly five). | | |
| A2 | No fetcher, crawler, or import path pulls AMC PDFs, AMFI, SEBI, blogs, or other Groww pages not in the allowlist. | | |
| A3 | No “helpful” expansion (extra schemes, factsheet mirrors) without Phase 0 / architecture update. | | |
| A4 | `source_url` (or equivalent) stored per chunk is always one of the five allowlisted URLs. | | |

## B. Privacy & security

| # | Item | Yes | N/A |
|---|------|-----|-----|
| B1 | Product does **not** collect or persist PAN, Aadhaar, bank/account numbers, OTPs, email, or phone. | | |
| B2 | API rejects or ignores profile fields (email, phone, etc.) if clients send them. | | |
| B3 | Logs and analytics do not store full user questions if they may contain pasted IDs (prefer truncation/redaction policy). | | |

## C. Facts-only content

| # | Item | Yes | N/A |
|---|------|-----|-----|
| C1 | No investment advice, recommendations, or “should I buy/sell/switch” guidance. | | |
| C2 | No fund-vs-fund comparisons or rankings from the assistant. | | |
| C3 | No custom return calculations or performance predictions; performance talk only from retrieved allowlisted text. | | |
| C4 | Advisory or opinion questions route to **refusal** (see `red-team-queries.yaml`). | | |

## D. Output contract (factual answers)

| # | Item | Yes | N/A |
|---|------|-----|-----|
| D1 | Answer body ≤ **3 sentences** (problem statement + architecture). | | |
| D2 | Exactly **one** citation URL, and it ∈ `allowlist.yaml`. | | |
| D3 | Footer includes: `Last updated from sources: <date>` with a defined sourcing rule (e.g. max `fetched_at` over used chunks). | | |
| D4 | Refusal responses do not introduce URLs outside the allowlist (current policy: **no links** on refusals). | | |

## E. UI & transparency

| # | Item | Yes | N/A |
|---|------|-----|-----|
| E1 | Disclaimer **“Facts-only. No investment advice.”** is visible on the main Q&A screen. | | |
| E2 | Welcome copy does not promise regulatory completeness beyond the five pages. | | |

---

**Sign-off**

| Role | Name | Date |
|------|------|------|
| Owner | | |

**Exceptions / notes:**
