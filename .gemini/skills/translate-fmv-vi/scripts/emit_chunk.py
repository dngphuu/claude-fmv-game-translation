#!/usr/bin/env python3
"""Emit a scenario-aware, anti-word-by-word prompt packet for a translation job."""

from __future__ import annotations

import argparse
from pathlib import Path
from pipeline_common import read_json, read_text


def emit_chunk(project_dir: Path, job_id: str, include_prefix: bool = False) -> str:
    bundle_file = project_dir / "contexts" / job_id / "current.json"
    if not bundle_file.exists():
        raise FileNotFoundError(f"Missing bundle for job: {job_id}")

    bundle = read_json(bundle_file)
    prefix_file = project_dir / "contexts" / "shared-prefix" / "prefix.md"
    prefix_text = read_text(prefix_file) if (include_prefix and prefix_file.exists()) else ""

    scn = bundle.get("scenario", {})
    prot = bundle.get("protagonist", {})
    choice_target = bundle.get("choice_target") or {}
    participants = bundle.get("participants", [])

    lines: list[str] = []
    if prefix_text:
        lines.append(prefix_text.strip())
        lines.append("")

    lines.extend([
        "=== NHIỆM VỤ DỊCH GAME FMV THEO PHÂN CẢNH (SCENARIO PACKET) ===",
        f"Mã Job: {job_id} | Scenario: {bundle.get('scenario_id')}",
        f"Phân cảnh gốc: {bundle.get('scene_id')} | Tuyến truyện: {bundle.get('route')}",
        "",
        "=== KỊCH BẢN PHÂN CẢNH HIỆN TẠI (SCENARIO BRIEF) ===",
        f"- Tên phân cảnh: {scn.get('title') or bundle.get('scene_id')}",
        f"- Bối cảnh (Setting): {scn.get('setting') or 'Chưa ghi chú — hãy bám sát lời thoại cảnh này'}",
        f"- Chủ đề trò chuyện (Topic): {scn.get('topic') or 'Chưa ghi chú — hãy đọc hết mạch thoại bên dưới để nắm chủ đề'}",
        f"- Tông giọng / Cảm xúc (Mood): {scn.get('mood') or 'Tự nhiên theo diễn xuất cảnh quay'}",
    ])
    if scn.get("dialogue_style"):
        lines.append(f"- Phong cách khẩu ngữ: {scn['dialogue_style']}")
    if scn.get("translation_notes"):
        lines.append(f"- Ghi chú chuyển ngữ riêng: {scn['translation_notes']}")
    lines.append(f"- Nhân vật chính (Protagonist): {prot.get('name', 'Nhân vật chính')}")
    if choice_target.get("name"):
        lines.append(f"- Đối tượng giao tiếp / Đích lựa chọn: {choice_target['name']}")

    if participants:
        lines.extend(["", "=== HỒ SƠ & KHẨU KHÍ NHÂN VẬT TRONG PHÂN CẢNH ==="])
        for p in participants:
            role_tag = " [NHÂN VẬT CHÍNH]" if p.get("is_protagonist") else ""
            meta_bits = [b for b in [p.get("gender"), f"{p['age']} tuổi" if p.get("age") else "", p.get("occupation")] if b]
            lines.append(f"- {p.get('name')}{role_tag} ({', '.join(meta_bits) or 'Diễn viên'}):")
            if p.get("personality"):
                lines.append(f"  + Tính cách: {p['personality']}")
            if p.get("speaking_style") or p.get("voice_tone"):
                lines.append(f"  + Khẩu khí: {p.get('speaking_style') or p.get('voice_tone')}")
            if p.get("frequent_particles"):
                lines.append(f"  + Trợ từ hay dùng: {', '.join(p['frequent_particles'])}")

    lines.extend(["", "=== KHÓA XƯNG HÔ BẮT BUỘC TRONG PHÂN CẢNH NÀY (ACTIVE PRONOUN LOCK) ==="])
    locks = bundle.get("directional_pronoun_locks", [])
    if locks:
        seen_phases: set[str] = set()
        for lk in locks:
            phase_hdr = f"{lk.get('phase')} — {lk.get('phase_label')}"
            if phase_hdr not in seen_phases:
                lines.append(f"[Giai đoạn: {phase_hdr}]")
                seen_phases.add(phase_hdr)
            forb_parts = []
            if lk.get("forbidden_self"):
                forb_parts.append(f"CẤM tự xưng: {', '.join(lk['forbidden_self'])}")
            if lk.get("forbidden_address"):
                forb_parts.append(f"CẤM gọi đối phương: {', '.join(lk['forbidden_address'])}")
            forb_str = f" | {' ; '.join(forb_parts)}" if forb_parts else ""
            lines.append(
                f"  - {lk.get('from_name')} -> {lk.get('to_name')}: "
                f"tự xưng \"{lk.get('self_pronouns')}\" | gọi đối phương \"{lk.get('address_pronouns')}\"{forb_str}"
            )
    else:
        lines.append("- Chưa có cặp luật xưng hô khớp sẵn trong pronoun_matrix.json cho cảnh này; giữ xưng hô nhất quán theo vai vế thực tế, cấm dùng 'Tôi - Bạn'.")

    for warn in bundle.get("unresolved_pronoun_warnings", []):
        lines.append(f"  [CẢNH BÁO PHASE] {warn}")

    choice_guidance = bundle.get("protagonist_choice_guidance")
    if choice_guidance and any(e.get("is_choice") for e in bundle.get("primary_entries", [])):
        lines.extend([
            "",
            "=== QUY TẮC LỰA CHỌN CỦA NHÂN VẬT CHÍNH [IS_CHOICE] ===",
            f"- {choice_guidance.get('instruction', '')}",
            "- Ngắn gọn dứt khoát (dưới 20-25 ký tự phần nội dung lựa chọn), giữ đúng thẻ đầu [LỰA CHỌN] nếu nguồn là lựa chọn.",
        ])

    lines.extend([
        "",
        "=== NGUYÊN TẮC CHỐNG DỊCH MÁY WORD-BY-WORD ===",
        "1. Đọc toàn bộ thoại trong phân cảnh để hiểu chủ đề và ẩn ý trước khi đặt bút dịch câu đầu tiên.",
        "2. Thoát ly cấu trúc ngữ pháp câu gốc: diễn đạt lại đúng cách người Việt nói chuyện ngoài đời trong tình huống này (dùng trợ từ nhé/nhá/nè/đấy/chứ/thôi phù hợp tính cách).",
        "3. Đọc nhẩm theo thời lượng (duration) để giữ CPS <= 18.",
    ])

    preceding = bundle.get("surrounding_context", {}).get("preceding_dialogue", [])
    if preceding:
        lines.extend(["", "=== MẠCH THOẠI TRƯỚC ĐÓ (GIỮ LIỀN MẠCH & XƯNG HÔ) ==="])
        for p in preceding:
            scope = "cùng phân cảnh" if p.get("same_scenario") else "phân cảnh trước"
            lines.append(f"[{p.get('speaker') or 'Unknown'} | {scope}]: {p.get('text')}")
            if p.get("prior_translation"):
                lines.append(f"  -> Bản dịch đã dùng: {p['prior_translation']}")

    succeeding = bundle.get("surrounding_context", {}).get("succeeding_dialogue", [])
    if succeeding:
        lines.extend(["", "=== MẠCH THOẠI TIẾP THEO (THAM KHẢO HƯỚNG CÂU CHUYỆN) ==="])
        for s in succeeding:
            scope = "cùng phân cảnh" if s.get("same_scenario") else "phân cảnh sau"
            lines.append(f"[{s.get('speaker') or 'Unknown'} | {scope}]: {s.get('text')}")

    lines.extend([
        "",
        "=== CÁC CÂU THOẠI CẦN DỊCH (BẮT BUỘC TRẢ VỀ DẠNG JSONL) ===",
        "Định dạng mỗi dòng đầu ra: {\"id\": \"...\", \"translation\": \"...\"}",
        "",
    ])

    for item in bundle.get("primary_entries", []):
        dur_sec = item.get("duration_ms", 0) / 1000.0
        sp_disp = item.get("speaker_display") or item.get("speaker") or "N/A"
        addr_disp = item.get("addressee_display") or ""
        if item.get("is_choice"):
            actor_label = (
                f"Lựa chọn của {prot.get('name', 'Nhân vật chính')}"
                + (f" -> Hướng tới: {addr_disp}" if addr_disp else "")
            )
            choice_tag = " [NÚT BẤM LỰA CHỌN / QTE]"
        else:
            actor_label = f"Người nói: {sp_disp}" + (f" -> Người nghe: {addr_disp}" if addr_disp else "")
            choice_tag = ""

        lines.append(f"ID: {item['id']} | {actor_label} | Thời lượng: {dur_sec:.1f}s{choice_tag}")
        if item.get("protected_tokens"):
            lines.append(f"  Thẻ bảo vệ (phải giữ nguyên): {item['protected_tokens']}")
        lines.append(f"  Thoại gốc: {item['text']}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit prompt packet for a job.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, required=True, help="Job identifier")
    parser.add_argument("--include-prefix", action="store_true", help="Include shared prefix markdown at top")
    args = parser.parse_args()

    packet = emit_chunk(args.project_dir, args.job_id, include_prefix=args.include_prefix)
    print(packet)


if __name__ == "__main__":
    main()
