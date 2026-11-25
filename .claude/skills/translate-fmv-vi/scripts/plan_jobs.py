#!/usr/bin/env python3
"""Plan scenario-isolated translation jobs from scenarios.json or extracted source records."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from pipeline_common import TokenCounter, read_json, read_jsonl, write_jsonl
from plan_scenarios import plan_scenarios


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
    source_map = {r["id"]: r for r in records}

    planning_dir = project_dir / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    scenarios_file = planning_dir / "scenarios.json"
    if not scenarios_file.exists():
        scenarios_data = plan_scenarios(project_dir)
    else:
        scenarios_data = read_json(scenarios_file)

    scenarios = scenarios_data.get("scenarios", [])
    jobs_file = planning_dir / "jobs.jsonl"
    existing_jobs = read_jsonl(jobs_file)
    existing_map = {j["job_id"]: j for j in existing_jobs}

    counter = TokenCounter()

    # Count scenarios per (route, scene_id) for clean backward-compatible naming
    scene_scn_counts: dict[tuple[str, str], int] = {}
    for scn in scenarios:
        key = (scn.get("route", "common"), scn.get("scene_id", "scene"))
        scene_scn_counts[key] = scene_scn_counts.get(key, 0) + 1

    proposed_jobs: list[dict[str, Any]] = []

    for scn in scenarios:
        scn_id = scn["scenario_id"]
        route = scn.get("route", "common")
        scene_id = scn.get("scene_id", "scene")
        scn_recs = [source_map[eid] for eid in scn.get("entry_ids", []) if eid in source_map]
        if not scn_recs:
            continue

        # Preserve single-scenario job_id format `route__scene_id`, or `scenario_id` when multiple scenarios exist
        job_prefix = f"{route}__{scene_id}" if scene_scn_counts.get((route, scene_id), 1) == 1 else scn_id

        chunks: list[list[dict[str, Any]]] = []
        current_chunk: list[dict[str, Any]] = []
        current_tokens = 0

        for r in scn_recs:
            line_tok = counter.count(r["text"])
            if current_chunk and (len(current_chunk) >= max_lines_per_job or current_tokens + line_tok > max_tokens_per_job):
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            current_chunk.append(r)
            current_tokens += line_tok

        if current_chunk:
            chunks.append(current_chunk)

        total_parts = len(chunks)
        for part_idx, chunk in enumerate(chunks, 1):
            job_id = f"{job_prefix}_part{part_idx:02d}" if total_parts > 1 else job_prefix
            proposed_jobs.append(create_job_entry(job_id, chunk, scn, existing_map))

    write_jsonl(jobs_file, proposed_jobs)
    print(f"[OK] Planned {len(proposed_jobs)} scenario-based translation jobs across {len(scenarios)} scenarios -> {jobs_file}")
    return proposed_jobs


def create_job_entry(
    job_id: str,
    records: list[dict[str, Any]],
    scenario: dict[str, Any],
    existing_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    speakers = sorted({r.get("speaker") for r in records if r.get("speaker")})
    choice_count = sum(1 for r in records if r.get("is_choice"))
    total_duration_ms = sum(r.get("duration_ms", 0) for r in records)

    if job_id in existing_map:
        item = existing_map[job_id].copy()
        item["scenario_id"] = scenario["scenario_id"]
        item["scenario_title"] = scenario.get("title", "")
        item["line_count"] = len(records)
        item["choice_count"] = choice_count
        item["has_choices"] = choice_count > 0
        item["speakers"] = speakers
        item["participants"] = scenario.get("participants", [])
        item["choice_target"] = scenario.get("choice_target")
        item["entry_ids"] = [r["id"] for r in records]
        return item

    return {
        "job_id": job_id,
        "scenario_id": scenario["scenario_id"],
        "scenario_title": scenario.get("title", ""),
        "scene_id": records[0].get("scene_id", "scene"),
        "route": records[0].get("route", "common"),
        "status": "pending",
        "speakers": speakers,
        "participants": scenario.get("participants", []),
        "choice_target": scenario.get("choice_target"),
        "line_count": len(records),
        "choice_count": choice_count,
        "has_choices": choice_count > 0,
        "total_duration_ms": total_duration_ms,
        "entry_ids": [r["id"] for r in records],
        "assigned_agent": None,
        "approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan scenario-based translation jobs.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--max-lines", type=int, default=60, help="Max lines per job chunk")
    parser.add_argument("--max-tokens", type=int, default=4000, help="Max estimated tokens per chunk")
    args = parser.parse_args()

    plan_jobs(args.project_dir, args.max_lines, args.max_tokens)


if __name__ == "__main__":
    main()
