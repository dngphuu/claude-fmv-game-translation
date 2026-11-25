# CLAUDE.md - FMV Game Localization Pipeline

This repository provides an autonomous AI agent skill specialized in **Full Motion Video (FMV) Game and Interactive Cinema Localization** from **Chinese (ZH), Japanese (JA), Korean (KO), and English (EN)** to **Natural, Cinematic Vietnamese (vi-VN)** with zero "AI slop", strict reading speed (CPS) limits, and dynamic pronoun matrices.

## 🚀 Quick Skill Activation

### In Claude Code:
You can invoke the skill anytime:
```text
Use translate-fmv-vi to localize this FMV game into Vietnamese.
```
Or in Vietnamese:
```text
Sử dụng $translate-fmv-vi để dịch tựa game FMV này sang tiếng Việt chuẩn điện ảnh, khử hoàn toàn AI slop, tuân thủ ma trận xưng hô và kiểm soát tốc độ đọc CPS.
```

### In Google Antigravity:
The skill is located at `.gemini/skills/translate-fmv-vi/SKILL.md` and `skills/translate-fmv-vi/SKILL.md`.

---

## 🛠️ CLI Pipeline Commands

```bash
# 1. Initialize project
python skills/translate-fmv-vi/scripts/init_project.py --project-dir ./my-project --title "My FMV Game" --source-lang zh --target-lang vi-VN

# 2. Build file manifest & Extract subtitles (.srt, .vtt, .ass, .json)
python skills/translate-fmv-vi/scripts/build_manifest.py --project-dir ./my-project
python skills/translate-fmv-vi/scripts/extract_subtitles.py --project-dir ./my-project

# 3. Test roundtrip integrity
python skills/translate-fmv-vi/scripts/export_subtitles.py --project-dir ./my-project --dry-run
python skills/translate-fmv-vi/scripts/set_stage.py roundtrip-proven --project-dir ./my-project --evidence staging/roundtrip/roundtrip-proven.json

# 4. Plan scenarios, jobs & Build shared prefix
python skills/translate-fmv-vi/scripts/plan_scenarios.py --project-dir ./my-project
python skills/translate-fmv-vi/scripts/plan_jobs.py --project-dir ./my-project
python skills/translate-fmv-vi/scripts/build_shared_prefix.py --project-dir ./my-project
python skills/translate-fmv-vi/scripts/build_context_bundle.py --project-dir ./my-project --all-pending

# 5. Validate & Apply review delta
python skills/translate-fmv-vi/scripts/validate_translation.py --project-dir ./my-project --job-id <job_id>
python skills/translate-fmv-vi/scripts/apply_review_delta.py --project-dir ./my-project --job-id <job_id>

# 6. Merge jobs & Export release
python skills/translate-fmv-vi/scripts/merge_jobs.py --project-dir ./my-project
python skills/translate-fmv-vi/scripts/export_subtitles.py --project-dir ./my-project --output-dir ./my-project/build
python skills/translate-fmv-vi/scripts/audit_font_coverage.py --project-dir ./my-project
```

---

## 🧪 Testing
Run the complete regression test suite:
```bash
python -B -X utf8 skills/translate-fmv-vi/scripts/tests/test_fmv_pipeline.py
```
