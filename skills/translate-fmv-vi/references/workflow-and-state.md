# Quản Lý Trạng Thái, Cấu Trúc Dự Án & Vận Hành (Workflow & State)

## 1. Cấu Trúc Thư Mục Chuẩn của Dự Án FMV

Mỗi dự án game FMV được tổ chức trong một thư mục độc lập:

```text
fmv-project/
├── project.json                    # Metadata dự án (tên game, ngôn ngữ gốc, target: vi-VN, engine)
├── run-state.json                  # Máy trạng thái lưu tiến độ hiện tại kèm bằng chứng
├── source/                         # Tệp gốc của game (phụ đề srt/vtt/json/ass, video sample)
│   ├── file-manifest.json          # Danh mục tệp kèm mã băm SHA-256
│   └── signatures.md               # Ghi chú phiên bản game & định dạng tệp
├── research/                       # Nghiên cứu bối cảnh, diễn viên, kịch bản
│   ├── sources.jsonl               # Nguồn tư liệu (IMDb, Steam, Wiki, kịch bản gốc)
│   ├── cast-and-actors.md          # Danh sách diễn viên đời thực, nhân vật tương ứng
│   └── decisions.md                # Các quyết định chuyển ngữ ban đầu
├── staging/                        # Thư mục thử nghiệm đóng gói & kiểm tra round-trip
│   ├── unpacked/
│   └── roundtrip/
├── extracted/                      # Dữ liệu phụ đề đã chuẩn hóa
│   ├── source.jsonl                # Toàn bộ câu thoại gốc kèm timecode, ID, speaker
│   ├── script-map.json             # Bản đồ phân cảnh video & nhánh rẽ
│   └── control-token-report.json   # Danh sách các thẻ tag, mã màu cần bảo vệ
├── bible/                          # Kinh thánh dự án (Bộ tài liệu quy chuẩn)
│   ├── world.md                    # Bối cảnh thế giới, cốt truyện
│   ├── characters.json             # Hồ sơ nhân vật (tuổi, tính cách, vai vế)
│   ├── pronoun_matrix.json         # Ma trận xưng hô biến thiên theo giai đoạn
│   ├── voice.json                  # Hướng dẫn khẩu khí từng nhân vật
│   ├── glossary.tsv                # Từ điển thuật ngữ, địa danh, tên riêng (khóa cứng)
│   └── version.json                # Phiên bản đóng băng của bộ quy chuẩn
├── planning/                       # Kế hoạch phân chia công việc theo phân cảnh (Scenario)
│   ├── scenarios.json              # Phân tách từng scenario kèm chủ đề, bối cảnh, khóa phase & choice_target
│   ├── jobs.jsonl                  # Danh sách các job dịch tách rạch ròi theo từng scenario
│   └── translation-decisions.json  # Quyết định phân công
├── contexts/                       # Gói ngữ cảnh tối ưu hóa cho AI Subagents
│   ├── shared-prefix/              # Tiền tố chung cacheable (Kinh thánh + quy tắc chống slop)
│   └── <job_id>/current.json       # Ngữ cảnh cụ thể của từng phân cảnh (thời gian, nhân vật)
├── translations/                   # Kết quả dịch qua các vòng
│   ├── drafts/                     # Bản dịch sơ bộ của Translator Agent
│   ├── approved/                   # Bản dịch đã qua Cinematic Reviewer phê duyệt
│   └── final.jsonl                 # Toàn bộ bản dịch hợp nhất cuối cùng
├── reviews/                        # Báo cáo thẩm định độc lập & đối chiếu chỉnh sửa
│   └── <job_id>.review.jsonl
├── qa/                             # Báo cáo kiểm định chất lượng tự động
│   ├── cps-violations.json         # Cảnh báo vi phạm tốc độ đọc CPS
│   ├── slop-detections.json        # Phát hiện từ ngữ AI slop
│   └── font-coverage.json          # Kiểm tra hiển thị ký tự tiếng Việt
├── build/                          # Tệp phụ đề sau khi hoàn tất dịch được đóng gói lại
└── release/                        # Bản phát hành hoàn chỉnh kèm hướng dẫn cài đặt patch
```

---

## 2. Cỗ Máy Trạng Thái 12 Giai Đoạn (12-Stage State Machine)

Tiến độ dự án được quản lý nghiêm ngặt qua 12 trạng thái trong `run-state.json`:

1. `initialized`: Khởi tạo dự án, quét mã băm file nguồn.
2. `researched`: Nghiên cứu kịch bản, diễn viên, bối cảnh, lập danh sách nguồn.
3. `roundtrip-proven`: Thử nghiệm xuất đóng gói file phụ đề gốc thành công 100% không suy hao.
4. `extracted`: Trích xuất toàn bộ câu thoại, gắn ID, tính thời lượng miligiây, phân tích token.
5. `bible-frozen`: Hoàn thiện hồ sơ nhân vật, Ma trận xưng hô, bảng thuật ngữ và ĐÓNG BĂNG phiên bản.
6. `plan-approved`: Phê duyệt kế hoạch chia job theo phân cảnh video (Scene-based splitting).
7. `translating`: Translator Agent thực hiện dịch từng cảnh theo khế ước dịch thuật.
8. `reviewed`: Cinematic Reviewer Agent thẩm định độc lập, biên tập lại lời thoại cho tự nhiên.
9. `validated`: Chạy bộ công cụ kiểm thử tự động (khớp ID, thẻ tag, CPS, phát hiện slop).
10. `repacked`: Xuất bản dịch ngược lại định dạng file phụ đề chuẩn của game (.srt/.vtt/.json).
11. `playtested`: Đưa vào game hoặc trình phát video test đối soát trực quan trên video.
12. `released`: Đóng gói bộ patch hoàn chỉnh kèm checksum và hướng dẫn người chơi.

> **Quy tắc Thăng Hạng Trạng Thái**: Không được sửa tay trạng thái trong `run-state.json`. Phải chạy script `scripts/set_stage.py <stage> --evidence <file_path>` để ghi nhận bằng chứng rõ ràng!

---

## 3. Khả Năng Khôi Phục & Chạy Tiếp Tục (Resumability)

- Trạng thái từng Job dịch trong `planning/jobs.jsonl`:
  ```text
  pending -> assigned -> translated -> validated -> reviewed -> approved -> merged
  ```
- Nếu máy tính tắt ngang hoặc tiến trình bị ngắt:
  - Khi khởi động lại, hệ thống chỉ cần đọc `run-state.json` và `planning/jobs.jsonl`.
  - Các job đang `assigned` mà chưa có bản dịch hoàn chỉnh sẽ được đưa về `pending` để dịch tiếp.
  - Các job đã `approved` được giữ nguyên vẹn, **tuyệt đối không dịch lại từ đầu gây lãng phí token và thời gian**!
