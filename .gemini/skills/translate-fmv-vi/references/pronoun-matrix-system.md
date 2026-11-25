# Hệ Thống Ma Trận Xưng Hô Tiếng Việt (Vietnamese Pronoun Matrix System)

## Vấn Đề Cốt Tử của Tiếng Việt
Trong hầu hết ngôn ngữ (EN, JA, KO, ZH), đại từ nhân xưng tương đối cố định hoặc có lớp kính ngữ rõ rệt. Tuy nhiên, tiếng Việt sở hữu hệ thống đại từ nhân xưng biến thiên liên tục theo:
1. **Tuổi tác & thế hệ tương quan** (anh, chị, em, chú, bác, cô, dì, cháu, ông, bà).
2. **Cương vị xã hội & môi trường** (sếp - nhân viên, bác sĩ - bệnh nhân, thầy - trò, đối tác).
3. **Mức độ thân mật / giai đoạn quan hệ** (người lạ -> đồng nghiệp -> tán tỉnh -> người yêu -> xung đột).
4. **Ngữ cảnh Scenario** (ở công sở trước mặt mọi người vs nói chuyện riêng 2 người).

**Nguyên tắc bất biến của pipeline**: Mỗi **Scenario** trong `planning/scenarios.json` phải khóa **CHỈ MỘT** giai đoạn (`active_phases`) cho từng cặp nhân vật có mặt, tránh đổ đồng thời nhiều giai đoạn xung đột vào prompt gây loạn ngôi xưng hô.

---

## 1. Cấu Trúc File `bible/characters.json` & `bible/pronoun_matrix.json`

### A. Khai báo Nhân vật chính & Aliases (`bible/characters.json`)
Định nghĩa rõ `"protagonist_id"` (hoặc `"is_protagonist": true`) cùng đầy đủ `"aliases"` để mọi biến thể tên trong phụ đề (`"Triệu tổng"`, `"Sếp Triệu"`, `"Mẫn Mẫn"`) và mọi lựa chọn `[CHOICE]` của người chơi được ánh xạ chính xác về đúng ID nhân vật:
```json
{
  "protagonist_id": "char_male_lead",
  "characters": [
    {
      "id": "char_male_lead",
      "is_protagonist": true,
      "canonical_name": "Nam Chính",
      "aliases": ["Cố Hải", "A Hải"]
    }
  ]
}
```

### B. Cấu trúc chuẩn `bible/pronoun_matrix.json`
Mỗi phần tử trong `relationship_rules` định nghĩa hai chiều xưng hô, các đại từ bị cấm trong giai đoạn đó, và chỉ dẫn riêng cho các nút bấm lựa chọn (`choice_guidance`):

```json
{
  "relationship_rules": [
    {
      "pair": ["char_male_lead", "char_female_lead_1"],
      "phase": "phase_1_office_interview",
      "phase_label": "Giai đoạn 1: Công sở / Phỏng vấn — Cấp trên & Cấp dưới",
      "speaker_a": "char_male_lead",
      "speaker_b": "char_female_lead_1",
      "a_calls_b": "Tổng giám đốc Triệu / Sếp Triệu / chị",
      "a_calls_self": "em / tôi",
      "b_calls_a": "cậu Cố / cậu",
      "b_calls_self": "tôi",
      "forbidden_a_self": ["anh", "tao", "tớ"],
      "forbidden_a_to_b": ["em", "bạn", "mày", "cô"],
      "forbidden_b_self": ["em", "tao", "tớ"],
      "forbidden_b_to_a": ["anh", "em", "bạn", "mày"],
      "choice_guidance": "Lựa chọn của Cố Hải hướng tới Triệu Mẫn: xưng 'em / tôi', gọi đối phương 'sếp / chị / Triệu tổng'; tuyệt đối không dùng 'anh - em' hay 'bạn'.",
      "notes": "Quan hệ công sở cấp trên - cấp dưới"
    },
    {
      "pair": ["char_male_lead", "char_female_lead_1"],
      "phase": "phase_2_dating_romance",
      "phase_label": "Giai đoạn 2: Hẹn hò thân mật",
      "speaker_a": "char_male_lead",
      "speaker_b": "char_female_lead_1",
      "a_calls_b": "em / Mẫn Mẫn",
      "a_calls_self": "anh",
      "b_calls_a": "anh / Cố Hải",
      "b_calls_self": "em",
      "forbidden_a_self": ["tôi", "tao", "tớ"],
      "forbidden_a_to_b": ["bạn", "chị", "cô", "sếp", "mày"],
      "forbidden_b_self": ["tôi", "tao", "chị"],
      "forbidden_b_to_a": ["cậu", "bạn", "mày", "chú"],
      "choice_guidance": "Lựa chọn của Cố Hải hướng tới Triệu Mẫn: dùng 'anh - em' hoặc gọi 'Mẫn Mẫn', cấm lùi về 'tôi - bạn' hay 'cô'."
    }
  ]
}
```
*(Ghi chú: Bộ chuẩn hóa trong `pipeline_common.py` cũng hỗ trợ tương thích ngược dạng `relationships.<pair>.phases`.)*

