from app.services.deadline import DeadlineExceededError
from app.services.model_errors import ModelErrorCategory, classify_model_error


class HTTPFailure(RuntimeError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


def test_model_error_classification_drives_retry_and_circuit_policy():
    cases = [
        (DeadlineExceededError("budget"), ModelErrorCategory.DEADLINE_EXCEEDED, False, False),
        (TimeoutError("timed out"), ModelErrorCategory.TIMEOUT, True, True),
        (HTTPFailure(429), ModelErrorCategory.RATE_LIMIT, True, True),
        (HTTPFailure(401), ModelErrorCategory.AUTHENTICATION, False, False),
        (HTTPFailure(400), ModelErrorCategory.INVALID_REQUEST, False, False),
        (HTTPFailure(503), ModelErrorCategory.PROVIDER_5XX, True, True),
        (ConnectionError("connection reset"), ModelErrorCategory.NETWORK, True, True),
        (RuntimeError("response was not valid JSON"), ModelErrorCategory.INVALID_RESPONSE, True, True),
    ]

    for error, category, retryable, counts_toward_circuit in cases:
        classification = classify_model_error(error)
        assert classification.category == category
        assert classification.retryable is retryable
        assert classification.counts_toward_circuit is counts_toward_circuit


def test_model_error_classification_follows_wrapped_provider_cause():
    provider_error = HTTPFailure(401)
    try:
        raise RuntimeError("LLM call failed") from provider_error
    except RuntimeError as wrapped:
        classification = classify_model_error(wrapped)

    assert classification.category == ModelErrorCategory.AUTHENTICATION
    assert classification.counts_toward_circuit is False
