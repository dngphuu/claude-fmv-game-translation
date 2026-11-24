#!/usr/bin/env python3
"""Emit a clean model prompt packet for a translation job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pipeline_common import read_json, read_text


def emit_chunk(project_dir: Path, job_id: str) -> str:
    bundle_file = project_dir / "contexts" / job_id / "current.json"
    if not bundle_file.exists():
        raise FileNotFoundError(f"Missing bundle for job: {job_id}")

    bundle = read_json(bundle_file)
    prefix_file = project_dir / "contexts" / "shared-prefix" / "prefix.md"
    prefix_text = read_text(prefix_file) if prefix_file.exists() else ""

    lines = [
        "=== BẢN DỊCH PHỤ ĐỀ PHIM/GAME FMV: NHIỆM VỤ DỊCH ===",
        f"Mã Job: {job_id}",
        f"Phân cảnh: {bundle.get('scene_id')} | Tuyến truyện: {bundle.get('route')}",
        f"Nhân vật tham gia: {', '.join(bundle.get('speakers', [])) or 'Không rõ'}",
        "",
        "=== QUY TẮC XƯNG HÔ ÁP DỤNG TRONG PHÂN CẢNH NÀY ===",
        json.dumps(bundle.get("active_pronoun_rules", []), indent=2, ensure_ascii=False),
        "",
        "=== MẠCH THOẠI TRƯỚC ĐÓ (NGỮ CẢNH ĐỂ HIỂU ĐÚNG CẢM XÚC) ===",
    ]

    for p in bundle.get("surrounding_context", {}).get("preceding_dialogue", []):
        lines.append(f"[{p.get('speaker', 'Unknown')}]: {p.get('text')}")

    lines.extend([
        "",
        "=== CÁC CÂU THOẠI CẦN DỊCH (BẮT BUỘC TRẢ VỀ DẠNG JSONL) ===",
        "Định dạng mỗi dòng đầu ra: {\"id\": \"...\", \"translation\": \"...\"}",
        "",
    ])

    for item in bundle.get("primary_entries", []):
        dur_sec = item.get("duration_ms", 0) / 1000.0
        choice_tag = " [NÚT BẤM LỰA CHỌN / QTE]" if item.get("is_choice") else ""
        lines.append(
            f"ID: {item['id']} | Người nói: {item.get('speaker', 'N/A')} | Thời lượng: {dur_sec:.1f}s{choice_tag}"
        )
        if item.get("protected_tokens"):
            lines.append(f"  Thẻ bảo vệ (phải giữ nguyên): {item['protected_tokens']}")
        lines.append(f"  Thoại gốc: {item['text']}")
        lines.append("")

    packet = "\n".join(lines)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit prompt packet for a job.")
    parser.add_argument("--project-dir", type=Path, required=True, help="Path to project directory")
    parser.add_argument("--job-id", type=str, required=True, help="Job identifier")
    args = parser.parse_args()

    packet = emit_chunk(args.project_dir, args.job_id)
    print(packet)


if __name__ == "__main__":
    main()
