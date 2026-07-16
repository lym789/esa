from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence


ALLOWED_ANSWERABILITY = {"answerable", "partial", "unanswerable"}


@dataclass(frozen=True)
class Evidence:
    index: int
    chunk_uid: str
    content: str


@dataclass(frozen=True)
class ClaimValidation:
    text: str
    citation_ids: list[str]
    supported: bool
    reason: str


@dataclass(frozen=True)
class CitationValidationReport:
    valid: bool
    answerability: str
    selected_indices: list[int]
    claims: list[ClaimValidation]
    error: str | None = None


def _terms(text: str) -> set[str]:
    lowered = text.lower()
    ascii_terms = set(re.findall(r"[a-z0-9]+", lowered))
    cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
    return ascii_terms | {left + right for left, right in zip(cjk, cjk[1:])}


def _resolve_citation(value: Any, evidence: Sequence[Evidence]) -> Evidence | None:
    raw = str(value).strip()
    match = re.fullmatch(r"\[(\d+)\]|(\d+)", raw)
    if match:
        index = int(match.group(1) or match.group(2))
        return next((item for item in evidence if item.index == index), None)
    return next((item for item in evidence if item.chunk_uid == raw), None)


def _claim_supported(text: str, cited: Sequence[Evidence]) -> tuple[bool, str]:
    combined = "\n".join(item.content for item in cited)
    numeric_facts = re.findall(r"(?<![\w-])\d+(?:[.,]\d+)?%?", text)
    missing_numbers = [value for value in numeric_facts if value not in combined]
    if missing_numbers:
        return False, f"引用中缺少数字事实：{', '.join(missing_numbers)}"

    claim_terms = _terms(text)
    evidence_terms = _terms(combined)
    if not claim_terms:
        return False, "声明没有可校验内容"
    coverage = len(claim_terms & evidence_terms) / len(claim_terms)
    if coverage < 0.1:
        return False, "声明与引用内容缺少可验证重叠"
    return True, "引用内容支持该声明"


def validate_claim_citations(
    payload: dict[str, Any],
    evidence: Sequence[Evidence],
) -> CitationValidationReport:
    answerability = payload.get("answerability", "answerable")
    if answerability not in ALLOWED_ANSWERABILITY:
        return CitationValidationReport(False, "unanswerable", [], [], "unsupported answerability")
    if answerability == "unanswerable":
        return CitationValidationReport(True, answerability, [], [])

    raw_claims = payload.get("claims")
    if raw_claims is None:
        raw_claims = [
            {
                "text": payload.get("answer", ""),
                "citation_ids": payload.get("citations", []),
            }
        ]
    if not isinstance(raw_claims, list) or not raw_claims:
        return CitationValidationReport(False, answerability, [], [], "claims are required")

    validations: list[ClaimValidation] = []
    selected_indices: list[int] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            return CitationValidationReport(False, answerability, [], validations, "claim must be an object")
        text = raw_claim.get("text")
        citation_ids = raw_claim.get("citation_ids")
        if not isinstance(text, str) or not text.strip():
            return CitationValidationReport(False, answerability, [], validations, "claim text is required")
        if not isinstance(citation_ids, list) or not citation_ids:
            validations.append(ClaimValidation(text, [], False, "声明没有引用"))
            continue

        resolved = [_resolve_citation(value, evidence) for value in citation_ids]
        if any(item is None for item in resolved):
            validations.append(
                ClaimValidation(text, [str(value) for value in citation_ids], False, "引用不存在")
            )
            continue
        cited = [item for item in resolved if item is not None]
        supported, reason = _claim_supported(text, cited)
        validations.append(
            ClaimValidation(text, [str(value) for value in citation_ids], supported, reason)
        )
        if supported:
            for item in cited:
                if item.index not in selected_indices:
                    selected_indices.append(item.index)

    valid = bool(validations) and all(item.supported for item in validations)
    return CitationValidationReport(
        valid=valid,
        answerability=answerability,
        selected_indices=selected_indices,
        claims=validations,
        error=None if valid else "one or more claims are unsupported",
    )

