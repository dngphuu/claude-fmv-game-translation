#!/usr/bin/env python3
"""Audit project integrity and stage transition readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from pipeline_common import read_json, read_jsonl

STAGES_ORDER = [
    "initialized",
    "researched",
    "roundtrip-proven",
    "extracted",
    "bible-frozen",
    "plan-approved",
    "translating",
    "reviewed",
    "validated",
    "repacked",
    "playtested",
    "released",
]


def audit_stage_evidence(project_dir: Path, target_stage: str) -> tuple[bool, str]:
    if target_stage not in STAGES_ORDER:
        return False, f"Unknown stage: {target_stage}"

    if target_stage == "initialized":
        if not (project_dir / "project.json").exists():
            return False, "Missing project.json"
        return True, "project.json present"

    if target_stage == "researched":
        research_dir = project_dir / "research"
        if not (research_dir / "cast-and-actors.md").exists() and not (research_dir / "decisions.md").exists():
            return False, "Missing research evidence (cast-and-actors.md or decisions.md)"
        return True, "Research documentation present"

    if target_stage == "roundtrip-proven":
        proof = project_dir / "staging" / "roundtrip" / "roundtrip-proven.json"
        if not proof.exists():
            return False, "Missing roundtrip-proven.json proof in staging/roundtrip"
        return True, "Roundtrip proof present"

    if target_stage == "extracted":
        source_jsonl = project_dir / "extracted" / "source.jsonl"
        if not source_jsonl.exists():
            return False, "Missing extracted/source.jsonl"
        records = read_jsonl(source_jsonl)
        if not records:
            return False, "extracted/source.jsonl is empty"
        return True, f"Extracted {len(records)} dialogue units"

    if target_stage == "bible-frozen":
        bible_dir = project_dir / "bible"
        ver_file = bible_dir / "version.json"
        pm_file = bible_dir / "pronoun_matrix.json"
        if not ver_file.exists():
            return False, "Missing bible/version.json"
        if not pm_file.exists():
            return False, "Missing bible/pronoun_matrix.json"
        return True, "Bible and Pronoun Matrix frozen"

    if target_stage == "plan-approved":
        jobs_file = project_dir / "planning" / "jobs.jsonl"
        if not jobs_file.exists():
            return False, "Missing planning/jobs.jsonl"
        jobs = read_jsonl(jobs_file)
        if not jobs:
            return False, "planning/jobs.jsonl is empty"
        return True, f"Plan contains {len(jobs)} jobs"

    if target_stage == "translating":
        drafts_dir = project_dir / "translations" / "drafts"
        if not drafts_dir.exists() or not list(drafts_dir.glob("*.jsonl")):
            return False, "No draft translation files in translations/drafts"
        return True, "Draft translations present"

    if target_stage == "reviewed":
        app_dir = project_dir / "translations" / "approved"
        if not app_dir.exists() or not list(app_dir.glob("*.jsonl")):
            return False, "No approved translation files in translations/approved"
        return True, "Approved translations present"

    if target_stage == "validated":
        qa_file = project_dir / "qa" / "validation-report.json"
        if not qa_file.exists():
            return False, "Missing qa/validation-report.json"
        report = read_json(qa_file)
        raw_errors = report.get("errors", 0)
        error_count = report.get(
            "error_count",
            len(raw_errors) if isinstance(raw_errors, list) else int(raw_errors or 0),
        )
        if error_count > 0:
            return False, f"Validation report contains {error_count} errors"
        return True, "Validation passed with 0 errors"

    if target_stage == "repacked":
        build_dir = project_dir / "build"
        if not build_dir.exists() or not list(build_dir.rglob("*.*")):
            return False, "No exported files in build/"
        return True, "Repacked subtitle files present"

    if target_stage == "playtested":
        qa_playtest = project_dir / "qa" / "playtest-evidence.json"
        if not qa_playtest.exists():
            return False, "Missing qa/playtest-evidence.json"
        return True, "Playtest evidence recorded"

    if target_stage == "released":
        rel_dir = project_dir / "release"
        manifest = rel_dir / "release-manifest.json"
        if not manifest.exists():
            return False, "Missing release/release-manifest.json"
        return True, "Release manifest present"

    return False, "Unhandled stage check"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit project state and stage evidence.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--stage", type=str, default=None, help="Specific stage to verify")
    args = parser.parse_args()

    run_state_file = args.project_dir / "run-state.json"
    if not run_state_file.exists():
        print(f"[FAIL] Missing {run_state_file}")
        sys.exit(1)

    state = read_json(run_state_file)
    current_stage = state.get("current_stage", "initialized")
    target_stage = args.stage or current_stage

    ok, reason = audit_stage_evidence(args.project_dir, target_stage)
    if ok:
        print(f"[AUDIT PASS] Stage '{target_stage}': {reason}")
        sys.exit(0)
    else:
        print(f"[AUDIT FAIL] Stage '{target_stage}': {reason}")
        sys.exit(2)


if __name__ == "__main__":
    main()
