# Kiểm Định Chất Lượng & Phát Hành (QA & Release Protocols)

## Tôn Chỉ Kiểm Định Game FMV
Một bản dịch game FMV chỉ được coi là hoàn tất khi người chơi có thể bật game lên, vừa xem diễn viên diễn xuất vừa đọc phụ đề tiếng Việt một cách trơn tru, không gặp bất kỳ ký tự lỗi font nào, không bị sót chữ và không có cảm giác "đang đọc văn bản dịch tự động".

---

## 1. Bộ Kiểm Thử Tự Động 5 Tầng (5-Layer Automated QA)

### Tầng 1: Kiểm thử cấu trúc & ID (Structural & ID Audit)
- Kiểm tra số lượng dòng dịch có khớp 100% với danh mục ID nguồn không.
- Phát hiện dòng dịch bị thiếu (missing ID) hoặc thừa (duplicate / rogue ID).
- Kiểm tra tính toàn vẹn của mã băm `source_hash`.

### Tầng 2: Kiểm thử thẻ bảo vệ (Protected Token Integrity)
- Mọi thẻ định dạng màu sắc (`{\c&H...&}`), thẻ in nghiêng (`<i>`, `</i>`), biến số (`%s`, `{0}`), ký tự ngắt dòng (`\N`, `\n`) phải giữ nguyên vị trí và số lượng tương ứng.
- Tuyệt đối không để AI tự ý "Việt hóa" tên biến (ví dụ đổi `{playerName}` thành `{tênNgườiChơi}`).

### Tầng 3: Kiểm định tốc độ đọc CPS & Độ dài dòng (CPS & CPL Audit)
- Tự động tính CPS cho từng dòng phụ đề dựa trên `duration_ms`:
  - **CPS > 20 ký tự/giây**: Báo lỗi mức `HIGH_SEVERITY` -> Bắt buộc biên tập viên rút gọn câu.
  - **CPL > 40 ký tự trên một dòng**: Báo cảnh báo `WARNING` -> Cần ngắt thành 2 dòng.
  - **Số dòng > 2**: Báo lỗi `ERROR` -> Phụ đề không được quá 2 dòng.

### Tầng 4: Bộ quét Anti-AI-Slop Tiếng Việt (Vietnamese Slop Scanner)
- Tự động quét và gắn cờ các cụm từ bị cấm:
  - "Tôi - Bạn" trong các đoạn thoại thân mật hoặc đời thường.
  - Từ ngữ dịch máy thô thiển: *"chết tiệt"*, *"quỷ tha ma bắt"*, *"một cách nhanh chóng"*, *"bởi vì... cho nên..."*, *"cảm thấy được"*, v.v.
  - Lạm dụng thể bị động: phát hiện tần suất từ *"bị"* và *"được"* bất thường.

### Tầng 5: Kiểm định độ phủ ký tự Tiếng Việt (Vietnamese Font Coverage Audit)
- Tiếng Việt có **134 ký tự chữ cái có dấu** (bao gồm cả hoa và thường) cùng hệ thống 5 thanh điệu phức tạp (huyền, sắc, hỏi, ngã, nặng) và các dấu phụ (ă, â, đ, ê, ô, ơ, ư).
- Nhiều font chữ mặc định của game nước ngoài (chỉ hỗ trợ Latin cơ bản hoặc tiếng Trung/Nhật) khi hiển thị tiếng Việt sẽ bị:
  - Lỗi "ô vuông" (tofu box `□`).
  - Lỗi nhảy font (ký tự có dấu bị biến thành font Times New Roman hoặc font hệ thống xấu xí).
  - Lỗi đè chữ hoặc lệch dấu thanh.
- Script `scripts/audit_font_coverage.py` sẽ quét toàn bộ file bản dịch cuối cùng, thống kê danh sách 100% các ký tự tiếng Việt được sử dụng, và đối chiếu với bảng mã font chữ của game hoặc kiểm tra file `.ttf` / `.otf` đi kèm.

---

## 2. Quy Trình Duyệt Phim Trực Quan (Cinematic Playtest Protocol)

Sau khi vượt qua kiểm thử tự động:
1. **Kiểm tra trên Video mẫu (Video Overlay Preview)**:
   - Dùng tệp `.srt` / `.ass` vừa dịch xuất ra, load vào video game tương ứng bằng VLC Media Player hoặc MPC-HC / PotPlayer.
   - Biên tập viên theo dõi trực tiếp khẩu hình diễn viên khớp với nhịp xuất hiện của phụ đề.
2. **Kiểm tra lựa chọn tương tác (Choice & QTE Test)**:
   - Đảm bảo các nút bấm lựa chọn ngắn gọn, không bị tràn viền khung giao diện (UI overflow).
3. **Kiểm tra nhánh rẽ cốt truyện (Branching Route Test)**:
   - Thử nghiệm ít nhất 2 nhánh rẽ tính cách (ví dụ: nhánh tình cảm thân mật vs nhánh từ chối lạnh lùng) để xác nhận xưng hô thay đổi chính xác.

---

## 3. Đóng Gói Bộ Patch Phát Hành (Release Packaging)

Thư mục `release/` cuối cùng sẽ bao gồm:
1. Tệp phụ đề đã dịch tương thích định dạng game (ví dụ: `patch/Localization/vi-VN/subtitles.json` hoặc thư mục `.srt`).
2. Tệp font chữ đã việt hóa đầy đủ (nếu game cần patch font).
3. File `README.txt` hướng dẫn người chơi cài đặt (kèm theo cách gỡ bỏ nếu muốn).
4. File `CHECKSUM.sha256` chứa mã băm xác thực toàn bộ các tệp trong bản patch.
5. Danh sách credit đội ngũ thực hiện và changelog phiên bản.
