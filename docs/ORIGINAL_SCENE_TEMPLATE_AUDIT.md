# Đối chiếu scene và template với TubeCraft v0.1.61

Ngày kiểm: 18-07-2026. Nguồn đối chiếu là payload Python đã trích từ
`TubeCraft_v0.1.61_Setup.exe`, không phải ảnh chụp hay suy đoán từ UI.

## Kết luận có thể kiểm chứng

- EXE gốc có **29 template**, **41 scene nền tảng** và **47 scene theo bộ**:
  **88 scene**.
- Bản độc lập có đủ 88 scene đó, và một scene local thêm là
  `neon_sprite_panel`.
- Với dữ liệu demo gốc, **88/88 scene gốc có cùng `height` và SHA-256 của
  canvas code sinh ra**. Điều này bao gồm mọi `td_*`, `wp_*` và `mn_*`.
- Mỗi scene độc lập đã đi qua `validate_script` và preview renderer thật:
  **89/89 thành công**. Mỗi template đã đi qua `preview_demo` thật:
  **29/29 thành công**.
- Trong 29 định nghĩa template, 28 định nghĩa trùng EXE. Khác biệt duy nhất là
  `neon_sketch`: EXE cho AI gửi JavaScript canvas raw; bản này chỉ nhận
  `template + params` và dựng bằng `neon_sprite_panel` local. Đây là thay đổi
  an toàn có chủ đích, không phải một preset/license bị thiếu.

## Quy tắc layout phải giữ nguyên

1. `td_chrome`, `wp_chrome`, `mn_chrome` là overlay 1.800 px: luôn là element
   đầu tiên, nằm ở `(0, 0)`, nhưng **không phải** nội dung thứ hai của step.
2. `news_backdrop`, `cosmic_backdrop`, `light_backdrop` là nền overlay; height
   10 px chỉ là giá trị dòng chảy, còn code vẽ full-canvas. Luôn ghép với một
   scene nội dung, không dùng riêng.
3. Template scene-first chỉ có một body scene mỗi step. Tech Decode có headline
   riêng; Paper Brief và Math Noir đặt headline bên trong scene nên `no_headline`.
4. Với body quá thấp, subtitle dùng anchor 82%. Chỉ khi đáy body vượt 1.470 px,
   logic gốc mới dời caption vào khoảng 84–88% để tránh đè lên nội dung.

## 29 template

| ID | Art style | Scene/effect chủ đạo | Kiểu |
|---|---|---|---|
| `lux_finance` | liquidglass | `counter_metric` | preset |
| `neon_tech` | cyberpunk | `flow_pipeline` | preset |
| `warm_edu` | watercolor | `step_reveal_list` | preset |
| `kids_fun` | cartoon | `orbit_ecosystem` | preset |
| `clean_biz` | sketchnote | `bar_compare` | preset |
| `calm_wellness` | pastel | `growth_curve` | preset |
| `ink_tradition` | inkwash | `gauge_dial` | preset |
| `retro_game` | pixel | `leak_bucket` | preset |
| `midnight_pro` | default | `quote_card` | preset |
| `health_green` | liquidglass | `donut_percent` | preset |
| `news_hot` | default | `timeline_road` | preset |
| `science_blue` | default | `icon_grid` | preset |
| `beauty_purple` | liquidglass | `star_rating` | preset |
| `food_orange` | liquidglass | `flat_stat` | preset |
| `whiteboard` | sketch | `step_reveal_list` | preset |
| `dev_code` | default | `code_typing` | preset |
| `series_course` | default | `episode_ring` | preset |
| `review_scan` | liquidglass | `laser_scan` | preset |
| `ai_assistant` | default | `neuro_stream` | preset |
| `app_maker` | default | `forge_apk` | preset |
| `mobile_ui` | liquidglass | `phone_hero` | preset |
| `tech_news` | cyberpunk | `breaking_news` | curated backdrop + body |
| `ai_hotlist` | default | `hotlist_board` | curated backdrop + body |
| `light_news` | aurora | `timeline_road` | exemplar-safe |
| `tech_light` | aurora | `metric_grid` | exemplar-safe |
| `neon_sketch` | neonsketch | `neon_sprite_panel` | local safe scene |
| `tech_explainer` | techdark | `td_title_hero` | scene-first |
| `paper_explainer` | warmpaper | `wp_title_stack` | scene-first |
| `math_noir` | mathnoir | `mn_unit_circle` | scene-first |

