# Bản Khế Ước Dịch Thuật FMV Chuẩn Quốc Tế (Translation Contract)

## 1. Nguyên Tắc Cốt Lõi
Mục tiêu là dịch phụ đề game FMV sang tiếng Việt tự nhiên, chuẩn điện ảnh, truyền cảm, khớp khẩu khí diễn viên và tuân thủ nghiêm ngặt định mức thời gian hiển thị (CPS).

Thứ tự ưu tiên khi chuyển ngữ:
1. **Tính chính xác về logic, sự thật cốt truyện, quan hệ nhân quả và dòng thời gian.**
2. **Đại từ nhân xưng chuẩn xác tuyệt đối theo Ma trận Quan hệ Nhân vật (Pronoun Matrix).**
3. **Khẩu khí tự nhiên của diễn viên, cảm xúc, ngữ điệu và bối cảnh hiện trường.**
4. **Ràng buộc thời lượng đọc (CPS < 18, không vượt quá giới hạn mắt người đọc).**
5. **Cấu trúc ngữ pháp tiếng Việt mượt mà (Anti-AI-Slop).**
6. **Hình thức câu chữ bề mặt của tiếng gốc (Ưu tiên cuối cùng - không dịch từng từ một word-by-word).**

---

## 2. Các Quy Định Cấu Trúc Bất Khả Xâm Phạm

- **Định dạng đầu ra**: Xuất từng dòng theo chuẩn **JSONL**. Tuyệt đối không bọc trong Markdown, không thêm lời chào, không giải thích dài dòng ngoài cấu trúc JSON.
- **Bảo toàn ID**: Mỗi dòng đầu ra phải trả về chính xác trường `id` của câu tương ứng. Không được phép thêm bớt, gộp 2 dòng thành 1 hay tách 1 dòng thành 2.
- **Bảo toàn Thẻ Được Bảo Vệ (`protected_tokens`)**: Mọi mã màu, định dạng tag (`<i>`, `{\b1}`, `%s`, `\N`) phải được giữ nguyên vẹn 100% cả về ký tự, viết hoa/thường, thứ tự và vị trí.
- **Chỉ dịch nội dung hiển thị**: Tuyệt đối không dịch tên biến, tên tệp, nhãn clip, ID thoại hay thuộc tính kỹ thuật.
- **Báo cáo nghi vấn qua cấu trúc `issues`**: Khi gặp câu tối nghĩa hoặc mâu thuẫn cốt truyện, phải ghi nhận vào trường `issues` dạng JSON, không được tự ý đoán mò rồi viết bừa vào câu dịch.

---

## 3. Định Dạng JSONL Đầu Ra Chuẩn

Mỗi dòng trong tệp kết quả dịch (`draft.jsonl` hoặc `approved.jsonl`) phải có định dạng:

```json
{"id":"scene_01.srt:000042","translation":"Nói thật nhé, cách này không ổn chút nào đâu."}
```

Nếu phát hiện vấn đề cần biên tập viên lưu ý hoặc đề xuất thuật ngữ mới:
```json
{
  "id": "scene_01.srt:000043",
  "translation": "Để sếp biết chuyện này thì hai đứa mình toi đời đấy!",
  "confidence": "high",
  "issues": [
    {"type": "cps-warning", "message": "Câu gốc nói nhanh, đã cô đọng từ 85 ký tự xuống 52 ký tự để đảm bảo CPS = 16.5"}
  ],
  "term_proposals": [
    {
      "source": "老头子",
      "proposal": "ông bô",
      "scope": "char_gu_hai",
      "reason": "Nhân vật Cố Hải nói chuyện suồng sã với bạn bè về bố mình"
    }
  ]
}
```

---

## 4. Bảng Kiểm Tra Trước Khi Trả Kết Quả (Self-Check Checklist)
Trước khi xuất kết quả dịch của một phân đoạn:
1. Đã đối chiếu đúng xưng hô trong `bible/pronoun_matrix.json` cho cảnh này chưa?
2. Có từ nào thuộc danh sách "AI Slop" không (Ví dụ: "Tôi - Bạn", "bị/được" bừa bãi, "chết tiệt", "một cách...")?
3. Đã tính nhẩm CPS chưa? Nếu thời lượng ngắn mà câu dịch dài, người chơi có đọc kịp không?
4. Đọc nhẩm thành tiếng bằng miệng: Nghe có giống diễn viên phim điện ảnh đang nói không?
5. Các thẻ biến số, mã định dạng có nguyên vẹn không?
