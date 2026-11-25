#!/usr/bin/env python3
"""Comprehensive validator: IDs, protected tokens, CPS, anti-slop, glossary, scenario pronouns & protagonist choices."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any
from pipeline_common import (
    VIETNAMESE_SLOP_PATTERNS,
    atomic_json,
    build_character_resolver,
    build_directional_locks,
    calculate_cps,
    contains_forbidden_address,
    contains_pronoun_token,
    load_bible,
    read_json,
    read_jsonl,
    resolve_scenario_pronoun_rules,
    resolve_speaker_id,
    split_pronoun_options,
)

RAW_CHOICE_TAG_RE = re.compile(r"^\[(?:QTE(?:_CHOICE_\d+)?|CHOICE(?:_\d+)?|OPTION(?:_\d+)?)\]", re.IGNORECASE)
LOCALIZED_CHOICE_PREFIX_RE = re.compile(r"^\[(?:LỰA\s*CHỌN|CHOICE|QTE)\]\s*", re.IGNORECASE)
TRACKED_SELF_PRONOUNS = ("tôi", "anh", "em", "tớ", "tao", "cháu")
CORE_COMPETING_SELF_PRONOUNS = ("tôi", "anh", "em", "tớ", "tao")


def _load_bundle_index(project_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load context bundles keyed by job_id and entry_id."""
    contexts_dir = project_dir / "contexts"
    by_job: dict[str, dict[str, Any]] = {}
    entry_to_job: dict[str, dict[str, Any]] = {}
    if not contexts_dir.exists():
        return by_job, entry_to_job

    for bundle_file in contexts_dir.glob("*/current.json"):
        bundle = read_json(bundle_file)
        jid = bundle.get("job_id")
        if jid:
            by_job[jid] = bundle
            for entry in bundle.get("primary_entries", []):
                eid = entry.get("id")
                if eid:
                    entry_to_job[eid] = {"bundle": bundle, "entry": entry}
    return by_job, entry_to_job