`neon_sketch` giữ geometry gốc: sprite tâm tại `cursorY + 280`, terminal panel
từ `cursorY + 560`, cao 320 px. Title lớn không còn bị vẽ lại trong panel;
headline của step chịu trách nhiệm hiển thị title một lần.

## Scene nền tảng (42 scene hiện có)

| Scene | Height demo | Chức năng / cách dùng |
|---|---:|---|
| `neon_sprite_panel` | 880 | Sprite Neon + terminal rows local; chỉ dùng Neon Doodle. |
| `episode_ring` | 400 | Vòng số tập và tiến độ series. |
| `phone_hero` | 640 | Điện thoại hero với icon quỹ đạo. |
| `code_typing` | 180 | Khung code/terminal gõ dần; dùng với code ngắn. |
| `edge_globe` | 560 | Globe/edge network, phù hợp hạ tầng phân tán. |
| `data_river` | 330 | Luồng APP → worker → database. |
| `shield_wall` | 480 | Luồng bị chặn/cho phép qua lớp bảo vệ. |
| `neuro_stream` | 470 | Neural stream đi tới trả lời chatbot. |
| `laser_scan` | 440 | Quét sản phẩm, tên, giá, tồn kho. |
| `metric_grid` | động | Grid KPI; phải cấp `metrics/items`, không dùng rỗng. |
| `rocket_finale` | 560 | Hero kết thúc/bứt phá. |
| `forge_apk` | 400 | Dây chuyền đóng gói ứng dụng. |
| `journey_path` | 500 | Lộ trình/mốc theo thứ tự. |
| `tool_dock` | 400 | Dãy công cụ/app. |
| `keycaps` | 230 | Một từ khoá hành động lớn. |
| `stamp_done` | 380 | Dấu hoàn thành/milestone. |
| `versus_split` | 340 | So sánh hai phương án. |
| `web_window` | 410 | Khung web/url/badge. |
| `check_sweep` | động | Danh sách đúng/sai; phải cấp items. |
| `style_sync` | 400 | Thẻ nhấn tính đồng bộ phong cách. |
| `big_word` | 420 | Hook typography lớn, một thông điệp. |
| `progress_map` | 330 | Bản đồ tiến độ series. |
| `stairs_steps` | động | Bậc thang tuần tự; cần items. |
| `domino_flow` | 360 | Chuỗi nguyên nhân-kết quả. |
| `orbit_cycle` | 660 | Vòng lặp khép kín. |
| `news_backdrop` | overlay | Nền lưới tin công nghệ; ghép cùng nội dung. |
| `breaking_pill` | 110 | Badge BREAKING. |
| `gradient_title` | động | Tiêu đề gradient/strike cũ→mới. |
| `merge_nodes` | 360 | Hai node hợp nhất. |
| `node_line` | 220 | Chuỗi node và completion. |
| `announce_block` | động | Khối thông báo nhiều dòng. |
| `breaking_news` | 740 | Composite breaking-news hoàn chỉnh. |
| `cosmic_backdrop` | overlay | Nền aurora/tinh vân; ghép cùng nội dung. |
| `hotlist_board` | 474 | Bảng top-list. |
| `rank_card` | 600 | Thẻ xếp hạng đơn. |
| `glass_list` | 270 | Danh sách glass theo nhóm. |
| `glass_duel` | 470 | So sánh A/B glass. |
| `cosmic_caption` | 130 | Caption kết cho hotlist. |
| `light_backdrop` | overlay | Nền sáng; không thêm một backdrop thứ hai. |
| `headline_card` | 364 | Thẻ tiêu đề editorial sáng. |
| `bento_stats` | 316 | Bento KPI. |
| `light_list` | 160 | Danh sách editorial sáng. |

41 scene nền tảng từ `episode_ring` đến `light_list` trùng mã sinh canvas với
EXE. `neon_sprite_panel` là scene local thêm như mô tả ở trên.

## Tech Decode — 15 scene `td_*`

