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

# Large rotating pools — always show 3 fresh follow-ups (not a shrinking filter list).
FUND_QUESTIONS: dict[str, tuple[str, ...]] = {
    "mid_cap": (
        "What is the latest NAV for HDFC Mid Cap Fund Direct Growth?",
        "What is the expense ratio for HDFC Mid Cap Fund Direct Growth?",
        "What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
        "What is the benchmark for HDFC Mid Cap Fund Direct Growth?",
        "What are the exit load details for HDFC Mid Cap Fund Direct Growth?",
        "What is the riskometer for HDFC Mid Cap Fund Direct Growth?",
        "What is the minimum lumpsum for HDFC Mid Cap Fund Direct Growth?",
    ),
    "equity": (
        "What is the latest NAV for HDFC Equity Fund Direct Growth?",
        "What is the expense ratio for HDFC Equity Fund Direct Growth?",
        "What are the exit load details for HDFC Equity Fund Direct Growth?",
        "What is the minimum SIP for HDFC Equity Fund Direct Growth?",
        "What is the benchmark for HDFC Equity Fund Direct Growth?",
        "What is the riskometer for HDFC Equity Fund Direct Growth?",
        "What is the minimum lumpsum for HDFC Equity Fund Direct Growth?",
    ),
    "focused": (
        "What is the latest NAV for HDFC Focused Fund Direct Growth?",
        "What is the expense ratio for HDFC Focused Fund Direct Growth?",
        "What is the minimum SIP for HDFC Focused Fund Direct Growth?",
        "What is the benchmark for HDFC Focused Fund Direct Growth?",
        "What are the exit load details for HDFC Focused Fund Direct Growth?",
        "What is the riskometer for HDFC Focused Fund Direct Growth?",
        "What is the minimum lumpsum for HDFC Focused Fund Direct Growth?",
    ),
    "elss": (
        "What is the latest NAV for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the lock-in period for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the expense ratio for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the benchmark for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What are the exit load details for HDFC ELSS Tax Saver Direct Plan Growth?",
        "What is the riskometer for HDFC ELSS Tax Saver Direct Plan Growth?",
    ),
    "large_cap": (
        "What is the latest NAV for HDFC Large Cap Fund Direct Growth?",
        "What is the expense ratio for HDFC Large Cap Fund Direct Growth?",
        "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
        "What is the benchmark for HDFC Large Cap Fund Direct Growth?",
        "What are the exit load details for HDFC Large Cap Fund Direct Growth?",
        "What is the riskometer for HDFC Large Cap Fund Direct Growth?",
        "What is the minimum lumpsum for HDFC Large Cap Fund Direct Growth?",
    ),
}

FOLLOW_UP_COUNT = 3
THEME_ORDER = ("mid_cap", "equity", "focused", "elss", "large_cap")


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


def _new_chat_record(*, title: str) -> dict:
    return {"title": title, "messages": [], "follow_up_turn": 0}


def _init_session() -> None:
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = str(uuid.uuid4())
    if "chats" not in st.session_state:
        st.session_state.chats = {
            st.session_state.active_chat_id: _new_chat_record(title="Chat 1"),
        }
    if "chat_order" not in st.session_state:
        st.session_state.chat_order = list(st.session_state.chats.keys())
    for chat in st.session_state.chats.values():
        chat.setdefault("follow_up_turn", 0)
        chat.setdefault("messages", [])


def _active_chat() -> dict:
    return st.session_state.chats[st.session_state.active_chat_id]


def _active_messages() -> list[dict]:
    return _active_chat()["messages"]


def _truncate_title(text: str, max_len: int = 36) -> str:
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _maybe_rename_chat(question: str) -> None:
    chat = _active_chat()
    title = chat.get("title", "")
    if not title.startswith("Chat "):
        return
    user_msgs = [m for m in chat["messages"] if m.get("role") == "user"]
    if len(user_msgs) == 1:
        chat["title"] = _truncate_title(question)


def _chat_preview(chat: dict) -> str:
    for m in reversed(chat.get("messages", [])):
        if m.get("role") == "user" and m.get("content"):
            return _truncate_title(m["content"], 42)
        if m.get("role") == "assistant":
            if m.get("error"):
                return _truncate_title(m["error"], 42)
            if m.get("result") is not None:
                return _truncate_title(m["result"].answer, 42)
    return "No messages yet"


