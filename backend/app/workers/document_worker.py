from __future__ import annotations

import argparse
import time

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.document_job_service import run_next_processing_job


def run_once() -> bool:
    db = SessionLocal()
    try:
        return run_next_processing_job(db) is not None
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process durable document indexing jobs")
    parser.add_argument("--once", action="store_true", help="process at most one queued job")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    init_db()

    while True:
        processed = run_once()
        if args.once:
            return
        if not processed:
            time.sleep(max(0.2, args.poll_seconds))


if __name__ == "__main__":
    main()
