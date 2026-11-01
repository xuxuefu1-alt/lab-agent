from __future__ import annotations

import time
from dataclasses import dataclass


class RequestDeadlineExceeded(TimeoutError):
    """表示当前 AI 请求已经超过总预算。"""


@dataclass(frozen=True)
class RequestBudget:
    """保存单次请求的截止时间。"""

    deadline: float

    @classmethod
    def start(cls, timeout_seconds: float) -> "RequestBudget":
        return cls(time.monotonic() + max(0.1, timeout_seconds))

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def check(self, stage: str = "ai_request") -> float:
        remaining = self.remaining()
        if remaining <= 0:
            raise RequestDeadlineExceeded(f"AI request deadline exceeded at {stage}")
        return remaining
