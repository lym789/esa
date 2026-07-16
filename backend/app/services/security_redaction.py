from __future__ import annotations

import re
from typing import Any


REDACTION_RULES = (
    (re.compile(r"(?<![\w.-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.IGNORECASE), "[REDACTED_EMAIL]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[REDACTED_PHONE]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]{12,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)((?:password|passwd|密码)\s*[:=]\s*)\S+"), r"\1[REDACTED_SECRET]"),
)
SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?:password|passwd|secret|token|api[_-]?key|authorization|cookie)", re.IGNORECASE
)


def redact_sensitive_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value
    for pattern, replacement in REDACTION_RULES:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_sensitive_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED_SECRET]"
                if SENSITIVE_FIELD_PATTERN.search(str(key))
                else redact_sensitive_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_value(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive_value(item) for item in value]
    return value
