"""End-to-end tests for the FastAPI pairing endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_root_and_openapi():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"]

    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"]
    assert "/pairings" in spec["paths"]
    assert "/health" in spec["paths"]
    assert "post" in spec["paths"]["/pairings"]


def test_docs_pages_render():
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_pairing_basic():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b", "c", "d"],
            "forbidden_pairs": [],
            "past_meetings": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["num_pairs"] == 2
    assert body["total_repeated_meetings"] == 0
    assert body["pairs"] == [{"a": "a", "b": "b"}, {"a": "c", "b": "d"}]


def test_pairing_minimizes_repeated_meetings():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b", "c", "d"],
            "past_meetings": [
                {"a": "a", "b": "b", "count": 5},
                {"a": "c", "b": "d", "count": 5},
                {"a": "d", "b": "a", "count": 5},
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pairs"] == [{"a": "a", "b": "c"}, {"a": "b", "b": "d"}]
    assert body["total_repeated_meetings"] == 0


def test_pairing_stable_tie_break_with_history():
    # Two zero-cost options; lex-smallest sequence must win.
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b", "c", "d"],
            "past_meetings": [{"a": "b", "b": "d", "count": 3}],
        },
    )
    assert r.status_code == 200
    assert r.json()["pairs"] == [{"a": "a", "b": "b"}, {"a": "c", "b": "d"}]


def test_duplicate_meeting_records_are_summed():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b"],
            "past_meetings": [
                {"a": "a", "b": "b", "count": 2},
                {"a": "b", "b": "a", "count": 3},
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["total_repeated_meetings"] == 5


def test_infeasible_isolated_participant_returns_422():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b", "c", "d"],
            "forbidden_pairs": [
                {"a": "d", "b": "a"},
                {"a": "d", "b": "b"},
                {"a": "d", "b": "c"},
            ],
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "infeasible"
    assert body["blocking_participants"] == ["d"]
    assert "d" in body["detail"]


def test_infeasible_subset_obstruction_returns_422():
    # Two disjoint odd triangles -> no perfect matching, nobody isolated.
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b", "c", "d", "e", "f"],
            "forbidden_pairs": [
                {"a": "a", "b": "d"}, {"a": "a", "b": "e"}, {"a": "a", "b": "f"},
                {"a": "b", "b": "d"}, {"a": "b", "b": "e"}, {"a": "b", "b": "f"},
                {"a": "c", "b": "d"}, {"a": "c", "b": "e"}, {"a": "c", "b": "f"},
            ],
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "infeasible"
    assert body["blocking_participants"] == []
    assert "完美配对" in body["detail"] or "完整配对" in body["detail"]


def test_odd_number_of_participants_is_422_validation_error():
    r = client.post("/pairings", json={"participants": ["a", "b", "c"]})
    assert r.status_code == 422


def test_out_of_range_participant_count_is_422():
    r = client.post("/pairings", json={"participants": ["a"]})
    assert r.status_code == 422

    r = client.post("/pairings", json={"participants": [f"p{i}" for i in range(18)]})
    assert r.status_code == 422


def test_duplicate_participant_ids_rejected():
    r = client.post("/pairings", json={"participants": ["a", "b", "a", "c"]})
    assert r.status_code == 422


def test_unknown_participant_in_relation_rejected():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b"],
            "forbidden_pairs": [{"a": "a", "b": "zzz"}],
        },
    )
    assert r.status_code == 422


def test_self_relation_rejected():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b"],
            "forbidden_pairs": [{"a": "a", "b": "a"}],
        },
    )
    assert r.status_code == 422


def test_negative_meeting_count_rejected():
    r = client.post(
        "/pairings",
        json={
            "participants": ["a", "b"],
            "past_meetings": [{"a": "a", "b": "b", "count": -1}],
        },
    )
    assert r.status_code == 422
