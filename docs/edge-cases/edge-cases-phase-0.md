# Edge Cases — Phase 0: Foundations and Compliance

**Scope:** Policy, AMC/schemes, five-URL allowlist, PII, content rules, output contract.  
**Architecture ref:** `phased-architecture.md` — Phase 0.

| ID | Scenario | Expected handling | Severity |
|----|----------|-------------------|----------|
| P0-01 | Someone proposes adding a 6th URL (AMC factsheet, AMFI, SEBI, or another Groww fund) “just for better answers.” | Reject for this build: allowlist stays exactly five Groww scheme URLs; document as out-of-scope change requiring explicit scope revision. | High |
| P0-02 | Allowlist file (YAML/JSON) has duplicate URL entries or two rows mapping to the same slug. | Validation fails; dedupe or fix config before any ingestion job runs. | High |
| P0-03 | Allowlist uses `http://` vs `https://`, trailing slash, or UTM query params vs canonical Groww URLs in Phase 0 table. | Normalize to one canonical string per URL; treat mismatches as config errors if they are not byte-identical to the agreed allowlist after normalization rules are defined. | Medium |
| P0-04 | Stakeholder asks for “which fund is better?” as an in-scope FAQ. | Classified as out of scope for content policy; must be refused in Phase 3; Phase 0 checklist should list this as explicitly disallowed. | High |
| P0-05 | Output contract conflict: product wants bullet lists or tables inside answers. | Problem statement caps at three sentences and one link; Phase 0 locks that contract—any UI copy must not promise richer formatting than the engine can guarantee. | Medium |
| P0-06 | Request to log user email/phone for “support follow-up.” | Disallowed: no collection or persistence of email/phone; capture requirement in Phase 0 sign-off so Phase 4/API does not add such fields. | High |
| P0-07 | Ambiguity: “performance-heavy” questions allowed only if page text supports them—no separate factsheet URL. | Phase 0 documents that citations remain one of the five Groww pages; no exception for external performance links. | Medium |
| P0-08 | Red-team list treats borderline queries (e.g. “Is ELSS lock-in 3 years?”) as factual vs educational. | Define golden labels in Phase 0 deliverables so Phase 3 routing stays consistent across releases. | Low |

**Review trigger:** Any change to allowlist size, URL strings, PII policy, or output contract should force a Phase 0 doc refresh before Phases 1–3 ship.
