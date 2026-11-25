#!/usr/bin/env python3
"""Segment extracted subtitle records into coherent scenarios with active pronoun phases."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from pipeline_common import (
    GENERIC_CHOICE_SPEAKERS,
    atomic_json,
    build_character_resolver,
    display_character_name,
    find_phase_override,
    load_bible,
    normalize_pronoun_rules,
    read_json,
    read_jsonl,
    resolve_speaker_id,
)


def _speaker_identity(
    record: dict[str, Any],
    resolver: dict[str, Any],
) -> tuple[str | None, str]:
    """Return (stable_key, resolved_id_or_raw) for a non-choice speaker, or (None, '') if generic/empty."""
    raw_speaker = (record.get("speaker") or "").strip()
    is_choice = bool(record.get("is_choice"))
    if is_choice:
        return None, ""
    cid = resolve_speaker_id(raw_speaker, resolver, is_choice=False)
    if cid:
        return cid, cid
    low = raw_speaker.lower()
    if not low or low in GENERIC_CHOICE_SPEAKERS:
        return None, ""
    return f"raw:{low}", raw_speaker


def _has_cast_shift(
    active_cast: set[str],
    candidate_key: str,
    records: list[dict[str, Any]],
    curr_idx: int,
    resolver: dict[str, Any],
    lookahead: int = 4,
) -> bool:
    """Detect whether a new speaker starts a different conversation rather than a 3+ person group scene."""
    if len(active_cast) < 2:
        return False

    future_cast: list[str] = []
    for rec in records[curr_idx + 1 : curr_idx + 1 + lookahead]:
        fkey, _ = _speaker_identity(rec, resolver)
        if fkey:
            future_cast.append(fkey)

    # If fewer than 2 previous cast members speak soon, treat as a new conversational scenario
    prev_speakers_continuing = {s for s in future_cast if s in active_cast}
    return len(prev_speakers_continuing) < 2


def segment_records_into_scenarios(
    records: list[dict[str, Any]],
    resolver: dict[str, Any],
    gap_threshold_ms: int = 15000,
    split_after_choice_gap_ms: int = 3000,
) -> list[list[dict[str, Any]]]:
    """Group sequential records into distinct scenario segments."""
    if not records:
        return []

    by_scene: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rec in records:
        key = (rec.get("route", "common"), rec.get("scene_id", "scene"))
        by_scene.setdefault(key, []).append(rec)

    segments: list[list[dict[str, Any]]] = []

    for (_route, _scene_id), scene_recs in by_scene.items():
        current_seg: list[dict[str, Any]] = []
        active_cast: set[str] = set()

        for idx, rec in enumerate(scene_recs):
            sp_key, _ = _speaker_identity(rec, resolver)

            if not current_seg:
                current_seg.append(rec)
                if sp_key:
                    active_cast.add(sp_key)
                continue

            prev = current_seg[-1]
            start_new = False

            # 1. Explicit scenario_id boundary
            prev_scn = prev.get("scenario_id")
            curr_scn = rec.get("scenario_id")
            if (prev_scn or curr_scn) and prev_scn != curr_scn:
                start_new = True

            # 2. File boundary or timecode jump / long pause
            elif rec.get("file") != prev.get("file"):
                start_new = True
            elif rec.get("start_ms", 0) < prev.get("end_ms", 0) - 1000:
                start_new = True
            elif rec.get("start_ms", 0) - prev.get("end_ms", 0) >= gap_threshold_ms:
                start_new = True

            # 3. Post-choice scene transition
            elif prev.get("is_choice") and not rec.get("is_choice"):
                gap = rec.get("start_ms", 0) - prev.get("end_ms", 0)
                if gap >= split_after_choice_gap_ms or (sp_key and sp_key not in active_cast):
                    start_new = True

            # 4. Speaker cast switch (e.g. {Protagonist, Heroine A} -> {Protagonist, Heroine B})
            elif sp_key and sp_key not in active_cast:
                if _has_cast_shift(active_cast, sp_key, scene_recs, idx, resolver):
                    start_new = True

            if start_new:
                segments.append(current_seg)
                current_seg = [rec]
                active_cast = {sp_key} if sp_key else set()
            else:
                current_seg.append(rec)
                if sp_key:
                    active_cast.add(sp_key)

        if current_seg:
            segments.append(current_seg)

    return segments


def _infer_active_phases_for_scenario(
    participants: list[str],
    segment: list[dict[str, Any]],
    route: str,
    bible: dict[str, Any],
) -> tuple[dict[str, str], list[str]]:
    """Resolve initial active_phases map and report ambiguous multi-phase pairs."""
    all_rules = normalize_pronoun_rules(bible.get("pronoun_matrix", {}))
    timeline_routes = bible.get("timeline_relationships", {}).get("routes", {})
    route_phases = timeline_routes.get(route, {}).get("active_phases", {})

    explicit_phase = next((r.get("relationship_phase") for r in segment if r.get("relationship_phase")), None)
    part_set = set(participants)

    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rule in all_rules:
        pair = rule.get("pair") or [rule.get("speaker_a", ""), rule.get("speaker_b", "")]
        if len(pair) == 2 and pair[0] in part_set and pair[1] in part_set:
            by_pair.setdefault(tuple(sorted(pair)), []).append(rule)

    active_phases: dict[str, str] = {}
    ambiguous_notes: list[str] = []

    for (c1, c2), rules in by_pair.items():
        pair_key = f"{c1}__{c2}"
        if explicit_phase and any(r.get("phase") == explicit_phase for r in rules):
            active_phases[pair_key] = explicit_phase
        else:
            route_override = find_phase_override(route_phases, c1, c2)
            if route_override and any(r.get("phase") == route_override for r in rules):
                active_phases[pair_key] = route_override
            elif len(rules) == 1:
                active_phases[pair_key] = rules[0].get("phase", "default")
            else:
                default_rule = next((r for r in rules if r.get("phase") == "default"), None)
                if default_rule:
                    active_phases[pair_key] = "default"
                else:
                    phases_avail = [r.get("phase", "?") for r in rules]
                    ambiguous_notes.append(
                        f"{pair_key}: nhiều giai đoạn {phases_avail} — cần kiểm tra thoại cảnh này và khóa phase phù hợp"
                    )

    return active_phases, ambiguous_notes


def plan_scenarios(
    project_dir: Path,
    gap_threshold_ms: int = 15000,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate or refresh planning/scenarios.json from extracted/source.jsonl."""
    source_file = project_dir / "extracted" / "source.jsonl"
    if not source_file.exists():
        raise FileNotFoundError(f"Missing {source_file}")

    records = read_jsonl(source_file)
    if not records:
        raise ValueError("Source records are empty")

    bible = load_bible(project_dir)
    resolver = build_character_resolver(bible.get("characters", {}))
    protagonist_id = resolver.get("protagonist_id")

    planning_dir = project_dir / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    scenarios_file = planning_dir / "scenarios.json"

    existing_by_id: dict[str, dict[str, Any]] = {}
    existing_by_entry_tuple: dict[tuple[str, ...], dict[str, Any]] = {}
    if scenarios_file.exists() and not overwrite:
        prev_data = read_json(scenarios_file)
        for scn in prev_data.get("scenarios", []):
            if scn.get("scenario_id"):
                existing_by_id[scn["scenario_id"]] = scn
            if scn.get("entry_ids"):
                existing_by_entry_tuple[tuple(scn["entry_ids"])] = scn

    segments = segment_records_into_scenarios(
        records, resolver, gap_threshold_ms=gap_threshold_ms
    )

    # Track per-(route, scene_id) counter for clean deterministic IDs
    scene_counters: dict[tuple[str, str], int] = {}
    scene_totals: dict[tuple[str, str], int] = {}
    for seg in segments:
        key = (seg[0].get("route", "common"), seg[0].get("scene_id", "scene"))
        scene_totals[key] = scene_totals.get(key, 0) + 1

    scenarios: list[dict[str, Any]] = []
    curated_fields = (
        "title", "setting", "topic", "mood", "dialogue_style",
        "translation_notes", "protagonist_id", "choice_target",
        "participants", "active_phases",
    )

    for seg in segments:
        route = seg[0].get("route", "common")
        scene_id = seg[0].get("scene_id", "scene")
        key = (route, scene_id)
        scene_counters[key] = scene_counters.get(key, 0) + 1
        scn_num = scene_counters[key]

        explicit_scn_id = seg[0].get("scenario_id")
        if explicit_scn_id:
            scenario_id = str(explicit_scn_id)
        elif scene_totals[key] == 1:
            scenario_id = f"{route}__{scene_id}__scn_01"
        else:
            scenario_id = f"{route}__{scene_id}__scn_{scn_num:02d}"

        # Collect ordered participants
        participants: list[str] = []
        last_non_protagonist: str | None = None
        has_choices = any(bool(r.get("is_choice")) for r in seg)
        choice_count = sum(1 for r in seg if r.get("is_choice"))

        for r in seg:
            is_c = bool(r.get("is_choice"))
            if not is_c:
                cid = resolve_speaker_id(r.get("speaker", ""), resolver, is_choice=False)
                ident = cid or (r.get("speaker") or "").strip()
                if ident and ident.lower() not in GENERIC_CHOICE_SPEAKERS and ident not in participants:
                    participants.append(ident)
                if ident and ident != protagonist_id and ident.lower() not in GENERIC_CHOICE_SPEAKERS:
                    last_non_protagonist = ident

        if has_choices and protagonist_id and protagonist_id not in participants:
            participants.insert(0, protagonist_id)

        # Infer choice_target (explicit field -> last non-protagonist speaker before/in scene)
        choice_target = next(
            (
                resolve_speaker_id(str(r.get("choice_target") or r.get("addressee")), resolver)
                or str(r.get("choice_target") or r.get("addressee"))
                for r in seg
                if r.get("is_choice") and (r.get("choice_target") or r.get("addressee"))
            ),
            None,
        )
        if not choice_target:
            choice_target = last_non_protagonist or next(
                (p for p in participants if p != protagonist_id), None
            )

        active_phases, ambiguous_notes = _infer_active_phases_for_scenario(
            participants, seg, route, bible
        )

        # Extract optional pre-populated topic/setting/mood from source JSON
        src_topic = next((r.get("topic") for r in seg if r.get("topic")), "")
        src_setting = next((r.get("setting") for r in seg if r.get("setting")), "")
        src_mood = next((r.get("mood") for r in seg if r.get("mood")), "")

        sample_lines = []
        for r in seg[:5]:
            tag = f"LỰA CHỌN -> {display_character_name(choice_target, resolver)}" if r.get("is_choice") and choice_target else (r.get("speaker") or "N/A")
            sample_lines.append(f"[{tag}]: {r['text']}")

        scn_obj: dict[str, Any] = {
            "scenario_id": scenario_id,
            "scene_id": scene_id,
            "route": route,
            "file": seg[0].get("file", ""),
            "start_index": seg[0].get("index"),
            "end_index": seg[-1].get("index"),
            "entry_ids": [r["id"] for r in seg],
            "line_count": len(seg),
            "choice_count": choice_count,
            "has_choices": has_choices,
            "title": f"{scene_id} - Phân cảnh {scn_num}",
            "setting": src_setting or "[TODO: Bối cảnh không gian/thời gian diễn ra phân cảnh]",
            "topic": src_topic or "[TODO: Nhân vật đang nói chuyện với nhau về chủ đề gì?]",
            "mood": src_mood or "[TODO: Sắc thái cảm xúc & nhịp điệu cảnh]",
            "dialogue_style": "",
            "translation_notes": "",
            "protagonist_id": protagonist_id,
            "participants": participants,
            "participant_names": [display_character_name(p, resolver) for p in participants],
            "choice_target": choice_target,
            "active_phases": active_phases,
            "sample_lines": sample_lines,
        }
        if ambiguous_notes:
            scn_obj["phase_warnings"] = ambiguous_notes

        # Preserve curated values from existing scenarios.json
        entry_tuple = tuple(scn_obj["entry_ids"])
        prev_scn = existing_by_entry_tuple.get(entry_tuple) or existing_by_id.get(scenario_id)
        if prev_scn:
            for field in curated_fields:
                prev_val = prev_scn.get(field)
                if prev_val:
                    scn_obj[field] = prev_val
            scn_obj["participant_names"] = [
                display_character_name(p, resolver) for p in scn_obj.get("participants", [])
            ]

        scenarios.append(scn_obj)

    payload = {
        "version": "1.0",
        "protagonist_id": protagonist_id,
        "total_scenarios": len(scenarios),
        "scenarios": scenarios,
    }
    atomic_json(scenarios_file, payload)

    unresolved_count = sum(1 for s in scenarios if s.get("phase_warnings") and not s.get("active_phases"))
    print(f"[OK] Planned {len(scenarios)} scenarios -> {scenarios_file}")
    if unresolved_count:
        print(f"[WARN] {unresolved_count} scenario(s) have multiple pronoun phases and need 'active_phases' locked in {scenarios_file}.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Segment extracted dialogue into translation scenarios.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--gap-threshold-ms", type=int, default=15000, help="Silence gap (ms) to split scenario")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing curated scenario metadata")
    args = parser.parse_args()

    plan_scenarios(args.project_dir, args.gap_threshold_ms, args.overwrite)


if __name__ == "__main__":
    main()
