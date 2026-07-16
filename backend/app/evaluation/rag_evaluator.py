from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.db.session import SessionLocal
from app.models.user import User
from app.services.rag_service import search

from .rag_metrics import aggregate_rankings, evaluate_ranking


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    query: str
    relevant_documents: list[str]
    user_email: str | None = None
    knowledge_base_id: str | None = None


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Evaluation case requires non-empty {key}")
    return value.strip()


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        relevant = payload.get("relevant_documents")
        if not isinstance(relevant, list) or not relevant or not all(isinstance(item, str) for item in relevant):
            raise ValueError(f"Line {line_number} requires relevant_documents")
        cases.append(
            EvaluationCase(
                case_id=_required_string(payload, "case_id"),
                query=_required_string(payload, "query"),
                relevant_documents=relevant,
                user_email=payload.get("user_email"),
                knowledge_base_id=payload.get("knowledge_base_id"),
            )
        )
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases


def run_evaluation(path: Path, *, k: int, threshold: float) -> dict[str, Any]:
    cases = load_cases(path)
    case_results: list[dict[str, Any]] = []
    ranking_metrics = []

    db = SessionLocal()
    try:
        for case in cases:
            user = None
            if case.user_email:
                user = db.query(User).filter(User.email == case.user_email).first()
                if user is None:
                    raise ValueError(f"Unknown evaluation user: {case.user_email}")
            results = search(
                db=db,
                query=case.query,
                top_k=k,
                similarity_threshold=threshold,
                user=user,
                knowledge_base_id=case.knowledge_base_id,
            )
            retrieved = [result.document_name for result in results]
            metrics = evaluate_ranking(retrieved, case.relevant_documents, k=k)
            ranking_metrics.append(metrics)
            case_results.append(
                {
                    "case_id": case.case_id,
                    "query": case.query,
                    "retrieved_documents": retrieved,
                    "relevant_documents": case.relevant_documents,
                    "metrics": asdict(metrics),
                }
            )
    finally:
        db.close()

    return {
        "dataset": str(path),
        "k": k,
        "threshold": threshold,
        "aggregate": asdict(aggregate_rankings(ranking_metrics)),
        "cases": case_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval against a JSONL golden set")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_evaluation(args.dataset, k=args.k, threshold=args.threshold)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()

