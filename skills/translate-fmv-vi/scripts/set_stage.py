#!/usr/bin/env python3
"""Advance the project stage state machine with verified evidence."""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path
from audit_project import STAGES_ORDER, audit_stage_evidence
from pipeline_common import atomic_json, read_json


def set_stage(project_dir: Path, new_stage: str, evidence: str | None = None) -> None:
    if new_stage not in STAGES_ORDER:
        raise ValueError(f"Invalid stage '{new_stage}'. Must be one of: {STAGES_ORDER}")

    run_state_path = project_dir / "run-state.json"
    state = read_json(run_state_path) if run_state_path.exists() else {"history": []}

    current_stage = state.get("current_stage", "initialized")
    curr_idx = STAGES_ORDER.index(current_stage) if current_stage in STAGES_ORDER else 0
    new_idx = STAGES_ORDER.index(new_stage)

    # Verify stage evidence unless forcing
    ok, reason = audit_stage_evidence(project_dir, new_stage)
    if not ok:
        print(f"[ERROR] Cannot advance to '{new_stage}': {reason}", file=sys.stderr)
        sys.exit(1)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state["current_stage"] = new_stage
    history = state.setdefault("history", [])
    history.append({
        "stage": new_stage,
        "entered_at": now,
        "evidence": evidence or reason,
    })

    atomic_json(run_state_path, state)
    print(f"[OK] Advanced stage: {current_stage} -> {new_stage}")
    print(f"     Evidence: {evidence or reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Advance project stage state.")
    parser.add_argument("stage", type=str, help="Target stage name")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--evidence", type=str, default=None, help="Evidence path or notes")
    args = parser.parse_args()

    set_stage(args.project_dir, args.stage, args.evidence)


if __name__ == "__main__":
    main()
