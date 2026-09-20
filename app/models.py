"""API 请求/响应的 Pydantic 模型定义。

参与者 ID 统一规范化为非空字符串（整数 ID 会被转换为字符串形式），
配对相关的排序与比较均基于该字符串形式。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = ["Pair", "HistoryEntry", "PairingRequest", "PairingResponse"]


def _normalize_id(value: Any) -> str:
    """将参与者 ID 规范化为非空字符串；非法类型抛出 ValueError。"""
    if isinstance(value, bool):  # bool 是 int 的子类，需显式拒绝
        raise ValueError("参与者 ID 必须是字符串或整数")
    if isinstance(value, (str, int)):
        text = str(value).strip()
        if not text:
            raise ValueError("参与者 ID 不能为空字符串")
        return text
    raise ValueError("参与者 ID 必须是字符串或整数")


class Pair(BaseModel):
    """一对无序的参与者。"""

    a: str = Field(description="参与者 ID")
    b: str = Field(description="参与者 ID")

    @field_validator("a", "b", mode="before")
    @classmethod
    def _coerce_id(cls, value: Any) -> str:
        return _normalize_id(value)

    @model_validator(mode="after")
    def _check_distinct(self) -> "Pair":
        if self.a == self.b:
            raise ValueError("同一对中的两个参与者 ID 不能相同")
        return self


class HistoryEntry(Pair):
    """一对参与者的历史相遇次数。"""

    count: int = Field(ge=0, description="两人历史上已相遇的次数，非负整数")


class PairingRequest(BaseModel):
    """POST /pairings 请求体。"""

    participants: list[str] = Field(
        min_length=2,
        max_length=16,
        description="参与者 ID 列表，长度为 2~16 的偶数且互不重复",
    )
    forbidden_pairs: list[Pair] = Field(
        default_factory=list,
        description="禁配关系列表，列表中的两人不得被配成一对",
    )
    history: list[HistoryEntry] = Field(
        default_factory=list,
        description="历史相遇记录；同一对出现多次时次数累加",
    )

    @field_validator("participants", mode="before")
    @classmethod
    def _coerce_participants(cls, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return [_normalize_id(item) for item in value]
        return value

    @field_validator("participants")
    @classmethod
    def _check_participants(cls, value: list[str]) -> list[str]:
        if len(value) % 2 != 0:
            raise ValueError("参与者数量必须为偶数")
        if len(set(value)) != len(value):
            raise ValueError("参与者 ID 必须唯一，存在重复项")
        return value

    @model_validator(mode="after")
    def _check_references(self) -> "PairingRequest":
        known = set(self.participants)
        for pair in self.forbidden_pairs:
            unknown = [x for x in (pair.a, pair.b) if x not in known]
            if unknown:
                raise ValueError(f"禁配关系引用了未登记的参与者: {unknown}")
        for entry in self.history:
            unknown = [x for x in (entry.a, entry.b) if x not in known]
            if unknown:
                raise ValueError(f"历史相遇记录引用了未登记的参与者: {unknown}")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "participants": ["alice", "bob", "carol", "dave"],
                    "forbidden_pairs": [{"a": "alice", "b": "bob"}],
                    "history": [
                        {"a": "alice", "b": "carol", "count": 2},
                        {"a": "bob", "b": "dave", "count": 1},
                    ],
                }
            ]
        }
    }


class PairingResponse(BaseModel):
    """POST /pairings 成功响应体。"""

    pairs: list[tuple[str, str]] = Field(
        description="最优配对序列：每对内部按 ID 升序，各对之间按字典序排列"
    )
    total_repeat_encounters: int = Field(
        ge=0,
        description="该配对方案的重复相遇总次数（全局最小值）",
    )
