# Hướng Dẫn Kỹ Năng Việt Hóa Game FMV Chuẩn Điện Ảnh (translate-fmv-vi)

> **Kỹ năng AI Agent chuyên biệt dịch game FMV (Full Motion Video) và Phim tương tác**
> *Hỗ trợ dịch từ Tiếng Trung (ZH), Tiếng Nhật (JA), Tiếng Hàn (KO), Tiếng Anh (EN) sang Tiếng Việt (vi-VN).*
> **Tuyệt đối không "AI Slop" · Kiểm soát tốc độ đọc CPS · Ma trận xưng hô biến thiên · Bảo toàn phụ đề nguyên bản.**

Dùng được trực tiếp trên cả **Claude Code** và **Google Antigravity**.

---

## 🎬 Vì Sao Game FMV Cần Bộ Kỹ Năng Riêng Biệt?

Game FMV (như *Love Is All Around - 完蛋！我被美女包围了！*, *The Invisible Guardian - 隐形守护者*, *Death Come True*, *Late Shift*, *Her Story*) là **phim điện ảnh người thật đóng kết hợp lựa chọn tương tác**.

Khi dùng các công cụ dịch thông thường hoặc prompt AI chung chung, bản dịch thường mắc 4 thảm họa:
1. **Lạm dụng "Tôi - Bạn"**: Xưng hô gượng gạo như đọc sách giáo khoa, làm mất hết sự thân mật, tình cảm hay kịch tính trong diễn xuất của diễn viên.
2. **Câu quá dài, đọc không kịp (Lỗi CPS)**: Chữ tiếng Việt thường dài hơn chữ Hán hay Kanji. Nếu dịch máy dài dòng, phụ đề sẽ biến mất khi người chơi mới đọc được nửa câu!
3. **Mùi "AI Slop" nồng nặc**: Lạm dụng từ bị động ("bị/được"), câu chửi thề buồn cười ("chết tiệt", "quỷ tha ma bắt"), từ nối hành chính lê thê ("bởi vì... cho nên...", "một cách...").
4. **Lỗi format phụ đề**: Làm mất timecode miligiây, hỏng mã màu font chữ ASS, hoặc làm tràn nút bấm lựa chọn QTE.

Kỹ năng `translate-fmv-vi` được xây dựng độc lập để giải quyết triệt để các vấn đề này.

---

## 🌟 Các Tính Năng Nổi Bật

### 1. Bản Tuyên Ngôn Triệt Hạ "AI Slop" (Anti-AI-Slop Manifesto)
- Cấm tuyệt đối dịch mặc định thành "Tôi - Bạn".
- Tự động thay thế bằng đại từ xưng hô đời thực: *anh - em, cậu - tớ, sếp - em, mày - tao, chú - cháu*.
- Thêm trợ từ khẩu ngữ cuối câu tự nhiên: *nhé, nha, nè, à, hả, chứ, thôi, đấy, cơ mà*.
- Bảng từ chửi thề phân cấp theo độ căng thẳng của cảnh phim, thay thế hoàn toàn chữ "chết tiệt".

### 2. Thuật Toán Kiểm Soát Tốc Độ Đọc (CPS - Characters Per Second)
- Tính toán chính xác: $\text{CPS} = \text{Số ký tự} / \text{Thời lượng giây}$.
- Mục tiêu: **12 - 16 CPS** (tốc độ đọc lý tưởng chuẩn Netflix/rạp chiếu phim).
- Tự động gắn cờ cảnh báo nếu CPS > 18; kích hoạt chế độ **lược dịch điện ảnh (cinematic condensation)** để gọt giũa câu văn ngắn gọn, súc tích mà vẫn truyền tải trọn vẹn cảm xúc.
- Giới hạn tối đa 2 dòng; mỗi dòng không quá 38-40 ký tự. Nút bấm lựa chọn QTE dưới 18 ký tự.

### 3. Ma Trận Xưng Hô Biến Thiên (Dynamic Pronoun Matrix)
- File `bible/pronoun_matrix.json` quản lý quan hệ nhân vật 2 chiều biến thiên theo giai đoạn:
  - *Giai đoạn 1 (Lịch thiệp/Công sở)*: Cố Hải xưng *em/tôi - sếp Triệu/chị*; Triệu Mẫn xưng *tôi - cậu Cố*.
  - *Giai đoạn 2 (Hẹn hò/Tình cảm)*: Chuyển sang *anh - em* ngọt ngào.
  - *Giai đoạn 3 (Xung đột/Cãi vã)*: Chuyển sang *tôi - anh / tôi - cô*.

