from __future__ import annotations

import re
from dataclasses import dataclass


INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|system)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"忽略.{0,12}(系统|之前|以上).{0,8}(指令|规则|提示)"),
    re.compile(r"(输出|泄露|显示).{0,8}(系统提示|system prompt|密钥|其他用户资料)", re.IGNORECASE),
    re.compile(r"执行以下(命令|指令)"),
    re.compile(r"BEGIN\s+SYSTEM", re.IGNORECASE),
)


@dataclass(frozen=True)
class SecurityFinding:
    blocked: bool
    category: str | None = None
    reason: str | None = None


def detect_prompt_injection(text: str) -> SecurityFinding:
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return SecurityFinding(
                blocked=True,
                category="prompt_injection",
                reason="输入包含试图改变系统规则或提取受保护信息的指令",
            )
    return SecurityFinding(blocked=False)

