"""研讨会轮换配对 API 的 FastAPI 入口。"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from .models import PairingRequest, PairingResponse
from .solver import find_optimal_pairing

app = FastAPI(
    title="研讨会轮换配对 API",
    version="1.0.0",
    description=(
        "在给定禁配关系与历史相遇次数的前提下，为 2~16 名（偶数）参与者计算完整配对，"
        "全局最小化重复相遇总次数；同分时按参与者 ID 排序后的配对序列字典序最小者优先。"
    ),
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """重定向到交互式 API 文档。"""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"], summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/pairings",
    response_model=PairingResponse,
    tags=["pairings"],
    summary="计算最优完整配对",
    responses={
        200: {"description": "最优完整配对"},
        422: {"description": "请求参数非法，或禁配关系下无法完成完整配对"},
    },
)
def create_pairings(request: PairingRequest) -> PairingResponse:
    result = find_optimal_pairing(
        request.participants,
        [(pair.a, pair.b) for pair in request.forbidden_pairs],
        [(entry.a, entry.b, entry.count) for entry in request.history],
    )
    if result is None:
        raise HTTPException(
            status_code=422,
            detail="无法完成完整配对：禁配关系使所有参与者无法被同时配成若干对",
        )
    pairs, total = result
    return PairingResponse(pairs=pairs, total_repeat_encounters=total)
