"""求解器单元测试：正确性、禁配、同分稳定择优、无解与规模上限。"""
from __future__ import annotations

import time

from app.solver import find_optimal_pairing


def test_two_participants_trivial():
    pairs, total = find_optimal_pairing(["b", "a"])
    assert pairs == [("a", "b")]
    assert total == 0


def test_zero_cost_prefers_lexicographically_smallest():
    # 无历史、无禁配：三种配对方案同分 0，取规范化序列字典序最小者
    pairs, total = find_optimal_pairing(["a", "b", "c", "d"])
    assert pairs == [("a", "b"), ("c", "d")]
    assert total == 0


def test_history_minimization():
    history = [
        ("a", "b", 5), ("c", "d", 5),
        ("a", "c", 1), ("b", "d", 1),
        ("a", "d", 2), ("b", "c", 2),
    ]
    pairs, total = find_optimal_pairing(["a", "b", "c", "d"], history=history)
    assert pairs == [("a", "c"), ("b", "d")]
    assert total == 2


def test_forbidden_pairs_are_respected():
    pairs, total = find_optimal_pairing(
        ["a", "b", "c", "d"], forbidden_pairs=[("a", "b")]
    )
    # (a,b) 被禁后，剩余两个零分方案中取字典序最小者
    assert pairs == [("a", "c"), ("b", "d")]
    assert total == 0


def test_no_solution_returns_none():
    # a 与其余所有人禁配，完整配对不存在
    forbidden = [("a", "b"), ("a", "c"), ("a", "d")]
    assert find_optimal_pairing(["a", "b", "c", "d"], forbidden) is None


def test_forced_unique_matching():
    forbidden = [
        ("a", "c"), ("a", "d"), ("a", "e"), ("a", "f"),  # a 只能配 b
        ("c", "e"), ("c", "f"),                          # c 只能配 d
    ]
    pairs, total = find_optimal_pairing(
        ["a", "b", "c", "d", "e", "f"], forbidden_pairs=forbidden
    )
    assert pairs == [("a", "b"), ("c", "d"), ("e", "f")]
    assert total == 0


def test_tie_break_across_three_pairs():
    # 6 人全部零分，共 15 种方案，取规范化序列字典序最小者
    pairs, total = find_optimal_pairing(["p1", "p2", "p3", "p4", "p5", "p6"])
    assert pairs == [("p1", "p2"), ("p3", "p4"), ("p5", "p6")]
    assert total == 0


def test_tie_break_prefers_smaller_sequence_not_first_found():
    # 两种最低分方案 [(a,d),(b,c)] 与 [(a,c),(b,d)] 同分，应选字典序更小者
    history = [("a", "c", 1), ("b", "d", 1), ("a", "d", 1), ("b", "c", 1),
               ("a", "b", 9), ("c", "d", 9)]
    pairs, total = find_optimal_pairing(["a", "b", "c", "d"], history=history)
    assert pairs == [("a", "c"), ("b", "d")]
    assert total == 2


def test_duplicate_history_entries_accumulate():
    history = [("a", "b", 1), ("a", "b", 2)]  # 合计 3，应逼使方案避开 (a,b)
    pairs, total = find_optimal_pairing(["a", "b", "c", "d"], history=history)
    assert pairs == [("a", "c"), ("b", "d")]
    assert total == 0


def test_unsorted_input_is_normalized():
    pairs, _ = find_optimal_pairing(["dave", "alice", "carol", "bob"])
    assert pairs == [("alice", "bob"), ("carol", "dave")]


def test_result_is_deterministic():
    participants = [f"p{i:02d}" for i in range(10)]
    history = [("p00", "p01", 3), ("p02", "p03", 1), ("p04", "p05", 2)]
    first = find_optimal_pairing(participants, history=history)
    second = find_optimal_pairing(list(reversed(participants)), history=history)
    assert first == second


def test_sixteen_participants_performance_and_shape():
    participants = [f"p{i:02d}" for i in range(16)]
    forbidden = [("p00", "p01"), ("p02", "p03")]
    history = [("p00", "p02", 4), ("p01", "p03", 4)]
    start = time.perf_counter()
    pairs, total = find_optimal_pairing(participants, forbidden, history)
    elapsed = time.perf_counter() - start
    assert len(pairs) == 8
    assert sorted(pid for pair in pairs for pid in pair) == participants
    assert ("p00", "p01") not in pairs and ("p02", "p03") not in pairs
    assert elapsed < 5.0  # 位掩码 DP 应远快于此上限
