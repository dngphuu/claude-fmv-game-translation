#!/usr/bin/env python3
"""Universal subtitle extractor for FMV game formats (SRT, VTT, ASS, JSON)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from pipeline_common import (
    atomic_json,
    digest_text,
    ms_to_srt_timecode,
    timecode_to_ms,
    write_jsonl,
)

# Common protected token regex (HTML tags, ASS tags, format variables)
PROTECTED_TOKEN_REGEX = re.compile(
    r"(<[^>]+>|\{\\[^}]+\}|%[0-9]*[sdif]|(?:\{[0-9a-zA-Z_]+\})|\\N|\\n)"
)

CHOICE_MARKER_REGEX = re.compile(
    r"^\s*(?:\[(?:QTE(?:_CHOICE_\d+)?|CHOICE(?:_\d+)?|OPTION(?:_\d+)?|LỰA\s*CHỌN)\]|【(?:选项|选择|選択肢|選択)\d*】)",
    re.IGNORECASE,
)

SRT_BRACKET_SPEAKER_RE = re.compile(r"^(【([^】]+)】\s*)(.*)", re.DOTALL)
SRT_COLON_SPEAKER_RE = re.compile(
    r"^(([A-Za-zÀ-ỹ0-9_\-\.\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+(?:\s+[A-Za-zÀ-ỹ0-9_\-\.\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+){0,3})\s*[:：]\s*)(.*)",
    re.DOTALL,
)


def extract_protected_tokens(text: str) -> list[str]:
    """Find all markup, styling tags, or variable placeholders."""
    return PROTECTED_TOKEN_REGEX.findall(text)


def detect_is_choice(speaker: str, text: str) -> bool:
    """Detect interactive player choice / QTE cues across subtitle formats."""
    if CHOICE_MARKER_REGEX.match(text or ""):
        return True
    sp_norm = (speaker or "").strip().lower()
    if re.match(r"^(?:choice\d*|qte\d*|option\d*)$", sp_norm):
        return True
    return False


def _extract_srt_speaker(raw_text: str) -> tuple[str, str, str]:
    """Return (speaker, speaker_prefix, dialogue_text) for an SRT cue."""
    if CHOICE_MARKER_REGEX.match(raw_text):
        return "", "", raw_text

    bracket_match = SRT_BRACKET_SPEAKER_RE.match(raw_text)
    if bracket_match:
        prefix, speaker_name, rest = bracket_match.group(1), bracket_match.group(2).strip(), bracket_match.group(3)
        return speaker_name, prefix, rest

    colon_match = SRT_COLON_SPEAKER_RE.match(raw_text)
    if colon_match:
        prefix = colon_match.group(1)
        speaker_name = colon_match.group(2).strip()
        rest = colon_match.group(3)
        if (
            len(speaker_name) <= 25
            and not speaker_name.isdigit()
            and speaker_name.lower() not in {"http", "https", "ftp"}
            and not rest.startswith("//")
        ):
            return speaker_name, prefix, rest

    return "", "", raw_text


def parse_srt(content: str, filename: str) -> list[dict[str, Any]]:
    """Parse SRT content into standard subtitle records."""
    records: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        tc_line_idx = 1 if "-->" in lines[1] else 0
        if "-->" not in lines[tc_line_idx]:
            continue

        raw_tc = lines[tc_line_idx]
        tc_match = re.search(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", raw_tc)
        if not tc_match:
            continue

        start_tc, end_tc = tc_match.group(1), tc_match.group(2)
        start_ms = timecode_to_ms(start_tc)
        end_ms = timecode_to_ms(end_tc)
        duration_ms = max(0, end_ms - start_ms)

        raw_text = "\n".join(lines[tc_line_idx + 1 :])
        speaker, speaker_prefix, text = _extract_srt_speaker(raw_text)
        is_choice = detect_is_choice(speaker, text)

        idx = len(records) + 1
        entry_id = f"{filename}:{idx:06d}"

        record: dict[str, Any] = {
            "id": entry_id,
            "source_hash": digest_text(text),
            "file": filename,
            "index": idx,
            "start_time": start_tc,
            "end_time": end_tc,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "speaker": speaker,
            "route": "common",
            "scene_id": Path(filename).stem,
            "text": text,
            "protected_tokens": extract_protected_tokens(text),
            "is_choice": is_choice,
        }
        if speaker_prefix:
            record["speaker_prefix"] = speaker_prefix

        records.append(record)

    return records


def parse_vtt(content: str, filename: str) -> list[dict[str, Any]]:
    """Parse WebVTT content into standard subtitle records."""
    records: list[dict[str, Any]] = []
    lines = content.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines) and not lines[i].startswith("WEBVTT"):
        i += 1
    if i < len(lines):
        i += 1

    current_cue: list[str] = []
    blocks: list[list[str]] = []

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            if current_cue:
                blocks.append(current_cue)
                current_cue = []
        else:
            current_cue.append(line)
        i += 1
    if current_cue:
        blocks.append(current_cue)

    for block in blocks:
        tc_line = None
        text_lines = []
        for line in block:
            if "-->" in line:
                tc_line = line
            elif tc_line is not None:
                text_lines.append(line)

        if not tc_line:
            continue

        tc_match = re.search(r"(\d+:?\d+:\d+[.]\d+)\s*-->\s*(\d+:?\d+:\d+[.]\d+)", tc_line)
        if not tc_match:
            continue

        start_tc, end_tc = tc_match.group(1), tc_match.group(2)
        cue_settings = tc_line[tc_match.end():].strip()
        start_ms = timecode_to_ms(start_tc)
        end_ms = timecode_to_ms(end_tc)
        duration_ms = max(0, end_ms - start_ms)

        raw_text = "\n".join(text_lines)
        speaker = ""
        v_match = re.match(r"^<v\s+([^>]+)>(.*)", raw_text, re.DOTALL)
        if v_match:
            speaker = v_match.group(1).strip()
            text = v_match.group(2).strip()
        else:
            text = raw_text

        is_choice = detect_is_choice(speaker, text)
        idx = len(records) + 1
        entry_id = f"{filename}:{idx:06d}"

        record: dict[str, Any] = {
            "id": entry_id,
            "source_hash": digest_text(text),
            "file": filename,
            "index": idx,
            "start_time": start_tc,
            "end_time": end_tc,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "speaker": speaker,
            "route": "common",
            "scene_id": Path(filename).stem,
            "text": text,
            "protected_tokens": extract_protected_tokens(text),
            "is_choice": is_choice,
        }
        if cue_settings:
            record["vtt_settings"] = cue_settings
        records.append(record)

    return records


def parse_ass(content: str, filename: str) -> list[dict[str, Any]]:
    """Parse Advanced SubStation Alpha (.ass) dialogue events."""
    records: list[dict[str, Any]] = []
    lines = content.replace("\r\n", "\n").split("\n")
    events_section = False
    format_fields: list[str] = []

    for line in lines:
        line_s = line.strip()
        if line_s.startswith("[Events]"):
            events_section = True
            continue
        if events_section and line_s.startswith("["):
            events_section = False
            continue

        if events_section and line_s.startswith("Format:"):
            format_fields = [f.strip().lower() for f in line_s[7:].split(",")]
            continue

        if events_section and line_s.startswith("Dialogue:"):
            raw_data = line_s[9:].split(",", len(format_fields) - 1)
            event_dict = dict(zip(format_fields, raw_data))

            start_tc = event_dict.get("start", "0:00:00.00").strip()
            end_tc = event_dict.get("end", "0:00:00.00").strip()
            start_ms = timecode_to_ms(start_tc)
            end_ms = timecode_to_ms(end_tc)
            duration_ms = max(0, end_ms - start_ms)

            speaker = event_dict.get("name", "").strip()
            text = event_dict.get("text", "")
            is_choice = detect_is_choice(speaker, text)

            idx = len(records) + 1
            entry_id = f"{filename}:{idx:06d}"

            records.append({
                "id": entry_id,
                "source_hash": digest_text(text),
                "file": filename,
                "index": idx,
                "start_time": start_tc,
                "end_time": end_tc,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration_ms,
                "speaker": speaker,
                "route": "common",
                "scene_id": Path(filename).stem,
                "text": text,
                "protected_tokens": extract_protected_tokens(text),
                "is_choice": is_choice,
                "ass_style": event_dict.get("style", "Default").strip(),
            })

    return records


def parse_json_table(content: str, filename: str) -> list[dict[str, Any]]:
    """Parse game engine JSON dialogue arrays, preserving optional scenario metadata."""
    data = json.loads(content)
    if isinstance(data, dict) and "dialogues" in data:
        items = data["dialogues"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"Unsupported JSON structure in {filename}")

    records: list[dict[str, Any]] = []
    optional_keys = (
        "clip_id", "scenario_id", "addressee", "choice_target",
        "topic", "setting", "mood", "relationship_phase",
    )

    for idx, item in enumerate(items, 1):
        text = item.get("text") or item.get("dialogue") or item.get("content") or ""
        start_ms = int(item.get("start_ms") or item.get("timestamp_start_ms") or 0)
        end_ms = int(item.get("end_ms") or item.get("timestamp_end_ms") or 0)
        duration_ms = max(0, end_ms - start_ms)
        speaker = item.get("speaker") or item.get("name") or ""
        is_choice = bool(item.get("is_choice") or item.get("choice")) or detect_is_choice(speaker, text)

        entry_id = f"{filename}:{idx:06d}"
        record: dict[str, Any] = {
            "id": entry_id,
            "source_hash": digest_text(text),
            "file": filename,
            "index": idx,
            "start_time": ms_to_srt_timecode(start_ms),
            "end_time": ms_to_srt_timecode(end_ms),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "speaker": speaker,
            "route": item.get("route", "common"),
            "scene_id": item.get("scene_id", Path(filename).stem),
            "text": text,
            "protected_tokens": extract_protected_tokens(text),
            "is_choice": is_choice,
        }
        for key in optional_keys:
            if item.get(key) is not None:
                record[key] = item[key]

        records.append(record)

    return records


def extract_all(project_dir: Path) -> list[dict[str, Any]]:
    source_dir = project_dir / "source"
    extracted_dir = project_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    tokens_found: set[str] = set()

    for file_path in sorted(source_dir.rglob("*")):
        if not file_path.is_file() or file_path.name == "file-manifest.json":
            continue

        rel_path = file_path.relative_to(source_dir).as_posix()
        ext = file_path.suffix.lower()
        content = file_path.read_text(encoding="utf-8-sig")

        if ext == ".srt":
            file_records = parse_srt(content, rel_path)
        elif ext == ".vtt":
            file_records = parse_vtt(content, rel_path)
        elif ext in {".ass", ".ssa"}:
            file_records = parse_ass(content, rel_path)
        elif ext == ".json":
            file_records = parse_json_table(content, rel_path)
        else:
            continue

        for r in file_records:
            tokens_found.update(r.get("protected_tokens", []))
        all_records.extend(file_records)

    source_jsonl_path = extracted_dir / "source.jsonl"
    write_jsonl(source_jsonl_path, all_records)

    token_report_path = extracted_dir / "control-token-report.json"
    atomic_json(token_report_path, {
        "tokens_detected": sorted(tokens_found),
        "total_tokens": len(tokens_found),
    })

    scenes = sorted({r.get("scene_id", "default") for r in all_records})
    script_map_path = extracted_dir / "script-map.json"
    atomic_json(script_map_path, {
        "total_lines": len(all_records),
        "scenes": scenes,
        "total_scenes": len(scenes),
    })

    print(f"[OK] Extracted {len(all_records)} subtitle dialogue units across {len(scenes)} scenes.")
    print(f"     Saved to: {source_jsonl_path}")
    return all_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract FMV game subtitles to standard source.jsonl.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    args = parser.parse_args()
    extract_all(args.project_dir)


if __name__ == "__main__":
    main()