| Scene | Height demo | Nghĩa và ràng buộc |
|---|---:|---|
| `td_chrome` | 1800 | Overlay series/chapter/progress, bắt buộc đứng đầu. |
| `td_title_hero` | 560 | Intro typographic + vòng task. |
| `td_cards` | 382 | Lưới 1–6 component/input cards. |
| `td_window` | 600 | Cửa sổ 3 chấm, heading/body/code gõ dần. |
| `td_pipeline` | 374 | Pipeline 5 bước với active state. |
| `td_turn_ring` | 460 | Turn/task loop và breakdown. |
| `td_hex_chain` | 560 | Trạng thái chuyển qua nhiều turn. |
| `td_shield` | 520 | Policy allow/confirm/deny. |
| `td_sandbox` | 560 | Hộp sandbox, tool, gate, result. |
| `td_context_gauge` | 600 | Context capacity + thành phần chiếm chỗ. |
| `td_state_board` | 520 | Task state và các ràng buộc. |
| `td_versus_cross` | 460 | Sai/cũ gạch chéo đối lập cách đúng. |
| `td_step_chain` | 330 | Chuỗi cause-effect bốn bước. |
| `td_chat_rail` | 560 | Chat một lượt đối chiếu workflow nhiều trạm. |
| `td_outro` | 640 | Outro CTA / tags. |

## Paper Brief — 10 scene `wp_*`

| Scene | Height demo | Nghĩa và ràng buộc |
|---|---:|---|
| `wp_chrome` | 1800 | Overlay thương hiệu trên nền kem, đứng đầu. |
| `wp_title_stack` | 696 | Intro/kết luận bằng nhiều headline xếp tầng. |
| `wp_timeline` | 848 | Timeline có ngày, brand, event. |
| `wp_rules` | 686 | Ba quy tắc / hard constraints. |
| `wp_duo_cards` | 1330 | Hai triết lý/đối thủ đối xứng. |
| `wp_layer_table` | 710 | Bảng so sánh theo lớp. |
| `wp_grid` | 708 | Provider/component grid. |
| `wp_before_after` | 1212 | Kiến trúc cũ/mới. |
| `wp_news_card` | 974 | Tin headline với window card. |
| `wp_outro` | 640 | Outro CTA/platform. |

## Math Noir — 22 scene `mn_*`

| Scene | Height demo | Nghĩa và ràng buộc |
|---|---:|---|
| `mn_chrome` | 1800 | Overlay brand + progress, đứng đầu. |
| `mn_title` | 560 | Intro `word` lớn, sub và kicker. |
| `mn_unit_circle` | 1000 | Góc, sin/cos trên vòng tròn đơn vị. |
| `mn_sine_trace` | 880 | Vòng tròn sinh sóng sin. |
| `mn_graph` | 930 | Hàm số/tangent. |
| `mn_shape_grid` | 820 | Lưới glyph hình học. |
| `mn_formula` | 560 | Một công thức lớn. |
| `mn_number_line` | 460 | Điểm/khoảng trên trục số. |
| `mn_triangle_anatomy` | 800 | Tam giác, cạnh, góc, đường cao. |
| `mn_transform` | 620 | Hình biến đổi liên tục. |
| `mn_steps_math` | 670 | Biến đổi phương trình theo dòng. |
| `mn_big_symbol` | 980 | Một ký hiệu lớn như π, 0, ∞. |
| `mn_integral_area` | 900 | Diện tích dưới đồ thị/tích phân. |
| `mn_venn` | 820 | Hai tập hợp giao nhau. |
| `mn_pendulum` | 880 | Con lắc/dao động. |
| `mn_spiral` | 940 | Xoắn ốc Fibonacci/vàng. |
| `mn_light_trail` | 840 | Quỹ đạo ném. |
| `mn_grid_cells` | 780 | Ma trận/cell đang xét. |
| `mn_equation_duel` | 760 | Hai đáp án cho một biểu thức. |
| `mn_definition_card` | 880 | Thuật ngữ + định nghĩa. |
| `mn_zoom_lens` | 860 | Kính lúp soi chi tiết. |
| `mn_outro` | 560 | Outro thương hiệu/CTA. |

Các scene `mn_*` có quy tắc semantic: scene chủ đề hẹp (đồ thị, sin, tích
phân, tam giác…) chỉ được dùng khi narration thực sự nói về chủ đề đó. Khi
không phù hợp, dùng `mn_formula`, `mn_steps_math`, `mn_definition_card`,
`mn_grid_cells` hoặc `mn_big_symbol` thay vì chọn một hình đẹp nhưng sai nghĩa.

## Lần kiểm cuối

Sau audit, `td_window` đã được sửa để dấu nháy trong code sample hiển thị như
EXE (`request_tool("search_code")`). Hai test suite liên quan chạy xanh:
`tests/test_script_schema.py` và `tests/test_renderer_integration.py` —
**24 passed**.
