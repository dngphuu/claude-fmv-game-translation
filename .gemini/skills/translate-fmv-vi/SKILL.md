---
name: translate-fmv-vi
description: "Chuyên dịch và bản địa hóa game FMV (Full Motion Video), phim tương tác và game điện ảnh từ tiếng Nhật, Hàn, Trung, Anh sang tiếng Việt tự nhiên chuẩn điện ảnh, không AI slop, kiểm soát tốc độ đọc CPS, ma trận xưng hô biến thiên và bảo toàn phụ đề srt/vtt/ass/json."
---

# Quy Trình Việt Hóa Game FMV (FMV Game Localization Pipeline)

Kỹ năng chuyên biệt dành cho **Game FMV (Full Motion Video)**, phim tương tác thực tế (Interactive Cinema) và game nhập vai đời thực. Hỗ trợ chuyển ngữ từ **Tiếng Trung (ZH), Tiếng Nhật (JA), Tiếng Hàn (KO), Tiếng Anh (EN)** sang **Tiếng Việt (VI)** với chất lượng tương đương phim chiếu rạp, hoàn toàn triệt tiêu văn phong dịch máy ("AI slop"), kiểm soát nghiêm ngặt thời lượng đọc (CPS) và ma trận xưng hô biến thiên theo tuyến truyện.

Hoạt động trơn tru trên cả **Claude Code** và **Google Antigravity**.

---

## 1. Các Điểm Vào Dự Án (Entry Points)

- **Dự án Việt hóa mới từ đầu**:
  Khởi tạo dự án, quét mã băm tệp gốc, nghiên cứu diễn viên/bối cảnh, chứng minh quy trình trích xuất và xuất ngược không suy hao (`roundtrip-proven`), thiết lập Kinh thánh dự án (Ma trận xưng hô `pronoun_matrix.json`, hồ sơ nhân vật, thuật ngữ), chia job theo phân cảnh, tiến hành dịch 2 vòng (Translator -> Cinematic Editor), kiểm thử tự động (CPS, slop, font), đóng gói phụ đề và xuất bản phát hành.
- **Tiếp tục dự án đang dở dang (Resume)**:
  Tự động kiểm tra `run-state.json` và `planning/jobs.jsonl`, tái sử dụng các job đã được duyệt (`approved`), chỉ giao việc các job còn tồn đọng (`pending`), không dịch lại các phân đoạn đã hoàn thành.
- **Kiểm định / Thẩm định chất lượng bản dịch (QA / Audit Only)**:
  Quét các tệp phụ đề hiện có để phát hiện vi phạm tốc độ đọc CPS, câu thoại quá dài trên màn hình, lỗi font chữ tiếng Việt, hoặc dấu vết văn dịch máy ("AI slop").

---

## 2. Các Ràng Buộc Bắt Buộc Tuân Thủ (Non-Negotiable Constraints)

1. **Chu trình Khứ hồi Không suy hao (Lossless Round-Trip)**:
   Trước khi tiến hành dịch, phải chạy trích xuất và xuất ngược lại các tệp phụ đề gốc của game để chứng minh cấu trúc thời gian (`start_time`, `end_time`) và mã định dạng không bị xê dịch dù chỉ 1 mili-giây.
2. **Triệt Hạ Tuyệt Đối "AI Slop"**:
   - Nghiêm cấm mặc định dịch thành "Tôi - Bạn". Bắt buộc tra cứu Ma trận xưng hô (`pronoun_matrix.json`).
   - Loại bỏ lối nói bị động gượng gạo ("bị", "được"), từ nối hành chính lê thê ("bởi vì... cho nên...", "một cách...").
   - Lời thoại phải mang khẩu âm đời thực của người Việt, có trợ từ cuối câu tự nhiên (`nhé`, `nhá`, `à`, `hả`, `chứ`, `thôi`, `đấy`, `nè`).
3. **Kiểm Soát Tốc Độ Đọc Điện Ảnh (CPS & CPL Constraints)**:
   - CPS mục tiêu: 12 - 16 ký tự/giây.
   - CPS tối đa: không vượt quá 18 - 20 ký tự/giây. Với những câu thoại diễn viên nói dồn dập, bắt buộc cô đọng câu chữ để người chơi kịp đọc.
   - Tối đa 2 dòng phụ đề trên một cảnh; không vượt quá 38-40 ký tự mỗi dòng.
4. **Bảo Tồn Toàn Vẹn Thẻ Kỹ Thuật (`protected_tokens`)**:
   - Mọi thẻ HTML (`<i>`, `<b>`), mã màu ASS (`{\c&H...&}`), biến số game (`%s`, `{playerName}`), và ký hiệu ngắt dòng (`\N`, `\n`) phải được giữ nguyên vẹn 100%.
