---
name: translate-fmv-vi
description: "Chuyên dịch và bản địa hóa game FMV (Full Motion Video), phim tương tác và game điện ảnh từ tiếng Nhật, Hàn, Trung, Anh sang tiếng Việt tự nhiên chuẩn điện ảnh, không AI slop, tách theo từng scenario, kiểm soát tốc độ đọc CPS, ma trận xưng hô biến thiên, chuẩn hóa góc nhìn lựa chọn nhân vật chính và bảo toàn phụ đề srt/vtt/ass/json."
---

# Quy Trình Việt Hóa Game FMV (FMV Game Localization Pipeline)

Kỹ năng chuyên biệt dành cho **Game FMV (Full Motion Video)**, phim tương tác thực tế (Interactive Cinema) và game nhập vai đời thực. Hỗ trợ chuyển ngữ từ **Tiếng Trung (ZH), Tiếng Nhật (JA), Tiếng Hàn (KO), Tiếng Anh (EN)** sang **Tiếng Việt (VI)** với chất lượng tương đương phim chiếu rạp, tách ngữ cảnh theo từng **Scenario** riêng biệt để dịch đúng chủ đề và khẩu khí, khóa chặt **ma trận xưng hô** cho từng cặp thoại và từng **lựa chọn của nhân vật chính**, triệt tiêu hoàn toàn văn dịch máy word-by-word ("AI slop") và kiểm soát nghiêm ngặt tốc độ đọc (CPS).

Hoạt động trơn tru trên cả **Claude Code** và **Google Antigravity**.

---

## 1. Các Điểm Vào Dự Án (Entry Points)

- **Dự án Việt hóa mới từ đầu**:
  Khởi tạo dự án, quét mã băm tệp gốc, nghiên cứu diễn viên/bối cảnh, chứng minh quy trình trích xuất và xuất ngược không suy hao (`roundtrip-proven`), thiết lập Kinh thánh dự án (`characters.json` kèm `protagonist_id` & `aliases`, `pronoun_matrix.json`, thuật ngữ), **tách thành từng Scenario riêng (`plan_scenarios.py`) và mô tả chủ đề/tâm lý/khóa phase xưng hô cho từng scenario**, chia job theo scenario (`plan_jobs.py`), tiến hành dịch 2 vòng (Translator -> Cinematic Editor), kiểm thử tự động (ID, thẻ tag, CPS, slop, khóa xưng hô & lựa chọn nhân vật chính, font), đóng gói phụ đề và xuất bản phát hành.
- **Tiếp tục dự án đang dở dang (Resume)**:
  Tự động kiểm tra `run-state.json` và `planning/jobs.jsonl`, tái sử dụng các job đã được duyệt (`approved`), chỉ giao việc các job còn tồn đọng (`pending`), không dịch lại các phân đoạn đã hoàn thành.
- **Kiểm định / Thẩm định chất lượng bản dịch (QA / Audit Only)**:
  Quét các tệp phụ đề hiện có để phát hiện vi phạm tốc độ đọc CPS, lỗi xưng hô theo scenario, lỗi ngôi ở lựa chọn nhân vật chính, lỗi font chữ tiếng Việt, hoặc dấu vết văn dịch máy word-by-word ("AI slop").

---

## 2. Các Ràng Buộc Bắt Buộc Tuân Thủ (Non-Negotiable Constraints)

1. **Chu trình Khứ hồi Không suy hao (Lossless Round-Trip)**:
   Trước khi tiến hành dịch, phải chạy trích xuất và xuất ngược lại các tệp phụ đề gốc của game để chứng minh cấu trúc thời gian (`start_time`, `end_time`), tiền tố người nói và mã định dạng không bị xê dịch.
2. **Tách Từng Scenario Riêng Để Dịch (Scenario-Based Isolation & Enrichment)**:
   - Không gộp nhiều tình huống/cặp nhân vật khác nhau vào cùng một job dịch.
   - Chạy `plan_scenarios.py` để phân đoạn thoại thành từng Scenario riêng, sau đó điền rõ: **bối cảnh (`setting`)**, **chủ đề cuộc nói chuyện (`topic`)**, **cảm xúc (`mood`)**, **đối tượng hướng tới của lựa chọn (`choice_target`)**, và **khóa cứng đúng 1 giai đoạn quan hệ (`active_phases`)** cho từng cặp nhân vật trong scenario đó.
