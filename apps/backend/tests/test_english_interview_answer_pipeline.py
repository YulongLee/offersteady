import json

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def unwrap(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def parse_sse(payload: str) -> list[dict[str, object]]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in payload.splitlines()
        if line.startswith("data: ")
    ]


def test_english_session_routes_nonstream_and_stream_answers_to_english_prompts() -> None:
    user_id = "synthetic-english-answer-user"
    created = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "Synthetic English interview",
        "interviewLanguage": "en-US",
    }))
    session_id = created["sessionId"]
    assert created["interviewLanguage"] == "en-US"
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    ordinary = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "How would you design a safe deployment pipeline?",
        "stream": False,
    }))["task"]
    assert ordinary["promptTemplateId"] == "interview-chat-en-system"
    assert "Quick Answer" in ordinary["answerText"]
    assert "详细回答" not in ordinary["answerText"]

    with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "Tell me about a production incident you handled.",
        "stream": True,
    }) as response:
        assert response.status_code == 200
        events = parse_sse(response.read().decode("utf-8"))

    completed = events[-1]["task"]
    assert isinstance(completed, dict)
    assert completed["promptTemplateId"] == "interview-chat-quick+detail"
    assert "Quick Answer" in completed["answerText"]
    assert "Detailed Answer" in completed["answerText"]
    assert "简单回答" not in completed["answerText"]


def test_language_route_validates_values_and_locks_after_start() -> None:
    user_id = "synthetic-language-route-user"
    created = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "Route contract"}))
    session_id = created["sessionId"]

    invalid = client.patch(
        f"/api/v1/sessions/{session_id}/language",
        json={"userId": user_id, "interviewLanguage": "fr-FR"},
    )
    assert invalid.status_code == 422

    updated = unwrap(client.patch(
        f"/api/v1/sessions/{session_id}/language",
        json={"userId": user_id, "interviewLanguage": "en-US"},
    ))
    assert updated["interviewLanguage"] == "en-US"

    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    locked = client.patch(
        f"/api/v1/sessions/{session_id}/language",
        json={"userId": user_id, "interviewLanguage": "zh-CN"},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["details"]["errorCode"] == "interview_language_locked"
