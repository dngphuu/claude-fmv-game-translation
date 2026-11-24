#!/usr/bin/env python3
"""Merge approved translation jobs into final.jsonl and prepare release manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any
from pipeline_common import atomic_json, digest_value, read_jsonl, write_jsonl


def merge_jobs(project_dir: Path) -> Path:
    jobs_file = project_dir / "planning" / "jobs.jsonl"
    source_file = project_dir / "extracted" / "source.jsonl"

    if not jobs_file.exists() or not source_file.exists():
        raise FileNotFoundError("Missing jobs.jsonl or source.jsonl")

    jobs = read_jsonl(jobs_file)
    source_records = read_jsonl(source_file)
    source_ids = [r["id"] for r in source_records]

    approved_dir = project_dir / "translations" / "approved"
    drafts_dir = project_dir / "translations" / "drafts"

    merged_map: dict[str, str] = {}

    for job in jobs:
        jid = job["job_id"]
        app_file = approved_dir / f"{jid}.approved.jsonl"
        draft_file = drafts_dir / f"{jid}.draft.jsonl"

        target_file = app_file if app_file.exists() else draft_file
        if not target_file.exists():
            print(f"[WARN] Job {jid} has neither approved nor draft translation file!")
            continue

        for r in read_jsonl(target_file):
            merged_map[r["id"]] = r.get("translation", "")

    # Ensure all source IDs are accounted for
    final_records: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for sid in source_ids:
        if sid in merged_map:
            final_records.append({
                "id": sid,
                "translation": merged_map[sid],
            })
        else:
            missing_ids.append(sid)

    final_file = project_dir / "translations" / "final.jsonl"
    write_jsonl(final_file, final_records)

    coverage_pct = (len(final_records) / len(source_ids) * 100) if source_ids else 0.0

    release_dir = project_dir / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = release_dir / "release-manifest.json"
    atomic_json(manifest_file, {
        "total_source_lines": len(source_ids),
        "total_translated_lines": len(final_records),
        "coverage_percentage": round(coverage_pct, 2),
        "missing_ids_count": len(missing_ids),
        "digest": digest_value(final_records),
    })

    print(f"[OK] Merged {len(final_records)} / {len(source_ids)} lines ({coverage_pct:.1f}% coverage).")
    print(f"     Saved to: {final_file}")
    if missing_ids:
        print(f"[WARN] {len(missing_ids)} IDs are missing translations!")

    return final_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge approved jobs into final translation.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    args = parser.parse_args()

    merge_jobs(args.project_dir)


if __name__ == "__main__":
    main()
