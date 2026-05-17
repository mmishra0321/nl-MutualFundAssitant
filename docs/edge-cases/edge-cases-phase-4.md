# Edge Cases — Phase 4: API and Minimal UI

**Scope:** `POST /api/ask`, minimal UI, disclaimer visibility, no PII collection.  
**Architecture ref:** `phased-architecture.md` — Phase 4.

| ID | Scenario | Expected handling | Severity |
|----|----------|-------------------|----------|
| P4-01 | Request body includes extra fields (`email`, `phone`, `pan`) “for personalization.” | API ignores or rejects request with 400; never persist; document in README. | High |
| P4-02 | Extremely long question string (DoS or token burn). | Enforce max length (chars/tokens); return 413/400 with friendly message. | High |
| P4-03 | XSS attempt in question reflected in UI (`<script>`, markdown). | Escape or sanitize display; never `dangerouslySetInnerHTML` with raw user input. | High |
| P4-04 | API returns 500; UI shows stack trace or internal paths. | Generic error message client-side; log details server-side only (without PII). | Medium |
| P4-05 | Disclaimer hidden on small viewports (mobile) below fold or behind chat. | Disclaimer remains permanently visible per architecture (e.g. sticky bar or fixed header). | High |
| P4-06 | `source_url` is valid allowlist string but UI link component breaks (missing `https://`, wrong encoding). | Render full URL as sent; test all five URLs as clickable. | Medium |
| P4-07 | User double-clicks submit; duplicate in-flight requests. | Disable button while loading; debounce or idempotency key optional. | Low |
| P4-08 | Example question buttons send a query that always triggers refusal (bad demo). | Curate three examples that hit factual path on current corpus; refresh when corpus changes. | Medium |
| P4-09 | CORS misconfiguration exposes API to arbitrary origins. | Lock to known frontend origin for production; document dev vs prod. | Medium |
| P4-10 | Rate limiting absent; scripted abuse hits LLM/vector costs. | Basic IP or token bucket limits on `/api/ask` for demo hardening. | Medium |

**Review trigger:** New API fields, new UI surfaces, or auth/session introduction.
