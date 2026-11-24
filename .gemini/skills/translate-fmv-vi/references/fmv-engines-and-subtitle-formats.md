# Định Dạng Phụ Đề & Game Engine FMV (Engines & Subtitle Formats)

## Tổng Quan Kỹ Thuật
Khác với game Visual Novel (thường dùng mã nguồn kịch bản KiriKiri `.ks`, Ren'Py `.rpy`, BGI/Ethornell), game FMV được xây dựng trên:
1. **Engine dựng video chuyên biệt**: Unity (dùng AVPro Video, Unity VideoPlayer), Unreal Engine (Media Framework, Electra Player), hoặc Web/HTML5 hybrid engines.
2. **Định dạng dữ liệu phụ đề**:
   - Định dạng chuẩn công nghiệp: `.srt` (SubRip), `.vtt` (WebVTT), `.ass` / `.ssa` (SubStation Alpha).
   - Định dạng kịch bản tích hợp: `.json`, `.csv`, `.tsv`, Unity `TextAsset` (chứa mảng thoại đồng bộ với frame hoặc miligiây video).

Kỹ năng này cung cấp các bộ trích xuất (extractor) và đóng gói (exporter) bảo toàn 100% cấu trúc thời gian và siêu dữ liệu.

---

## 1. Các Định Dạng Phổ Biến

### A. SubRip (.srt)
```srt
1
00:00:12,450 --> 00:00:15,200
Anh có chắc là chúng ta không bị theo dõi chứ?

2
00:00:15,800 --> 00:00:18,100
Yên tâm đi, tôi đã cắt đuôi bọn chúng từ ngã tư rồi.
```
- **Quy tắc trích xuất**:
  - `id`: `<filename>:<index>` (ví dụ `scene_01.srt:000001`).
  - `start_time`: `00:00:12,450` (hoặc chuyển thành mili-giây: `12450`).
  - `end_time`: `00:00:15,200` (`15200`).
  - `duration_ms`: `2750`.
  - `text`: Nội dung câu thoại.

### B. WebVTT (.vtt)
```vtt
WEBVTT

00:01.500 --> 00:04.000 position:50% line:85%
<v Gu Hai>Trịnh tổng, cô tìm tôi có việc gì không?
```
- Có thêm thẻ voice `<v Character>` và các thuộc tính tọa độ màn hình `position`, `line`, `align`. Phải bảo tồn nguyên vẹn siêu dữ liệu này!

### C. Advanced SubStation Alpha (.ass)
```ass
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:23.45,0:01:26.10,Default,XiaoYu,0,0,0,,{\c&H0000FF&}Cố Hải ca ca, đợi muội với!
```
- Chứa các mã override style như `{\b1}`, `{\c&H...&}`, `\N` (ngắt dòng bắt buộc).
- Phải đưa các mã style này vào danh sách `protected_tokens` để AI không dịch đè hoặc xóa mất mã màu/hiệu ứng font.

### D. JSON / CSV Data Table (Unity / Unreal FMV)
```json
[
  {
    "clip_id": "clip_ch01_004",
    "timestamp_start_ms": 4200,
    "timestamp_end_ms": 6800,
    "speaker": "Triệu Mẫn",
    "dialogue": "这是今天需要审核的合同，抓紧时间看一遍。",
    "is_choice": false
  }
]
```
- Các trường `clip_id`, `timestamp_*`, `speaker`, `is_choice` phải được giữ nguyên. Chỉ dịch duy nhất trường văn bản hiển thị!

---

## 2. Tiêu Chuẩn File Trích Xuất Nội Bộ (`extracted/source.jsonl`)

Mọi định dạng đầu vào đều được chuẩn hóa về file `source.jsonl` duy nhất để quản lý tập trung:

```json
{
  "id": "ch01_meet.srt:000012",
  "source_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "file": "ch01_meet.srt",
  "index": 12,
  "start_time": "00:01:23,450",
  "end_time": "00:01:26,100",
  "duration_ms": 2650,
  "speaker": "Triệu Mẫn",
  "route": "common",
  "scene_id": "ch01_meet",
  "text": "这是今天需要审核的合同，抓紧时间看一遍。",
  "protected_tokens": [],
  "is_choice": false
}
```

---

## 3. Quy Trình Vòng Lặp Tròn (Round-Trip Guarantee)

Trước khi tiến hành dịch hàng ngàn câu:
1. **Giải nén / Trích xuất**: Chạy script trích xuất file phụ đề gốc ra `extracted/source.jsonl`.
2. **Thử nghiệm Đóng gói không chỉnh sửa (Zero-Edit Repack)**:
   - Dùng chính script xuất (export) để tạo lại các file `.srt` / `.vtt` / `.json` từ bản trích xuất gốc mà không đổi chữ nào.
3. **So sánh nhị phân / Khớp nội dung (Diff Audit)**:
   - Đảm bảo file tạo lại khớp 100% về timecode, số lượng dòng, và thứ tự câu so với file gốc của game.
4. **Kiểm tra khởi chạy game**:
   - Đưa file đóng gói thử nghiệm vào game xem video có hiển thị phụ đề mượt mà, đúng frame không.
5. Khi và chỉ khi quy trình này thành công mỹ mãn thì mới được cấp chứng nhận `roundtrip-proven` để bước vào giai đoạn dịch!