5. **Quy Trình 2 Vòng Độc Lập (Two-Pass Translation & Editorial)**:
   - Vòng 1 (Translator Agent): Chuyển ngữ chính xác theo bối cảnh kịch bản và ma trận xưng hô.
   - Vòng 2 (Cinematic Reviewer / Editor): Đóng vai đạo diễn lồng tiếng/biên tập phụ đề, đọc to lời thoại, trau chuốt nhịp điệu, cắt tỉa từ thừa để đạt chuẩn CPS.
6. **Định Dạng Xuất Chuẩn JSONL**:
   - Giao tiếp giữa các công cụ thông qua tệp JSONL có cấu trúc. Không xuất Markdown tự do, không chém gió giải thích ngoài luồng.

---

## 3. Cẩm Nang Đọc Theo Vai Trò & Tài Liệu Tham Khảo

- **Khẩu âm tiếng Việt tự nhiên & Triệt hạ AI Slop**: Đọc [vietnamese-natural-voice-guide.md](references/vietnamese-natural-voice-guide.md).
- **Ràng buộc thời gian, tính toán CPS & Lược dịch điện ảnh**: Đọc [cinematic-timing-and-cps.md](references/cinematic-timing-and-cps.md).
- **Thiết lập và vận hành Ma trận xưng hô**: Đọc [pronoun-matrix-system.md](references/pronoun-matrix-system.md).
- **Đặc thù chuyển ngữ từ tiếng Trung, Nhật, Hàn, Anh**: Đọc [multilingual-source-adaptation.md](references/multilingual-source-adaptation.md).
- **Định dạng phụ đề (.srt, .vtt, .ass, Unity/Unreal JSON/CSV)**: Đọc [fmv-engines-and-subtitle-formats.md](references/fmv-engines-and-subtitle-formats.md).
- **Khế ước dịch thuật chi tiết cho Model**: Đọc [translation-contract.md](references/translation-contract.md).
- **Cỗ máy trạng thái & cấu trúc dự án**: Đọc [workflow-and-state.md](references/workflow-and-state.md).
- **Kiểm định chất lượng QA & Đóng gói phát hành**: Đọc [qa-and-release.md](references/qa-and-release.md).

---

## 4. Bộ Lệnh Công Cụ CLI (CLI Scripts)

Các script nằm trong thư mục `scripts/` hỗ trợ tự động hóa toàn bộ quy trình:

| Script | Chức năng |
| :--- | :--- |
| `init_project.py` | Khởi tạo thư mục dự án FMV, sinh file metadata và cấu trúc chuẩn |
| `build_manifest.py` | Quét và tính mã băm SHA-256 toàn bộ file phụ đề nguồn |
| `extract_subtitles.py` | Trích xuất phụ đề (.srt, .vtt, .ass, .json, .csv) thành `extracted/source.jsonl` |
| `export_subtitles.py` | Xuất ngược từ `final.jsonl` hoặc `source.jsonl` ra định dạng file phụ đề gốc |
| `audit_project.py` | Kiểm tra tính hợp lệ của các bằng chứng theo từng giai đoạn |
| `set_stage.py` | Thăng hạng trạng thái an toàn trong `run-state.json` khi có đủ bằng chứng |
| `plan_jobs.py` | Chia các phân cảnh video thành các job dịch vừa vặn ngữ cảnh và ngân sách token |
| `build_shared_prefix.py` | Đóng gói Kinh thánh dự án (Ma trận xưng hô, hồ sơ, thuật ngữ) thành prompt cache |
| `build_context_bundle.py` | Đóng gói ngữ cảnh chi tiết cho từng job (kèm các câu thoại xung quanh để hiểu mạch truyện) |
| `emit_chunk.py` | Xuất packet tối ưu gửi cho mô hình AI dịch |
| `validate_translation.py` | Bộ kiểm thử tự động: đối soát ID, thẻ bảo vệ, đo CPS, quét AI slop |
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

# 4. Đóng băng Kinh thánh & Ma trận xưng hô
# (Sau khi hoàn thiện bible/pronoun_matrix.json và bible/glossary.tsv)
python scripts/set_stage.py bible-frozen --project-dir ./my-fmv-project --evidence bible/version.json

# 5. Lập kế hoạch job & Tạo context bundle
python scripts/plan_jobs.py --project-dir ./my-fmv-project
python scripts/build_shared_prefix.py --project-dir ./my-fmv-project
python scripts/build_context_bundle.py --project-dir ./my-fmv-project --all-pending

# 6. Dịch, Biên tập, Kiểm định tự động
# (Translator Agent & Cinematic Reviewer Agent xử lý qua emit_chunk & validate)
python scripts/validate_translation.py --project-dir ./my-fmv-project --job-id scene_01
python scripts/apply_review_delta.py --project-dir ./my-fmv-project --job-id scene_01

# 7. Hợp nhất & Đóng gói phát hành
python scripts/merge_jobs.py --project-dir ./my-fmv-project
python scripts/export_subtitles.py --project-dir ./my-fmv-project --output-dir release/subtitles
python scripts/audit_font_coverage.py --project-dir ./my-fmv-project
python scripts/set_stage.py released --project-dir ./my-fmv-project --evidence release/release-manifest.json
```