### 4. Hỗ Trợ Đa Ngôn Ngữ Nguồn (ZH, JA, KO, EN)
- **Tiếng Trung**: Khử hoàn toàn văn dịch convert Hán-Việt kiếm hiệp trong bối cảnh hiện đại đô thị. Chuyển thành lời thoại giới trẻ Hà Nội / Sài Gòn sắc sảo, tự nhiên.
- **Tiếng Nhật**: Chuyển đổi chuẩn xác kính ngữ (Keigo) và khẩu âm nhân vật (Yakuwarigo), biến âm hậu tố -san, -kun, -chan, senpai linh hoạt.
- **Tiếng Hàn**: Nhận biết ranh giới Jondaenmal (kính ngữ) và Banmal (nói trống không) khi nhân vật thân mật hoặc nổi nóng.
- **Tiếng Anh**: Xử lý mượt mà thành ngữ tiếng lóng Mỹ/Anh, thoại hành động dồn dập.

### 5. Bộ Trích Xuất & Xuất Ngược Phụ Đề Hoàn Toàn Không Suy Hao
- Tương thích trực tiếp: `.srt`, `.vtt`, `.ass`, `.ssa`, bảng dữ liệu `.json`, `.csv` của Unity / Unreal Engine.
- Cam kết kiểm tra vòng lặp tròn (Round-trip verification) bảo toàn 100% timecode miligiây và thẻ màu trước khi bắt đầu dịch.

---

## 🚀 Hướng Dẫn Sử Dụng

### Dùng Trong Claude Code:
Chỉ cần gõ:
```text
Sử dụng $translate-fmv-vi để dịch tựa game FMV này sang tiếng Việt chuẩn điện ảnh.
```

### Dùng Trong Google Antigravity:
Kỹ năng đã được cài đặt sẵn tại `.gemini/skills/translate-fmv-vi/SKILL.md` và `skills/translate-fmv-vi/SKILL.md`.

### Quy Trình Dịch Dự Án Từng Bước (CLI):

```bash
# 1. Khởi tạo dự án
python skills/translate-fmv-vi/scripts/init_project.py --project-dir ./my-game --title "Love In The City" --source-lang zh --target-lang vi-VN

# 2. Đặt các file phụ đề gốc vào my-game/source/ rồi trích xuất
python skills/translate-fmv-vi/scripts/build_manifest.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/extract_subtitles.py --project-dir ./my-game

# 3. Chạy thử nghiệm round-trip để đảm bảo file gốc không bị suy hao
python skills/translate-fmv-vi/scripts/export_subtitles.py --project-dir ./my-game --dry-run
python skills/translate-fmv-vi/scripts/set_stage.py roundtrip-proven --project-dir ./my-game --evidence staging/roundtrip/roundtrip-proven.json

# 4. Tinh chỉnh Kinh thánh (bible/pronoun_matrix.json, bible/glossary.tsv) và đóng băng
python skills/translate-fmv-vi/scripts/set_stage.py bible-frozen --project-dir ./my-game --evidence bible/version.json

# 5. Lập kế hoạch job theo phân cảnh và đóng gói ngữ cảnh
python skills/translate-fmv-vi/scripts/plan_jobs.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/build_shared_prefix.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/build_context_bundle.py --project-dir ./my-game --all-pending

# 6. Dịch và Biên tập (AI Translator -> Cinematic Reviewer)
python skills/translate-fmv-vi/scripts/validate_translation.py --project-dir ./my-game --job-id scene_01
python skills/translate-fmv-vi/scripts/apply_review_delta.py --project-dir ./my-game --job-id scene_01

# 7. Hợp nhất bản dịch, xuất file phụ đề và kiểm tra font chữ
python skills/translate-fmv-vi/scripts/merge_jobs.py --project-dir ./my-game
python skills/translate-fmv-vi/scripts/export_subtitles.py --project-dir ./my-game --output-dir ./my-game/build
python skills/translate-fmv-vi/scripts/audit_font_coverage.py --project-dir ./my-game
```

---

## 📂 Các Dự Án Mẫu Có Sẵn (Examples)

Trong thư mục `examples/` đã chuẩn bị sẵn 3 dự án mẫu thực tế:
- `examples/fmv-zh-romance/`: Game tình cảm hài hước Trung Quốc (*Love Is All Around* style) - file `.srt`.
- `examples/fmv-ja-mystery/`: Game trinh thám án mạng Nhật Bản (*Death Come True* style) - file `.vtt`.
- `examples/fmv-en-action/`: Phim tương tác hành động trộm két sắt (*Late Shift* style) - file `.json`.

---

## 🧪 Chạy Kiểm Thử Toàn Diện (Regression Tests)

Để xác nhận toàn bộ hệ thống hoạt động hoàn hảo:
```bash
python -B -X utf8 skills/translate-fmv-vi/scripts/tests/test_fmv_pipeline.py
```
Toàn bộ quy trình từ khởi tạo, băm SHA-256, trích xuất, round-trip, lập kế hoạch, ngữ cảnh, kiểm tra CPS, phát hiện AI slop, duyệt biên tập, hợp nhất, xuất file và quét font tiếng Việt đều được tự động kiểm thử và vượt qua trong chưa đầy 1 giây!
