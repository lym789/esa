from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.core.config import Settings
from app.services.embedding_client import (
    EmbeddingClientError,
    FakeEmbeddingClient,
    ResilientEmbeddingClient,
)
from app.services.llm_client import FakeLLMClient, LLMClientError, ResilientLLMClient
from app.services.resilience import (
    BulkheadFullError,
    CircuitBreaker,
    CircuitOpenError,
    ComponentGuard,
    resilience_registry,
)


def test_circuit_breaker_opens_fast_fails_and_recovers_with_single_probe():
    now = [100.0]
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_seconds=10,
        clock=lambda: now[0],
    )

    breaker.before_call()
    breaker.record_failure()
    breaker.before_call()
    breaker.record_failure()

    assert breaker.snapshot().state == "open"
    with pytest.raises(CircuitOpenError):
        breaker.before_call()

    now[0] += 10
    breaker.before_call()
    assert breaker.snapshot().state == "half_open"
    with pytest.raises(CircuitOpenError):
        breaker.before_call()
    breaker.record_success()

    assert breaker.snapshot().state == "closed"
    assert breaker.snapshot().consecutive_failures == 0


def test_component_circuits_are_isolated_by_provider_key():
    resilience_registry.reset()
    settings = Settings(
        _env_file=None,
        model_circuit_failure_threshold=1,
        model_circuit_recovery_seconds=30,
    )

    with pytest.raises(RuntimeError):
        resilience_registry.execute(
            "llm:provider-a",
            lambda: (_ for _ in ()).throw(RuntimeError("down")),
            settings=settings,
            max_concurrency=1,
        )
    result = resilience_registry.execute(
        "embedding:provider-b",
        lambda: "ok",
        settings=settings,
        max_concurrency=1,
    )

    snapshot = resilience_registry.snapshot()
    assert result == "ok"
    assert snapshot["llm:provider-a"]["state"] == "open"
    assert snapshot["embedding:provider-b"]["state"] == "closed"


def test_bulkhead_rejects_excess_concurrency_without_opening_circuit():
    guard = ComponentGuard(
        failure_threshold=2,
        recovery_seconds=30,
        max_concurrency=1,
        bulkhead_timeout_seconds=0,
    )
    started = Event()
    release = Event()

    def blocking_operation():
        started.set()
        release.wait(timeout=2)
        return "done"

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(guard.execute, blocking_operation)
        assert started.wait(timeout=1)
        with pytest.raises(BulkheadFullError):
            guard.execute(lambda: "should-not-run")
        release.set()
        assert future.result(timeout=2) == "done"

    snapshot = guard.snapshot()
    assert snapshot["bulkhead_rejections"] == 1
    assert snapshot["state"] == "closed"
    assert snapshot["max_in_flight"] == 1


def test_llm_wrapper_fast_fails_after_provider_threshold():
    resilience_registry.reset()
    settings = Settings(
        _env_file=None,
        model_circuit_failure_threshold=1,
        model_circuit_recovery_seconds=30,
    )
    delegate = FakeLLMClient(error=LLMClientError("provider unavailable"))
    client = ResilientLLMClient(delegate, settings)

    with pytest.raises(LLMClientError, match="provider unavailable"):
        client.generate_json([{"role": "user", "content": "test"}])
    with pytest.raises(LLMClientError, match="reliability guard rejected"):
        client.generate_json([{"role": "user", "content": "test"}])

    assert len(delegate.calls) == 1


def test_embedding_wrapper_has_independent_fast_failure():
    resilience_registry.reset()
    settings = Settings(
        _env_file=None,
        model_circuit_failure_threshold=1,
        model_circuit_recovery_seconds=30,
    )

    class FailingEmbeddingClient(FakeEmbeddingClient):
        def embed_texts(self, texts):
            del texts
            raise EmbeddingClientError("embedding unavailable")

    delegate = FailingEmbeddingClient()
    client = ResilientEmbeddingClient(delegate, settings)

    with pytest.raises(EmbeddingClientError, match="embedding unavailable"):
        client.embed_texts(["test"])
    with pytest.raises(EmbeddingClientError, match="reliability guard rejected"):
        client.embed_texts(["test"])

    snapshot = resilience_registry.snapshot()
    assert snapshot[client.component]["state"] == "open"


def test_invalid_request_is_observed_without_opening_provider_circuit():
    class InvalidRequest(RuntimeError):
        status_code = 400

    guard = ComponentGuard(
        failure_threshold=1,
        recovery_seconds=30,
        max_concurrency=1,
        bulkhead_timeout_seconds=0,
    )

    with pytest.raises(InvalidRequest):
        guard.execute(lambda: (_ for _ in ()).throw(InvalidRequest("bad input")))

    snapshot = guard.snapshot()
    assert snapshot["state"] == "closed"
    assert snapshot["consecutive_failures"] == 0
    assert snapshot["error_categories"] == {"invalid_request": 1}
