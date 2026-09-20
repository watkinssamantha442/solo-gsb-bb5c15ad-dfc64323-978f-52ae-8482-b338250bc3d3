"""配对求解器：在满足全部禁配关系的完整配对中，全局最小化重复相遇总次数。

参与者规模 n 满足 2 <= n <= 16 且为偶数，采用位掩码动态规划求一般图上的
最小权重完美匹配，状态数 2^n（n=16 时为 65536），复杂度可接受。

择优规则（与 API 语义一致）：
1. 首要目标：配对方案中"重复相遇总次数"（即各配对历史相遇次数之和）全局最小；
2. 同分处理：在并列最优的方案中，取"按参与者 ID 排序后的配对序列"字典序最小者，
   保证结果稳定且唯一。配对序列的规范化形式为：每对内部按 ID 升序、各对之间按
   字典序排序后的序列。

实现要点：参与者先按 ID 排序映射为下标 0..n-1，下标序与 ID 序一致，因此直接
比较下标配对元组即等价于比较 ID 配对序列。DP 状态记录 (最小代价, 字典序最小的
规范化配对元组)，由于"向有序序列中合并同一元素"对字典序是单调的，最优子结构
成立，子问题的 (代价, 元组) 字典序最优可推出父问题最优。
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence

__all__ = ["find_optimal_pairing"]


def find_optimal_pairing(
    participants: Sequence[str],
    forbidden_pairs: Iterable[tuple[str, str]] = (),
    history: Iterable[tuple[str, str, int]] = (),
) -> tuple[list[tuple[str, str]], int] | None:
    """求解最优完整配对。

    :param participants: 参与者 ID 列表，长度为 2~16 的偶数且互不重复。
    :param forbidden_pairs: 禁配关系，元素为 (a, b)，无序。
    :param history: 历史相遇记录，元素为 (a, b, count)，无序；重复记录累加。
    :return: (pairs, total) —— pairs 为规范化排序后的配对序列，total 为最小
        重复相遇总次数；若不存在满足禁配关系的完整配对则返回 None。
    """
    ids = sorted(participants)
    n = len(ids)
    index = {pid: i for i, pid in enumerate(ids)}

    # 历史相遇次数累加到权重矩阵（无向）。
    weight = [[0] * n for _ in range(n)]
    for a, b, count in history:
        i, j = index[a], index[b]
        weight[i][j] += count
        weight[j][i] += count

    # 禁配关系用位掩码邻接表示。
    forbidden = [0] * n
    for a, b in forbidden_pairs:
        i, j = index[a], index[b]
        forbidden[i] |= 1 << j
        forbidden[j] |= 1 << i

    @lru_cache(maxsize=None)
    def dp(mask: int) -> tuple[int, tuple[tuple[int, int], ...]] | None:
        """对 mask 指定的参与者集合求最优完整配对。

        返回 (最小重复相遇次数, 字典序最小的规范化配对元组)；无解返回 None。
        """
        if mask == 0:
            return (0, ())

        lowest = mask & -mask
        i = lowest.bit_length() - 1
        rest = mask ^ lowest

        best: tuple[int, tuple[tuple[int, int], ...]] | None = None
        candidates = rest
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            j = bit.bit_length() - 1
            if forbidden[i] & bit:
                continue
            sub = dp(rest ^ bit)
            if sub is None:
                continue
            sub_cost, sub_pairs = sub
            # i 是 mask 最低位，故 i < j，对内已有序；合并后重排保持规范化。
            merged = tuple(sorted(sub_pairs + ((i, j),)))
            candidate = (sub_cost + weight[i][j], merged)
            if best is None or candidate < best:
                best = candidate
        return best

    result = dp((1 << n) - 1)
    if result is None:
        return None
    total, pairing = result
    return [(ids[i], ids[j]) for i, j in pairing], total
