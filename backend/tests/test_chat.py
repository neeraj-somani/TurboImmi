from fastapi.testclient import TestClient

from app.main import app
from app.policy_chat import MAX_CHAT_MESSAGE, SILENCE
from app.store import MAX_CHAT_TURNS, get_store
from tests.jwt_util import auth_header

client = TestClient(app)


def _headers(sub: str = "chat-user") -> dict[str, str]:
    return auth_header(sub, **{"cognito:username": sub})


def test_chat_requires_jwt() -> None:
    assert client.post("/chat", json={"message": "What is the H-1B cap?"}).status_code == 401


def test_empty_and_overlong_message_are_validation() -> None:
    headers = _headers("chat-validate")
    empty = client.post("/chat", headers=headers, json={"message": "   "})
    assert empty.status_code == 400
    assert empty.json()["detail"]["code"] == "VALIDATION"
    huge = client.post("/chat", headers=headers, json={"message": "x" * (MAX_CHAT_MESSAGE + 1)})
    assert huge.status_code == 400
    assert huge.json()["detail"]["code"] == "VALIDATION"


def test_off_corpus_question_is_silence() -> None:
    headers = _headers("chat-pizza")
    response = client.post("/chat", headers=headers, json={"message": "How do I bake sourdough bread?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert body["citations"] == []
    assert body["answer"] == SILENCE
    assert "uscis.gov" not in body["answer"].lower() or "attorney" in body["answer"].lower()


def test_cap_question_cites_uscis() -> None:
    headers = _headers("chat-cap")
    response = client.post(
        "/chat",
        headers=headers,
        json={"message": "What is the H-1B regular cap of 65,000?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert body["citations"]
    first = body["citations"][0]
    assert "uscis.gov" in first["source_url"]
    assert first["title"]
    assert first["retrieved_at"]
    assert "65,000" in body["answer"] or "regular cap" in body["answer"].lower()


def test_lca_question_cites_uscis() -> None:
    headers = _headers("chat-lca")
    response = client.post(
        "/chat",
        headers=headers,
        json={"message": "Does an H-1B petitioner need a certified labor condition application LCA?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert any("uscis.gov" in str(item.get("source_url")) for item in body["citations"])
    assert any("retrieved_at" in item and item["title"] for item in body["citations"])


def test_sixteenth_turn_is_rate_limited() -> None:
    headers = _headers("chat-limit")
    for index in range(MAX_CHAT_TURNS):
        response = client.post("/chat", headers=headers, json={"message": f"What is the H-1B regular cap {index}?"})
        assert response.status_code == 200, response.text
        assert response.json()["remaining"] == MAX_CHAT_TURNS - index - 1
    blocked = client.post("/chat", headers=headers, json={"message": "What is the H-1B regular cap again?"})
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMIT"


def test_chat_audit_stores_urls_not_transcript() -> None:
    headers = _headers("chat-audit")
    question = "What is the H-1B regular cap of 65,000?"
    response = client.post("/chat", headers=headers, json={"message": question})
    assert response.status_code == 200
    audits = [item for item in getattr(get_store(), "_audits", []) if item.get("kind") == "chat"]
    assert audits
    row = audits[-1]
    assert row.get("citationUrls")
    assert all("uscis.gov" in url for url in row["citationUrls"])
    assert question not in str(row)
    assert response.json()["answer"] not in str(row)
