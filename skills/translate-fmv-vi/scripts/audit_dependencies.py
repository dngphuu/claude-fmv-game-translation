#!/usr/bin/env python3
"""Audit project dependencies: detect if Bible or Prefix changes invalidate translation jobs."""

from __future__ import annotations

import argparse
from pathlib import Path
from pipeline_common import read_json, read_jsonl


def audit_dependencies(project_dir: Path) -> dict[str, Any]:
    prefix_meta_file = project_dir / "contexts" / "shared-prefix" / "prefix-meta.json"
    current_prefix_hash = None
    if prefix_meta_file.exists():
        current_prefix_hash = read_json(prefix_meta_file).get("prefix_hash")

    jobs_file = project_dir / "planning" / "jobs.jsonl"
    if not jobs_file.exists():
        return {"reusable_jobs": [], "invalidated_jobs": []}

    jobs = read_jsonl(jobs_file)
    reusable = []
    invalidated = []

    for j in jobs:
        jid = j["job_id"]
        bundle_file = project_dir / "contexts" / jid / "current.json"
        if not bundle_file.exists():
            invalidated.append(jid)
            continue

        bundle = read_json(bundle_file)
        bundle_hash = bundle.get("shared_prefix_hash")

        if bundle_hash == current_prefix_hash:
            reusable.append(jid)
        else:
            invalidated.append(jid)

    print(f"[DEP AUDIT] Reusable jobs: {len(reusable)} | Needs context rebuild: {len(invalidated)}")
    return {"reusable_jobs": reusable, "invalidated_jobs": invalidated}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit job prefix dependencies.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    args = parser.parse_args()

    audit_dependencies(args.project_dir)


if __name__ == "__main__":
    main()
