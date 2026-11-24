#!/usr/bin/env python3
"""End-to-end regression test suite for FMV Game Translation Pipeline."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_common import (
    calculate_cps,
    digest_text,
    ms_to_ass_timecode,
    ms_to_srt_timecode,
    ms_to_vtt_timecode,
    read_json,
    read_jsonl,
    timecode_to_ms,
    write_jsonl,
)
from init_project import init_project
from build_manifest import build_manifest
from extract_subtitles import extract_all
from export_subtitles import export_subtitles
from plan_jobs import plan_jobs
from build_shared_prefix import build_shared_prefix
from build_context_bundle import build_context_bundle
from emit_chunk import emit_chunk
from validate_translation import validate_translation
from create_review_report import create_review_report
from apply_review_delta import apply_review_delta
from merge_jobs import merge_jobs
from set_stage import set_stage
from audit_font_coverage import audit_font_coverage


SAMPLE_SRT = """1
00:00:05,200 --> 00:00:08,000
Triệu tổng: 这是今天需要审核的合同。

2
00:00:08,500 --> 00:00:10,200
Triệu tổng: 抓紧时间看一遍。

3
00:00:11,000 --> 00:00:13,500
Cố Hải: 没问题，包在我身上！
"""

SAMPLE_VTT = """WEBVTT

00:02.000 --> 00:05.500
<v XiaoYu>Cố Hải ca ca, đợi muội với!

