"""FastAPI application: seminar round rotation pairing service.

Endpoints
---------
* ``GET  /health``   -- liveness probe
* ``GET  /``         -- service summary
* ``POST /pairings`` -- compute the minimum-repeated-meetings perfect matching
* ``GET  /openapi.json`` and interactive docs at ``/docs`` (Swagger) and
  ``/redoc`` are provided automatically by FastAPI.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .models import ErrorResponse, Pair, PairingRequest, PairingResponse
from .solver import find_blocking_participants, solve_pairing

APP_NAME = "Seminar Rotation Pairing API"
APP_VERSION = "1.0.0"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    summary="Globally optimal round pairings under forbidden relations and meeting history",
    description=(
        "Accepts 2–16 (even) participants, forbidden pair relations and past "
        "meeting counts, and returns a complete pairing that satisfies every "
        "forbidden relation while globally minimizing the total number of "
        "repeated meetings. Ties are broken deterministically: pairs are "
        "internally sorted, then the pairing is sorted lexicographically by "
        "participant ID and the smallest sequence wins. If no complete pairing "
        "exists, HTTP 422 is returned with an explanation."
    ),
    contact={"name": "Pairing Service"},
    license_info={"name": "MIT"},
)


def _normalize_key(a: str, b: str) -> tuple[str, str]:
    """Undirected pair key with ascending endpoints."""
    return (a, b) if a < b else (b, a)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Service banner and documentation links."""
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "health": "/health",
        "pairings": "POST /pairings",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe; always 200 while the process can serve requests."""
    return {"status": "ok", "service": APP_NAME, "version": APP_VERSION}


@app.post(
    "/pairings",
    response_model=PairingResponse,
    tags=["pairings"],
    status_code=200,
    responses={
        422: {"model": ErrorResponse, "description": "No complete pairing satisfies the constraints"},
    },
    summary="Compute the optimal complete pairing",
)
def create_pairing(request: PairingRequest) -> PairingResponse | JSONResponse:
    # Normalize relations into undirected keys. Duplicate forbidden entries
    # collapse; duplicate meeting records are summed.
    forbidden: set[tuple[str, str]] = set()
    for rel in request.forbidden_pairs:
        forbidden.add(_normalize_key(rel.a, rel.b))

    meetings: dict[tuple[str, str], int] = defaultdict(int)
    for meeting in request.past_meetings:
        meetings[_normalize_key(meeting.a, meeting.b)] += meeting.count

    result = solve_pairing(request.participants, forbidden, dict(meetings))
    if result is None:
        blocking = find_blocking_participants(request.participants, forbidden)
        if blocking:
            detail = (
                "无法完成完整配对：以下参与者与其余所有人均为禁配关系，无法安排搭档: "
                + ", ".join(blocking)
            )
        else:
            detail = (
                "无法完成完整配对：在给定禁配关系下不存在覆盖全部 "
                f"{len(request.participants)} 名参与者的完美配对（"
                "禁配关系造成了无法同时满足的子集冲突），请调整禁配规则后重试。"
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": "infeasible",
                "detail": detail,
                "blocking_participants": blocking,
            },
        )

    pairs, total = result
    return PairingResponse(
        pairs=[Pair(a=a, b=b) for a, b in pairs],
        total_repeated_meetings=total,
        num_pairs=len(pairs),
    )
