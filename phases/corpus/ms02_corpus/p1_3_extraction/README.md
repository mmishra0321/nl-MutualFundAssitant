# Phase 1.3 — HTML extraction

**Architecture:** `../../../../phased-architecture.md` — Phase 1, subphase 1.3.

## Implemented

| Module | Role |
|--------|------|
| `extractor.py` | Reads `raw/<scheme_id>/latest.html` + `manifest.json`, verifies `ok` and **SHA-256** vs disk, parses with **BeautifulSoup**, removes script/style/link/meta/svg/etc., strips **header / nav / footer** and ARIA **`role`** `navigation` / `banner` / `contentinfo`, collapses `<head>` to `<title>`, wraps **`#__next`** (fallback `body` / `main`), writes `intermediate/<scheme_id>/extracted.html` + `manifest.json`. **No HTTP** — no outbound link following. |

## Output

```text
intermediate/<scheme_id>/extracted.html
intermediate/<scheme_id>/manifest.json
```

## Run

Requires successful **Phase 1.2** snapshots under `raw/`.

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
pip install -r requirements.txt
python -m ms02_corpus.p1_3_extraction
# optional: python -m ms02_corpus.p1_3_extraction /path/to/raw /path/to/intermediate
```

Or: `./scripts/run_p1_3.sh`
