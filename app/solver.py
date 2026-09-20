"""Minimum-weight perfect matching for seminar round pairings.

Given an even number of participants (2..16), a set of forbidden pair
relations and, for each pair, the number of times the two participants have
met before, find a complete pairing (perfect matching) that:

1. never pairs two participants whose relation is forbidden;
2. globally minimizes the total number of repeated meetings;
3. among all minimum-cost pairings, deterministically returns the one whose
   canonical pairing sequence --
       sort(pair) inside each pair, then sort all pairs lexicographically --
   is lexicographically smallest (a stable tie-break on participant IDs).

The solver uses bitmask dynamic programming over subsets.  With at most 16
participants the state space is 2**16 = 65 536 subsets, which is trivial.

A None result means no perfect matching exists under the constraints.
"""

from __future__ import annotations

from typing import Optional

#: maximum number of participants supported by this service
MAX_PARTICIPANTS = 16

#: DP sentinel for subsets that admit no feasible matching
_INF: int = 10**18


def solve_pairing(
    participant_ids: list[str],
    forbidden: set[tuple[str, str]],
    meetings: dict[tuple[str, str], int],
) -> Optional[tuple[list[tuple[str, str]], int]]:
    """Return the optimal perfect matching or ``None`` if none exists.

    Participant IDs are assumed already validated: non-empty, unique, even
    count between 2 and 16.  ``forbidden`` / ``meetings`` use *undirected*
    keys whose two members are distinct participant IDs, normalized so that
    ``key[0] < key[1]`` under plain Python ordering.

    The returned pairs follow the same convention: each tuple is ordered
    ``(lower_id, higher_id)`` and the list of pairs is sorted ascending.
    """

    # Canonical order of participants: sort the IDs once and index by that
    # order; this ordering also defines the lexicographic tie-break.
    ids = sorted(participant_ids)
    n = len(ids)
    index = {pid: i for i, pid in enumerate(ids)}

    # Allowed adjacency and per-edge cost matrices.
    allowed: list[list[bool]] = [[True] * n for _ in range(n)]
    cost: list[list[int]] = [[0] * n for _ in range(n)]
    for a, b in forbidden:
        i, j = index[a], index[b]
        allowed[i][j] = False
        allowed[j][i] = False
    for (a, b), times in meetings.items():
        i, j = index[a], index[b]
        cost[i][j] = times
        cost[j][i] = times

    size = 1 << n
    full = size - 1

    # Enumerate even-cardinality masks in ascending order.  Sub-masks only
    # ever remove bits, so they are numerically smaller than the containing
    # mask; plain ascending iteration is therefore a valid DP order, and
    # skipping odd masks (which never admit a perfect matching) halves the
    # work to 32 768 states for n == 16.
    even_masks = [mask for mask in range(1, size) if not (mask.bit_count() & 1)]

    # dp[mask] = minimum total cost of a perfect matching of the vertices
    # in `mask`; _INF if no matching exists.  choice[mask] records the
    # partner chosen for the lowest-indexed vertex in `mask` in the optimal
    # (and tie-break-minimal) solution.
    dp: list[int] = [_INF] * size
    choice: list[int] = [-1] * size
    dp[0] = 0

    for mask in even_masks:
        # Lowest set bit: every canonical pairing of this subset pairs this
        # vertex with someone; enumerate its partner.  Iterating partners in
        # ascending order and switching only on strictly lower cost gives
        # the lexicographically smallest optimal pairing sequence, because
        # the first pair (containing the smallest unmatched ID) dominates
        # all later pairs in the sorted pairing sequence.
        i = (mask & -mask).bit_length() - 1
        rest = mask ^ (1 << i)
        best = _INF
        best_j = -1
        bits = rest
        while bits:
            bit = bits & -bits
            j = bit.bit_length() - 1
            bits ^= bit
            if not allowed[i][j]:
                continue
            sub = rest ^ bit
            sub_cost = dp[sub]
            if sub_cost == _INF:
                continue
            total = cost[i][j] + sub_cost
            if total < best:
                best = total
                best_j = j
        if best_j >= 0:
            dp[mask] = best
            choice[mask] = best_j

    if dp[full] == _INF:
        return None

    # Reconstruct the pairing from the recorded choices.
    pairs: list[tuple[str, str]] = []
    mask = full
    while mask:
        i = (mask & -mask).bit_length() - 1
        j = choice[mask]
        pairs.append((ids[i], ids[j]))
        mask &= ~(1 << i)
        mask &= ~(1 << j)

    # IDs are sorted and i < j always (i is the lowest set bit, j is in the
    # remaining higher bits); successive i's ascend, so `pairs` is already
    # in the canonical sorted order.  Sort anyway to make the guarantee
    # explicit and independent of reconstruction details.
    pairs.sort()
    return pairs, dp[full]


def find_blocking_participants(
    participant_ids: list[str],
    forbidden: set[tuple[str, str]],
) -> list[str]:
    """Return IDs that cannot be paired with anyone (immediate infeasibility).

    Used to build a helpful 422 error message.  Sorted by ID.  An empty
    result does not prove feasibility -- a subset-level obstruction may
    remain -- it only means there is no trivially isolated participant.
    """
    ids = set(participant_ids)
    blocked: dict[str, set[str]] = {pid: set() for pid in ids}
    for a, b in forbidden:
        blocked[a].add(b)
        blocked[b].add(a)
    return sorted(pid for pid, others in blocked.items() if len(others) >= len(ids) - 1)
