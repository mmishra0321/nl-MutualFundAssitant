# Phase 0: Foundations and compliance

Implements **Phase 0** from `phased-architecture.md` (repository root).

## Deliverables (this folder)

| File | Purpose |
|------|---------|
| `allowlist.yaml` | **Single source of truth** for the five scheme URLs. Ingestion, index metadata, and citations must use **only** these URLs. |
| `content-policy-checklist.md` | Sign-off checklist for PII, facts-only scope, output contract, and allowlist discipline. |
| `red-team-queries.yaml` | Labeled queries for routing tests: factual vs advisory vs borderline. |

## Invariants (summary)

- **AMC:** HDFC; **schemes:** five Groww mutual fund pages (see allowlist).
- **No other URLs** for corpus ingestion, indexing, or assistant citations (no link-following to AMC PDFs, AMFI, SEBI, or other Groww pages).
- **PII:** Do not collect or persist PAN, Aadhaar, account numbers, OTPs, email, or phone.
- **Responses:** Max three sentences; exactly one `source_url` from the allowlist for factual answers; footer `Last updated from sources: <date>`; refusals use **no** outbound links per current architecture.

## Related docs

- `../../phased-architecture.md`
- [`../../docs/edge-cases/edge-cases-phase-0.md`](../../docs/edge-cases/edge-cases-phase-0.md) — Phase 0 edge-case catalog

Optional automation can be added under `corpus/` later to fail builds if the allowlist size ≠ 5.

## Validation (script)

From repository root (or this directory):

```bash
./phases/foundations/validate_allowlist.sh
```

Requires `bash` and standard Unix tools (`grep`, `wc`, `sort`, `uniq`).
