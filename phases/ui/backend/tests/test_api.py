"""Tests for Phase 4 HTTP API."""

from fastapi.testclient import TestClient

from main import create_app

from ms02_answer.models import AnswerResult


class _StubEngine:
    def ask(self, question: str) -> AnswerResult:
        return AnswerResult(
            question=question,
            answer="Stub answer.",
            source_url=None,
            last_updated=None,
            route="refusal:test",
            detail=None,
        )


class _StubFactualEngine:
    def ask(self, question: str) -> AnswerResult:
        return AnswerResult(
            question=question,
            answer="Facts here.",
            source_url="https://groww.in/mutual-funds/foo",
            last_updated="2025-05-01",
            route="factual",
        )


def test_health_ok_when_engine_ready() -> None:
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        got = c.get("/health").json()
    assert got["status"] == "ok"
    assert got.get("startup_error") is None


def test_ask_response_shape_matches_architecture_docs() -> None:
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        r = c.post("/api/ask", json={"question": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"answer", "source_url", "last_updated", "route"}
    assert data["route"] == "refusal:test"
    assert data["answer"]


def test_ask_factual_includes_optional_fields_as_json_null() -> None:
    app = create_app(answer_engine=_StubFactualEngine())
    with TestClient(app) as c:
        r = c.post("/api/ask", json={"question": "Expense ratio?"})
    assert r.status_code == 200
    body = r.json()
    assert body["source_url"] is not None
    assert body["last_updated"] is not None


def test_ask_rejects_blank_question() -> None:
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        r = c.post("/api/ask", json={"question": "   "})
    assert r.status_code == 422


def test_ask_ignores_extra_json_fields_no_pii_channel() -> None:
    """Unknown keys are stripped (AskBody.extra=ignore)—no accidental profile storage."""
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        r = c.post(
            "/api/ask",
            json={"question": "ok", "email": "ignored@example.com"},
        )
    assert r.status_code == 200


def test_openapi_docs_available() -> None:
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        r = c.get("/docs")
    assert r.status_code == 200


def test_index_serves_html_with_disclaimer() -> None:
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        r = c.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Facts-only. No investment advice." in r.text


def test_static_styles_served() -> None:
    app = create_app(answer_engine=_StubEngine())
    with TestClient(app) as c:
        r = c.get("/static/styles.css")
    assert r.status_code == 200