00:06.000 --> 00:08.000
<v Gu Hai>Nhanh lên nào, muộn giờ chiếu phim rồi đấy!
"""

SAMPLE_JSON = json.dumps([
    {
        "clip_id": "clip_01",
        "timestamp_start_ms": 1000,
        "timestamp_end_ms": 3500,
        "speaker": "Triệu Mẫn",
        "dialogue": "这是今天需要审核的合同，抓紧时间看一遍。",
        "is_choice": False
    },
    {
        "clip_id": "clip_02",
        "timestamp_start_ms": 4000,
        "timestamp_end_ms": 6500,
        "speaker": "Cố Hải",
        "dialogue": "Tôi đồng ý ký hợp đồng này.",
        "is_choice": True
    }
])


class FMVPipelineTests(unittest.TestCase):

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp(prefix="fmv_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_timecode_and_cps_calculations(self) -> None:
        """Verify precision of timecodes and CPS reading speeds."""
        # SRT parsing
        ms = timecode_to_ms("00:01:23,450")
        self.assertEqual(ms, 83450)
        self.assertEqual(ms_to_srt_timecode(ms), "00:01:23,450")

        # VTT parsing
        ms_vtt = timecode_to_ms("00:01:23.450")
        self.assertEqual(ms_vtt, 83450)
        self.assertEqual(ms_to_vtt_timecode(ms_vtt), "00:01:23.450")

        # ASS centiseconds
        self.assertEqual(ms_to_ass_timecode(83450), "0:01:23.45")

        # CPS calculation
        # 30 chars in 2000 ms = 15.0 CPS
        cps = calculate_cps("Đây là một câu phụ đề mẫu.", 2000)
        self.assertEqual(cps, 13.0)

    def test_full_pipeline_roundtrip_and_localization(self) -> None:
        """Run an entire end-to-end simulation from init to release."""
        proj = self.test_dir / "project"

        # 1. Initialize project
        init_project(
            project_dir=proj,
            project_name="fmv-love-city",
            display_title="Love In The City FMV",
            source_lang="zh",
            target_lang="vi-VN",
            engine="unity-fmv",
            subtitle_format="srt",
            cps_target=15.0,
            cps_max=18.0,
        )
        self.assertTrue((proj / "project.json").exists())
        self.assertTrue((proj / "run-state.json").exists())

        # 2. Populate source files
        source_dir = proj / "source"
        (source_dir / "scene_01.srt").write_text(SAMPLE_SRT, encoding="utf-8")
        (source_dir / "scene_02.vtt").write_text(SAMPLE_VTT, encoding="utf-8")
        (source_dir / "dialogues.json").write_text(SAMPLE_JSON, encoding="utf-8")

        # 3. Build manifest
        manifest = build_manifest(proj)
        self.assertEqual(len(manifest), 3)

        # 4. Extract subtitles
        records = extract_all(proj)
        self.assertEqual(len(records), 7)  # 3 from SRT + 2 from VTT + 2 from JSON
        self.assertTrue((proj / "extracted" / "source.jsonl").exists())

        # 5. Roundtrip verification test
        export_subtitles(proj, dry_run=True)
        self.assertTrue((proj / "staging" / "roundtrip" / "roundtrip-proven.json").exists())

        # Advance stage to roundtrip-proven
        set_stage(proj, "roundtrip-proven", evidence="staging/roundtrip/roundtrip-proven.json")

        # 6. Setup Bible & Freeze
        # Customize glossary and pronoun matrix
        glossary_tsv = proj / "bible" / "glossary.tsv"
        glossary_tsv.write_text("source\ttarget\tscope\tcategory\tnotes\n合同\thợp đồng\tglobal\tbusiness\tHợp đồng thương mại\n", encoding="utf-8")
        set_stage(proj, "bible-frozen", evidence="bible/version.json")

        # 7. Plan jobs
        jobs = plan_jobs(proj, max_lines_per_job=10)
        self.assertTrue(len(jobs) >= 2)
        set_stage(proj, "plan-approved", evidence="planning/jobs.jsonl")

        # 8. Build shared prefix & context bundles
        build_shared_prefix(proj)
        self.assertTrue((proj / "contexts" / "shared-prefix" / "prefix.md").exists())
        build_context_bundle(proj)

        # Verify emit_chunk
        first_job_id = jobs[0]["job_id"]
        packet = emit_chunk(proj, first_job_id)
        self.assertIn("Mã Job:", packet)

        # 9. Simulate Translation Drafts
        # Create drafts for all jobs with high quality Vietnamese dialogue
        drafts_dir = proj / "translations" / "drafts"
        draft_entries = []
        for r in records:
            # Provide concise natural translation matching duration and glossary
            if "合同" in r["text"]:
                trans = "Hợp đồng cần duyệt đây, xem gấp nhé."  # 36 chars / 2.5s = 14.4 CPS
            elif "包在我身上" in r["text"]:
                trans = "Cứ yên tâm, để đấy anh lo!"
            elif "muộn giờ" in r["text"]:
                trans = "Nhanh lên nào, muộn giờ chiếu phim rồi đấy!"
            elif "ký hợp đồng" in r["text"]:
                trans = "Tôi đồng ý ký hợp đồng này."
            else:
                trans = f"Thoại ngắn cho {r['id']}."
            draft_entries.append({"id": r["id"], "translation": trans})

        # Split into job draft files
        for j in jobs:
            j_recs = [d for d in draft_entries if d["id"] in j["entry_ids"]]
            write_jsonl(drafts_dir / f"{j['job_id']}.draft.jsonl", j_recs)

        set_stage(proj, "translating", evidence="translations/drafts")

        # 10. Test Validation (Clean pass)
        val_report = validate_translation(proj, job_id=first_job_id)
        self.assertEqual(val_report["error_count"], 0)

        # 11. Test Cinematic Review & Delta Apply
        rev_report = create_review_report(
            proj,
            job_id=first_job_id,
            reviewer_name="cinematic-editor",
            revisions=[
                {
                    "id": draft_entries[0]["id"],
                    "revised_translation": "Hợp đồng cần duyệt hôm nay đây, em xem gấp nhé.",
                    "reason": "Tăng độ tự nhiên, giảm CPS"
                }
            ],
            review_summary="Duyệt sau khi gọt giũa lời thoại"
        )
        self.assertTrue(rev_report.exists())
        approved_file = apply_review_delta(proj, first_job_id)
        self.assertTrue(approved_file.exists())

        # Approve remaining jobs
        for j in jobs[1:]:
            apply_review_delta(proj, j["job_id"])

        set_stage(proj, "reviewed", evidence="translations/approved")

        # 12. Merge jobs into final.jsonl
        final_file = merge_jobs(proj)
        self.assertTrue(final_file.exists())
        self.assertEqual(len(read_jsonl(final_file)), len(records))

        # 13. Export Subtitles to build
        export_subtitles(proj, output_dir=proj / "build")
        self.assertTrue((proj / "build" / "scene_01.srt").exists())
        self.assertTrue((proj / "build" / "scene_02.vtt").exists())
        self.assertTrue((proj / "build" / "dialogues.json").exists())

        set_stage(proj, "repacked", evidence="build")

        # 14. Vietnamese Font Coverage Check
        font_cov = audit_font_coverage(proj)
        self.assertTrue(font_cov["vietnamese_accented_used_count"] > 10)
        self.assertEqual(font_cov["status"], "pass")

        # 15. Playtest evidence and Release
        qa_evidence = proj / "qa" / "playtest-evidence.json"
        qa_evidence.write_text(json.dumps({"playtest": "passed", "visual_inspection": "ok"}), encoding="utf-8")
        set_stage(proj, "playtested", evidence="qa/playtest-evidence.json")
        set_stage(proj, "released", evidence="release/release-manifest.json")

        # Final state check
        final_state = read_json(proj / "run-state.json")
        self.assertEqual(final_state["current_stage"], "released")

    def test_anti_slop_and_cps_detection(self) -> None:
        """Verify that AI slop and CPS overloads are properly flagged."""
        proj = self.test_dir / "project_slop"
        init_project(
            project_dir=proj,
            project_name="slop-test",
            display_title="Slop Test",
            source_lang="en",
            target_lang="vi-VN",
            engine="generic",
            subtitle_format="srt",
            cps_max=18.0,
        )

        source_dir = proj / "source"
        (source_dir / "test.srt").write_text(
            "1\n00:00:01,000 --> 00:00:02,000\nHello world!\n",
            encoding="utf-8"
        )
        extract_all(proj)

        # Create a draft with intentional AI slop and huge CPS
        draft_file = proj / "translations" / "drafts" / "test.draft.jsonl"
        # 1 second duration, text with "chết tiệt" and 80 chars -> CPS = 80!
        write_jsonl(draft_file, [
            {
                "id": "test.srt:000001",
                "translation": "Chết tiệt, tôi và bạn chạy một cách nhanh chóng bởi vì trời mưa cho nên bị ướt hết!"
            }
        ])

        report = validate_translation(proj, draft_file=draft_file)
        # Should flag cps_critical_overload
        err_codes = [e["code"] for e in report["errors"]]
        self.assertIn("cps_critical_overload", err_codes)

        # Should flag slop warnings
        warn_codes = [w["code"] for w in report["warnings"]]
        self.assertTrue(any("slop" in c for c in warn_codes))


if __name__ == "__main__":
    unittest.main()
