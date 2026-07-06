"""API tests for the hardened FastAPI service.

Covers input validation, input caps (422), the CORS allowlist, and rate limiting.
"""
import os

# Keep the default limit high so the functional tests below never trip the
# rate limiter (the dedicated test overrides this locally).
os.environ.setdefault("RATE_LIMIT_FIND_WORDS", "1000/minute")

from fastapi.testclient import TestClient  # noqa: E402

import app as app_module  # noqa: E402

client = TestClient(app_module.app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["word_count"] > 0


def test_find_words_happy_path():
    response = client.post("/api/find-words", json={"letters": "CAT"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    scores = {r["word"]: r["score"] for r in body["results"]}
    assert scores["CAT"] == 5


def test_results_sorted_by_score_desc():
    response = client.post("/api/find-words", json={"letters": "WERTASH"})
    scores = [r["score"] for r in response.json()["results"]]
    assert scores == sorted(scores, reverse=True)


def test_empty_letters_rejected():
    response = client.post("/api/find-words", json={"letters": "   "})
    assert response.status_code == 400


def test_invalid_characters_rejected():
    response = client.post("/api/find-words", json={"letters": "CA3"})
    assert response.status_code == 400


def test_too_many_tiles_rejected():
    response = client.post("/api/find-words", json={"letters": "ABCDEFGHIJK"})  # 11 tiles
    assert response.status_code == 422


def test_too_many_blanks_rejected():
    response = client.post("/api/find-words", json={"letters": "A B C D"})  # 3 blanks
    assert response.status_code == 422


def test_too_many_board_letters_rejected():
    response = client.post(
        "/api/find-words",
        json={"letters": "CAT", "boardLetters": "ABCDEFGHIJKLMNOP"},  # 16 letters
    )
    assert response.status_code == 422


def test_cors_allows_configured_origin():
    response = client.post(
        "/api/find-words",
        json={"letters": "CAT"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin():
    response = client.post(
        "/api/find-words",
        json={"letters": "CAT"},
        headers={"Origin": "http://evil.example"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_rate_limit_returns_429():
    original = os.environ.get("RATE_LIMIT_FIND_WORDS")
    os.environ["RATE_LIMIT_FIND_WORDS"] = "3/minute"
    try:
        statuses = [
            client.post("/api/find-words", json={"letters": "CAT"}).status_code
            for _ in range(6)
        ]
    finally:
        if original is None:
            os.environ.pop("RATE_LIMIT_FIND_WORDS", None)
        else:
            os.environ["RATE_LIMIT_FIND_WORDS"] = original
    assert 429 in statuses
