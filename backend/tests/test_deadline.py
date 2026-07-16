import pytest

from app.services.deadline import (
    DeadlineExceededError,
    deadline_budget,
    ensure_time_remaining,
    remaining_seconds,
    remaining_timeout,
)


def test_deadline_clamps_downstream_timeout_and_cannot_be_extended():
    with deadline_budget(10, now=100):
        assert remaining_seconds(now=103) == 7
        assert remaining_timeout(30, now=103) == 7
        with deadline_budget(20, now=103):
            assert remaining_seconds(now=104) == 6


def test_deadline_raises_when_budget_is_exhausted_and_resets_context():
    with deadline_budget(1, now=100):
        with pytest.raises(DeadlineExceededError):
            remaining_timeout(30, now=101)
        with pytest.raises(DeadlineExceededError, match="dense retrieval"):
            ensure_time_remaining("dense retrieval", now=101)

    assert remaining_seconds(now=101) is None
