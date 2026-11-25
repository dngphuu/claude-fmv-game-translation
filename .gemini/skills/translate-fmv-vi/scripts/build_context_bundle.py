#!/usr/bin/env python3
"""Build scenario-aware context bundles with locked dyad pronouns and protagonist choice rules."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from pipeline_common import (
    GENERIC_CHOICE_SPEAKERS,
    atomic_json,
    build_character_resolver,
    build_directional_locks,
    display_character_name,
    load_bible,
    read_json,
    read_jsonl,
    resolve_scenario_pronoun_rules,
    resolve_speaker_id,
)


def _load_existing_translations(project_dir: Path) -> dict[str, str]:
    """Load already translated/approved lines so multi-part scenarios keep exact continuity."""
    trans_map: dict[str, str] = {}
    for folder in ("drafts", "approved"):
        d = project_dir / "translations" / folder
        if d.exists():
            for f in sorted(d.glob("*.jsonl")):
                for r in read_jsonl(f):
                    if r.get("id") and r.get("translation"):
                        trans_map[r["id"]] = r["translation"]
    return trans_map


def _infer_addressee_id(
    idx_in_job: int,
    primary_items: list[dict[str, Any]],
    speaker_id: str | None,
    participants: list[str],
    protagonist_id: str | None,
    choice_target: str | None,
    resolver: dict[str, Any],
) -> str | None:
    item = primary_items[idx_in_job]
    explicit = item.get("addressee") or item.get("choice_target")
    if explicit:
        return resolve_speaker_id(str(explicit), resolver) or str(explicit)

    if item.get("is_choice"):
        if choice_target:
            return choice_target
        for j in range(idx_in_job - 1, -1, -1):
            prev_sp = resolve_speaker_id(primary_items[j].get("speaker", ""), resolver) or primary_items[j].get("speaker", "")
            if prev_sp and prev_sp != protagonist_id and prev_sp.lower() not in GENERIC_CHOICE_SPEAKERS:
                return prev_sp
        return None

    if speaker_id and len(participants) == 2:
        other = [p for p in participants if p != speaker_id]
        if len(other) == 1:
            return other[0]

    # Fall back to nearest adjacent different speaker in this scenario
    for offset in (-1, 1, -2, 2):
        j = idx_in_job + offset
        if 0 <= j < len(primary_items) and not primary_items[j].get("is_choice"):
            adj_sp = resolve_speaker_id(primary_items[j].get("speaker", ""), resolver) or primary_items[j].get("speaker", "")
            if adj_sp and adj_sp != speaker_id and adj_sp.lower() not in GENERIC_CHOICE_SPEAKERS:
                return adj_sp
    return None


def _build_choice_guidance(
    protagonist_id: str | None,
    choice_target: str | None,
    directional_locks: list[dict[str, Any]],
    resolver: dict[str, Any],
) -> dict[str, Any] | None:
    if not protagonist_id and not choice_target:
        return None

    prot_name = display_character_name(protagonist_id, resolver) if protagonist_id else "Nhân vật chính"
    target_name = display_character_name(choice_target, resolver) if choice_target else "người đối diện"

    matched_lock = None
    if protagonist_id and choice_target:
        matched_lock = next(
            (l for l in directional_locks if l["from_id"] == protagonist_id and l["to_id"] == choice_target),
            None,
        )

    guidance: dict[str, Any] = {
        "protagonist_id": protagonist_id,
        "protagonist_name": prot_name,
        "target_id": choice_target,
        "target_name": target_name,
        "protagonist_calls_self": matched_lock.get("self_pronouns", "") if matched_lock else "",
        "protagonist_calls_target": matched_lock.get("address_pronouns", "") if matched_lock else "",
        "forbidden_self": matched_lock.get("forbidden_self", []) if matched_lock else [],
        "forbidden_address": matched_lock.get("forbidden_address", []) if matched_lock else [],
    }

    if matched_lock:
        custom_note = matched_lock.get("choice_guidance")
        default_note = (
            f"Mọi nút bấm LỰA CHỌN [IS_CHOICE] đều do {prot_name} đưa ra hướng tới {target_name}. "
            f"Nếu là lời thoại trực tiếp của nhân vật chính: tự xưng '{matched_lock['self_pronouns']}', "
            f"gọi đối phương '{matched_lock['address_pronouns']}'. "
            f"Nếu là nhãn hành động (VD: trêu chọc / an ủi / thú nhận): gọi {target_name} đúng vai vế '{matched_lock['address_pronouns']}' trong cảnh này, "
            f"tuyệt đối KHÔNG dùng 'bạn' hay nhảy sai giai đoạn quan hệ."
        )
        guidance["instruction"] = custom_note or default_note
    else:
        guidance["instruction"] = (
            f"Mọi nút bấm LỰA CHỌN [IS_CHOICE] đều do {prot_name} (Nhân vật chính) đưa ra hướng tới {target_name}. "
            "Giữ nhất quán ngôi xưng hô của nhân vật chính trong phân cảnh này, tránh 'Tôi - Bạn' hoặc đại từ lệch vai vế."
        )

    return guidance


def build_context_bundle(project_dir: Path, job_ids: list[str] | None = None) -> None:
    source_file = project_dir / "extracted" / "source.jsonl"
    jobs_file = project_dir / "planning" / "jobs.jsonl"
    scenarios_file = project_dir / "planning" / "scenarios.json"
    prefix_meta_file = project_dir / "contexts" / "shared-prefix" / "prefix-meta.json"

    if not source_file.exists() or not jobs_file.exists():
        raise FileNotFoundError("Missing source or jobs file.")

    source_records = read_jsonl(source_file)
    source_map = {r["id"]: r for r in source_records}
    jobs = read_jsonl(jobs_file)

    scenarios_map: dict[str, dict[str, Any]] = {}
    if scenarios_file.exists():
        for scn in read_json(scenarios_file).get("scenarios", []):
            if scn.get("scenario_id"):
                scenarios_map[scn["scenario_id"]] = scn

    bible = load_bible(project_dir)
    resolver = build_character_resolver(bible.get("characters", {}))
    voice_map = bible.get("voice", {})
    prefix_meta = read_json(prefix_meta_file) if prefix_meta_file.exists() else {}
    existing_trans = _load_existing_translations(project_dir)

    target_jobs = jobs if job_ids is None else [j for j in jobs if j["job_id"] in job_ids]

    for job in target_jobs:
        jid = job["job_id"]
        entry_ids = job.get("entry_ids", [])
        primary_items = [source_map[eid] for eid in entry_ids if eid in source_map]
        if not primary_items:
            continue

        scenario = scenarios_map.get(job.get("scenario_id", ""), {})
        route = job.get("route", scenario.get("route", "common"))
        protagonist_id = scenario.get("protagonist_id") or resolver.get("protagonist_id")

        # Resolve participants for this scenario
        participants: list[str] = list(scenario.get("participants") or job.get("participants") or [])
        if not participants:
            for item in primary_items:
                if item.get("is_choice"):
                    continue
                cid = resolve_speaker_id(item.get("speaker", ""), resolver)
                ident = cid or (item.get("speaker") or "").strip()
                if ident and ident.lower() not in GENERIC_CHOICE_SPEAKERS and ident not in participants:
                    participants.append(ident)
        if any(item.get("is_choice") for item in primary_items) and protagonist_id and protagonist_id not in participants:
            participants.insert(0, protagonist_id)

        choice_target = scenario.get("choice_target") or job.get("choice_target")
        if not choice_target:
            choice_target = next((p for p in participants if p != protagonist_id), None)

        applicable_rules, phase_warnings = resolve_scenario_pronoun_rules(
            participants=participants,
            bible=bible,
            route=route,
            scenario_active_phases=scenario.get("active_phases"),
        )
        directional_locks = build_directional_locks(applicable_rules, resolver)

        # Participant bios & voice styles (scoped to this scenario only)
        participant_profiles: list[dict[str, Any]] = []
        for pid in participants:
            char_info = resolver.get("by_id", {}).get(pid, {})
            voice_info = voice_map.get(pid, {})
            participant_profiles.append({
                "id": pid,
                "name": display_character_name(pid, resolver),
                "is_protagonist": pid == protagonist_id,
                "gender": char_info.get("gender", ""),
                "age": char_info.get("age", ""),
                "occupation": char_info.get("occupation", ""),
                "personality": char_info.get("personality", ""),
                "voice_tone": char_info.get("voice_tone", ""),
                "speaking_style": voice_info.get("speaking_style", ""),
                "frequent_particles": voice_info.get("frequent_particles", []),
                "anti_slop_notes": voice_info.get("anti_slop_notes", ""),
            })

        # Surrounding context within the same file
        first_idx = primary_items[0]["index"]
        last_idx = primary_items[-1]["index"]
        filename = primary_items[0]["file"]
        scn_entry_set = set(scenario.get("entry_ids", entry_ids))

        file_recs = [r for r in source_records if r["file"] == filename]
        preceding = [r for r in file_recs if r["index"] < first_idx][-3:]
        succeeding = [r for r in file_recs if r["index"] > last_idx][:3]

        enriched_entries: list[dict[str, Any]] = []
        for idx_i, item in enumerate(primary_items):
            is_choice = bool(item.get("is_choice"))
            raw_sp = item.get("speaker", "")
            sp_id = resolve_speaker_id(raw_sp, resolver, is_choice=is_choice) or raw_sp
            addr_id = _infer_addressee_id(
                idx_i, primary_items, sp_id if sp_id else None,
                participants, protagonist_id, choice_target, resolver,
            )
            enriched_entries.append({
                "id": item["id"],
                "speaker": raw_sp,
                "speaker_id": sp_id,
                "speaker_display": display_character_name(sp_id, resolver) if sp_id else raw_sp,
                "addressee_id": addr_id,
                "addressee_display": display_character_name(addr_id, resolver) if addr_id else "",
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time"),
                "duration_ms": item.get("duration_ms", 0),
                "text": item["text"],
                "protected_tokens": item.get("protected_tokens", []),
                "is_choice": is_choice,
            })

        has_choices = any(e["is_choice"] for e in enriched_entries)
        choice_guidance = (
            _build_choice_guidance(protagonist_id, choice_target, directional_locks, resolver)
            if (has_choices or choice_target)
            else None
        )

        bundle_data = {
            "job_id": jid,
            "scenario_id": scenario.get("scenario_id") or job.get("scenario_id") or jid,
            "scene_id": job.get("scene_id"),
            "route": route,
            "shared_prefix_hash": prefix_meta.get("prefix_hash"),
            "scenario": {
                "title": scenario.get("title") or job.get("scenario_title") or job.get("scene_id", ""),
                "setting": scenario.get("setting", ""),
                "topic": scenario.get("topic", ""),
                "mood": scenario.get("mood", ""),
                "dialogue_style": scenario.get("dialogue_style", ""),
                "translation_notes": scenario.get("translation_notes", ""),
            },
            "protagonist": {
                "id": protagonist_id,
                "name": display_character_name(protagonist_id, resolver) if protagonist_id else "Nhân vật chính",
            },
            "choice_target": {
                "id": choice_target,
                "name": display_character_name(choice_target, resolver) if choice_target else "",
            } if choice_target else None,
            "speakers": job.get("speakers", []),
            "participants": participant_profiles,
            "active_pronoun_rules": applicable_rules,
            "directional_pronoun_locks": directional_locks,
            "protagonist_choice_guidance": choice_guidance,
            "unresolved_pronoun_warnings": phase_warnings,
            "surrounding_context": {
                "preceding_dialogue": [
                    {
                        "id": p.get("id"),
                        "speaker": p.get("speaker"),
                        "text": p.get("text"),
                        "same_scenario": p.get("id") in scn_entry_set,
                        "prior_translation": existing_trans.get(p.get("id", "")),
                    }
                    for p in preceding
                ],
                "succeeding_dialogue": [
                    {
                        "id": s.get("id"),
                        "speaker": s.get("speaker"),
                        "text": s.get("text"),
                        "same_scenario": s.get("id") in scn_entry_set,
                    }
                    for s in succeeding
                ],
            },
            "primary_entries": enriched_entries,
        }

        job_context_dir = project_dir / "contexts" / jid
        job_context_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(job_context_dir / "current.json", bundle_data)

    print(f"[OK] Built scenario-aware context bundles for {len(target_jobs)} jobs.")


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
