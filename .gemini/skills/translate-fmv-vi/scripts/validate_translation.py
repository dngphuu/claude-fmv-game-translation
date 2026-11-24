#!/usr/bin/env python3
"""Comprehensive validator: ID matching, protected tokens, CPS limits, Vietnamese anti-slop, and glossary adherence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from pipeline_common import (
    VIETNAMESE_SLOP_PATTERNS,
    atomic_json,
    calculate_cps,
    read_json,
    read_jsonl,
    read_tsv,
)


def validate_translation(
    project_dir: Path,
    job_id: str | None = None,
    draft_file: Path | None = None,
) -> dict[str, Any]:
    project_meta = read_json(project_dir / "project.json")
    cps_max = float(project_meta.get("cps_max", 18.0))
    cpl_max = int(project_meta.get("cpl_max", 38))
    max_lines = int(project_meta.get("max_lines", 2))

    source_records = read_jsonl(project_dir / "extracted" / "source.jsonl")
    source_map = {r["id"]: r for r in source_records}

    # Load glossary
    glossary = read_tsv(project_dir / "bible" / "glossary.tsv")

    # Determine files to validate
    if draft_file:
        files_to_check = [draft_file]
    elif job_id:
        draft = project_dir / "translations" / "drafts" / f"{job_id}.draft.jsonl"
        approved = project_dir / "translations" / "approved" / f"{job_id}.approved.jsonl"
        target = approved if approved.exists() else draft
        if not target.exists():
            raise FileNotFoundError(f"No translation file found for job '{job_id}'")
        files_to_check = [target]
    else:
        drafts = list((project_dir / "translations" / "drafts").glob("*.jsonl"))
        files_to_check = drafts

    total_checked = 0
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for file_path in files_to_check:
        records = read_jsonl(file_path)
        for rec in records:
            total_checked += 1
            entry_id = rec.get("id")
            translation = rec.get("translation", "")

            if not entry_id or entry_id not in source_map:
                errors.append({
                    "id": entry_id,
                    "code": "unknown_id",
                    "file": file_path.name,
                    "message": f"ID {entry_id} does not exist in source records.",
                })
                continue

            src = source_map[entry_id]
            src_text = src["text"]
            duration_ms = src.get("duration_ms", 0)

            # 1. Protected token check
            for token in src.get("protected_tokens", []):
                if token not in translation:
                    errors.append({
                        "id": entry_id,
                        "code": "missing_protected_token",
                        "token": token,
                        "message": f"Missing protected token '{token}' in translation.",
                    })

            # 2. Line count & CPL check
            lines = translation.split("\n")
            if len(lines) > max_lines:
                warnings.append({
                    "id": entry_id,
                    "code": "line_count_exceeded",
                    "lines": len(lines),
                    "message": f"Translation has {len(lines)} lines (max {max_lines}).",
                })
            for line in lines:
                if len(line) > cpl_max + 10:
                    warnings.append({
                        "id": entry_id,
                        "code": "cpl_exceeded",
                        "char_count": len(line),
                        "message": f"Line exceeds maximum recommended length ({len(line)} > {cpl_max}).",
                    })

            # 3. CPS check
            if duration_ms > 0:
                cps = calculate_cps(translation, duration_ms)
                if cps > cps_max + 4.0:
                    errors.append({
                        "id": entry_id,
                        "code": "cps_critical_overload",
                        "cps": cps,
                        "duration_ms": duration_ms,
                        "message": f"Reading speed ({cps:.1f} CPS) critically exceeds limit ({cps_max}). Viewer cannot read this in time!",
                    })
                elif cps > cps_max:
                    warnings.append({
                        "id": entry_id,
                        "code": "cps_warning",
                        "cps": cps,
                        "duration_ms": duration_ms,
                        "message": f"Reading speed ({cps:.1f} CPS) exceeds target ({cps_max}). Consider condensing.",
                    })

            # 4. Vietnamese Anti-AI-Slop detector
            for pattern, slop_code, slop_desc in VIETNAMESE_SLOP_PATTERNS:
                if pattern.search(translation):
                    warnings.append({
                        "id": entry_id,
                        "code": f"slop_{slop_code}",
                        "message": f"Phát hiện văn phong dịch máy (AI Slop): {slop_desc}",
                        "sample": translation,
                    })

            # 5. Glossary adherence
            for g in glossary:
                sterm = g.get("source", "").strip()
                tterm = g.get("target", "").strip()
                if sterm and tterm and sterm in src_text:
                    # If target has slash options e.g. "ông bô / bố"
                    options = [opt.strip().lower() for opt in tterm.split("/")]
                    trans_lower = translation.lower()
                    if not any(opt in trans_lower for opt in options):
                        warnings.append({
                            "id": entry_id,
                            "code": "glossary_term_mismatch",
                            "source_term": sterm,
                            "expected_target": tterm,
                            "message": f"Source contains '{sterm}', expected '{tterm}' in translation.",
                        })

    report = {
        "total_lines_validated": total_checked,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if len(errors) == 0 else "fail",
    }

    qa_dir = project_dir / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    report_file = qa_dir / "validation-report.json"
    atomic_json(report_file, report)

    print(f"[QA] Validated {total_checked} lines: {len(errors)} errors, {len(warnings)} warnings.")
    if errors:
        print(f"     STATUS: FAILED (Errors found)")
        for err in errors[:5]:
            print(f"     - [ERROR {err['code']}] {err.get('id')}: {err['message']}")
    else:
        print(f"     STATUS: PASSED")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate translation against rules, CPS, and AI slop.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, default=None, help="Job ID to validate")
    parser.add_argument("--draft", type=Path, default=None, help="Specific draft JSONL file")
    args = parser.parse_args()

    report = validate_translation(args.project_dir, args.job_id, args.draft)
    if report["error_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
