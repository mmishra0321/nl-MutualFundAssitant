"""
Phase 4 — Streamlit UI for MS02 (facts-only HDFC mutual fund FAQ).

Local:
    streamlit run app.py   # from repo root
    ./phases/ui/scripts/run_app.sh

Streamlit Community Cloud: main file ``app.py`` (repo root wrapper).
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PHASES = _REPO_ROOT / "phases"
for _subdir in ("corpus", "index", "answer_engine"):
    _p = str(_PHASES / _subdir)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")

from ms02_answer.engine import AnswerEngine
from ms02_answer.models import AnswerResult

DISCLAIMER = "Facts-only. No investment advice."

EXAMPLE_QUESTIONS = (
    "What is the latest NAV for HDFC Mid Cap Fund Direct Growth?",
    "What is the expense ratio for HDFC Mid Cap Fund Direct Growth?",
    "What are the exit load details for HDFC Equity Fund Direct Growth?",
    "What is the minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?",
)

SUPPORTED_FUNDS = (
    "HDFC Mid Cap Fund Direct Growth",
    "HDFC Equity Fund Direct Growth",
    "HDFC Focused Fund Direct Growth",
    "HDFC ELSS Tax Saver Direct Plan Growth",
    "HDFC Large Cap Fund Direct Growth",
)


def _apply_streamlit_secrets() -> None:
    """Streamlit Cloud secrets → env (local: repo-root ``.env``)."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key and not os.environ.get("GROQ_API_KEY"):
            os.environ["GROQ_API_KEY"] = str(key)
        model = st.secrets.get("GROQ_MODEL", "")
        if model and not os.environ.get("GROQ_MODEL"):
            os.environ["GROQ_MODEL"] = str(model)
    except Exception:
        pass


def _configure_runtime() -> None:
    index_dir = _PHASES / "index"
    os.environ.setdefault("HF_HOME", str(index_dir / ".cache" / "huggingface"))


@st.cache_resource(show_spinner="Loading answer engine…")
def _load_engine() -> AnswerEngine:
    _configure_runtime()
    return AnswerEngine()


def _init_session() -> None:
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = str(uuid.uuid4())
    if "chats" not in st.session_state:
        st.session_state.chats = {
            st.session_state.active_chat_id: {"title": "Chat 1", "messages": []}
        }


def _active_messages() -> list[dict]:
    cid = st.session_state.active_chat_id
    return st.session_state.chats[cid]["messages"]


def _render_message(result: AnswerResult) -> None:
    with st.chat_message("assistant"):
        st.markdown(result.answer)
        if result.source_url:
            st.link_button("View source", result.source_url, use_container_width=False)
        if result.last_updated:
            st.caption(f"Last updated from sources: {result.last_updated}")


def _ask(question: str) -> None:
    question = question.strip()
    if not question:
        return
    messages = _active_messages()
    messages.append({"role": "user", "content": question})
    try:
        engine = _load_engine()
        result = engine.ask(question)
    except Exception as exc:
        messages.append(
            {
                "role": "assistant",
                "result": None,
                "error": (
                    "The answer engine is unavailable. Ensure the Phase 2 index is built "
                    f"(`phases/index/index_build.json`). ({exc})"
                ),
            }
        )
        return
    messages.append({"role": "assistant", "result": result})


def main() -> None:
    _apply_streamlit_secrets()
    _configure_runtime()
    _init_session()

    st.set_page_config(
        page_title="groww-factor — HDFC facts",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        st.title("groww-factor")
        st.caption("Factual intelligence for HDFC Mutual Fund analysis.")
        st.divider()
        if st.button("+ New chat", use_container_width=True, type="primary"):
            cid = str(uuid.uuid4())
            n = len(st.session_state.chats) + 1
            st.session_state.chats[cid] = {"title": f"Chat {n}", "messages": []}
            st.session_state.active_chat_id = cid
            st.rerun()
        st.markdown("**Supported funds**")
        for fund in SUPPORTED_FUNDS:
            st.markdown(f"- {fund}")
        st.divider()
        st.warning(DISCLAIMER)

    st.header("How can I help you today?")
    st.caption(
        "Strict, compliance-oriented answers from the five allowlisted Groww scheme pages."
    )

    cols = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
            with st.spinner("Retrieving facts…"):
                _ask(q)
            st.rerun()

    for entry in _active_messages():
        if entry["role"] == "user":
            with st.chat_message("user"):
                st.markdown(entry["content"])
        elif entry.get("error"):
            with st.chat_message("assistant"):
                st.error(entry["error"])
        else:
            _render_message(entry["result"])

    prompt = st.chat_input("Ask a factual question about HDFC schemes…")
    if prompt:
        with st.spinner("Retrieving facts…"):
            _ask(prompt)
        st.rerun()

    if os.environ.get("MS02_LOCAL_DEV"):
        st.caption(
            f"Local dev — Streamlit: `localhost:{os.environ.get('STREAMLIT_SERVER_PORT', '8501')}`"
        )


if __name__ == "__main__":
    main()
