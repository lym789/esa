from app.services.rag_citation_service import Evidence, validate_claim_citations


EVIDENCE = [
    Evidence(1, "chunk-vpn", "VPN 登录失败时，请检查统一身份认证和网络连接。"),
    Evidence(2, "chunk-leave", "员工每年享有 10 天年假。"),
]


def test_claim_validator_accepts_supported_claim_and_chunk_uid():
    report = validate_claim_citations(
        {
            "answerability": "answerable",
            "answer": "请检查统一身份认证。",
            "claims": [{"text": "请检查统一身份认证。", "citation_ids": ["chunk-vpn"]}],
        },
        EVIDENCE,
    )

    assert report.valid is True
    assert report.selected_indices == [1]


def test_claim_validator_rejects_unsupported_numeric_fact():
    report = validate_claim_citations(
        {
            "answerability": "answerable",
            "answer": "员工每年享有 20 天年假。",
            "claims": [{"text": "员工每年享有 20 天年假。", "citation_ids": ["chunk-leave"]}],
        },
        EVIDENCE,
    )

    assert report.valid is False
    assert "20" in report.claims[0].reason


def test_claim_validator_supports_legacy_index_citations():
    report = validate_claim_citations(
        {"answer": "VPN 登录需要检查网络。", "citations": ["[1]"]},
        EVIDENCE,
    )

    assert report.valid is True
    assert report.selected_indices == [1]


def test_unanswerable_response_does_not_require_claims():
    report = validate_claim_citations(
        {"answerability": "unanswerable", "answer": "无法确认。", "claims": []},
        EVIDENCE,
    )

    assert report.valid is True
    assert report.selected_indices == []