3. **Triệt Hạ Tuyệt Đối Dịch Máy Word-by-Word & "AI Slop"**:
   - Đọc hiểu toàn bộ Scenario và ý định phát ngôn trước khi dịch; tuyệt đối không dịch đối xứng từng chữ (word-by-word).
   - Nghiêm cấm mặc định dịch thành "Tôi - Bạn". Bắt buộc tra cứu khóa xưng hô `Speaker -> Addressee` của scenario hiện tại.
   - Loại bỏ lối nói bị động gượng gạo ("bị", "được"), từ nối hành chính lê thê ("bởi vì... cho nên...", "một cách...", "nghĩ rằng...", "điều đó có nghĩa là...").
   - Lời thoại phải mang khẩu âm đời thực của người Việt, có trợ từ cuối câu tự nhiên (`nhé`, `nhá`, `à`, `hả`, `chứ`, `thôi`, `đấy`, `nè`).
4. **Chuẩn Hóa Ngôi Xưng Hô Cho Lựa Chọn Nhân Vật Chính (`is_choice`)**:
   - Mọi nút bấm lựa chọn dù gắn nhãn `System`, `Choice1` hay không có speaker đều thuộc về **Nhân vật chính (`protagonist_id`)** hướng tới `choice_target` trong phân cảnh đó.
   - Bắt buộc giữ đúng ngôi tự xưng & vai vế gọi đối phương theo phase đang khóa trong scenario, tuyệt đối không trượt sang `"Tôi - Bạn"` hay nhảy sai phase.
5. **Kiểm Soát Tốc Độ Đọc Điện Ảnh (CPS & CPL Constraints)**:
   - CPS mục tiêu: 12 - 16 ký tự/giây; tối đa không vượt quá 18 - 20 ký tự/giây.
   - Tối đa 2 dòng phụ đề trên một cảnh; không vượt quá 38-40 ký tự mỗi dòng. Lựa chọn QTE ngắn gọn (< 20-25 ký tự phần nội dung).
6. **Bảo Tồn Toàn Vẹn Thẻ Kỹ Thuật (`protected_tokens`) & Xuất Chuẩn JSONL**:
   - Mọi thẻ HTML (`<i>`, `<b>`), mã màu ASS (`{\c&H...&}`), biến số game (`%s`, `{playerName}`), và ký hiệu ngắt dòng (`\N`, `\n`) phải giữ nguyên 100%.
   - Giao tiếp giữa các công cụ thông qua tệp JSONL có cấu trúc.

---

## 3. Cẩm Nang Đọc Theo Vai Trò & Tài Liệu Tham Khảo

- **Khẩu âm tiếng Việt tự nhiên & Triệt hạ dịch Word-by-Word / AI Slop**: Đọc [vietnamese-natural-voice-guide.md](references/vietnamese-natural-voice-guide.md).
- **Ràng buộc thời gian, tính toán CPS & Lược dịch điện ảnh**: Đọc [cinematic-timing-and-cps.md](references/cinematic-timing-and-cps.md).
- **Thiết lập và vận hành Ma trận xưng hô & Choice**: Đọc [pronoun-matrix-system.md](references/pronoun-matrix-system.md).
- **Đặc thù chuyển ngữ từ tiếng Trung, Nhật, Hàn, Anh**: Đọc [multilingual-source-adaptation.md](references/multilingual-source-adaptation.md).
- **Định dạng phụ đề (.srt, .vtt, .ass, Unity/Unreal JSON)**: Đọc [fmv-engines-and-subtitle-formats.md](references/fmv-engines-and-subtitle-formats.md).
- **Khế ước dịch thuật chi tiết cho Model**: Đọc [translation-contract.md](references/translation-contract.md).
- **Cỗ máy trạng thái & cấu trúc dự án**: Đọc [workflow-and-state.md](references/workflow-and-state.md).
- **Kiểm định chất lượng QA & Đóng gói phát hành**: Đọc [qa-and-release.md](references/qa-and-release.md).

---

## 4. Bộ Lệnh Công Cụ CLI (CLI Scripts)

