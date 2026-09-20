"""API 集成测试（需要安装 requirements-dev.txt）。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_and_docs_available():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/pairings" in paths and "/health" in paths
    assert client.get("/docs").status_code == 200


def test_pairings_happy_path():
    resp = client.post("/pairings", json={
        "participants": ["alice", "bob", "carol", "dave"],
        "forbidden_pairs": [{"a": "alice", "b": "bob"}],
        "history": [
            {"a": "alice", "b": "carol", "count": 2},
            {"a": "bob", "b": "dave", "count": 1},
        ],
    })
    assert resp.status_code == 200
    # 候选方案：[(alice,carol),(bob,dave)] 代价 3；[(alice,dave),(bob,carol)] 代价 0
    assert resp.json() == {
        "pairs": [["alice", "dave"], ["bob", "carol"]],
        "total_repeat_encounters": 0,
    }


def test_pairings_deterministic_across_requests():
    payload = {
        "participants": ["p1", "p2", "p3", "p4", "p5", "p6"],
        "history": [{"a": "p1", "b": "p2", "count": 1}],
    }
    first = client.post("/pairings", json=payload).json()
    second = client.post("/pairings", json=payload).json()
    assert first == second


def test_integer_ids_are_coerced_to_strings():
    resp = client.post("/pairings", json={"participants": [1, 2, 3, 4]})
    assert resp.status_code == 200
    assert resp.json()["pairs"] == [["1", "2"], ["3", "4"]]


def test_no_complete_pairing_returns_422_with_explanation():
    # a 与其余所有人禁配，完整配对不存在
    resp = client.post("/pairings", json={
        "participants": ["a", "b", "c", "d"],
        "forbidden_pairs": [
            {"a": "a", "b": "b"},
            {"a": "a", "b": "c"},
            {"a": "a", "b": "d"},
        ],
    })
    assert resp.status_code == 422
    assert "无法完成完整配对" in resp.json()["detail"]


def test_validation_errors_return_422():
    base = {"participants": ["a", "b", "c", "d"]}

    # 奇数人数
    resp = client.post("/pairings", json={"participants": ["a", "b", "c"]})
    assert resp.status_code == 422

    # 人数低于下限
    resp = client.post("/pairings", json={"participants": ["a"]})
    assert resp.status_code == 422

    # 人数超过上限
    resp = client.post("/pairings", json={"participants": [f"p{i}" for i in range(18)]})
    assert resp.status_code == 422

    # 重复参与者
    resp = client.post("/pairings", json={"participants": ["a", "a", "b", "c"]})
    assert resp.status_code == 422

    # 禁配引用未知参与者
    resp = client.post("/pairings", json={
        **base, "forbidden_pairs": [{"a": "a", "b": "zzz"}],
    })
    assert resp.status_code == 422

    # 历史记录引用未知参与者
    resp = client.post("/pairings", json={
        **base, "history": [{"a": "a", "b": "zzz", "count": 1}],
    })
    assert resp.status_code == 422

    # 自配对（同一对中两个 ID 相同）
    resp = client.post("/pairings", json={
        **base, "forbidden_pairs": [{"a": "a", "b": "a"}],
    })
    assert resp.status_code == 422

    # 负的历史次数
    resp = client.post("/pairings", json={
        **base, "history": [{"a": "a", "b": "b", "count": -1}],
    })
    assert resp.status_code == 422