def _switch_chat(chat_id: str) -> None:
    if chat_id == st.session_state.active_chat_id:
        return
    if chat_id not in st.session_state.chats:
        return
    st.session_state.active_chat_id = chat_id


def _render_chat_history() -> None:
    st.markdown("**History**")
    order = [
        cid for cid in st.session_state.chat_order if cid in st.session_state.chats
    ]
    if not order:
        st.caption("No chats yet.")
        return

    active_id = st.session_state.active_chat_id
    for cid in order:
        chat = st.session_state.chats[cid]
        preview = _chat_preview(chat)
        label = chat.get("title", "Chat")
        is_active = cid == active_id
        if st.button(
            label,
            key=f"hist_{cid}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
            help=preview,
        ):
            if cid != active_id:
                _switch_chat(cid)
                st.rerun()
        if preview and preview != "No messages yet" and not is_active:
            st.caption(preview)
        elif preview and preview != "No messages yet" and is_active:
            st.caption(f"▸ {preview}")


def _last_user_question(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return m["content"].strip().lower()
    return ""


def _conversation_context(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return m["content"]
        if m.get("role") == "assistant" and m.get("result") is not None:
            return m["result"].answer
    return ""


def _suggestion_pool(theme: str | None) -> list[str]:
    """Same-fund questions first, then other funds — large list for rotation."""
    pool: list[str] = []
    seen: set[str] = set()

    def _add(items: tuple[str, ...]) -> None:
        for q in items:
            key = q.strip().lower()
            if key not in seen:
                seen.add(key)
                pool.append(q)

    if theme and theme in FUND_QUESTIONS:
        _add(FUND_QUESTIONS[theme])
    for t in THEME_ORDER:
        if t != theme:
            _add(FUND_QUESTIONS[t])
    return pool


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
    """Return 3 follow-ups, rotating to new questions each turn (not a shrinking list)."""
    if not messages:
        return []

    theme = _detect_scheme_theme(_conversation_context(messages))
    pool = _suggestion_pool(theme)
    if not pool:
        return []

    last_q = _last_user_question(messages)
    turn = int(_active_chat().get("follow_up_turn", 0))
    start = (turn * FOLLOW_UP_COUNT) % len(pool)

    out: list[str] = []
    scanned = 0
    while len(out) < FOLLOW_UP_COUNT and scanned < len(pool) * 2:
        q = pool[(start + scanned) % len(pool)]
        scanned += 1
        if q.strip().lower() == last_q:
            continue
        if q in out:
            continue
        out.append(q)
    return out


def _clear_active_chat() -> None:
    chat = _active_chat()
    chat["messages"] = []
    chat["follow_up_turn"] = 0


def _clear_all_chats() -> None:
    cid = str(uuid.uuid4())
    st.session_state.chats = {cid: _new_chat_record(title="Chat 1")}
    st.session_state.active_chat_id = cid
    st.session_state.chat_order = [cid]


def _render_follow_ups(messages: list[dict]) -> None:
    suggestions = _follow_up_suggestions(messages)
    if not suggestions:
        return
    st.markdown("**Suggested follow-ups**")
    col_a, col_b = st.columns(2, gap="small")
    for i, question in enumerate(suggestions):
        col = col_a if i % 2 == 0 else col_b
        label = question if len(question) <= 58 else question[:55] + "…"
        if col.button(
            label,
            key=f"follow_{st.session_state.active_chat_id}_{_active_chat().get('follow_up_turn', 0)}_{i}",
            use_container_width=True,
            help=question,
        ):
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
    _maybe_rename_chat(question)
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
    _active_chat()["follow_up_turn"] = int(_active_chat().get("follow_up_turn", 0)) + 1


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
            st.session_state.chats[cid] = _new_chat_record(title=f"Chat {n}")
            st.session_state.chat_order.insert(0, cid)
            st.session_state.active_chat_id = cid
            st.rerun()
        _render_chat_history()
        st.divider()
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
    active_title = _active_chat().get("title", "Chat")
    if has_chat:
        st.caption(active_title)

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
