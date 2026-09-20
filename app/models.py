"""Pydantic request/response models for the pairing API."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

#: participant count bounds enforced by the API (even count, 2..16)
MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 16


class ForbiddenPair(BaseModel):
    """A pair of participants that must not be matched together."""

    a: str = Field(..., min_length=1, max_length=128, description="First participant ID")
    b: str = Field(..., min_length=1, max_length=128, description="Second participant ID")

    @model_validator(mode="after")
    def _distinct(self) -> "ForbiddenPair":
        if self.a == self.b:
            raise ValueError("a forbidden pair must reference two different participants")
        return self


class MeetingCount(BaseModel):
    """How many times two participants have been paired before."""

    a: str = Field(..., min_length=1, max_length=128, description="First participant ID")
    b: str = Field(..., min_length=1, max_length=128, description="Second participant ID")
    count: int = Field(..., ge=0, le=1_000_000, description="Number of past meetings (non-negative)")

    @model_validator(mode="after")
    def _distinct(self) -> "MeetingCount":
        if self.a == self.b:
            raise ValueError("a meeting record must reference two different participants")
        return self


class PairingRequest(BaseModel):
    """Request body for ``POST /pairings``."""

    participants: list[str] = Field(
        ...,
        min_length=MIN_PARTICIPANTS,
        max_length=MAX_PARTICIPANTS,
        description="Participant IDs; must be unique and even in number (2..16)",
    )
    forbidden_pairs: list[ForbiddenPair] = Field(
        default_factory=list,
        description="Relations that may never appear in a pairing",
    )
    past_meetings: list[MeetingCount] = Field(
        default_factory=list,
        description="Past meeting counts per pair; repeated entries are summed",
    )

    @model_validator(mode="after")
    def _validate_request(self) -> "PairingRequest":
        # Trim whitespace on IDs; reject entries that become empty.
        trimmed = [pid.strip() for pid in self.participants]
        for pid in trimmed:
            if not pid:
                raise ValueError("participant IDs must not be empty or blank")
        self.participants = trimmed

        if len(trimmed) % 2 != 0:
            raise ValueError(
                f"number of participants must be even, got {len(trimmed)}"
            )
        if len(set(trimmed)) != len(trimmed):
            dupes = sorted({pid for pid in trimmed if trimmed.count(pid) > 1})
            raise ValueError(f"participant IDs must be unique; duplicates: {dupes}")

        known = set(trimmed)
        for rel in self.forbidden_pairs:
            rel.a, rel.b = rel.a.strip(), rel.b.strip()
            if rel.a == rel.b:
                raise ValueError(
                    f"a forbidden pair must reference two different participants: {rel.a!r}"
                )
            if rel.a not in known or rel.b not in known:
                raise ValueError(
                    f"forbidden pair {rel.a!r}/{rel.b!r} references an unknown participant"
                )
        for meeting in self.past_meetings:
            meeting.a, meeting.b = meeting.a.strip(), meeting.b.strip()
            if meeting.a == meeting.b:
                raise ValueError(
                    f"a meeting record must reference two different participants: {meeting.a!r}"
                )
            if meeting.a not in known or meeting.b not in known:
                raise ValueError(
                    f"past meeting {meeting.a!r}/{meeting.b!r} references an unknown participant"
                )
        return self


class Pair(BaseModel):
    """A single matched pair, with IDs ordered ascending."""

    a: str = Field(..., description="Lower participant ID of the pair")
    b: str = Field(..., description="Higher participant ID of the pair")


class PairingResponse(BaseModel):
    """Optimal pairing returned by ``POST /pairings``."""

    pairs: list[Pair] = Field(..., description="Matched pairs, sorted lexicographically by (a, b)")
    total_repeated_meetings: int = Field(
        ..., description="Sum of past meeting counts over the matched pairs (global minimum)"
    )
    num_pairs: int = Field(..., description="Number of pairs produced")


class ErrorResponse(BaseModel):
    """Error body used for 422 infeasibility responses."""

    detail: str = Field(..., description="Human-readable explanation of the failure")
    error: str = Field(default="infeasible", description="Stable machine-readable error code")
    blocking_participants: list[str] = Field(
        default_factory=list,
        description="Participants that cannot be matched with anyone, if any",
    )
