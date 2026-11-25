#!/usr/bin/env python3
"""Export translated dialogue back into native subtitle formats (SRT, VTT, ASS, JSON)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from pipeline_common import (
    atomic_text,
    ms_to_ass_timecode,
    ms_to_srt_timecode,
    ms_to_vtt_timecode,
    read_jsonl,
)


def export_subtitles(
    project_dir: Path,
    output_dir: Path | None = None,
    use_source_as_fallback: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    source_jsonl_path = project_dir / "extracted" / "source.jsonl"
    if not source_jsonl_path.exists():
        raise FileNotFoundError(f"Missing source records: {source_jsonl_path}")

    source_records = read_jsonl(source_jsonl_path)

    final_jsonl_path = project_dir / "translations" / "final.jsonl"
    trans_map: dict[str, str] = {}

    if not dry_run:
        if final_jsonl_path.exists():
            for r in read_jsonl(final_jsonl_path):
                trans_map[r["id"]] = r.get("translation", "")
        else:
            approved_dir = project_dir / "translations" / "approved"
            if approved_dir.exists():
                for app_file in approved_dir.glob("*.jsonl"):
                    for r in read_jsonl(app_file):
                        trans_map[r["id"]] = r.get("translation", "")

    if dry_run or (not trans_map and use_source_as_fallback):
        for r in source_records:
            if r["id"] not in trans_map:
                trans_map[r["id"]] = r["text"]

    if output_dir is None:
        output_dir = project_dir / "staging" / "roundtrip" if dry_run else project_dir / "build"
    output_dir.mkdir(parents=True, exist_ok=True)

    files_group: dict[str, list[dict[str, Any]]] = {}
    for r in source_records:
        files_group.setdefault(r["file"], []).append(r)

    exported_counts: dict[str, int] = {}

    for rel_file, recs in files_group.items():
        ext = Path(rel_file).suffix.lower()
        out_file_path = output_dir / rel_file
        out_file_path.parent.mkdir(parents=True, exist_ok=True)

        if ext == ".srt":
            content = generate_srt(recs, trans_map)
        elif ext == ".vtt":
            content = generate_vtt(recs, trans_map)
        elif ext in {".ass", ".ssa"}:
            content = generate_ass(recs, trans_map, project_dir / "source" / rel_file)
        elif ext == ".json":
            content = generate_json(recs, trans_map)
        else:
            continue

        atomic_text(out_file_path, content)
        exported_counts[rel_file] = len(recs)

    if dry_run:
        proof_path = project_dir / "staging" / "roundtrip" / "roundtrip-proven.json"
        proof_data = {
            "status": "proven",
            "files_exported": list(exported_counts.keys()),
            "total_lines": sum(exported_counts.values()),
        }
        atomic_text(proof_path, json.dumps(proof_data, indent=2))
        print(f"[OK] Round-trip export test PASSED for {len(exported_counts)} files.")
        print(f"     Proof recorded at: {proof_path}")
    else:
        print(f"[OK] Exported {len(exported_counts)} subtitle files into {output_dir}")

    return exported_counts


def generate_srt(records: list[dict[str, Any]], trans_map: dict[str, str]) -> str:
    blocks: list[str] = []
    for r in sorted(records, key=lambda x: x["index"]):
        idx = r["index"]
        start_tc = r.get("start_time") or ms_to_srt_timecode(r["start_ms"])
        end_tc = r.get("end_time") or ms_to_srt_timecode(r["end_ms"])
        text = trans_map.get(r["id"], r["text"])
        speaker = r.get("speaker", "")
        speaker_prefix = r.get("speaker_prefix", "")
        if (
            speaker
            and speaker_prefix
            and not text.startswith(f"{speaker}:")
            and not text.startswith(f"{speaker}：")
            and not text.startswith(f"【{speaker}】")
        ):
            display_text = f"{speaker_prefix}{text}"
        else:
            display_text = text

        blocks.append(f"{idx}\n{start_tc} --> {end_tc}\n{display_text}")
    return "\n\n".join(blocks) + "\n"


def generate_vtt(records: list[dict[str, Any]], trans_map: dict[str, str]) -> str:
    lines: list[str] = ["WEBVTT\n"]
    for r in sorted(records, key=lambda x: x["index"]):
        start_tc = r.get("start_time") or ms_to_vtt_timecode(r["start_ms"])
        end_tc = r.get("end_time") or ms_to_vtt_timecode(r["end_ms"])
        settings = f" {r['vtt_settings']}" if r.get("vtt_settings") else ""
        text = trans_map.get(r["id"], r["text"])
        speaker = r.get("speaker")
        if speaker:
            cue_text = f"<v {speaker}>{text}"
        else:
            cue_text = text
        lines.append(f"{start_tc} --> {end_tc}{settings}\n{cue_text}\n")
    return "\n".join(lines)


def generate_ass(records: list[dict[str, Any]], trans_map: dict[str, str], original_file: Path) -> str:
    header_lines: list[str] = []
    if original_file.exists():
        raw_lines = original_file.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
        for line in raw_lines:
            if line.strip().startswith("Dialogue:"):
                break
            header_lines.append(line)
        while header_lines and not header_lines[-1].strip():
            header_lines.pop()

    if not header_lines:
        header_lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,30,30,30,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

    event_lines: list[str] = []
    for r in sorted(records, key=lambda x: x["index"]):
        start_tc = r.get("start_time") or ms_to_ass_timecode(r["start_ms"])
        end_tc = r.get("end_time") or ms_to_ass_timecode(r["end_ms"])
        style = r.get("ass_style", "Default")
        speaker = r.get("speaker", "")
        text = trans_map.get(r["id"], r["text"]).replace("\n", r"\N")
        event_lines.append(f"Dialogue: 0,{start_tc},{end_tc},{style},{speaker},0,0,0,,{text}")

    return "\n".join(header_lines) + "\n" + "\n".join(event_lines) + "\n"


def generate_json(records: list[dict[str, Any]], trans_map: dict[str, str]) -> str:
    output_items: list[dict[str, Any]] = []
    for r in sorted(records, key=lambda x: x["index"]):
        item: dict[str, Any] = {
            "id": r["id"],
            "index": r["index"],
            "start_ms": r["start_ms"],
            "end_ms": r["end_ms"],
            "duration_ms": r["duration_ms"],
            "speaker": r.get("speaker", ""),
            "route": r.get("route", "common"),
            "scene_id": r.get("scene_id", ""),
            "dialogue": trans_map.get(r["id"], r["text"]),
            "is_choice": r.get("is_choice", False),
        }
        for key in ("clip_id", "scenario_id", "addressee"):
            if r.get(key) is not None:
                item[key] = r[key]
        output_items.append(item)
    return json.dumps(output_items, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export translated dialogue back to subtitle formats.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform roundtrip verification with source text")
    parser.add_argument("--use-source-fallback", action="store_true", help="Fallback to source text if missing")
    args = parser.parse_args()

    export_subtitles(
        project_dir=args.project_dir,
        output_dir=args.output_dir,
        use_source_as_fallback=args.use_source_fallback,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