---

## 2. Khóa Xưng Hô Theo Scenario (`planning/scenarios.json`) & Tuyến (`timeline_relationships.json`)

1. Script `plan_scenarios.py` tách mạch thoại thành từng phân cảnh (`scenario`) theo chuyển đổi bối cảnh, khoảng lặng thời gian hoặc thay đổi cặp nhân vật đối thoại.
2. Mỗi scenario khóa:
   - `participants`: các nhân vật đang có mặt trong cảnh.
   - `choice_target`: nhân vật mà **nhân vật chính** đang đối diện / hướng lựa chọn tới.
   - `active_phases`: chọn đúng 1 phase cho từng cặp nhân vật trong cảnh (ưu tiên từ nguồn -> `planning/scenarios.json` -> `timeline_relationships.json` -> `default`).
3. `build_context_bundle.py` chỉ giải nén **đúng các quy tắc thuộc `active_phases` của phân cảnh đó** thành `directional_pronoun_locks` (chiều `from -> to`), tránh đưa các phase xung đột vào ngữ cảnh dịch.

---

## 3. Quy Tắc Xử Lý Lựa Chọn Nhân Vật Chính (`is_choice: true`)

Trong game FMV, nút lựa chọn thường có `speaker` là `System`, `Choice1` hoặc để trống, nhưng **người thực hiện luôn là Nhân vật chính (Protagonist)**:
1. **Lựa chọn là lời thoại trực tiếp** (*"Tôi đồng ý"*, *"Trust me"*, *"别生气了"*):
   - Dịch đúng theo ngôi `protagonist -> choice_target` đang khóa trong scenario (`"Em đồng ý..."` ở giai đoạn công sở vs `"Tin anh đi"` ở giai đoạn hẹn hò).
2. **Lựa chọn là nhãn mô tả hành động** (*"An ủi cô ấy"*, *"逗她开心"*, *"Tell her the truth"*):
   - Luôn tự hỏi nhân vật chính đang đối diện ai trong scenario này (`choice_target`):
     - Nếu đang là cấp dưới - sếp nữ -> *"Tiếp tục trêu chọc sếp"*, *"Nói thật với chị ấy"*.
     - Nếu đang là người yêu -> *"An ủi em ấy"*, *"Dỗ Mẫn Mẫn vui"*.
     - Cấm dùng `"bạn"` hoặc từ xưng hô lệch vai vế (`"cô ta"`, `"anh ta"`).

---

## 4. Cách Xử Lý Nguồn Không Rõ Ngôi Thứ (JA / KO / ZH / EN)

- **Tiếng Nhật (lược bỏ chủ ngữ)**: Căn cứ `Speaker -> Addressee` của từng dòng trong `emit_chunk` (VD `"好きだよ"` -> nam chính tỏ tình nữ chính: *"Anh thích em"*; nữ chính đáp: *"Em cũng thích anh"*).
- **Tiếng Hàn (Jondaenmal vs Banmal)**: Khi nhân vật đổi từ đuôi `-yo/-nida` sang Banmal (`-ya/-eo`), cần tách hoặc cập nhật `active_phases` của scenario tương ứng để phản ánh bước chuyển thân mật hoặc bùng nổ xung đột.
- **Tiếng Anh (You & I)** / **Tiếng Trung (你 & 我)**: Dựa hoàn toàn vào `directional_pronoun_locks` của scenario, cấm tuyệt đối mặc định thành `"Tôi - Bạn"`.
