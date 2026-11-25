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
    contains_pronoun_token,
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
from plan_scenarios import plan_scenarios
from plan_jobs import plan_jobs
from build_shared_prefix import build_shared_prefix
from build_context_bundle import build_context_bundle
from emit_chunk import emit_chunk
from validate_translation import validate_translation
from create_review_report import create_review_report
from apply_review_delta import apply_review_delta
from merge_jobs import merge_jobs
from set_stage import set_stage
from audit_project import audit_stage_evidence
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

MULTI_SCENARIO_SRT = """1
00:00:03,100 --> 00:00:05,800
Triệu Mẫn: 顾海，你发什么呆呢？这可是集团今年最重要的并购案。

2
00:00:06,200 --> 00:00:08,900
Cố Hải: 报告赵总，我这不是在看案子，是在看你……今天的耳环挺别致的。

3
00:00:09,300 --> 00:00:11,500
Triệu Mẫn: 油嘴滑舌。要是搞砸了，看我怎么收拾你！

4
00:00:12,000 --> 00:00:14,200
[QTE_CHOICE_1] 认真承诺保证完成任务

5
00:00:35,000 --> 00:00:37,500
Tiểu Vũ: 顾海哥，我把材料整理好啦！

6
00:00:38,000 --> 00:00:40,500
Cố Hải: 辛苦你了，先去休息一会儿吧。

7
00:00:41,000 --> 00:00:43,200
[QTE_CHOICE_2] 摸摸她的头表示鼓励

8
00:01:10,000 --> 00:01:13,000
Triệu Mẫn: 今晚的夜风真舒服，只有我们两个人。

9
00:01:13,500 --> 00:01:16,500
Cố Hải: 是啊，以后每个周末我都陪你来这里。

10
00:01:17,000 --> 00:01:19,500
[QTE_CHOICE_3] 牵起她的手
"""


