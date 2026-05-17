# Edge Cases — Phase 5: Hardening, Documentation, and Handoff

**Scope:** Quality gates, ops (re-crawl, embeddings), security review, README, disclaimer snippet, success criteria.  
**Architecture ref:** `phased-architecture.md` — Phase 5.

| ID | Scenario | Expected handling | Severity |
|----|----------|-------------------|----------|
| P5-01 | Scheduled re-crawl succeeds for four URLs; one fails silently in logs. | Monitoring alert on “≠ 5 successes”; block “green” release until fixed or document degraded mode. | High |
| P5-02 | README lists wrong AMC, wrong scheme names, or old URL set. | Align README allowlist table with Phase 0 byte-for-byte; add CI check or manual checklist item. | Medium |
| P5-03 | Golden tests pass locally but fail in CI due to missing API keys or vector seed. | Document required secrets; use mocked retrieval/LLM for CI where appropriate; separate smoke vs integration jobs. | Medium |
| P5-04 | Logs accidentally capture full request body including pasted PAN from user (policy violation). | Redact patterns in logging middleware; audit log sinks. | High |
| P5-05 | “Known limitations” section omits narrow corpus (five pages only); reviewers assume regulatory completeness. | README states explicitly: not HDFC/AMFI primary documents; stale vs live site; coverage gaps. | High |
| P5-06 | Embedding refresh job runs against half-updated crawl (mixed versions). | Atomic publish: version corpus snapshot ID in README/API health; index only pairs with complete five-page snapshot. | High |
| P5-07 | Disclaimer snippet duplicated inconsistently (“Facts only” vs “Facts-only.”). | Single source of truth string in code or content file; copy into README once. | Low |
| P5-08 | Handoff package missing how to rotate Groww blocking/rate-limit issues. | Runbook: contact, retry policy, user-agent notes, link to internal on-call if any. | Low |
| P5-09 | Success criteria “valid source citations” checked manually once; regression later. | Automate subset: citation ∈ allowlist, sentence count, disclaimer present in E2E test. | Medium |
| P5-10 | License/ToS ambiguity for scraping Groww pages in production. | Document project/educational use assumption; legal review if deployment beyond class demo. | Medium |

**Review trigger:** Release checklist, ownership change, or move from demo to hosted deployment.
