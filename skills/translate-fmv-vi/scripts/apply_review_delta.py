#!/usr/bin/env python3
"""Apply reviewer delta revisions to draft translations to generate approved files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from pipeline_common import read_jsonl, write_jsonl


def apply_review_delta(project_dir: Path, job_id: str) -> Path:
    draft_file = project_dir / "translations" / "drafts" / f"{job_id}.draft.jsonl"
    if not draft_file.exists():
        raise FileNotFoundError(f"Missing draft file: {draft_file}")

    review_file = project_dir / "reviews" / f"{job_id}.review.jsonl"
    revisions: dict[str, str] = {}

    if review_file.exists():
        for item in read_jsonl(review_file):
            if item.get("__type__") == "review_meta":
                continue
            entry_id = item.get("id")
            revised_text = item.get("revised_translation") or item.get("translation")
            if entry_id and revised_text:
                revisions[entry_id] = revised_text

    draft_records = read_jsonl(draft_file)
    approved_records: list[dict[str, Any]] = []

    for r in draft_records:
        entry_id = r["id"]
        final_trans = revisions.get(entry_id, r.get("translation", ""))
        approved_records.append({
            "id": entry_id,
            "translation": final_trans,
            "was_revised": entry_id in revisions,
        })

    approved_dir = project_dir / "translations" / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    approved_file = approved_dir / f"{job_id}.approved.jsonl"
    write_jsonl(approved_file, approved_records)

    print(f"[OK] Applied {len(revisions)} review edits for {job_id} -> {approved_file}")
    return approved_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply reviewer revisions to draft.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, required=True, help="Job identifier")
    args = parser.parse_args()

    apply_review_delta(args.project_dir, args.job_id)


if __name__ == "__main__":
    main()
