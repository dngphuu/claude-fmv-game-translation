# Hệ Thống Ma Trận Xưng Hô Tiếng Việt (Vietnamese Pronoun Matrix System)

## Vấn Đề Cốt Tử của Tiếng Việt
Trong hầu hết ngôn ngữ (EN, JA, KO, ZH), đại từ nhân xưng tương đối cố định hoặc có lớp kính ngữ rõ rệt. Tuy nhiên, tiếng Việt sở hữu một hệ thống đại từ nhân xưng phức tạp bậc nhất thế giới, biến thiên theo:
1. **Tuổi tác & thế hệ tương quan** (anh, chị, em, chú, bác, cô, dì, cháu, ông, bà).
2. **Cương vị xã hội & môi trường** (sếp - nhân viên, bác sĩ - bệnh nhân, thầy - trò, đối tác kinh doanh).
3. **Mức độ thân mật / tình cảm** (người lạ -> bạn bè -> tán tỉnh -> người yêu -> vợ chồng -> trở mặt thù địch).
4. **Không gian giao tiếp** (trước mặt đám đông/công sở vs khi ở riêng 2 người trong phòng kín).

Trong game FMV, diễn viên diễn tiến triển mối quan hệ rõ mồn một qua từng cảnh quay. Dịch sai xưng hô sẽ biến một cảnh lãng mạn thành hài kịch lố lăng, hoặc biến một màn đấu trí thành cuộc cãi cọ vô duyên.

---

## 1. Cấu Trúc File `bible/pronoun_matrix.json`

Dự án chuẩn phải khởi tạo và đóng băng một bảng ma trận quan hệ nhân vật chi tiết:

```json
{
  "characters": {
    "protagonist": {
      "id": "char_gu_hai",
      "canonical_name": "Cố Hải",
      "gender": "male",
      "age": 25,
      "role": "Nhân vật chính, nhiếp ảnh gia tự do"
    },
    "heroine_boss": {
      "id": "char_trieu_man",
      "canonical_name": "Triệu Mẫn",
      "gender": "female",
      "age": 28,
      "role": "Tổng giám đốc công ty truyền thông, sắc sảo, kiêu kỳ"
    },
    "heroine_junior": {
      "id": "char_tieu_vu",
      "canonical_name": "Tiểu Vũ",
      "gender": "female",
      "age": 21,
      "role": "Thực tập sinh hoạt bát, ngây thơ, đàn em khóa dưới"
    }
  },
  "relationships": {
    "gu_hai__trieu_man": {
      "pair": ["char_gu_hai", "char_trieu_man"],
      "phases": {
        "phase_1_interview": {
          "description": "Giai đoạn đầu: Phỏng vấn xin việc & cấp trên cấp dưới nơi công sở",
          "gu_hai_calls_her": "tổng giám đốc Triệu / sếp Triệu / chị",
          "gu_hai_calls_self": "tôi / em",
          "trieu_man_calls_him": "cậu Cố / cậu",
          "trieu_man_calls_self": "tôi"
        },
        "phase_2_dating": {
          "description": "Giai đoạn hẹn hò bí mật / tình cảm thăng hoa",
          "gu_hai_calls_her": "em / Mẫn Mẫn (khi trêu)",
          "gu_hai_calls_self": "anh",
          "trieu_man_calls_her": "anh",
          "trieu_man_calls_self": "em"
        },
        "phase_3_conflict": {
          "description": "Giai đoạn hiểu lầm, tranh cãi gay gắt",
          "gu_hai_calls_her": "cô",
          "gu_hai_calls_self": "tôi",
          "trieu_man_calls_him": "anh",
          "trieu_man_calls_self": "tôi"
        }
      }
    }
  }
}
```

---

## 2. Quy Tắc Biến Thiên Xưng Hô Theo Nhánh Cốt Truyện (Route Context)

1. **Giai đoạn tiếp xúc ban đầu (Cold / Distant)**:
   - Dùng đại từ giữ khoảng cách lịch thiệp:
     - Nam thanh niên với nữ hơn tuổi: *cô/chị - tôi*
     - Nam với nữ bằng tuổi mới quen: *cô - tôi*, hoặc xưng tên.
     - KHÔNG vội vàng *anh - em* ngay từ cảnh 1 khi hai người chưa hề quen biết (trừ khi cố tình tán tỉnh kiểu trai trơ trẽn).
2. **Giai đoạn chuyển tiếp (Warm / Teasing)**:
   - Xuất hiện lời trêu chọc, xưng hô bắt đầu linh hoạt:
     - Bắt đầu chuyển sang gọi tên hoặc xưng *anh - em* nửa đùa nửa thật.
3. **Giai đoạn cao trào tình cảm (Intimate)**:
   - Cặp đôi hẹn hò chính thức: *anh - em* ngọt ngào, dùng biệt danh thân mật.
4. **Giai đoạn xung đột / Giận dỗi (Tension / Breakup)**:
   - Đang xưng *anh - em* tụt ngay xuống *tôi - cô / tôi - anh*:
     - *"Anh nói xong chưa? Nói xong rồi thì tôi đi."* (Sự lạnh lùng dứt khoát).
5. **Giai đoạn thù địch / Vạch mặt (Hostile)**:
   - Chuyển sang *mày - tao*, hoặc mỉa mai gọi đối phương bằng chức danh cũ.

---

## 3. Cách Xử Lý Xưng Hô Không Rõ Ngôi Thứ Ở Nguồn (JA / KO / ZH / EN)

- **Tiếng Nhật (lược bỏ chủ ngữ liên tục)**:
  - Nếu câu thoại là: *"好きだよ" (Suki da yo)*.
  - Phải xem ai đang nói với ai trên màn hình:
    - Nam chính tỏ tình nữ chính: *"Anh thích em."*
    - Nữ chính ngại ngùng đáp lại: *"Em cũng thích anh."*
    - Hai người bạn gái nói với nhau: *"Tớ quý cậu lắm đó."*
- **Tiếng Hàn (Jondaenmal vs Banmal)**:
  - Khi nhân vật chuyển từ đuôi câu kính ngữ `-yo / -nida` sang nói trống không (Banmal `-ya / -eo`):
    - Đây là cột mốc quan hệ trở nên thân thiết hoặc một bên tức giận phá bỏ phép lịch sự! Câu dịch tiếng Việt phải phản ánh ngay sự hạ bớt khoảng cách xưng hô này.
- **Tiếng Anh (You & I)**:
  - Phải căn cứ vào nét mặt diễn viên và kịch bản để chọn cặp xưng hô thích hợp nhất trong tiếng Việt, cấm tuyệt đối "Tôi - Bạn".
