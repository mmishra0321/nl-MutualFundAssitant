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
    "Latest NAV for HDFC Mid Cap Fund Direct Growth?",
    "Expense ratio for HDFC Mid Cap Fund Direct Growth?",
    "Exit load for HDFC Equity Fund Direct Growth?",
    "Minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?",
)

EXAMPLE_FULL = (
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

# Follow-up suggestions keyed by scheme theme (shown after each answer).
FOLLOW_UPS: dict[str, tuple[str, ...]] = {
    "mid_cap": (
        "What is the expense ratio for HDFC Mid Cap Fund Direct Growth?",
        "What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
        "What is the benchmark for HDFC Mid Cap Fund Direct Growth?",
    ),
    "equity": (
        "What are the exit load details for HDFC Equity Fund Direct Growth?",
        "What is the expense ratio for HDFC Equity Fund Direct Growth?",
        "What is the minimum SIP for HDFC Equity Fund Direct Growth?",
    ),
    "focused": (
        "What is the expense ratio for HDFC Focused Fund Direct Growth?",
        "What is the latest NAV for HDFC Focused Fund Direct Growth?",
        "What is the minimum SIP for HDFC Focused Fund Direct Growth?",
    ),
    "elss": (
        "What is the lock-in period for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the expense ratio for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?",
    ),
    "large_cap": (
        "What is the latest NAV for HDFC Large Cap Fund Direct Growth?",
        "What is the expense ratio for HDFC Large Cap Fund Direct Growth?",
        "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
    ),
}

GENERIC_FOLLOW_UPS = (
    "What is the latest NAV for HDFC Mid Cap Fund Direct Growth?",
    "What are the exit load details for HDFC Equity Fund Direct Growth?",
    "What is the minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
          .block-container { max-width: 52rem; padding-top: 1.25rem; }
          [data-testid="stSidebar"] { min-width: 17rem; }
          div[data-testid="stVerticalBlock"] div.stButton > button {
            white-space: normal;
            height: auto;
            min-height: 2.75rem;
            line-height: 1.35;
            text-align: left;
            padding: 0.55rem 0.75rem;
          }
          .disclaimer-box {
            font-size: 0.85rem;
            padding: 0.5rem 0.65rem;
            border-radius: 0.5rem;
            border: 1px solid rgba(94, 236, 200, 0.35);
            background: rgba(94, 236, 200, 0.08);
          }
        </style>
        """,
        unsafe_allow_html=True,
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
    cache = index_dir / ".cache" / "huggingface"
    cache.mkdir(parents=True, exist_ok=True)
    for var in ("HF_HOME", "SENTENCE_TRANSFORMERS_HOME", "TRANSFORMERS_CACHE"):
        os.environ.setdefault(var, str(cache))


def _index_ready() -> tuple[bool, str]:
    manifest = _PHASES / "index" / "index_build.json"
    chroma = _PHASES / "index" / "vector_store" / "chroma"
    if not manifest.is_file():
        return False, "Missing `phases/index/index_build.json` — run index build before deploy."
    if not chroma.is_dir():
        return False, "Missing `phases/index/vector_store/chroma` — commit the vector store to git."
    return True, ""


@st.cache_resource(show_spinner="Loading answer engine…")
def _load_engine() -> AnswerEngine:
    _configure_runtime()
    return AnswerEngine(
        vector_store_root=_PHASES / "index" / "vector_store",
        normalized_root=_PHASES / "corpus" / "normalized",
        allowlist_path=_PHASES / "foundations" / "allowlist.yaml",
    )


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


def _asked_questions(messages: list[dict]) -> set[str]:
    return {
        m["content"].strip().lower()
        for m in messages
        if m.get("role") == "user" and m.get("content")
    }


def _detect_scheme_theme(text: str) -> str | None:
    t = text.lower()
    if "elss" in t or "tax saver" in t:
        return "elss"
    if "mid cap" in t or "mid-cap" in t:
        return "mid_cap"
    if "large cap" in t or "large-cap" in t:
        return "large_cap"
    if "focused" in t:
        return "focused"
    if "equity fund" in t or "hdfc equity" in t:
        return "equity"
    return None


def _follow_up_suggestions(messages: list[dict]) -> list[str]:
    """Return up to 3 follow-up questions not already asked in this chat."""
    asked = _asked_questions(messages)
    context = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            context = m["content"]
            break
        if m.get("role") == "assistant" and m.get("result") is not None:
            context = m["result"].answer
            break

    theme = _detect_scheme_theme(context)
    pool: tuple[str, ...] = FOLLOW_UPS.get(theme, ()) + GENERIC_FOLLOW_UPS

    out: list[str] = []
    for q in pool:
        if q.strip().lower() not in asked and q not in out:
            out.append(q)
        if len(out) >= 3:
            break
    return out


def _clear_active_chat() -> None:
    cid = st.session_state.active_chat_id
    st.session_state.chats[cid]["messages"] = []


def _clear_all_chats() -> None:
    cid = str(uuid.uuid4())
    st.session_state.chats = {cid: {"title": "Chat 1", "messages": []}}
    st.session_state.active_chat_id = cid


def _render_follow_ups(messages: list[dict]) -> None:
    suggestions = _follow_up_suggestions(messages)
    if not suggestions:
        return
    st.markdown("**Suggested follow-ups**")
    col_a, col_b = st.columns(2, gap="small")
    for i, question in enumerate(suggestions):
        col = col_a if i % 2 == 0 else col_b
        label = question if len(question) <= 58 else question[:55] + "…"
        if col.button(label, key=f"follow_{i}", use_container_width=True, help=question):
            with st.spinner("Retrieving facts…"):
                _ask(question)
            st.rerun()


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
    ready, err = _index_ready()
    if not ready:
        _active_messages().append(
            {"role": "assistant", "result": None, "error": err}
        )
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
                "error": f"Could not answer right now: {exc}",
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
        layout="centered",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

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
        btn_col1, btn_col2 = st.columns(2, gap="small")
        with btn_col1:
            if st.button("Clear chat", use_container_width=True):
                _clear_active_chat()
                st.rerun()
        with btn_col2:
            if st.button("Clear all", use_container_width=True):
                _clear_all_chats()
                st.rerun()
        st.markdown("**Supported funds**")
        for fund in SUPPORTED_FUNDS:
            st.markdown(f"- {fund}")
        st.divider()
        st.markdown(f'<p class="disclaimer-box">{DISCLAIMER}</p>', unsafe_allow_html=True)

    messages = _active_messages()
    has_chat = len(messages) > 0

    if not has_chat:
        st.header("How can I help you today?")
        st.caption(
            "Compliance-oriented answers from five allowlisted Groww scheme pages."
        )
        st.markdown("**Try an example**")
        col_a, col_b = st.columns(2, gap="small")
        for i, (short, full) in enumerate(zip(EXAMPLE_QUESTIONS, EXAMPLE_FULL)):
            col = col_a if i % 2 == 0 else col_b
            if col.button(short, key=f"ex_{i}", use_container_width=True):
                with st.spinner("Retrieving facts…"):
                    _ask(full)
                st.rerun()

    for entry in messages:
        if entry["role"] == "user":
            with st.chat_message("user"):
                st.markdown(entry["content"])
        elif entry.get("error"):
            with st.chat_message("assistant"):
                st.error(entry["error"])
        else:
            _render_message(entry["result"])

    if has_chat:
        _render_follow_ups(messages)

    if prompt := st.chat_input("Ask a factual question about HDFC schemes…"):
        with st.spinner("Retrieving facts…"):
            _ask(prompt)
        st.rerun()

    if os.environ.get("MS02_LOCAL_DEV"):
        st.caption(
            f"Local dev — Streamlit: `localhost:{os.environ.get('STREAMLIT_SERVER_PORT', '8501')}`"
        )


if __name__ == "__main__":
    main()
