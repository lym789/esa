from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from time import monotonic
from typing import Iterator


class DeadlineExceededError(TimeoutError):
    """Raised when the shared request time budget has been exhausted."""


_deadline_at: ContextVar[float | None] = ContextVar("request_deadline_at", default=None)


def set_deadline(seconds: float, *, now: float | None = None) -> Token:
    current_time = monotonic() if now is None else now
    proposed = current_time + max(0.0, seconds)
    current = _deadline_at.get()
    return _deadline_at.set(min(current, proposed) if current is not None else proposed)


def reset_deadline(token: Token) -> None:
    _deadline_at.reset(token)


@contextmanager
def deadline_budget(seconds: float, *, now: float | None = None) -> Iterator[None]:
    token = set_deadline(seconds, now=now)
    try:
        yield
    finally:
        reset_deadline(token)


def remaining_seconds(*, now: float | None = None) -> float | None:
    deadline = _deadline_at.get()
    if deadline is None:
        return None
    current_time = monotonic() if now is None else now
    return max(0.0, deadline - current_time)


def remaining_timeout(default_seconds: float, *, now: float | None = None) -> float:
    remaining = remaining_seconds(now=now)
    if remaining is None:
        return default_seconds
    if remaining <= 0:
        raise DeadlineExceededError("request deadline exceeded")
    return min(default_seconds, remaining)


def ensure_time_remaining(stage: str = "operation", *, now: float | None = None) -> None:
    remaining = remaining_seconds(now=now)
    if remaining is not None and remaining <= 0:
        raise DeadlineExceededError(f"request deadline exceeded before {stage}")
