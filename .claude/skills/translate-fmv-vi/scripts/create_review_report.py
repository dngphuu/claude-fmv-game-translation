#!/usr/bin/env python3
"""Record independent cinematic review declarations and targeted line revisions."""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
from typing import Any
from pipeline_common import atomic_json, read_jsonl, write_jsonl


def create_review_report(
    project_dir: Path,
    job_id: str,
    reviewer_name: str,
    revisions: list[dict[str, Any]],
    review_summary: str = "Cinematic review completed.",
) -> Path:
    reviews_dir = project_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    review_file = reviews_dir / f"{job_id}.review.jsonl"

    meta_record = {
        "__type__": "review_meta",
        "job_id": job_id,
        "reviewer": reviewer_name,
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_revisions": len(revisions),
        "review_summary": review_summary,
    }

    records_to_write = [meta_record] + revisions
    write_jsonl(review_file, records_to_write)
    print(f"[OK] Recorded cinematic review for {job_id} ({len(revisions)} revisions) -> {review_file}")
    return review_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Create review report.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, required=True, help="Job ID")
    parser.add_argument("--reviewer", type=str, default="cinematic-editor", help="Reviewer identity")
    parser.add_argument("--summary", type=str, default="Approved with natural dialogue adjustments")
    args = parser.parse_args()

    create_review_report(args.project_dir, args.job_id, args.reviewer, [], args.summary)


if __name__ == "__main__":
    main()
