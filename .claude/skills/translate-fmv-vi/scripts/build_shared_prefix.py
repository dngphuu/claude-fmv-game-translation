#!/usr/bin/env python3
"""Build immutable shared prompt prefix from frozen Bible and Anti-Slop rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pipeline_common import atomic_json, atomic_text, digest_text, read_json, read_text, read_tsv


def build_shared_prefix(project_dir: Path) -> str:
    bible_dir = project_dir / "bible"
    if not bible_dir.exists():
        raise FileNotFoundError(f"Missing {bible_dir}")

    prefix_dir = project_dir / "contexts" / "shared-prefix"
    prefix_dir.mkdir(parents=True, exist_ok=True)

    project_json = read_json(project_dir / "project.json")
    world_md = read_text(bible_dir / "world.md") if (bible_dir / "world.md").exists() else ""
    characters = read_json(bible_dir / "characters.json") if (bible_dir / "characters.json").exists() else {}
    pronoun_matrix = read_json(bible_dir / "pronoun_matrix.json") if (bible_dir / "pronoun_matrix.json").exists() else {}
    timeline = read_json(bible_dir / "timeline_relationships.json") if (bible_dir / "timeline_relationships.json").exists() else {}
    voice = read_json(bible_dir / "voice.json") if (bible_dir / "voice.json").exists() else {}
    glossary = read_tsv(bible_dir / "glossary.tsv") if (bible_dir / "glossary.tsv").exists() else []

    ref_voice_guide = Path(__file__).resolve().parent.parent / "references" / "vietnamese-natural-voice-guide.md"
    anti_slop_summary = ""
    if ref_voice_guide.exists():
        anti_slop_summary = read_text(ref_voice_guide)

    scenario_rules = "\n".join([
        "1. **Dịch theo Scenario & Chủ đề hội thoại (Scenario-First, Anti-Word-by-Word)**: Trước khi dịch từng dòng, luôn đọc Scenario Brief (bối cảnh, chủ đề, tâm lý, mối quan hệ) để hiểu ý đồ giao tiếp. Chuyển hóa trọn vẹn ý nghĩa sang khẩu ngữ Việt tự nhiên, tuyệt đối không dịch đối xứng từng chữ (word-by-word).",
        "2. **Tuân thủ Khóa Xưng Hô từng Phân Cảnh (Active Pronoun Lock)**: Mỗi phân cảnh chỉ kích hoạt MỘT giai đoạn quan hệ cho từng cặp nhân vật. Không trộn lẫn xưng hô giữa các giai đoạn khác nhau và tuyệt đối không nhảy sang 'Tôi - Bạn'.",
        "3. **Các Lựa Chọn (`is_choice`) Là Của Nhân Vật Chính**: Mọi nút bấm lựa chọn đều xuất phát từ góc nhìn và hành động của Nhân vật chính (Protagonist) hướng tới nhân vật đối diện trong phân cảnh. Phải giữ đúng vai vế xưng hô của nhân vật chính với người đó.",
    ])

    sections = [
        "# DỰ ÁN VIỆT HÓA GAME FMV: QUY TẮC CỐT LÕI & TIỀN TỐ BẢN DỊCH",
        f"**Tựa game**: {project_json.get('display_title')} | Cặp ngôn ngữ: {project_json.get('source_language')} -> {project_json.get('target_language')}",
        f"**Định mức CPS mục tiêu**: {project_json.get('cps_target', 15.0)} chars/sec (Tối đa: {project_json.get('cps_max', 18.0)})",
        "",
        "## NGUYÊN TẮC DỊCH THEO PHÂN CẢNH & LỰA CHỌN",
        scenario_rules,
        "",
        "## BỐI CẢNH TÁC PHẨM",
        world_md.strip(),
        "",
        "## HỒ SƠ NHÂN VẬT & KHẨU KHÍ",
        json.dumps(characters, indent=2, ensure_ascii=False),
        "",
        "## MA TRẬN XƯNG HÔ TIẾNG VIỆT (PRONOUN MATRIX)",
        json.dumps(pronoun_matrix, indent=2, ensure_ascii=False),
        "",
        "## TIẾN TRÌNH QUAN HỆ THEO TUYẾN TRUYỆN (TIMELINE)",
        json.dumps(timeline, indent=2, ensure_ascii=False),
        "",
        "## HƯỚNG DẪN GIỌNG ĐIỆU NHÂN VẬT (VOICE)",
        json.dumps(voice, indent=2, ensure_ascii=False),
        "",
        "## TỪ ĐIỂN THUẬT NGỮ BẮT BUỘC (GLOSSARY)",
        format_glossary(glossary),
        "",
        "## QUY TẮC CHỐNG VĂN DỊCH MÁY (ANTI-AI-SLOP MANIFESTO)",
        anti_slop_summary.strip(),
    ]

    prefix_content = "\n\n".join(sections) + "\n"
    prefix_hash = digest_text(prefix_content)

    prefix_file = prefix_dir / "prefix.md"
    atomic_text(prefix_file, prefix_content)

    meta_file = prefix_dir / "prefix-meta.json"
    atomic_json(meta_file, {
        "prefix_hash": prefix_hash,
        "char_count": len(prefix_content),
        "glossary_term_count": len(glossary),
    })

    print(f"[OK] Built shared prefix ({len(prefix_content)} chars, hash: {prefix_hash[:16]}...)")
    print(f"     Saved to: {prefix_file}")
    return prefix_hash


def format_glossary(rows: list[dict[str, str]]) -> str:
    lines = ["| Nguồn | Đích (Tiếng Việt) | Phạm vi | Ghi chú |", "| --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r.get('source','')} | {r.get('target','')} | {r.get('scope','global')} | {r.get('notes','')} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build shared immutable prompt prefix.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    args = parser.parse_args()

    build_shared_prefix(args.project_dir)


if __name__ == "__main__":
    main()
