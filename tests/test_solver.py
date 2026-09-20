"""Unit tests for the pairing DP solver."""

from app.solver import find_blocking_participants, solve_pairing


def pairs_of(result):
    return result[0]


def cost_of(result):
    return result[1]


def test_two_participants():
    assert solve_pairing(["a", "b"], set(), {}) == ([("a", "b")], 0)


def test_two_participants_forbidden_is_infeasible():
    assert solve_pairing(["a", "b"], {("a", "b")}, {}) is None


def test_four_min_cost_lexicographic():
    # a-b=5, c-d=5 => 10 ; a-d + b-c = 5 ; a-c + b-d = 0
    meetings = {("a", "b"): 5, ("c", "d"): 5, ("a", "d"): 5}
    result = solve_pairing(["a", "b", "c", "d"], set(), meetings)
    assert pairs_of(result) == [("a", "c"), ("b", "d")]
    assert cost_of(result) == 0


def test_tie_prefers_lexicographically_smallest_sequence():
    # All costs zero: three perfect matchings for 4 participants; the
    # smallest sequence is (a,b),(c,d).
    result = solve_pairing(["a", "b", "c", "d"], set(), {})
    assert pairs_of(result) == [("a", "b"), ("c", "d")]


def test_tie_with_history_still_lexicographic():
    # (a,b)+(c,d) and (a,c)+(b,d) both cost 0; lex picks the first.
    meetings = {("b", "d"): 3}
    result = solve_pairing(["a", "b", "c", "d"], set(), meetings)
    assert pairs_of(result) == [("a", "b"), ("c", "d")]
    assert cost_of(result) == 0


def test_chooses_costlier_first_pair_to_minimize_total():
    # (a,b)+(c,d) costs 0+10=10; (a,c)+(b,d) costs 5+0=5; (a,d)+(b,c)=100.
    meetings = {("c", "d"): 10, ("a", "c"): 5, ("a", "d"): 100}
    result = solve_pairing(["a", "b", "c", "d"], set(), meetings)
    assert pairs_of(result) == [("a", "c"), ("b", "d")]
    assert cost_of(result) == 5


def test_forbidden_forces_alternative():
    # forbid (a,b) and (c,d): only (a,c)+(b,d) and (a,d)+(b,c) remain;
    # lex picks (a,c)+(b,d).
    forbidden = {("a", "b"), ("c", "d")}
    result = solve_pairing(["a", "b", "c", "d"], forbidden, {})
    assert pairs_of(result) == [("a", "c"), ("b", "d")]


def test_six_participant_subset_obstruction_is_infeasible():
    # Two triangles: edges only inside {a,b,c} and {d,e,f}; each set has
    # odd size, so no perfect matching exists even though nobody is isolated.
    ids = ["a", "b", "c", "d", "e", "f"]
    inside = [("a", "b"), ("a", "c"), ("b", "c"),
              ("d", "e"), ("d", "f"), ("e", "f")]
    forbidden = set()
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            if (x, y) not in inside:
                forbidden.add((x, y))
    assert solve_pairing(ids, forbidden, {}) is None
    # No participant is fully blocked, so diagnostics must be empty...
    assert find_blocking_participants(ids, forbidden) == []


def test_blocking_participants_diagnostic():
    # d cannot meet anyone: forbidden with a, b, c.
    forbidden = {("d", "a"), ("d", "b"), ("d", "c")}
    assert find_blocking_participants(["a", "b", "c", "d"], forbidden) == ["d"]


def test_unsorted_input_returns_sorted_output():
    meetings = {("b", "d"): 3}
    result = solve_pairing(["d", "c", "b", "a"], set(), meetings)
    assert pairs_of(result) == [("a", "b"), ("c", "d")]


def test_eight_participants_all_unique_matching_and_cost():
    ids = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
    meetings = {("p1", "p2"): 1, ("p3", "p4"): 1, ("p5", "p6"): 1, ("p7", "p8"): 1}
    result = solve_pairing(ids, set(), meetings)
    # Lex-smallest zero-cost matching avoids all four costly edges.
    assert cost_of(result) == 0
    flat = [x for pair in pairs_of(result) for x in pair]
    assert sorted(flat) == sorted(ids)
    assert len(set(pairs_of(result))) == 4


def test_sixteen_participants_runs_and_is_valid():
    ids = [f"p{i:02d}" for i in range(16)]
    meetings = {(f"p{i:02d}", f"p{(i + 1) % 16:02d}"): 1 for i in range(16)}
    result = solve_pairing(ids, set(), meetings)
    pairs, total = result
    assert len(pairs) == 8
    flat = [x for pair in pairs for x in pair]
    assert sorted(flat) == ids
    assert total >= 0
    for a, b in pairs:
        assert a < b