def _find_lock_for_entry(
    speaker_id: str | None,
    addressee_id: str | None,
    locks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not speaker_id:
        return None
    if addressee_id:
        for lk in locks:
            if lk.get("from_id") == speaker_id and lk.get("to_id") == addressee_id:
                return lk
    # Fallback when addressee wasn't set but only 1 outgoing lock exists for speaker
    candidates = [lk for lk in locks if lk.get("from_id") == speaker_id]
    if len(candidates) == 1:
        return candidates[0]
    return None


def validate_translation(
    project_dir: Path,
    job_id: str | None = None,
    draft_file: Path | None = None,
    strict_pronouns: bool = False,
) -> dict[str, Any]:
    project_meta = read_json(project_dir / "project.json")
    cps_max = float(project_meta.get("cps_max", 18.0))
    cpl_max = int(project_meta.get("cpl_max", 38))
    max_lines = int(project_meta.get("max_lines", 2))
    choice_max_chars = int(project_meta.get("choice_max_chars", 35))

    source_records = read_jsonl(project_dir / "extracted" / "source.jsonl")
    source_map = {r["id"]: r for r in source_records}

    bible = load_bible(project_dir)
    glossary = bible.get("glossary", [])
    resolver = build_character_resolver(bible.get("characters", {}))
    _, entry_ctx_map = _load_bundle_index(project_dir)

    scenarios_file = project_dir / "planning" / "scenarios.json"
    scenarios_by_entry: dict[str, dict[str, Any]] = {}
    if scenarios_file.exists():
        for scn in read_json(scenarios_file).get("scenarios", []):
            for eid in scn.get("entry_ids", []):
                scenarios_by_entry[eid] = scn

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
        approved_dir = project_dir / "translations" / "approved"
        drafts_dir = project_dir / "translations" / "drafts"
        files_to_check = sorted(drafts_dir.glob("*.jsonl")) if drafts_dir.exists() else []
        if approved_dir.exists():
            approved_files = {p.name.replace(".approved.jsonl", ""): p for p in approved_dir.glob("*.jsonl")}
            merged_list: list[Path] = []
            seen_jobs: set[str] = set()
            for jname, ap in sorted(approved_files.items()):
                merged_list.append(ap)
                seen_jobs.add(jname)
            for dp in files_to_check:
                jname = dp.name.replace(".draft.jsonl", "")
                if jname not in seen_jobs:
                    merged_list.append(dp)
            files_to_check = merged_list

    total_checked = 0
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    # Track observed unambiguous self-pronouns per (scenario_id, speaker_id, addressee_id)
    dyad_self_usage: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _emit_pronoun_issue(issue: dict[str, Any]) -> None:
        if strict_pronouns:
            errors.append(issue)
        else:
            warnings.append(issue)

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
            is_choice = bool(src.get("is_choice"))

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

            # 4. Vietnamese Anti-AI-Slop & word-by-word calque detector
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

            # 6. Scenario Pronoun Lock & Protagonist Choice Audit
            ctx_info = entry_ctx_map.get(entry_id)
            if ctx_info:
                bundle = ctx_info["bundle"]
                ctx_entry = ctx_info["entry"]
                scenario_id = bundle.get("scenario_id", file_path.stem)
                speaker_id = ctx_entry.get("speaker_id") or resolve_speaker_id(src.get("speaker", ""), resolver, is_choice=is_choice)
                addressee_id = ctx_entry.get("addressee_id")
                locks = bundle.get("directional_pronoun_locks", [])
                participants_count = len(bundle.get("participants", []))
            else:
                scn = scenarios_by_entry.get(entry_id, {})
                scenario_id = scn.get("scenario_id") or src.get("scene_id") or file_path.stem
                speaker_id = resolve_speaker_id(src.get("speaker", ""), resolver, is_choice=is_choice)
                addressee_id = scn.get("choice_target") if is_choice else None
                scn_participants = scn.get("participants") or ([p for p in (speaker_id, addressee_id) if p])
                rules, _ = resolve_scenario_pronoun_rules(
                    scn_participants, bible, src.get("route", "common"), scn.get("active_phases")
                )
                locks = build_directional_locks(rules, resolver)
                participants_count = len(scn_participants)

            lock = _find_lock_for_entry(speaker_id, addressee_id, locks)
            allowed_self = set(split_pronoun_options(lock.get("self_pronouns", ""))) if lock else set()
            allowed_addr = set(split_pronoun_options(lock.get("address_pronouns", ""))) if lock else set()

            # 6a. Standalone 'bạn' pronoun check (outside compound nouns like 'bạn thân')
            if contains_pronoun_token(translation, "bạn"):
                if not lock or ("bạn" not in allowed_addr and "bạn" not in allowed_self):
                    _emit_pronoun_issue({
                        "id": entry_id,
                        "code": "choice_pronoun_slop" if is_choice else "pronoun_toi_ban_forbidden",
                        "message": (
                            "Lựa chọn của nhân vật chính dùng đại từ rập khuôn 'bạn' — hãy sửa theo đúng quan hệ nhân vật."
                            if is_choice
                            else "Dùng đại từ 'bạn' không phù hợp với ma trận xưng hô trong phân cảnh."
                        ),
                        "sample": translation,
                    })

            # 6b. Locked dyad forbidden & out-of-spec self / address checks
            if lock:
                checked_forb_s: set[str] = set()
                for forb_s in lock.get("forbidden_self", []):
                    forb_s_low = forb_s.strip().lower()
                    if not forb_s_low or forb_s_low in allowed_self or forb_s_low in allowed_addr:
                        continue
                    checked_forb_s.add(forb_s_low)
                    if contains_pronoun_token(translation, forb_s_low):
                        _emit_pronoun_issue({
                            "id": entry_id,
                            "code": "choice_pronoun_mismatch" if is_choice else "pronoun_phase_self_mismatch",
                            "phase": lock.get("phase"),
                            "forbidden_token": forb_s,
                            "expected_self": lock.get("self_pronouns"),
                            "message": (
                                f"Sai ngôi tự xưng trong {'lựa chọn nhân vật chính' if is_choice else 'thoại'}: "
                                f"dùng '{forb_s}' dù giai đoạn '{lock.get('phase')}' yêu cầu tự xưng '{lock.get('self_pronouns')}'."
                            ),
                            "sample": translation,
                        })

                if allowed_self:
                    for core_s in CORE_COMPETING_SELF_PRONOUNS:
                        if core_s in allowed_self or core_s in allowed_addr or core_s in checked_forb_s:
                            continue
                        if contains_pronoun_token(translation, core_s):
                            _emit_pronoun_issue({
                                "id": entry_id,
                                "code": "choice_pronoun_mismatch" if is_choice else "pronoun_phase_self_mismatch",
                                "phase": lock.get("phase"),
                                "forbidden_token": core_s,
                                "expected_self": lock.get("self_pronouns"),
                                "message": (
                                    f"Lệch ngôi tự xưng trong {'lựa chọn nhân vật chính' if is_choice else 'thoại'}: "
                                    f"dùng '{core_s}' không khớp với '{lock.get('self_pronouns')}' ở giai đoạn '{lock.get('phase')}'."
                                ),
                                "sample": translation,
                            })

                for forb_a in lock.get("forbidden_address", []):
                    forb_a_low = forb_a.strip().lower()
                    if not forb_a_low or forb_a_low in allowed_addr:
                        continue
                    if contains_forbidden_address(translation, forb_a_low, allowed_self, is_choice=is_choice):
                        _emit_pronoun_issue({
                            "id": entry_id,
                            "code": "choice_pronoun_mismatch" if is_choice else "pronoun_phase_address_mismatch",
                            "phase": lock.get("phase"),
                            "forbidden_token": forb_a,
                            "expected_address": lock.get("address_pronouns"),
                            "message": (
                                f"Sai ngôi gọi đối phương trong {'lựa chọn nhân vật chính' if is_choice else 'thoại'}: "
                                f"dùng '{forb_a}' dù giai đoạn '{lock.get('phase')}' yêu cầu gọi '{lock.get('address_pronouns')}'."
                            ),
                            "sample": translation,
                        })

            # 6c. Choice-specific checks (raw tags, brevity, vague 3rd-person target)
            if is_choice:
                if RAW_CHOICE_TAG_RE.match(translation) and not any(
                    RAW_CHOICE_TAG_RE.match(t) for t in src.get("protected_tokens", [])
                ):
                    warnings.append({
                        "id": entry_id,
                        "code": "unlocalized_choice_tag",
                        "message": "Thẻ lựa chọn nguồn ([QTE_CHOICE_*] / [CHOICE]) chưa được chuyển thành [LỰA CHỌN] hoặc làm sạch.",
                        "sample": translation,
                    })

                choice_label = LOCALIZED_CHOICE_PREFIX_RE.sub("", translation).strip()
                if len(choice_label) > choice_max_chars:
                    warnings.append({
                        "id": entry_id,
                        "code": "choice_too_long",
                        "char_count": len(choice_label),
                        "message": f"Nút bấm lựa chọn quá dài ({len(choice_label)} > {choice_max_chars} ký tự), cần rút gọn súc tích.",
                        "sample": translation,
                    })

                if lock and participants_count <= 2:
                    for vague in ("cô ấy", "cô ta", "anh ấy", "anh ta"):
                        if vague in translation.lower() and vague not in allowed_addr:
                            warnings.append({
                                "id": entry_id,
                                "code": "choice_pronoun_vague_target",
                                "message": (
                                    f"Lựa chọn nhân vật chính dùng '{vague}' khá xa lạ; trong cảnh này đối phương là '{lock.get('to_name')}' "
                                    f"(gọi: '{lock.get('address_pronouns')}'). Hãy cân nhắc gọi đúng vai vế cho tự nhiên."
                                ),
                                "sample": translation,
                            })

            # 6d. Track intra-scenario self-pronoun drift
            sp_key = str(speaker_id or src.get("speaker") or ("protagonist" if is_choice else ""))
            addr_key = str(addressee_id or "")
            if sp_key:
                dyad_key = (str(scenario_id), sp_key, addr_key)
                observed = dyad_self_usage.setdefault(dyad_key, {
                    "tokens": set(),
                    "samples": {},
                    "allowed_self": set(allowed_self),
                    "forbidden_self": set(),
                })
                if allowed_self:
                    observed["allowed_self"].update(allowed_self)
                if lock:
                    observed["forbidden_self"].update(
                        t.strip().lower() for t in lock.get("forbidden_self", []) if t.strip()
                    )
                for p_tok in TRACKED_SELF_PRONOUNS:
                    # Only treat as unambiguous self-pronoun if it isn't also a known address term in this dyad
                    if p_tok in allowed_addr:
                        continue
                    if contains_pronoun_token(translation, p_tok):
                        observed["tokens"].add(p_tok)
                        observed["samples"].setdefault(p_tok, entry_id)

    for (scn_id, sp_key, addr_key), info in dyad_self_usage.items():
        used = info["tokens"]
        allowed_s = info["allowed_self"]
        forb_s = info["forbidden_self"]
        if len(used) >= 2:
            # If every used token is explicitly co-permitted in lock.self_pronouns (e.g. 'em / tôi'), no drift warning
            if allowed_s and used.issubset(allowed_s):
                continue
            # Exclude tokens already flagged via forbidden_self unless >=2 non-forbidden tokens drift
            non_forbidden_used = used - forb_s
            if len(non_forbidden_used) < 2 and forb_s:
                continue
            target_tok = next((t for t in sorted(used) if t not in allowed_s), next(iter(sorted(used))))
            warnings.append({
                "id": info["samples"][target_tok],
                "code": "pronoun_drift_in_scenario",
                "scenario_id": scn_id,
                "speaker": sp_key,
                "addressee": addr_key,
                "observed_self_pronouns": sorted(used),
                "message": (
                    f"Loạn ngôi tự xưng trong cùng phân cảnh '{scn_id}' ({sp_key} -> {addr_key or 'đối phương'}): "
                    f"lúc dùng {sorted(used)} không nhất quán."
                ),
            })

    pronoun_issue_codes = {
        "pronoun_toi_ban_forbidden",
        "choice_pronoun_slop",
        "choice_pronoun_mismatch",
        "pronoun_phase_self_mismatch",
        "pronoun_phase_address_mismatch",
        "choice_pronoun_vague_target",
        "pronoun_drift_in_scenario",
    }
    pronoun_issue_count = sum(
        1 for item in (errors + warnings) if item.get("code") in pronoun_issue_codes
    )

    report = {
        "total_lines_validated": total_checked,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "pronoun_issue_count": pronoun_issue_count,
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if len(errors) == 0 else "fail",
    }

    qa_dir = project_dir / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    report_file = qa_dir / "validation-report.json"
    atomic_json(report_file, report)

    print(f"[QA] Validated {total_checked} lines: {len(errors)} errors, {len(warnings)} warnings ({pronoun_issue_count} pronoun/choice notices).")
    if errors:
        print("     STATUS: FAILED (Errors found)")
        for err in errors[:5]:
            print(f"     - [ERROR {err['code']}] {err.get('id')}: {err['message']}")
    else:
        print("     STATUS: PASSED")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate translation against rules, CPS, pronouns, choices, and AI slop.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, default=None, help="Job ID to validate")
    parser.add_argument("--draft", type=Path, default=None, help="Specific draft JSONL file")
    parser.add_argument("--strict-pronouns", action="store_true", help="Treat pronoun/choice mismatches as hard errors")
    args = parser.parse_args()

    report = validate_translation(args.project_dir, args.job_id, args.draft, strict_pronouns=args.strict_pronouns)
    if report["error_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
