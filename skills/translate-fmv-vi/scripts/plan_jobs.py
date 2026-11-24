#!/usr/bin/env python3
"""Plan scene-based translation jobs from extracted source records."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from pipeline_common import TokenCounter, digest_text, read_jsonl, write_jsonl


def plan_jobs(
    project_dir: Path,
    max_lines_per_job: int = 50,
    max_tokens_per_job: int = 4000,
) -> list[dict[str, Any]]:
    source_file = project_dir / "extracted" / "source.jsonl"
    if not source_file.exists():
        raise FileNotFoundError(f"Missing {source_file}")

    records = read_jsonl(source_file)
    if not records:
        raise ValueError("Source records are empty")

    planning_dir = project_dir / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    jobs_file = planning_dir / "jobs.jsonl"

    existing_jobs = read_jsonl(jobs_file)
    existing_map = {j["job_id"]: j for j in existing_jobs}

    counter = TokenCounter()

    # Group records by scene_id and route
    scene_groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        group_key = f"{r.get('route', 'common')}__{r.get('scene_id', 'scene')}"
        scene_groups.setdefault(group_key, []).append(r)

    proposed_jobs: list[dict[str, Any]] = []

    for group_key, recs in scene_groups.items():
        # Split into chunks if too long
        current_chunk: list[dict[str, Any]] = []
        current_tokens = 0
        part_idx = 1

        for r in recs:
            line_tok = counter.count(r["text"])
            if current_chunk and (len(current_chunk) >= max_lines_per_job or current_tokens + line_tok > max_tokens_per_job):
                job_id = f"{group_key}_part{part_idx:02d}"
                proposed_jobs.append(create_job_entry(job_id, current_chunk, existing_map))
                current_chunk = []
                current_tokens = 0
                part_idx += 1

            current_chunk.append(r)
            current_tokens += line_tok

        if current_chunk:
            job_id = f"{group_key}_part{part_idx:02d}" if part_idx > 1 else group_key
            proposed_jobs.append(create_job_entry(job_id, current_chunk, existing_map))

    write_jsonl(jobs_file, proposed_jobs)
    print(f"[OK] Planned {len(proposed_jobs)} translation jobs -> {jobs_file}")
    return proposed_jobs


def create_job_entry(
    job_id: str,
    records: list[dict[str, Any]],
    existing_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if job_id in existing_map:
        # Preserve status of existing job
        item = existing_map[job_id].copy()
        item["line_count"] = len(records)
        item["entry_ids"] = [r["id"] for r in records]
        return item

    scene_id = records[0].get("scene_id", "scene")
    route = records[0].get("route", "common")
    speakers = sorted({r.get("speaker") for r in records if r.get("speaker")})
    total_duration_ms = sum(r.get("duration_ms", 0) for r in records)

    return {
        "job_id": job_id,
        "scene_id": scene_id,
        "route": route,
        "status": "pending",
        "speakers": speakers,
        "line_count": len(records),
        "total_duration_ms": total_duration_ms,
        "entry_ids": [r["id"] for r in records],
        "assigned_agent": None,
        "approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan scene-based translation jobs.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--max-lines", type=int, default=60, help="Max lines per job chunk")
    parser.add_argument("--max-tokens", type=int, default=4000, help="Max estimated tokens per chunk")
    args = parser.parse_args()

    plan_jobs(args.project_dir, args.max_lines, args.max_tokens)


if __name__ == "__main__":
    main()
