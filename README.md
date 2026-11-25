# FMV Game Localization Skill (Chuyên Dịch Game FMV sang Tiếng Việt Tự Nhiên)

> **Autonomous AI Agent Skill for Full Motion Video (FMV) Games and Interactive Cinema Localization**
> *From Chinese (ZH), Japanese (JA), Korean (KO), and English (EN) into Cinema-Grade Vietnamese (vi-VN).*
> **Zero AI Slop · Strict CPS Reading Speed Limits · Dynamic Pronoun Matrix · Lossless Subtitle Round-Trip.**

Compatible with both **Claude Code** and **Google Antigravity**.

---

## 🌟 Why FMV Games Need a Dedicated Localization Skill

In standard Visual Novels, readers advance dialogue at their own pace with mouse clicks. In **FMV (Full Motion Video) games** (*Love Is All Around, The Invisible Guardian, Death Come True, Late Shift, Immortality, Her Story*), live actors perform on screen and subtitles vanish when the shot cuts or the actor stops speaking!

Standard machine translation (and generic AI prompts) fails catastrophically on FMV games:
1. **The "Tôi - Bạn" Disease**: Unnaturally defaulting to robotic "Tôi - Bạn" pronouns instead of authentic Vietnamese social dynamics (*anh - em, cậu - tớ, sếp - em, mày - tao*).
2. **Reading Speed Overload (CPS > 20)**: Vietnamese compound words are often longer than Chinese characters or Japanese kanji. Verbose translations flash off-screen before viewers can finish reading.
3. **Stiff "AI Slop"**: Passive voice abuse (*"bị/được"*), literal idioms (*"chết tiệt"*, *"quỷ tha ma bắt"*), and bookish conjunctions (*"bởi vì... cho nên..."*).
4. **Broken Subtitle Sync**: Inability to handle exact millisecond timecodes, ASS styling codes, or QTE timer choices.

`translate-fmv-vi` is engineered from the ground up to solve all four challenges with an industrial-grade, reproducible pipeline.

---

## 🏗️ Architecture & Features

```text
skills/translate-fmv-vi/
├── SKILL.md                          # Master skill instruction for Claude Code & Antigravity
├── agents/                           # Agent personas
│   ├── translator.md                 # Pass 1: Contextual cinematic translator
│   ├── cinematic_editor.md           # Pass 2: Independent voice editor & CPS condenser
│   └── timing_qa.md                  # Pass 3: Technical timing & format QA
├── references/                       # Production standards & manuals
│   ├── vietnamese-natural-voice-guide.md # Anti-AI-slop manifesto & colloquial particles
│   ├── cinematic-timing-and-cps.md   # CPS formulas, reading limits & condensation tactics
│   ├── pronoun-matrix-system.md      # Dynamic timeline-based Vietnamese address system
│   ├── multilingual-source-adaptation.md # Dedicated rules for ZH, JA, KO, EN -> VI
│   ├── fmv-engines-and-subtitle-formats.md # SRT, VTT, ASS, Unity/Unreal JSON/CSV
│   ├── translation-contract.md       # Immutable JSONL output contract
│   ├── workflow-and-state.md         # 12-stage state machine & file contracts
│   └── qa-and-release.md             # 5-layer automated QA & playtest protocols
└── scripts/                          # Automated CLI tooling
    ├── pipeline_common.py            # Timecode math, atomic I/O, token counter, digests
    ├── init_project.py               # Initialize workspace with customized Bible templates
    ├── build_manifest.py             # SHA-256 source file catalog
    ├── extract_subtitles.py          # Universal parser (SRT/VTT/ASS/JSON/CSV -> source.jsonl)
    ├── export_subtitles.py           # Pristine lossless re-exporter
    ├── plan_scenarios.py             # Segment dialogue into scenarios with locked pronoun phases & choice targets
    ├── plan_jobs.py                  # Scenario-isolated job chunking with context budget
    ├── build_shared_prefix.py        # Compile frozen Bible into cacheable prompt prefix
    ├── build_context_bundle.py       # Package scenario brief, active pronoun locks & choice rules
    ├── emit_chunk.py                 # Clean scenario-aware LLM translation packet
    ├── validate_translation.py       # Validator (IDs, tokens, CPS, AI slop/word-by-word, pronoun & choice audit)
    ├── create_review_report.py       # Independent reviewer declaration recorder
    ├── apply_review_delta.py         # Deterministic merge of reviewer improvements
    ├── merge_jobs.py                 # Assemble final approved text & release manifest
    ├── set_job_status.py             # Atomic job status transitions
    ├── audit_font_coverage.py        # Vietnamese diacritics audit (134 accented characters)
    └── tests/test_fmv_pipeline.py    # Comprehensive regression test suite
```

---

## ⚡ Quick Start

### 1. In Claude Code
Invoke the skill directly in any Claude Code conversation:
```text
Use translate-fmv-vi to localize this FMV game into Vietnamese.
```
Or in Vietnamese:
```text
Sử dụng $translate-fmv-vi để dịch tựa game FMV này sang tiếng Việt chuẩn điện ảnh.
```

### 2. In Google Antigravity
The skill is configured and available at:
- `.gemini/skills/translate-fmv-vi/SKILL.md`
- `skills/translate-fmv-vi/SKILL.md`
- Packaged as an Antigravity Plugin via `plugin.json`.

---

## 💻 CLI Step-by-Step Workflow

```bash
# Step 1: Initialize new project
python skills/translate-fmv-vi/scripts/init_project.py --project-dir ./my-game --title "Love In The City" --source-lang zh --target-lang vi-VN

# Step 2: Extract subtitle data
python skills/translate-fmv-vi/scripts/build_manifest.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/extract_subtitles.py --project-dir ./my-game

# Step 3: Verify lossless round-trip
python skills/translate-fmv-vi/scripts/export_subtitles.py --project-dir ./my-game --dry-run
python skills/translate-fmv-vi/scripts/set_stage.py roundtrip-proven --project-dir ./my-game --evidence staging/roundtrip/roundtrip-proven.json

# Step 4: Configure Bible (pronoun matrix, character profiles, glossary) & freeze
python skills/translate-fmv-vi/scripts/set_stage.py bible-frozen --project-dir ./my-game --evidence bible/version.json

# Step 5: Plan scenarios & jobs, then generate context bundles
python skills/translate-fmv-vi/scripts/plan_scenarios.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/plan_jobs.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/build_shared_prefix.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/build_context_bundle.py --project-dir ./my-game --all-pending

# Step 6: Validate & Apply review edits
python skills/translate-fmv-vi/scripts/validate_translation.py --project-dir ./my-game --job-id scene_01
python skills/translate-fmv-vi/scripts/apply_review_delta.py --project-dir ./my-game --job-id scene_01

# Step 7: Merge jobs & export release
python skills/translate-fmv-vi/scripts/merge_jobs.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/export_subtitles.py --project-dir ./my-game --output-dir ./my-game/build
python skills/translate-fmv-vi/scripts/audit_font_coverage.py --project-dir ./my-game
```

---

## 🧪 Testing

Run the automated regression test suite:
```bash
python -B -X utf8 skills/translate-fmv-vi/scripts/tests/test_fmv_pipeline.py
```