| Script | Chức năng |
| :--- | :--- |
| `init_project.py` | Khởi tạo thư mục dự án FMV, sinh file metadata và cấu trúc chuẩn |
| `build_manifest.py` | Quét và tính mã băm SHA-256 toàn bộ file phụ đề nguồn |
| `extract_subtitles.py` | Trích xuất phụ đề (.srt, .vtt, .ass, .json) thành `extracted/source.jsonl`, nhận diện người nói & `is_choice` |
| `export_subtitles.py` | Xuất ngược từ `final.jsonl` hoặc `source.jsonl` ra định dạng file phụ đề gốc |
| `audit_project.py` | Kiểm tra tính hợp lệ của các bằng chứng theo từng giai đoạn |
| `set_stage.py` | Thăng hạng trạng thái an toàn trong `run-state.json` khi có đủ bằng chứng |
| `plan_scenarios.py` | Phân tách `source.jsonl` thành từng Scenario riêng (`planning/scenarios.json`), tự suy luận `choice_target` & khóa `active_phases` |
| `plan_jobs.py` | Chia các Scenario thành từng job dịch tách biệt (không trộn 2 scenario vào 1 job) |
| `build_shared_prefix.py` | Đóng gói Kinh thánh dự án thành prompt cache |
| `build_context_bundle.py` | Đóng gói ngữ cảnh Scenario, khóa xưng hô `Speaker -> Addressee` và chỉ dẫn lựa chọn nhân vật chính |
| `emit_chunk.py` | Xuất packet Scenario tối ưu gửi cho mô hình AI dịch |
| `validate_translation.py` | Bộ kiểm thử tự động: ID, thẻ tag, CPS, AI slop/word-by-word, khóa xưng hô scenario & ngôi lựa chọn nhân vật chính |
| `create_review_report.py` | Ghi nhận báo cáo thẩm định và sửa lỗi của Cinematic Editor |
| `apply_review_delta.py` | Tự động áp dụng các sửa đổi của biên tập viên vào bản dịch chính thức |
| `merge_jobs.py` | Hợp nhất toàn bộ các job đã duyệt thành tệp `translations/final.jsonl` |
| `audit_font_coverage.py` | Quét 100% ký tự tiếng Việt có dấu và đối soát với font chữ của game |

---

## 5. Quy Trình Vận Hành Tiêu Biểu

```bash
# 1. Khởi tạo dự án
python scripts/init_project.py --project-dir ./my-fmv-project --title "Love In The City" --source-lang zh --target-lang vi-VN

# 2. Quét tệp nguồn & Trích xuất phụ đề
python scripts/build_manifest.py --project-dir ./my-fmv-project
python scripts/extract_subtitles.py --project-dir ./my-fmv-project

# 3. Thử nghiệm round-trip bảo toàn dữ liệu
python scripts/export_subtitles.py --project-dir ./my-fmv-project --dry-run
python scripts/set_stage.py roundtrip-proven --project-dir ./my-fmv-project --evidence staging/roundtrip/roundtrip-proven.json

# 4. Đóng băng Kinh thánh (nhân vật, protagonist_id, pronoun_matrix.json, glossary.tsv)
python scripts/set_stage.py bible-frozen --project-dir ./my-fmv-project --evidence bible/version.json

# 5. Phân tách Scenario, bổ sung topic/setting/active_phases vào planning/scenarios.json rồi chia job & tạo bundle
python scripts/plan_scenarios.py --project-dir ./my-fmv-project
# (Agent đọc mẫu thoại và điền title, setting, topic, mood, active_phases, choice_target vào planning/scenarios.json)
python scripts/plan_jobs.py --project-dir ./my-fmv-project
python scripts/build_shared_prefix.py --project-dir ./my-fmv-project
python scripts/build_context_bundle.py --project-dir ./my-fmv-project --all-pending

# 6. Dịch theo Scenario, Biên tập, Kiểm định tự động
python scripts/emit_chunk.py --project-dir ./my-fmv-project --job-id <job_id>
python scripts/validate_translation.py --project-dir ./my-fmv-project --job-id <job_id>
python scripts/apply_review_delta.py --project-dir ./my-fmv-project --job-id <job_id>

# 7. Hợp nhất & Đóng gói phát hành
python scripts/merge_jobs.py --project-dir ./my-fmv-project
python scripts/export_subtitles.py --project-dir ./my-fmv-project --output-dir release/subtitles
python scripts/audit_font_coverage.py --project-dir ./my-fmv-project
python scripts/set_stage.py released --project-dir ./my-fmv-project --evidence release/release-manifest.json
```
