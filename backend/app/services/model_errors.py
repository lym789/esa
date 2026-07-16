from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.services.deadline import DeadlineExceededError


class ModelErrorCategory(str, Enum):
    DEADLINE_EXCEEDED = "deadline_exceeded"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    PROVIDER_5XX = "provider_5xx"
    NETWORK = "network"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ModelErrorClassification:
    category: ModelErrorCategory
    retryable: bool
    counts_toward_circuit: bool


def _status_code(exc: Exception) -> int | None:
    value = getattr(exc, "status_code", None)
    if isinstance(value, int):
        return value
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _classify_single(exc: Exception) -> ModelErrorClassification:
    if isinstance(exc, DeadlineExceededError):
        return ModelErrorClassification(ModelErrorCategory.DEADLINE_EXCEEDED, False, False)

    status_code = _status_code(exc)
    message = str(exc).lower()
    class_name = exc.__class__.__name__.lower()
    if status_code == 429 or "rate limit" in message or "ratelimit" in class_name:
        return ModelErrorClassification(ModelErrorCategory.RATE_LIMIT, True, True)
    if status_code in {401, 403} or "authentication" in class_name:
        return ModelErrorClassification(ModelErrorCategory.AUTHENTICATION, False, False)
    if status_code in {400, 404, 409, 422} or "badrequest" in class_name:
        return ModelErrorClassification(ModelErrorCategory.INVALID_REQUEST, False, False)
    if status_code is not None and status_code >= 500:
        return ModelErrorClassification(ModelErrorCategory.PROVIDER_5XX, True, True)
    if isinstance(exc, TimeoutError) or "timeout" in class_name or "timed out" in message:
        return ModelErrorClassification(ModelErrorCategory.TIMEOUT, True, True)
    if isinstance(exc, ConnectionError) or "connection" in class_name:
        return ModelErrorClassification(ModelErrorCategory.NETWORK, True, True)
    if "invalid json" in message or "valid json" in message or "did not contain" in message:
        return ModelErrorClassification(ModelErrorCategory.INVALID_RESPONSE, True, True)
    return ModelErrorClassification(ModelErrorCategory.UNKNOWN, True, True)


def classify_model_error(exc: Exception) -> ModelErrorClassification:
    current: BaseException | None = exc
    visited: set[int] = set()
    fallback = ModelErrorClassification(ModelErrorCategory.UNKNOWN, True, True)
    while isinstance(current, Exception) and id(current) not in visited:
        visited.add(id(current))
        classification = _classify_single(current)
        if classification.category != ModelErrorCategory.UNKNOWN:
            return classification
        fallback = classification
        current = current.__cause__ or current.__context__
    return fallback
