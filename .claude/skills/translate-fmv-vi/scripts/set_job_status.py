#!/usr/bin/env python3
"""Safely update job status in planning/jobs.jsonl."""

from __future__ import annotations

import argparse
from pathlib import Path
from pipeline_common import read_jsonl, write_jsonl

VALID_STATUSES = {"pending", "assigned", "translated", "validated", "reviewed", "approved", "merged", "failed"}


def set_job_status(project_dir: Path, job_id: str, new_status: str, agent: str | None = None) -> None:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Allowed: {VALID_STATUSES}")

    jobs_file = project_dir / "planning" / "jobs.jsonl"
    if not jobs_file.exists():
        raise FileNotFoundError(f"Missing {jobs_file}")

    jobs = read_jsonl(jobs_file)
    found = False

    for j in jobs:
        if j["job_id"] == job_id:
            found = True
            j["status"] = new_status
            if agent:
                j["assigned_agent"] = agent
            if new_status == "approved":
                j["approved"] = True
            break

    if not found:
        raise KeyError(f"Job {job_id} not found in {jobs_file}")

    write_jsonl(jobs_file, jobs)
    print(f"[OK] Job '{job_id}' status updated to '{new_status}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update translation job status.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, required=True, help="Job ID")
    parser.add_argument("--status", type=str, required=True, help="New status")
    parser.add_argument("--agent", type=str, default=None, help="Agent name")
    args = parser.parse_args()

    set_job_status(args.project_dir, args.job_id, args.status, args.agent)


if __name__ == "__main__":
    main()
