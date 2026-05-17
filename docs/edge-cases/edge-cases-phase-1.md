# Edge Cases — Phase 1: Corpus Pipeline (Ingestion)

**Scope:** Closed allowlist fetch, HTML extract, normalize, storage—exactly five Groww pages.  
**Architecture ref:** `phased-architecture.md` — Phase 1.

| ID | Scenario | Expected handling | Severity |
|----|----------|-------------------|----------|
| P1-01 | HTTP 403/429/503 from Groww for one or more allowlisted URLs. | Retry with backoff; record failure per URL; do not substitute another URL; pipeline fails exit criteria until all five succeed or you define a degraded mode (document as limitation). | High |
| P1-02 | Page returns 200 but body is empty, captcha, or “unavailable in your region” placeholder. | Treat as fetch failure or zero-content warning; do not crawl alternate mirrors; flag for manual review. | High |
| P1-03 | HTML is largely client-rendered (minimal SSR content; key numbers in JSON inside `<script>`). | Extractor must handle documented structure; if critical text is missing, corpus is incomplete—document in README; do not follow external API URLs not on allowlist. | High |
| P1-04 | Redirect chain: allowlisted URL 302 → another path on `groww.in` (still scheme page) vs redirect to login or home. | If final URL is still one of the five allowlisted canonical URLs after redirect policy, OK; if final URL leaves allowlist, fail ingestion for that job. | High |
| P1-05 | Content hash unchanged between crawls but `fetched_at` should advance. | Store both `fetched_at` and hash; `last_updated` logic in Phase 3 can use max `fetched_at` over used chunks. | Low |
| P1-06 | Accidental recursive link follower pulls in blog/help/groww pages. | Forbidden by architecture: fetcher must only GET the five configured URLs; add tests that only five GETs occur per run. | High |
| P1-07 | Config PR adds a sixth URL “for testing.” | CI/registry validation fails (registry size ≠ 5 or URL not in Phase 0 table). | High |
| P1-08 | Encoding issues (mojibake) or mixed encodings in HTML. | Normalization step detects and fixes or fails loudly; avoid silent corruption of numbers (SIP, expense ratio). | Medium |
| P1-09 | Extremely large HTML payload (heavy inline assets in markup). | Strip non-text nodes; size cap with logging; ensure chunking in Phase 2 still fits limits. | Low |
| P1-10 | Clock skew: `fetched_at` in UTC vs local time in footers. | Standardize on UTC storage; format consistently for “Last updated from sources” in Phase 3. | Low |

**Review trigger:** Groww markup or anti-bot behavior changes—re-run golden extraction checks on all five URLs.
