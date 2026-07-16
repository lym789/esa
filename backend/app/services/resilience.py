from __future__ import annotations

from dataclasses import dataclass
from threading import BoundedSemaphore, RLock
from time import monotonic
from typing import Any, Callable, TypeVar

from app.core.config import Settings, get_settings
from app.services.model_errors import classify_model_error


T = TypeVar("T")


class ResilienceError(RuntimeError):
    """Base error for local reliability controls."""


class CircuitOpenError(ResilienceError):
    """Raised when a provider circuit is open or already probing half-open."""


class BulkheadFullError(ResilienceError):
    """Raised when a component has exhausted its concurrency budget."""


@dataclass(frozen=True)
class CircuitSnapshot:
    state: str
    consecutive_failures: int
    opened_count: int
    rejected_count: int


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int,
        recovery_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._clock = clock
        self._lock = RLock()
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open_probe_active = False
        self._opened_count = 0
        self._rejected_count = 0

    def before_call(self) -> None:
        with self._lock:
            if self._state == "closed":
                return
            now = self._clock()
            if self._state == "open":
                assert self._opened_at is not None
                if now - self._opened_at < self.recovery_seconds:
                    self._rejected_count += 1
                    raise CircuitOpenError("component circuit is open")
                self._state = "half_open"
            if self._half_open_probe_active:
                self._rejected_count += 1
                raise CircuitOpenError("component circuit is half-open and already probing")
            self._half_open_probe_active = True

    def record_success(self) -> None:
        with self._lock:
            self._state = "closed"
            self._consecutive_failures = 0
            self._opened_at = None
            self._half_open_probe_active = False

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            should_open = (
                self._state == "half_open"
                or self._consecutive_failures >= self.failure_threshold
            )
            self._half_open_probe_active = False
            if should_open:
                self._state = "open"
                self._opened_at = self._clock()
                self._opened_count += 1

    def record_ignored_failure(self) -> None:
        with self._lock:
            self._half_open_probe_active = False
            if self._state == "half_open":
                self._state = "open"
                self._opened_at = self._clock()

    def snapshot(self) -> CircuitSnapshot:
        with self._lock:
            return CircuitSnapshot(
                state=self._state,
                consecutive_failures=self._consecutive_failures,
                opened_count=self._opened_count,
                rejected_count=self._rejected_count,
            )


class ComponentGuard:
    def __init__(
        self,
        *,
        failure_threshold: int,
        recovery_seconds: float,
        max_concurrency: int,
        bulkhead_timeout_seconds: float,
    ) -> None:
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_seconds=recovery_seconds,
        )
        self._semaphore = BoundedSemaphore(max_concurrency)
        self._bulkhead_timeout_seconds = bulkhead_timeout_seconds
        self._lock = RLock()
        self._calls = 0
        self._successes = 0
        self._failures = 0
        self._bulkhead_rejections = 0
        self._error_categories: dict[str, int] = {}
        self._in_flight = 0
        self._max_in_flight = 0

    def execute(self, operation: Callable[[], T]) -> T:
        acquired = self._semaphore.acquire(timeout=self._bulkhead_timeout_seconds)
        if not acquired:
            with self._lock:
                self._bulkhead_rejections += 1
            raise BulkheadFullError("component concurrency limit reached")
        with self._lock:
            self._in_flight += 1
            self._max_in_flight = max(self._max_in_flight, self._in_flight)
        try:
            self.breaker.before_call()
            with self._lock:
                self._calls += 1
            try:
                result = operation()
            except Exception as exc:
                classification = classify_model_error(exc)
                if classification.counts_toward_circuit:
                    self.breaker.record_failure()
                else:
                    self.breaker.record_ignored_failure()
                with self._lock:
                    self._failures += 1
                    category = classification.category.value
                    self._error_categories[category] = self._error_categories.get(category, 0) + 1
                raise
            self.breaker.record_success()
            with self._lock:
                self._successes += 1
            return result
        finally:
            with self._lock:
                self._in_flight -= 1
            self._semaphore.release()

    def snapshot(self) -> dict[str, Any]:
        circuit = self.breaker.snapshot()
        with self._lock:
            return {
                "state": circuit.state,
                "consecutive_failures": circuit.consecutive_failures,
                "opened_count": circuit.opened_count,
                "circuit_rejections": circuit.rejected_count,
                "calls": self._calls,
                "successes": self._successes,
                "failures": self._failures,
                "bulkhead_rejections": self._bulkhead_rejections,
                "in_flight": self._in_flight,
                "max_in_flight": self._max_in_flight,
                "error_categories": dict(self._error_categories),
            }


class ResilienceRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._guards: dict[str, ComponentGuard] = {}

    def execute(
        self,
        component: str,
        operation: Callable[[], T],
        *,
        settings: Settings,
        max_concurrency: int,
    ) -> T:
        with self._lock:
            guard = self._guards.get(component)
            if guard is None:
                guard = ComponentGuard(
                    failure_threshold=settings.model_circuit_failure_threshold,
                    recovery_seconds=settings.model_circuit_recovery_seconds,
                    max_concurrency=max_concurrency,
                    bulkhead_timeout_seconds=settings.model_bulkhead_timeout_seconds,
                )
                self._guards[component] = guard
        return guard.execute(operation)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            guards = dict(self._guards)
        return {component: guard.snapshot() for component, guard in guards.items()}

    def reset(self) -> None:
        with self._lock:
            self._guards.clear()


resilience_registry = ResilienceRegistry()


def execute_resilient(
    component: str,
    operation: Callable[[], T],
    *,
    settings: Settings | None = None,
    max_concurrency: int,
) -> T:
    active_settings = settings or get_settings()
    return resilience_registry.execute(
        component,
        operation,
        settings=active_settings,
        max_concurrency=max_concurrency,
    )
