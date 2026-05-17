# Phase 3: Answer engine

**Architecture:** `../../phased-architecture.md` — Phase 3.

## Citation policy

| Situation | URL in response |
|-----------|-----------------|
| Factual answer grounded in retrieved chunks | **Yes** — one allowlisted Groww URL |
| Unknown / insufficient context | **No** |
| Advisory / opinion refusal | **No** |
| PII detected in question | **No** |
| Out of scope (fund not in corpus) | **No** |

- **Groq RAG (Phase 3 factual path):** when `GROQ_API_KEY` is set, every useful factual query runs **retrieve → top-k chunks → Groq prompt**; the model must answer only from those chunks. Extractive `generator.py` is a fallback if the API fails. Set `MS02_USE_GROQ=0` or `--no-groq` for extractive-only.

## Run

Requires Phase **2** index (`../index/scripts/run_index_build.sh`).

```bash
cd phases/answer_engine
export PYTHONPATH="${PWD}:${PWD}/../index:${PWD}/../corpus"
export HF_HOME="${PWD}/../index/.cache/huggingface"
pip install -r requirements.txt
python -m ms02_answer "What is the minimum SIP for HDFC ELSS?"
python -m ms02_answer --red-team
# or: ./scripts/run_phase3.sh "expense ratio HDFC Mid Cap"
```

## Package layout

```text
ms02_answer/
  gate.py         # routing: factual / refusal / PII / insufficient
  generator.py    # extractive answers from retrieved chunks
  groq_client.py  # Groq LLM on factual path (fallback: extractive)
  validator.py    # output contract
  engine.py       # orchestrator + CLI
  templates.py    # refusal copy (no URLs)
```
