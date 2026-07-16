from app.services.security_redaction import redact_sensitive_text, redact_sensitive_value


def test_redact_sensitive_text_masks_common_enterprise_secrets():
    text = "邮箱 a@example.com 手机 13900001111 token Bearer abcdefghijklmnop password=hunter2 sk-abcdefghijk"
    redacted = redact_sensitive_text(text)

    assert "a@example.com" not in redacted
    assert "13900001111" not in redacted
    assert "hunter2" not in redacted
    assert "sk-abcdefghijk" not in redacted


def test_redact_sensitive_value_handles_nested_payloads():
    value = {
        "items": [{"email": "person@example.com", "api_key": "nonstandard-value"}],
        "authorization": "opaque-short-value",
    }

    assert redact_sensitive_value(value) == {
        "items": [{"email": "[REDACTED_EMAIL]", "api_key": "[REDACTED_SECRET]"}],
        "authorization": "[REDACTED_SECRET]",
    }
