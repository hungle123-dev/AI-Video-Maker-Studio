"""core/tts_everai.py — Engine TTS EverAI.

Luồng giống everai_engine.py gốc:
  1. POST /tts (response_type=indirect) → request_id
  2. Poll GET /tts/{request_id} tới khi status == "done" → audio_link
  3. Tải audio_link về output_path

Khác bản gốc: key lấy qua KeyManager của TubeCraft (xoay vòng, cooldown khi
quota), dùng requests đồng bộ — audio_engine gọi qua asyncio.to_thread.
"""
import os, time, logging, requests
from core.key_manager import key_manager; logger = logging.getLogger("TubeCraft.EverAI"); API_BASE = "https://everai.vn/api/v1/tts"; POLL_INTERVAL = 2.0; POLL_MAX_ATTEMPTS = 150
EVERAI_VOICES = [{"id": "vi_male_lehoang_mb", "name": "Lê Hoàng — nam, Miền Bắc"},
    {"id": "vi_female_thuytrang_mb", "name": "Thùy Trang — nữ, Miền Bắc"},
    {"id": "vi_male_minhtriet_mb", "name": "Minh Triết — nam, Miền Bắc"},
    {"id": "vi_female_hacuc_mb", "name": "Hạ Cúc — nữ, Miền Bắc"},
    {"id": "vi_male_ductrong_mb", "name": "Đức Trọng — nam, Miền Bắc"},
    {"id": "vi_female_kieunhi_mn", "name": "Kiều Nhi — nữ, Miền Nam"},
    {"id": "vi_female_huyenanh_mb", "name": "Huyền Anh — nữ, Miền Bắc"},
    {"id": "vi_female_halinh_mb", "name": "Hà Linh — nữ, Miền Bắc"},
    {"id": "vi_female_hoaian_mb", "name": "Hoài An — nữ, Miền Bắc"},
    {"id": "vi_female_khanhhuyentvc_mb", "name": "Khánh Huyền — nữ, Miền Bắc"},
    {"id": "vi_male_echo_default", "name": "Echo — nam, giọng Mỹ (TV)"},
    {"id": "vi_female_nova_default", "name": "Nova — nữ, giọng Mỹ (TV)"},
    {"id": "vi_male_onyx_default", "name": "Onyx — nam, giọng Mỹ (TV)"},
    {"id": "en_male_echo_default", "name": "Echo — male, American"},
    {"id": "en_female_nova_default", "name": "Nova — female, American"},
    {"id": "en_female_emily_us", "name": "Emily — female, American"},
    {"id": "en_female_elara_br", "name": "Elara — female, British"}]

class EverAIError(Exception):
    pass

def synthesize(text: str, voice: str, output_path: str, speed_rate: float=1.0) -> dict:
    entry = key_manager.acquire_key("everai")
    if not entry:
        raise EverAIError("Chưa có key EverAI — thêm ở tab Key AI Cloud (mục API TTS).")
    api_key = entry["key"]; headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}; payload = {"response_type": "indirect", "callback_url": "https://t2studio.local/callback", "input_text": text, "voice_code": voice, "audio_type": "mp3", "bitrate": 128, "speed_rate": speed_rate, "pitch_rate": 1.0}; start = time.time(); r = requests.post(API_BASE, headers=headers, json=payload, timeout=30)
    if r.status_code in (401, 403):
        key_manager.report_error("everai", api_key, quota=False, message=f"HTTP {r.status_code}")
        raise EverAIError(f"Key EverAI bị từ chối (HTTP {r.status_code}).")
    
    elif r.status_code == 429:
        key_manager.report_error("everai", api_key, quota=True, message="HTTP 429")
        raise EverAIError("Key EverAI hết quota — key đã được cho nghỉ.")
    elif r.status_code != 200:
        raise EverAIError(f"EverAI HTTP {r.status_code}: {r.text[:150]}")
    data = r.json()
    
    if str(data.get("status")) != "1" or not data.get("result", {}).get("request_id"):
        raise EverAIError(f"EverAI không nhận task: {str(data)[:200]}")
    request_id = data["result"]["request_id"]; logger.info(f"EverAI task {request_id} bắt đầu (voice={voice})")
    
    audio_link = None
    for _ in range(POLL_MAX_ATTEMPTS):
        time.sleep(POLL_INTERVAL)
        pr = requests.get(f"{API_BASE}/{request_id}", headers=headers, timeout=30)
        if pr.status_code != 200:
            continue
        pdata = pr.json()
        status = pdata.get("result", {}).get("status")
        if status == "done":
            audio_link = pdata["result"].get("audio_link")
            break
        elif status in ("error", "failed"):
            raise EverAIError(f"EverAI task lỗi: {str(pdata)[:200]}")
    if not audio_link:
        raise EverAIError(f"EverAI quá {int(POLL_MAX_ATTEMPTS * POLL_INTERVAL)}s chưa xong — thử lại sau.")
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with requests.get(audio_link, stream=True, timeout=120) as dl:
        if dl.status_code != 200:
            raise EverAIError(f"Tải audio thất bại: HTTP {dl.status_code}")
        with open(output_path, "wb") as f:
            for chunk in dl.iter_content(chunk_size=65_536):
                f.write(chunk)
    
    size = os.path.getsize(output_path)
    if size < 100:
        raise EverAIError("File audio EverAI rỗng.")
    logger.info(f"EverAI xong sau {time.time() - start:.1f}s → {output_path} ({size}B)")
    return {"status": "success", "output": output_path, "engine": "everai", "voice": voice, "size": size}
