#!/usr/bin/env python3
"""Initialize a new FMV Game Translation project."""

from __future__ import annotations

import argparse
import datetime
import shutil
import sys
from pathlib import Path
from pipeline_common import atomic_json, atomic_text, digest_value, read_json

PROJECT_DIR_LAYOUT = [
    "source",
    "research",
    "staging/unpacked",
    "staging/roundtrip",
    "extracted",
    "bible",
    "planning/decision-snapshots",
    "contexts/shared-prefix",
    "translations/drafts",
    "translations/approved",
    "reviews",
    "qa",
    "build",
    "release",
]


def init_project(
    project_dir: Path,
    project_name: str,
    display_title: str,
    source_lang: str,
    target_lang: str,
    engine: str,
    subtitle_format: str,
    cps_target: float = 15.0,
    cps_max: float = 18.0,
) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)

    for sub in PROJECT_DIR_LAYOUT:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    project_meta = {
        "project_name": project_name,
        "display_title": display_title,
        "source_language": source_lang,
        "target_language": target_lang,
        "engine": engine,
        "subtitle_format": subtitle_format,
        "created_at": now,
        "skill_name": "translate-fmv-vi",
        "skill_version": "1.0.0",
        "cps_target": cps_target,
        "cps_max": cps_max,
        "cpl_max": 38,
        "max_lines": 2,
    }
    project_json_path = project_dir / "project.json"
    if not project_json_path.exists():
        atomic_json(project_json_path, project_meta)

    run_state = {
        "current_stage": "initialized",
        "history": [
            {
                "stage": "initialized",
                "entered_at": now,
                "evidence": "project.json",
            }
        ],
        "project_name": project_name,
        "active_job_id": None,
    }
    run_state_path = project_dir / "run-state.json"
    if not run_state_path.exists():
        atomic_json(run_state_path, run_state)

    # Initialize Bible files from templates if templates exist
    templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "bible"
    bible_dir = project_dir / "bible"
    if templates_dir.exists():
        for template_file in templates_dir.glob("*"):
            target_file = bible_dir / template_file.name
            if not target_file.exists():
                shutil.copy2(template_file, target_file)
    else:
        # Default fallback creation
        (bible_dir / "world.md").write_text(f"# {display_title} - Bối Cảnh\n\nBối cảnh game FMV.", encoding="utf-8")
        atomic_json(bible_dir / "characters.json", {"characters": []})
        atomic_json(bible_dir / "pronoun_matrix.json", {"relationship_rules": []})
        atomic_json(bible_dir / "voice.json", {})
        atomic_json(bible_dir / "version.json", {"bible_version": "1.0.0", "frozen_at": now})
        (bible_dir / "glossary.tsv").write_text("source\ttarget\tscope\tcategory\tnotes\n", encoding="utf-8")

    print(f"[OK] Initialized FMV translation project at: {project_dir}")
    print(f"     Title: {display_title} ({source_lang} -> {target_lang})")
    print(f"     Stage: initialized")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize an FMV game localization project.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--name", type=str, default="fmv-game", help="Internal project slug name")
    parser.add_argument("--title", type=str, default="FMV Interactive Game", help="Human-readable title")
    parser.add_argument("--source-lang", type=str, default="zh", help="Source language (zh, ja, ko, en)")
    parser.add_argument("--target-lang", type=str, default="vi-VN", help="Target language (default: vi-VN)")
    parser.add_argument("--engine", type=str, default="unity-fmv", help="Game engine")
    parser.add_argument("--subtitle-format", type=str, default="srt", help="Default subtitle format (srt, vtt, ass, json)")
    parser.add_argument("--cps-target", type=float, default=15.0, help="Target reading CPS (default: 15.0)")
    parser.add_argument("--cps-max", type=float, default=18.0, help="Maximum reading CPS (default: 18.0)")

    args = parser.parse_args()
    init_project(
        project_dir=args.project_dir,
        project_name=args.name,
        display_title=args.title,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        engine=args.engine,
        subtitle_format=args.subtitle_format,
        cps_target=args.cps_target,
        cps_max=args.cps_max,
    )


if __name__ == "__main__":
    main()
