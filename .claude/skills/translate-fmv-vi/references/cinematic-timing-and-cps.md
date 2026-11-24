# Ràng Buộc Thời Gian Phim Ảnh & Giới Hạn CPS (Cinematic Timing & CPS)

## Bản chất của Phụ đề Game FMV
Không giống như game visual novel thông thường người chơi bấm chuột để đọc câu kế tiếp, trong game FMV:
1. **Phụ đề xuất hiện và biến mất theo đúng dòng thời gian (Timecode) của video.**
2. Người chơi vừa phải **nhìn hình ảnh diễn viên** (hành động, diễn xuất, bối cảnh), vừa phải **đọc kịp phụ đề**.
3. Nếu câu dịch tiếng Việt quá dài hoặc quá rườm rà, người chơi đọc không kịp trước khi phụ đề biến mất -> ức chế, mất thông tin cốt truyện!

---

## 1. Công Thức Tính CPS (Characters Per Second)

$$CPS = \frac{\text{Số ký tự trong phụ đề (bao gồm dấu cách)}}{\text{Thời lượng hiển thị (giây)}}$$

Ví dụ:
- Thời gian bắt đầu: `00:01:20,000`
- Thời gian kết thúc: `00:01:22,500`
- Thời lượng = `2.5` giây.
- Nếu câu dịch có 50 ký tự: $CPS = 50 / 2.5 = 20.0$ ký tự/giây.

### Bảng Định Mức CPS Chuẩn Quốc Tế Cho Phụ Đề Tiếng Việt:

| Chỉ số CPS | Đánh giá | Trải nghiệm người chơi | Hành động của Agent |
| :--- | :--- | :--- | :--- |
| **< 12 CPS** | Rất thong thả | Người chơi đọc xong rất nhanh, thoải mái ngắm diễn viên | Duyệt |
| **12 - 16 CPS** | **Lý tưởng (Sweet spot)** | Tốc độ đọc tự nhiên chuẩn phim chiếu rạp / Netflix | Duyệt |
| **17 - 19 CPS** | Nhanh / Cảnh dồn dập | Phù hợp khi diễn viên nói nhanh, cãi vã, bắn rap | Cho phép nếu ngữ cảnh thực sự dồn dập |
| **> 20 CPS** | **Quá tải (Overload)** | Người chơi đọc không kịp, câu bị trôi mất | **Bắt buộc cô đọng lại câu dịch!** |

---

## 2. Giới Hạn Dòng & Số Ký Tự Mỗi Dòng (CPL - Characters Per Line)

- **Số dòng tối đa**: **Tối đa 2 dòng** cho một subtitle event. Không bao giờ hiển thị 3 dòng (sẽ che mất mặt diễn viên và khung hình).
- **Độ dài mỗi dòng (CPL)**:
  - Tối đa: **37 - 40 ký tự** mỗi dòng trên màn hình chuẩn 16:9 (1080p / 4K).
  - Một phụ đề 2 dòng không nên vượt quá **75 - 80 ký tự tổng cộng**.
- **Quy tắc ngắt dòng thẩm mỹ (Natural Line Breaking)**:
  - Ngắt dòng theo **cụm ngữ nghĩa / vế câu**, KHÔNG bẻ gãy từ ghép hay tên riêng:
    - ❌ Sai:
      ```text
      Tôi không thể nào tin được là anh lại làm như
      thế với tôi!
      ```
    - ✔️ Đúng:
      ```text
      Tôi không thể nào tin được,
      rằng anh lại làm thế với tôi!
      ```
  - Dòng trên ngắn hơn dòng dưới hoặc hai dòng cân xứng nhau (dạng hình kim tự tháp lộn ngược hoặc cân bằng), tránh tình trạng dòng 1 có 38 chữ, dòng 2 chỉ có 1 chữ rơi rớt ("widow word").

---

## 3. Chiến Thuật Cô Đọng Câu Dịch (Condensation Strategies)

Khi gặp lời thoại gốc nói nhanh (CPS vượt ngưỡng 18-20), biên dịch viên phải áp dụng kỹ thuật **lược dịch điện ảnh (cinematic adaptation)**: giữ trọn vẹn thông điệp cốt lõi và cảm xúc, loại bỏ các hư từ phụ gia.

### Ví dụ Thực Tế:
- **Tiếng Anh gốc**: *"Well, to be honest with you, I don't really think that this is going to work out at all."* (1.8 giây, 83 ký tự).
  - ❌ Dịch máy nguyên si: *"À thì, thành thật mà nói với anh, tôi thực sự không nghĩ rằng điều này sẽ có tác dụng chút nào đâu."* (93 ký tự -> CPS = **51.6**! Không ai đọc kịp!)
  - ✔️ Cô đọng chuẩn điện ảnh: *"Nói thật nhé, cách này không ổn đâu."* (35 ký tự -> CPS = **19.4**, vừa vặn, chuẩn nhịp thở).

- **Tiếng Trung gốc**: *"我跟你讲，这件事情要是被董事会知道的话，我们两个人都吃不了兜着走！"* (2.2 giây).
  - ❌ Dịch lê thê: *"Tôi nói cho cậu biết, chuyện này nếu như bị ban giám đốc biết được thì hai người chúng ta đều phải gánh hậu quả không gánh nổi đâu!"* (125 ký tự -> CPS = **56.8**!).
  - ✔️ Cô đọng chuẩn điện ảnh: *"Để hội đồng quản trị biết chuyện này, hai đứa mình chết chắc đấy!"* (62 ký tự -> CPS = **28.1**, dồn dập, căng thẳng).

---

## 4. Phụ Đề Lựa Chọn Tương Tác & QTE (Quick Time Events)

Trong game FMV, người chơi liên tục đối mặt với các nút bấm lựa chọn cốt truyện, thường đi kèm **thanh thời gian đếm ngược (Timer 5 - 10 giây)**.
- **Quy tắc cho nút bấm lựa chọn**:
  - Tối đa **15 - 20 ký tự** cho mỗi tùy chọn.
  - Phải dùng **động từ hành động mạnh, dứt khoát**, không giải thích dài dòng:
    - ❌ *"Hãy quyết định giấu kín bí mật này với cô ấy"* -> ✔️ *"Giấu kín bí mật"*
    - ❌ *"Chạy thật nhanh về phía cánh cửa sổ bên trái"* -> ✔️ *"Nhảy qua cửa sổ"*
    - ❌ *"Bày tỏ tình cảm thật trong lòng của mình"* -> ✔️ *"Thổ lộ tình cảm"*
  - Người chơi chỉ có 1-2 giây để quét mắt qua các phương án và đưa ra quyết định bấm chuột, do đó độ ngắn gọn và rõ ràng là sinh mạng của game FMV!
