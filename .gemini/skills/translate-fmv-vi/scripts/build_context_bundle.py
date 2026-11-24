#!/usr/bin/env python3
"""Build scene context bundles containing primary entries, surroundings, and active pronoun rules."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from pipeline_common import atomic_json, digest_value, read_json, read_jsonl


def build_context_bundle(project_dir: Path, job_ids: list[str] | None = None) -> None:
    source_file = project_dir / "extracted" / "source.jsonl"
    jobs_file = project_dir / "planning" / "jobs.jsonl"
    prefix_meta_file = project_dir / "contexts" / "shared-prefix" / "prefix-meta.json"

    if not source_file.exists() or not jobs_file.exists():
        raise FileNotFoundError("Missing source or jobs file.")

    source_records = read_jsonl(source_file)
    source_map = {r["id"]: r for r in source_records}
    jobs = read_jsonl(jobs_file)

    bible_matrix = read_json(project_dir / "bible" / "pronoun_matrix.json") if (project_dir / "bible" / "pronoun_matrix.json").exists() else {}
    prefix_meta = read_json(prefix_meta_file) if prefix_meta_file.exists() else {}

    target_jobs = jobs if job_ids is None else [j for j in jobs if j["job_id"] in job_ids]

    for job in target_jobs:
        jid = job["job_id"]
        entry_ids = job.get("entry_ids", [])
        primary_items = [source_map[eid] for eid in entry_ids if eid in source_map]

        if not primary_items:
            continue

        # Find surrounding context (e.g., 3 lines before and 3 lines after in source sequence)
        first_idx = primary_items[0]["index"]
        last_idx = primary_items[-1]["index"]
        filename = primary_items[0]["file"]

        file_recs = [r for r in source_records if r["file"] == filename]
        preceding = [r for r in file_recs if r["index"] < first_idx][-3:]
        succeeding = [r for r in file_recs if r["index"] > last_idx][:3]

        # Extract active pronoun rules for characters involved in this job
        job_speakers = set(job.get("speakers", []))
        applicable_pronoun_rules = []
        for rule in bible_matrix.get("relationship_rules", []):
            pair = rule.get("pair", [])
            # If any character in pair is in speakers, include rule
            applicable_pronoun_rules.append(rule)

        bundle_data = {
            "job_id": jid,
            "scene_id": job.get("scene_id"),
            "route": job.get("route"),
            "shared_prefix_hash": prefix_meta.get("prefix_hash"),
            "speakers": job.get("speakers", []),
            "active_pronoun_rules": applicable_pronoun_rules,
            "surrounding_context": {
                "preceding_dialogue": [
                    {"speaker": p.get("speaker"), "text": p.get("text")} for p in preceding
                ],
                "succeeding_dialogue": [
                    {"speaker": s.get("speaker"), "text": s.get("text")} for s in succeeding
                ],
            },
            "primary_entries": [
                {
                    "id": item["id"],
                    "speaker": item.get("speaker", ""),
                    "start_time": item.get("start_time"),
                    "end_time": item.get("end_time"),
                    "duration_ms": item.get("duration_ms", 0),
                    "text": item["text"],
                    "protected_tokens": item.get("protected_tokens", []),
                    "is_choice": item.get("is_choice", False),
                }
                for item in primary_items
            ],
        }

        job_context_dir = project_dir / "contexts" / jid
        job_context_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(job_context_dir / "current.json", bundle_data)

    print(f"[OK] Built context bundles for {len(target_jobs)} jobs.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build context bundles for translation jobs.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, default=None, help="Specific job ID (or all if omitted)")
    parser.add_argument("--all-pending", action="store_true", help="Build for all pending jobs")
    args = parser.parse_args()

    jobs = [args.job_id] if args.job_id else None
    build_context_bundle(args.project_dir, jobs)


if __name__ == "__main__":
    main()
