# TubeCraft

TubeCraft là studio desktop local-first biến một ý tưởng thành video giáo dục có kịch bản AI, lời đọc, phụ đề karaoke và MP4 hoàn chỉnh.

## Chạy sau khi clone

Điều kiện duy nhất: Windows 10/11 và Python 3.12+.

```powershell
git clone https://github.com/hungle123-dev/AI-Video-Maker-Studio.git
cd AI-Video-Maker-Studio
python run.py
```

`python run.py` là lệnh chạy duy nhất: lần đầu nó tự tạo `.venv`, cài Python dependencies/Canvas, rồi tự tải Node, FFmpeg, FFprobe và Chromium vào máy local. Các lần sau mở app ngay. Lần đầu cần Internet; các runtime nặng không nằm trong GitHub repository.

## Quy trình tạo video

```text
Ý tưởng
  → AI tạo outline / lesson script
  → chỉnh step, scene và visual trong Editor
  → TTS tạo audio + timing từng từ
  → Canvas render + subtitle
  → FFmpeg encode và ghép audio
  → MP4
```

1. Tạo project, chọn template, tỉ lệ khung hình, giọng đọc và AI provider.
2. Dùng Autopilot để tạo series hoặc tự nhập/chỉnh script.
3. Preview từng cảnh, tạo audio, sau đó render từ hàng đợi.
4. MP4 được lưu trong `data/outputs/`.

## Tính năng

- AI: Gemini, OpenAI, Claude, DeepSeek, OpenRouter và 9Router local.
- TTS: Edge, Google TTS, Deepgram Aura, EverAI và Vivibe.
- Template, font, nền, scene Canvas, effect và subtitle preset.
- Video `9:16`, `16:9`, `1:1`; preview, queue, hủy job và export MP4.
- Project/data hoàn toàn local; cloud chỉ nhận nội dung khi bạn chọn provider tương ứng.

## Kiến trúc

| Thư mục | Vai trò |
| --- | --- |
| `ui/` | Flet desktop UI: Project, Editor, Template, Queue, Key và Settings |
| `core/` | Project store, schema, AI/TTS adapter, queue, preview, bảo mật |
| `engines/` | Audio pipeline, Canvas renderer, subtitle engine, FFmpeg encoder |
| `tools/` | Runtime tải tự động khi chạy lần đầu — không commit |
| `data/` | Dữ liệu local sinh khi chạy — không commit |
| `tests/` | Workflow, schema, renderer và release smoke tests |

## Dữ liệu và bảo mật

- API key được mã hoá bằng Windows DPAPI trong `data/keys.enc.json`.
- Project/audio/video/job nằm trong `data/`; backup thư mục này để backup toàn bộ công việc.
- Khi app bị đóng lúc render, job đang chạy bị đánh dấu gián đoạn để tránh publish file dở dang.

## Lưu ý hiệu năng

Canvas vẽ frame bằng CPU; NVIDIA/Intel/AMD GPU chủ yếu hỗ trợ encode video. Video 1080×1920, 30 FPS và nhiều animation sẽ cần đáng kể CPU/RAM. Đóng ứng dụng nặng hoặc hạ FPS khi cần xuất nhanh.

## Kiểm tra source

```powershell
python -m pytest -q
npm run check
```

## License

Chưa có license công khai. Hãy bổ sung license trước khi phân phối rộng rãi.