class FMVPipelineTests(unittest.TestCase):

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp(prefix="fmv_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_timecode_and_cps_calculations(self) -> None:
        """Verify precision of timecodes and CPS reading speeds."""
        ms = timecode_to_ms("00:01:23,450")
        self.assertEqual(ms, 83450)
        self.assertEqual(ms_to_srt_timecode(ms), "00:01:23,450")

        ms_vtt = timecode_to_ms("00:01:23.450")
        self.assertEqual(ms_vtt, 83450)
        self.assertEqual(ms_to_vtt_timecode(ms_vtt), "00:01:23.450")

        self.assertEqual(ms_to_ass_timecode(83450), "0:01:23.45")

        cps = calculate_cps("Đây là một câu phụ đề mẫu.", 2000)
        self.assertEqual(cps, 13.0)

    def test_srt_speaker_and_choice_extraction_and_roundtrip(self) -> None:
        """Verify SRT speaker extraction with spaces, choice detection, and lossless roundtrip."""
        proj = self.test_dir / "project_srt"
        init_project(proj, "srt-test", "SRT Test", "zh", "vi-VN", "unity-fmv", "srt")
        (proj / "source" / "multi.srt").write_text(MULTI_SCENARIO_SRT, encoding="utf-8")
        (proj / "source" / "hotel.vtt").write_text(
            "WEBVTT\n\n00:01.000 --> 00:03.000\n<v Choice1>[QTE] 警察に通報する\n",
            encoding="utf-8",
        )

        records = extract_all(proj)
        srt_recs = [r for r in records if r["file"] == "multi.srt"]
        self.assertEqual(srt_recs[0]["speaker"], "Triệu Mẫn")
        self.assertEqual(srt_recs[1]["speaker"], "Cố Hải")
        self.assertTrue(srt_recs[3]["is_choice"])
        self.assertTrue(srt_recs[6]["is_choice"])
        self.assertTrue(srt_recs[9]["is_choice"])

        vtt_recs = [r for r in records if r["file"] == "hotel.vtt"]
        self.assertTrue(vtt_recs[0]["is_choice"])

        export_subtitles(proj, dry_run=True)
        rt_srt = (proj / "staging" / "roundtrip" / "multi.srt").read_text(encoding="utf-8").strip()
        self.assertEqual(rt_srt, MULTI_SCENARIO_SRT.strip())

    def test_full_pipeline_roundtrip_and_localization(self) -> None:
        """Run an entire end-to-end simulation from init to release."""
        proj = self.test_dir / "project"

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

        source_dir = proj / "source"
        (source_dir / "scene_01.srt").write_text(SAMPLE_SRT, encoding="utf-8")
        (source_dir / "scene_02.vtt").write_text(SAMPLE_VTT, encoding="utf-8")
        (source_dir / "dialogues.json").write_text(SAMPLE_JSON, encoding="utf-8")

        manifest = build_manifest(proj)
        self.assertEqual(len(manifest), 3)

        records = extract_all(proj)
        self.assertEqual(len(records), 7)
        self.assertTrue((proj / "extracted" / "source.jsonl").exists())

        export_subtitles(proj, dry_run=True)
        self.assertTrue((proj / "staging" / "roundtrip" / "roundtrip-proven.json").exists())
        self.assertEqual(
            (proj / "staging" / "roundtrip" / "scene_01.srt").read_text(encoding="utf-8").strip(),
            SAMPLE_SRT.strip(),
        )

        set_stage(proj, "roundtrip-proven", evidence="staging/roundtrip/roundtrip-proven.json")

        glossary_tsv = proj / "bible" / "glossary.tsv"
        glossary_tsv.write_text(
            "source\ttarget\tscope\tcategory\tnotes\n合同\thợp đồng\tglobal\tbusiness\tHợp đồng thương mại\n",
            encoding="utf-8",
        )
        set_stage(proj, "bible-frozen", evidence="bible/version.json")

        jobs = plan_jobs(proj, max_lines_per_job=10)
        self.assertTrue(len(jobs) >= 2)
        self.assertTrue((proj / "planning" / "scenarios.json").exists())
        set_stage(proj, "plan-approved", evidence="planning/jobs.jsonl")

        build_shared_prefix(proj)
        self.assertTrue((proj / "contexts" / "shared-prefix" / "prefix.md").exists())
        build_context_bundle(proj)

        first_job_id = jobs[0]["job_id"]
        packet = emit_chunk(proj, first_job_id)
        self.assertIn("Mã Job:", packet)
        self.assertIn("KỊCH BẢN PHÂN CẢNH HIỆN TẠI", packet)

        drafts_dir = proj / "translations" / "drafts"
        draft_entries = []
        for r in records:
            if "合同" in r["text"]:
                trans = "Hợp đồng cần duyệt đây, xem gấp nhé."
            elif "包在我身上" in r["text"]:
                trans = "Cứ yên tâm, để đấy em lo!"
            elif "muộn giờ" in r["text"]:
                trans = "Nhanh lên nào, muộn giờ chiếu phim rồi đấy!"
            elif "ký hợp đồng" in r["text"]:
                trans = "Em đồng ý ký hợp đồng này."
            else:
                trans = f"Thoại ngắn cho {r['id']}."
            draft_entries.append({"id": r["id"], "translation": trans})

        for j in jobs:
            j_recs = [d for d in draft_entries if d["id"] in j["entry_ids"]]
            write_jsonl(drafts_dir / f"{j['job_id']}.draft.jsonl", j_recs)

        set_stage(proj, "translating", evidence="translations/drafts")

        val_report = validate_translation(proj, job_id=first_job_id)
        self.assertEqual(val_report["error_count"], 0)

        rev_report = create_review_report(
            proj,
            job_id=first_job_id,
            reviewer_name="cinematic-editor",
            revisions=[
                {
                    "id": draft_entries[0]["id"],
                    "revised_translation": "Hợp đồng cần duyệt hôm nay đây, cậu xem gấp nhé.",
                    "reason": "Tăng độ tự nhiên, giảm CPS và đúng vai vế sếp - cậu"
                }
            ],
            review_summary="Duyệt sau khi gọt giũa lời thoại"
        )
        self.assertTrue(rev_report.exists())
        approved_file = apply_review_delta(proj, first_job_id)
        self.assertTrue(approved_file.exists())

        for j in jobs[1:]:
            apply_review_delta(proj, j["job_id"])

        set_stage(proj, "reviewed", evidence="translations/approved")

        # Validate stage audit compatibility
        validate_translation(proj)
        ok_val, _ = audit_stage_evidence(proj, "validated")
        self.assertTrue(ok_val)
        set_stage(proj, "validated", evidence="qa/validation-report.json")

        final_file = merge_jobs(proj)
        self.assertTrue(final_file.exists())
        self.assertEqual(len(read_jsonl(final_file)), len(records))

        export_subtitles(proj, output_dir=proj / "build")
        self.assertTrue((proj / "build" / "scene_01.srt").exists())
        self.assertTrue((proj / "build" / "scene_02.vtt").exists())
        self.assertTrue((proj / "build" / "dialogues.json").exists())

        set_stage(proj, "repacked", evidence="build")

        font_cov = audit_font_coverage(proj)
        self.assertTrue(font_cov["vietnamese_accented_used_count"] > 10)
        self.assertEqual(font_cov["status"], "pass")

        qa_evidence = proj / "qa" / "playtest-evidence.json"
        qa_evidence.write_text(json.dumps({"playtest": "passed", "visual_inspection": "ok"}), encoding="utf-8")
        set_stage(proj, "playtested", evidence="qa/playtest-evidence.json")
        set_stage(proj, "released", evidence="release/release-manifest.json")

        final_state = read_json(proj / "run-state.json")
        self.assertEqual(final_state["current_stage"], "released")

    def test_multi_scenario_splitting_and_phase_locking(self) -> None:
        """Verify scenario segmentation isolates phases, topics, and choice targets per job."""
        proj = self.test_dir / "project_scenarios"
        init_project(proj, "scn-test", "Scenario Test", "zh", "vi-VN", "unity-fmv", "srt")
        (proj / "source" / "chapter_01.srt").write_text(MULTI_SCENARIO_SRT, encoding="utf-8")
        extract_all(proj)

        scn_data = plan_scenarios(proj)
        scenarios = scn_data["scenarios"]
        self.assertEqual(len(scenarios), 3)

        # Scenario 1: Cố Hải & Triệu Mẫn office, Choice target = Triệu Mẫn
        self.assertEqual(scenarios[0]["participants"], ["char_female_lead_1", "char_male_lead"])
        self.assertEqual(scenarios[0]["choice_target"], "char_female_lead_1")
        scenarios[0]["setting"] = "Văn phòng Tổng giám đốc Triệu Mẫn"
        scenarios[0]["topic"] = "Giao dự án sáp nhập và màn trêu sếp của nam chính"
        scenarios[0]["mood"] = "Công sở xen chút thả thính tinh nghịch"
        scenarios[0]["active_phases"] = {"char_male_lead__char_female_lead_1": "phase_1_office_interview"}

        # Scenario 2: Cố Hải & Tiểu Vũ
        self.assertEqual(scenarios[1]["participants"], ["char_female_lead_2", "char_male_lead"])
        self.assertEqual(scenarios[1]["choice_target"], "char_female_lead_2")
        scenarios[1]["topic"] = "Tiểu Vũ bàn giao tài liệu cho đàn anh"

        # Scenario 3: Cố Hải & Triệu Mẫn romantic date
        self.assertEqual(scenarios[2]["participants"], ["char_female_lead_1", "char_male_lead"])
        self.assertEqual(scenarios[2]["choice_target"], "char_female_lead_1")
        scenarios[2]["setting"] = "Ban công lộng gió buổi tối"
        scenarios[2]["topic"] = "Hai người tâm sự tình cảm riêng tư"
        scenarios[2]["active_phases"] = {"char_male_lead__char_female_lead_1": "phase_2_dating_romance"}

        (proj / "planning" / "scenarios.json").write_text(
            json.dumps(scn_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        jobs = plan_jobs(proj, max_lines_per_job=50)
        self.assertEqual(len(jobs), 3)
        build_shared_prefix(proj)
        build_context_bundle(proj)

        # Job 0 must ONLY carry phase_1_office_interview and NOT phase_2 or Tiểu Vũ
        b0 = read_json(proj / "contexts" / jobs[0]["job_id"] / "current.json")
        self.assertEqual(len(b0["active_pronoun_rules"]), 1)
        self.assertEqual(b0["active_pronoun_rules"][0]["phase"], "phase_1_office_interview")
        self.assertEqual(b0["choice_target"]["id"], "char_female_lead_1")
        self.assertEqual(b0["primary_entries"][3]["speaker_id"], "char_male_lead")
        self.assertEqual(b0["primary_entries"][3]["addressee_id"], "char_female_lead_1")

        p0 = emit_chunk(proj, jobs[0]["job_id"])
        self.assertIn("Giao dự án sáp nhập", p0)
        self.assertIn("phase_1_office_interview", p0)
        self.assertNotIn("phase_2_dating_romance", p0)
        self.assertIn("Lựa chọn của Cố Hải", p0)

        # Job 2 must ONLY carry phase_2_dating_romance
        b2 = read_json(proj / "contexts" / jobs[2]["job_id"] / "current.json")
        self.assertEqual(len(b2["active_pronoun_rules"]), 1)
        self.assertEqual(b2["active_pronoun_rules"][0]["phase"], "phase_2_dating_romance")

    def test_pronoun_choice_and_word_by_word_validation(self) -> None:
        """Verify detection of choice pronoun mistakes, phase leaks, drift, and word-by-word slop."""
        # Compound noun 'bạn thân' must NOT false-positive as 2nd-person pronoun 'bạn'
        self.assertFalse(contains_pronoun_token("Cô ấy là bạn thân của tôi.", "bạn"))
        self.assertTrue(contains_pronoun_token("Tôi sẽ giúp bạn làm việc này.", "bạn"))

        proj = self.test_dir / "project_pronoun_qa"
        init_project(proj, "qa-test", "QA Test", "zh", "vi-VN", "unity-fmv", "srt")
        (proj / "source" / "chapter_01.srt").write_text(MULTI_SCENARIO_SRT, encoding="utf-8")
        extract_all(proj)

        scn_data = plan_scenarios(proj)
        scn_data["scenarios"][0]["active_phases"] = {"char_male_lead__char_female_lead_1": "phase_1_office_interview"}
        scn_data["scenarios"][2]["active_phases"] = {"char_male_lead__char_female_lead_1": "phase_2_dating_romance"}
        (proj / "planning" / "scenarios.json").write_text(
            json.dumps(scn_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        jobs = plan_jobs(proj, max_lines_per_job=50)
        build_shared_prefix(proj)
        build_context_bundle(proj)

        # Job 0 (office phase_1): test valid 'Em hiểu rồi, sếp Triệu' vs bad choice & word-by-word
        j0 = jobs[0]["job_id"]
        write_jsonl(proj / "translations" / "drafts" / f"{j0}.draft.jsonl", [
            {"id": "chapter_01.srt:000001", "translation": "Cố Hải, làm gì mà thẫn thờ thế?"},
            {"id": "chapter_01.srt:000002", "translation": "Em hiểu rồi, sếp Triệu đừng lo nhé."},
            {"id": "chapter_01.srt:000003", "translation": "Khéo miệng đấy, làm cho tử tế!"},
            {"id": "chapter_01.srt:000004", "translation": "[LỰA CHỌN] Anh hứa hoàn thành nhiệm vụ cho em"},
        ])
        rep0 = validate_translation(proj, job_id=j0)
        codes0 = [w["code"] for w in rep0["warnings"]]
        # Line 4 uses 'Anh' & 'em' in phase_1 choice -> must catch choice_pronoun_mismatch
        self.assertIn("choice_pronoun_mismatch", codes0)
        # Line 2 ('Em hiểu rồi, sếp Triệu') must NOT trigger false forbidden_address on 'em'
        line2_warns = [w for w in rep0["warnings"] if w.get("id") == "chapter_01.srt:000002"]
        self.assertEqual(line2_warns, [])

        # Job 2 (romance phase_2): test 'Tôi - Bạn' in choice, vague 'cô ấy', word-by-word calques, and drift
        j2 = jobs[2]["job_id"]
        write_jsonl(proj / "translations" / "drafts" / f"{j2}.draft.jsonl", [
            {"id": "chapter_01.srt:000008", "translation": "Tôi nghĩ rằng gió đêm nay rất thoải mái cho bạn."},
            {"id": "chapter_01.srt:000009", "translation": "Điều đó có nghĩa là anh sẽ đi cùng em mỗi tuần."},
            {"id": "chapter_01.srt:000010", "translation": "[LỰA CHỌN] Nắm tay cô ấy và tôi hứa bên bạn"},
        ])
        rep2 = validate_translation(proj, job_id=j2)
        codes2 = [w["code"] for w in rep2["warnings"]]
        self.assertIn("choice_pronoun_slop", codes2)
        self.assertIn("choice_pronoun_mismatch", codes2)
        self.assertIn("choice_pronoun_vague_target", codes2)
        self.assertIn("slop_word_by_word_that_clause", codes2)
        self.assertIn("slop_word_by_word_means", codes2)

        # Clean pass in strict mode for job 2 when written naturally
        write_jsonl(proj / "translations" / "drafts" / f"{j2}.draft.jsonl", [
            {"id": "chapter_01.srt:000008", "translation": "Gió đêm nay mát quá, chỉ có hai đứa mình thôi."},
            {"id": "chapter_01.srt:000009", "translation": "Ừ, cuối tuần nào anh cũng đưa em ra đây."},
            {"id": "chapter_01.srt:000010", "translation": "[LỰA CHỌN] Nắm lấy tay em"},
        ])
        rep2_clean = validate_translation(proj, job_id=j2, strict_pronouns=True)
        self.assertEqual(rep2_clean["error_count"], 0)
        self.assertEqual(rep2_clean["pronoun_issue_count"], 0)

        # Intra-scenario drift detection when speaker switches unprompted (e.g. Job 1 without forbidden_self)
        j1 = jobs[1]["job_id"]
        write_jsonl(proj / "translations" / "drafts" / f"{j1}.draft.jsonl", [
            {"id": "chapter_01.srt:000005", "translation": "Anh Cố Hải ơi, em xếp xong hết rồi nè!"},
            {"id": "chapter_01.srt:000006", "translation": "Cảm ơn em nhé, tớ đi pha cà phê đây."},
            {"id": "chapter_01.srt:000007", "translation": "[LỰA CHỌN] Xoa đầu Tiểu Vũ"},
        ])
        rep1_drift = validate_translation(proj, job_id=j1)
        codes1 = [w["code"] for w in rep1_drift["warnings"]]
        # Line 6 ('tớ') conflicts with locked 'anh'
        self.assertIn("pronoun_phase_self_mismatch", codes1)

        # Drift test on unruled scenario speakers (Makoto -> Karaki switching 'anh' and 'tớ')
        proj_drift = self.test_dir / "project_drift"
        init_project(proj_drift, "drift-test", "Drift Test", "ja", "vi-VN", "unity-fmv", "vtt")
        (proj_drift / "source" / "scene.vtt").write_text(
            "WEBVTT\n\n00:01.000 --> 00:04.000\n<v Makoto>おい！\n\n00:04.500 --> 00:07.500\n<v Karaki>なんだ？\n\n00:08.000 --> 00:11.000\n<v Makoto>落ち着け！\n",
            encoding="utf-8",
        )
        extract_all(proj_drift)
        djobs = plan_jobs(proj_drift)
        build_shared_prefix(proj_drift)
        build_context_bundle(proj_drift)
        dj = djobs[0]["job_id"]
        write_jsonl(proj_drift / "translations" / "drafts" / f"{dj}.draft.jsonl", [
            {"id": "scene.vtt:000001", "translation": "Này, anh bảo cậu bình tĩnh lại đi!"},
            {"id": "scene.vtt:000002", "translation": "Chuyện gì thế?"},
            {"id": "scene.vtt:000003", "translation": "Tớ nói thật đấy, đừng hoảng!"},
        ])
        rep_drift = validate_translation(proj_drift, job_id=dj)
        self.assertIn("pronoun_drift_in_scenario", [w["code"] for w in rep_drift["warnings"]])

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

        draft_file = proj / "translations" / "drafts" / "test.draft.jsonl"
        write_jsonl(draft_file, [
            {
                "id": "test.srt:000001",
                "translation": "Chết tiệt, tôi và bạn chạy một cách nhanh chóng bởi vì trời mưa cho nên bị ướt hết!"
            }
        ])

        report = validate_translation(proj, draft_file=draft_file)
        err_codes = [e["code"] for e in report["errors"]]
        self.assertIn("cps_critical_overload", err_codes)

        warn_codes = [w["code"] for w in report["warnings"]]
        self.assertTrue(any("slop" in c for c in warn_codes))


if __name__ == "__main__":
    unittest.main()
