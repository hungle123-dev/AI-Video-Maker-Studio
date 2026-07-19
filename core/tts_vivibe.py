"""Vivibe TTS ported from CapAssistant's PREMIUM workflow.

The browser workflow intentionally follows the original implementation: submit
all paragraphs in one request, capture each generated card, retry failed cards
for three healing rounds, then merge the captured audio at 192 kbps.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Sequence

from config import BASE_DIR, DATA_DIR
from core.crypto import decrypt_value, encrypt_value, is_dpapi_value


logger = logging.getLogger("TubeCraft.Vivibe")
LOGIN_URL = base64.b64decode(
    b"aHR0cHM6Ly93d3cudml2aWJlLmFwcC9sb2dpbg=="
).decode("utf-8")
_CREDENTIALS_FILE = DATA_DIR / "vivibe.enc.json"
_PREVIEW_DIR = BASE_DIR / "samples" / "premium_voice_preview"
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

VIVIBE_VOICES = [
    {"id": "Giọng adam", "display": "Adam 1"},
    {"id": "Adam 2", "display": "Adam 2"},
    {"id": "Adam 3", "display": "Adam 3"},
    {"id": "Adam Trà Đá", "display": "Adam 4"},
    {"id": "Truyện Audio", "display": "Ngọc Huyền"},
    {"id": "Đức Trung", "display": "Đức Trung"},
    {"id": "Quang Anh", "display": "Quang Anh"},
    {"id": "Trung Quân", "display": "Trung Quân"},
    {"id": "Trường An (Phật Pháp)", "display": "Trường An (Phật Pháp)"},
    {"id": "Chi Chi", "display": "Chi Chi"},
    {"id": "Vy Tin Tức", "display": "Vy Tin Tức"},
    {"id": "My Review", "display": "My Review"},
    {"id": "Dung Lồng Tiếng", "display": "Dung Lồng Tiếng"},
]


def _configure_playwright_browser_path() -> Path | None:
    """Point Playwright at the browser shipped with this app before it starts."""
    bundled_browsers = BASE_DIR / "playwright-browsers"
    if not bundled_browsers.is_dir():
        return None
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browsers)
    return bundled_browsers


def load_credentials() -> tuple[str, str]:
    """Load credentials from environment or the encrypted local data file."""
    username = os.environ.get("VIVIBE_USERNAME", "").strip()
    password = os.environ.get("VIVIBE_PASSWORD", "")
    if username and password:
        return username, password
    try:
        data = json.loads(_CREDENTIALS_FILE.read_text(encoding="utf-8"))
        stored_username = str(data.get("username") or "")
        stored_password = str(data.get("password") or "")
        saved_username = decrypt_value(stored_username).strip()
        saved_password = decrypt_value(stored_password)
        if saved_username and saved_password and (
            not is_dpapi_value(stored_username) or not is_dpapi_value(stored_password)
        ):
            # Compatibility input is only used after it has been upgraded.
            # save_credentials atomically replaces the old plaintext/XOR file.
            save_credentials(saved_username, saved_password)
        return saved_username, saved_password
    except Exception:
        return "", ""


def save_credentials(username: str, password: str) -> None:
    """Persist Vivibe credentials encrypted at rest."""
    username, password = (username or "").strip(), password or ""
    if not username or not password:
        raise ValueError("Tài khoản và mật khẩu Vivibe không được để trống.")
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_path = Path(str(_CREDENTIALS_FILE) + ".tmp")
    temp_path.write_text(
        json.dumps(
            {"username": encrypt_value(username), "password": encrypt_value(password)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(temp_path, _CREDENTIALS_FILE)


def credentials_ready() -> bool:
    return all(load_credentials())


def preview_path(voice_id: str) -> Path | None:
    """Return the exact CapAssistant preview WAV for a Vivibe voice."""
    for index, voice in enumerate(VIVIBE_VOICES, 1):
        if voice["id"] == voice_id:
            path = _PREVIEW_DIR / f"{index:03d}.wav"
            return path if path.is_file() else None
    return None


def _voice_search_terms(voice_id: str) -> list[str]:
    """Return the original query plus a current-site parenthetical fallback."""
    original = re.sub(r"[^\w\s]", "", voice_id or "").strip()
    terms = [original] if original else []
    without_parenthetical = re.sub(r"\s*\([^)]*\)\s*", " ", voice_id or "")
    fallback = re.sub(r"[^\w\s]", "", without_parenthetical).strip()
    if fallback and fallback not in terms:
        terms.append(fallback)
    return terms


def _unique_card_prefixes(texts: Sequence[str], minimum: int = 15) -> list[str]:
    """Keep CapAssistant's text-card lookup unambiguous within one batch."""
    normalized = [re.sub(r"\s+", " ", str(text or "")).strip() for text in texts]
    prefixes = []
    for index, text in enumerate(normalized):
        if not text:
            prefixes.append("")
            continue
        start = min(max(1, int(minimum)), len(text))
        prefix = text[:start]
        for length in range(start, len(text) + 1):
            prefix = text[:length]
            if all(
                other_index == index or not other.startswith(prefix)
                for other_index, other in enumerate(normalized)
            ):
                break
        prefixes.append(prefix)
    return prefixes


def _parse_blocks(text: str, req_type: str, is_preview: bool) -> tuple[list[dict], str]:
    """Parse text exactly like CapAssistant's run_premium_engine."""
    blocks: list[dict] = []
    if req_type == "srt" and not is_preview:
        for raw_block in re.split(r"\n\s*\n", (text or "").strip()):
            lines = [line.strip() for line in raw_block.split("\n") if line.strip()]
            if len(lines) < 3 or "-->" not in lines[1]:
                continue
            try:
                start_str, end_str = (part.strip() for part in lines[1].split("-->", 1))

                def to_ms(timestamp: str) -> int:
                    hours, minutes, seconds_ms = timestamp.split(":")
                    seconds, milliseconds = seconds_ms.split(",")
                    return (
                        int(hours) * 3_600_000
                        + int(minutes) * 60_000
                        + int(seconds) * 1_000
                        + int(milliseconds)
                    )

                start_ms, end_ms = to_ms(start_str), to_ms(end_str)
                content = re.sub(r"<[^>]+>", "", " ".join(lines[2:]).strip())
                blocks.append(
                    {
                        "start": start_ms,
                        "end": end_ms,
                        "text": content,
                        "status": "pending",
                        "path": "",
                    }
                )
            except Exception:
                pass
        return blocks, "" if blocks else "File SRT rỗng hoặc sai cấu trúc."

    for paragraph in re.split(r"\n+", (text or "").strip()):
        clean = paragraph.strip()
        if clean:
            blocks.append(
                {"start": -1, "text": clean, "status": "pending", "path": ""}
            )
    return blocks, "" if blocks else "Văn bản rỗng hoặc không hợp lệ."


def _capassistant_text_lines(text: str) -> list[str]:
    """Match CapAssistant's text-to-SRT normalization exactly."""
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def build_capassistant_srt(texts: Sequence[str]) -> tuple[str, list[tuple[int, int]], list[list[str]]]:
    """Adapt TubeCraft narration to CapAssistant's plain-text → SRT contract."""
    cursor, caption_index = 0, 1
    captions, scene_slots, scene_groups = [], [], []
    for raw_text in texts:
        scene_start = cursor
        lines = _capassistant_text_lines(str(raw_text or ""))
        scene_groups.append(lines)
        for line in lines:
            # Exact ``universal_parse_to_srt(..., "text")`` timing in the
            # CapAssistant source: one input row is one two-second caption.
            end = cursor + 2_000
            captions.append(
                f"{caption_index}\n{_timestamp(cursor)} --> {_timestamp(end)}\n{line}"
            )
            cursor, caption_index = end, caption_index + 1
        scene_slots.append((scene_start, cursor))
    return "\n\n".join(captions), scene_slots, scene_groups


def _hidden_popen(*args, **kwargs):
    if os.name == "nt":
        kwargs.setdefault("creationflags", _CREATE_NO_WINDOW)
    return subprocess.Popen(*args, **kwargs)


def _audio_segment():
    try:
        from pydub import AudioSegment
        import pydub.audio_segment as pydub_audio_segment
        import pydub.utils as pydub_utils
    except ImportError as exc:
        raise RuntimeError("Thiếu pydub; hãy chạy setup.ps1 lại.") from exc

    # CapAssistant relies on ffmpeg from PATH. TubeCraft ships its own binaries,
    # so point pydub at those same executables in both source and packaged builds.
    from engines.audio_engine import _find_executable

    AudioSegment.converter = _find_executable("ffmpeg")
    AudioSegment.ffmpeg = AudioSegment.converter
    AudioSegment.ffprobe = _find_executable("ffprobe")
    if os.name == "nt":
        from types import SimpleNamespace

        # ponytail: pinned pydub only uses subprocess.Popen/PIPE here; revisit
        # this proxy when upgrading pydub.
        pydub_audio_segment.subprocess = SimpleNamespace(
            Popen=_hidden_popen, PIPE=subprocess.PIPE
        )
        pydub_utils.Popen = _hidden_popen
    return AudioSegment


def _replace_with_retry(temp_path: str, destination: str) -> None:
    last_error: Exception | None = None
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        try:
            if os.path.exists(destination):
                os.remove(destination)
            os.replace(temp_path, destination)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.5)
    if last_error:
        raise last_error
    raise RuntimeError(f"Không thể ghi tệp audio: {destination}")


def _fit_chunk_to_srt_slot(segment, block: dict, speed: str, req_type: str, sync_timeline: bool, mode_pro: bool):
    try:
        factor = float(speed)
    except (TypeError, ValueError):
        factor = 1.0
    if factor > 0 and abs(factor - 1.0) >= 0.01:
        rate = max(1_000, int(segment.frame_rate * factor))
        segment = segment._spawn(segment.raw_data, overrides={"frame_rate": rate}).set_frame_rate(segment.frame_rate)
    if req_type == "srt" and sync_timeline and not mode_pro:
        slot = int(block.get("end", -1)) - int(block.get("start", -1))
        if slot > 0 and len(segment) > slot:
            rate = max(1_000, int(segment.frame_rate * (len(segment) / slot)))
            segment = segment._spawn(segment.raw_data, overrides={"frame_rate": rate}).set_frame_rate(segment.frame_rate)
            if len(segment) > slot:
                segment = segment[:slot]
    return segment


def _export_chunk_outputs(blocks: Sequence[dict], output_paths: Sequence[str], speed: str, req_type: str, sync_timeline: bool, mode_pro: bool) -> None:
    if len(blocks) != len(output_paths):
        raise RuntimeError("Số câu Vivibe không khớp số tệp audio đầu ra.")
    AudioSegment = _audio_segment()
    for block, destination in zip(blocks, output_paths):
        if not block.get("path") or not os.path.isfile(block["path"]):
            raise RuntimeError("Thiếu chunk audio Vivibe sau khi thu hoạch.")
        destination = os.path.abspath(os.fspath(destination))
        temp_path = destination + ".tmp"
        _fit_chunk_to_srt_slot(
            AudioSegment.from_file(block["path"]), block, speed, req_type, sync_timeline, mode_pro
        ).export(
            temp_path, format="mp3", bitrate="192k"
        )
        _replace_with_retry(temp_path, destination)


def _merge_caption_parts(parts: Sequence[str], destination: str) -> None:
    AudioSegment = _audio_segment()
    audio = AudioSegment.empty()
    for part in parts:
        audio += AudioSegment.from_file(part)
    temp_path = os.path.abspath(os.fspath(destination)) + ".tmp"
    audio.export(temp_path, format="mp3", bitrate="192k")
    _replace_with_retry(temp_path, os.path.abspath(os.fspath(destination)))


def _merge_original_audio(
    blocks: Sequence[dict],
    session_mp3_path: str,
    req_type: str,
    is_preview: bool,
    speed: str = "1.0",
    sync_timeline: bool = True,
    mode_pro: bool = False,
) -> list[dict]:
    """Reproduce CapAssistant's pydub timeline merge exactly."""
    AudioSegment = _audio_segment()
    merged_audio = AudioSegment.empty()
    current_timeline = 0
    timeline = []
    for index, block in enumerate(blocks):
        chunk_path = block.get("path") or ""
        if not chunk_path or not os.path.exists(chunk_path):
            continue
        # CapAssistant keeps the downloaded Vivibe WAV untouched.  In
        # particular, SRT timestamps only insert silence when they are ahead
        # of the audio cursor; they never time-stretch, trim, or overlay a
        # generated sentence.
        chunk_segment = AudioSegment.from_file(chunk_path)
        target_start = block.get("start", -1)

        if req_type == "srt" and not is_preview:
            silence_duration = int(target_start) - current_timeline
            if silence_duration > 0:
                merged_audio += AudioSegment.silent(duration=silence_duration)
                current_timeline += silence_duration
        elif index > 0:
            merged_audio += AudioSegment.silent(duration=200)
            current_timeline += 200
        start = current_timeline
        merged_audio += chunk_segment
        current_timeline += len(chunk_segment)
        timeline.append({"start": start, "end": current_timeline})

    temp_mp3_path = session_mp3_path + ".tmp"
    merged_audio.export(temp_mp3_path, format="mp3", bitrate="192k")
    _replace_with_retry(temp_mp3_path, session_mp3_path)
    return timeline


def merge_step_audio_files(audio_files: Sequence[str], output_path: str) -> None:
    """Merge TubeCraft step files with CapAssistant's 200 ms/192 kbps rules."""
    blocks = [
        {"start": -1, "text": "", "status": "success", "path": os.fspath(path)}
        for path in audio_files
    ]
    if not blocks:
        raise ValueError("Không có audio Vivibe để ghép.")
    _merge_original_audio(blocks, os.path.abspath(output_path), "text", False)


def _run_premium_engine(
    text,
    voice_id,
    username,
    password,
    is_headless=True,
    speed="1.0",
    is_preview=False,
    mp3_path="",
    req_type="text",
    sync_timeline=True,
    mode_pro=False,
    progress_callback=None,
    log_callback=None,
    chunk_output_paths: Sequence[str] | None = None,
    timeline_out: list[dict] | None = None,
):
    """CapAssistant PREMIUM implementation with a TubeCraft chunk adapter."""
    def log(message):
        if log_callback:
            log_callback(message)

    if not username or not password:
        return False, "Yêu cầu Tài khoản / Mật khẩu hệ thống!"
    if not mp3_path:
        return False, "Lỗi System API: Chưa có đường dẫn tệp MP3 đầu ra."
    if progress_callback:
        progress_callback(5)

    blocks, parse_error = _parse_blocks(text, req_type, is_preview)
    if parse_error:
        return False, parse_error
    if chunk_output_paths is not None and len(chunk_output_paths) != len(blocks):
        return False, "Số câu Vivibe không khớp số tệp audio đầu ra."

    session_mp3_path = os.path.abspath(os.fspath(mp3_path))
    session_dir = os.path.dirname(session_mp3_path)
    os.makedirs(session_dir, exist_ok=True)
    base_name = os.path.basename(session_mp3_path)
    raw_wav_path = os.path.join(session_dir, f"raw_data_{base_name}.wav")
    download_event = threading.Event()
    temp_chunks_dir = os.path.join(session_dir, f"temp_chunks_{int(time.time())}")
    os.makedirs(temp_chunks_dir, exist_ok=True)
    browser = None

    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Thiếu Playwright; hãy chạy setup.ps1 lại.") from exc

        bundled_browsers = _configure_playwright_browser_path()
        if getattr(sys, "frozen", False) and bundled_browsers is None:
            raise RuntimeError(
                "Thiếu Chromium đi kèm bản TubeCraft. Cài lại bản portable đầy đủ."
            )
        with sync_playwright() as playwright:
            launch_args = {
                "headless": is_headless,
                "args": [
                    "--mute-audio",
                    '--disable-blink-features=AutomationControlled', '--no-sandbox'
                ],
            }
            try:
                browser = playwright.chromium.launch(channel="chrome", **launch_args)
            except Exception:
                browser = playwright.chromium.launch(**launch_args)

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            def ultimate_network_sniper(response):
                try:
                    url = response.url
                    if not (".mp3" in url.lower() or ".wav" in url.lower() or "ttsapi.app" in url.lower()):
                        return
                    if url.startswith("blob:"):
                        encoded = page.evaluate(
                            """async () => {
                                const r = await fetch('""" + url + """');
                                const blob = await r.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result);
                                    reader.readAsDataURL(blob);
                                });
                            }"""
                        )
                        if "," in encoded:
                            encoded = encoded.split(",", 1)[1]
                        payload = base64.b64decode(encoded)
                    else:
                        payload = response.body()
                    with open(raw_wav_path, "wb") as output:
                        output.write(payload)
                    download_event.set()
                except Exception:
                    pass

            page.on("response", ultimate_network_sniper)

            def harvest_card(expected_text):
                snippet = expected_text.replace("\n", " ")[:15].strip()
                card_locator = page.locator("div.group").filter(has_text=snippet).last
                card_ready = False

                for _ in range(100):
                    try:
                        popup_close = page.locator("button:has-text('Đã hiểu')").first
                        if popup_close.is_visible():
                            popup_close.click(timeout=300, force=True)
                    except Exception:
                        pass
                    try:
                        if card_locator.is_visible():
                            card_ready = True
                            break
                    except Exception:
                        pass
                    page.wait_for_timeout(200)

                if not card_ready:
                    return False
                try:
                    card_locator.evaluate(
                        "el => el.scrollIntoView({behavior: 'smooth', block: 'center'})"
                    )
                except Exception:
                    pass
                page.wait_for_timeout(500)

                download_event.clear()
                try:
                    if os.path.exists(raw_wav_path):
                        os.remove(raw_wav_path)
                except Exception:
                    pass
                page.wait_for_timeout(500)

                play_button_success = False
                for _ in range(3):
                    try:
                        play_button = card_locator.locator("button").first
                        if play_button.is_visible(timeout=1_000):
                            play_button.click(timeout=1_000, force=True)
                            play_button_success = True
                            break
                    except Exception:
                        pass
                    page.wait_for_timeout(500)
                if not play_button_success:
                    return False

                audio_success = False
                for _ in range(150):
                    if (
                        download_event.is_set()
                        and os.path.exists(raw_wav_path)
                        and os.path.getsize(raw_wav_path) > 0
                    ):
                        audio_success = True
                        break
                    page.wait_for_timeout(200)
                try:
                    play_button.click(timeout=500, force=True)
                except Exception:
                    pass
                return audio_success

            log("🌐 Đang khởi tạo kết nối đến Cổng PREMIUM...")
            try:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
            except Exception as exc:
                raise RuntimeError(
                    "Mạng quá chậm, không thể load trang Login của hệ thống Premium."
                ) from exc

            email_input = page.locator(
                "input[type='email'], input[name='username']"
            ).first
            email_input.wait_for(state="visible", timeout=15_000)
            if progress_callback:
                progress_callback(10)

            log("🔐 Đang đăng nhập hệ thống nội bộ...")
            email_input.fill(username)
            page.locator(
                "input[type='password'], input[name='password']"
            ).first.fill(password)
            page.click("button[type='submit'], button:has-text('Đăng nhập')")

            workspace_ready = False
            for _ in range(40):
                if page.locator(
                    "textarea, [contenteditable='true']"
                ).first.is_visible():
                    workspace_ready = True
                    break
                page.wait_for_timeout(500)
            if not workspace_ready:
                raise RuntimeError("Quá thời gian tải Workspace hoặc sai mật khẩu.")
            if progress_callback:
                progress_callback(15)
            log("🔐 Đăng nhập thành công, chuẩn bị WorkSpace!")

            page.wait_for_timeout(2_000)
            trigger_xpath = (
                "//*[contains(text(), 'Giọng mặc định')]/parent::*/following-sibling::div"
                " | //*[contains(text(), 'Giọng mặc định')]/following-sibling::div"
                " | //button[contains(text(), 'Chọn giọng nói')]"
            )
            trigger = page.locator(trigger_xpath).first
            if trigger.is_visible(timeout=3_000):
                trigger.click(force=True)
                page.wait_for_timeout(2_000)
                page.locator("button:has-text('Giọng cộng đồng')").first.click(timeout=3_000)
                page.wait_for_timeout(1_000)
                clean_voice = re.sub(r"[^\w\s]", "", voice_id).strip()
                log(f"🎙️ Đang tìm kiếm giọng đọc AI: '{clean_voice}'...")
                page.locator("input[placeholder='Tìm kiếm giọng nói...']").first.fill(clean_voice)
                page.wait_for_timeout(2_000)
                voice_cards = page.locator(
                    "//h3/ancestor::div[contains(@class, 'cursor-pointer')]"
                ).filter(has_text=clean_voice)
                for index in range(voice_cards.count()):
                    voice_card = voice_cards.nth(index)
                    if voice_card.is_visible(timeout=300):
                        voice_card.click(timeout=3_000, force=True)
                        break
                else:
                    raise RuntimeError(f"Không tìm thấy giọng Vivibe: {voice_id}")
                page.wait_for_timeout(2_000)

                try:
                    confirm = page.locator("button:has-text('Có')").first
                    if confirm.is_visible(timeout=1_500):
                        confirm.click(timeout=2_000, force=True)
                        page.wait_for_timeout(2_000)
                except Exception:
                    pass

            # Original CapAssistant enables the replacement dictionary before TTS.
            for _ in range(2):
                try:
                    dictionary_trigger = page.locator("div, button, span").filter(
                        has_text=re.compile(
                            r"Từ điển thay thế|Thay thế từ", re.IGNORECASE
                        )
                    ).last
                    if dictionary_trigger.is_visible(timeout=3_000):
                        dictionary_trigger.click(force=True)
                        page.wait_for_timeout(1_500)

                        toggle = page.locator(
                            "input[type='checkbox']:visible, button[role='switch']:visible"
                        ).first
                        if toggle.is_visible(timeout=3_000):
                            if toggle.get_attribute("type") == "checkbox":
                                is_checked = toggle.is_checked()
                            else:
                                is_checked = toggle.get_attribute("aria-checked") == "true"
                            if not is_checked:
                                toggle.click(force=True)
                                page.wait_for_timeout(1_000)

                        close_button = page.locator("button:visible").filter(
                            has_text=re.compile(r"^Đóng$|^Close$|Đóng", re.IGNORECASE)
                        ).last
                        if close_button.is_visible():
                            close_button.click(force=True)
                        else:
                            page.keyboard.press("Escape")
                        page.wait_for_timeout(1_000)
                        break
                except Exception:
                    try:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1_000)
                    except Exception:
                        pass

            total_blocks = len(blocks)
            log(f"📦 Đang đẩy GÓI CHỨA {total_blocks} CÂU lên máy chủ kết xuất...")
            textarea = page.locator("textarea, [contenteditable='true']").first
            textarea.wait_for(state="visible", timeout=10_000)
            textarea.click(force=True)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.wait_for_timeout(300)
            textarea.fill("\n\n".join(block["text"] for block in blocks))
            page.wait_for_timeout(2_000)

            generate_button = page.locator(
                "button:has-text('Tiếp tục'), button:has-text('Tạo audio'), "
                "button:has-text('Tạo')"
            ).first
            try:
                generate_button.click(timeout=5_000, force=True)
            except Exception as exc:
                raise RuntimeError(f"Lỗi ở bước điền Text hàng loạt: {exc}") from exc
            page.wait_for_timeout(3_000)

            for index, block in enumerate(blocks):
                log(f"👉 Đang thu hoạch câu {index + 1}/{total_blocks}...")
                if harvest_card(block["text"]):
                    chunk_path = os.path.join(temp_chunks_dir, f"chunk_{index}.wav")
                    try:
                        os.replace(raw_wav_path, chunk_path)
                    except Exception:
                        shutil.copy(raw_wav_path, chunk_path)
                    block["status"] = "success"
                    block["path"] = chunk_path
                else:
                    log(
                        f"⚠️ Câu {index + 1} bị lỗi/mất thẻ. "
                        "Đã GHI NỢ để chữa lành sau."
                    )
                    block["status"] = "failed"
                if progress_callback:
                    progress_callback(int(20 + ((index + 1) / total_blocks) * 50))

            for healing_round in range(1, 4):
                failed_indices = [
                    index
                    for index, block in enumerate(blocks)
                    if block["status"] == "failed"
                ]
                if not failed_indices:
                    break
                log(
                    f"🔄 BẮT ĐẦU VÒNG CHỮA LÀNH {healing_round}/3 "
                    f"(Đang nợ {len(failed_indices)} câu)..."
                )
                for index in failed_indices:
                    block = blocks[index]
                    log(f"🚑 Đang chữa lành câu {index + 1}...")
                    try:
                        textarea = page.locator(
                            "textarea, [contenteditable='true']"
                        ).first
                        textarea.click(force=True)
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.wait_for_timeout(300)
                        textarea.fill(block["text"])
                        page.wait_for_timeout(1_000)
                        page.locator(
                            "button:has-text('Tiếp tục'), "
                            "button:has-text('Tạo audio'), button:has-text('Tạo')"
                        ).first.click(timeout=3_000, force=True)
                        page.wait_for_timeout(4_000)
                        if harvest_card(block["text"]):
                            chunk_path = os.path.join(
                                temp_chunks_dir, f"chunk_{index}.wav"
                            )
                            try:
                                os.replace(raw_wav_path, chunk_path)
                            except Exception:
                                shutil.copy(raw_wav_path, chunk_path)
                            block["status"] = "success"
                            block["path"] = chunk_path
                            log(f"✅ Đã chữa lành thành công câu {index + 1}!")
                        else:
                            log(
                                f"⚠️ Chữa lành câu {index + 1} thất bại "
                                f"(Vòng {healing_round})."
                            )
                    except Exception as healing_error:
                        log(f"⚠️ Lỗi thao tác khi chữa lành: {healing_error}")

            final_failed = [
                index + 1
                for index, block in enumerate(blocks)
                if block["status"] == "failed"
            ]
            if final_failed:
                failed_text = ", ".join(map(str, final_failed))
                return False, (
                    "Đã thử tự chữa lành 3 vòng nhưng hệ thống vẫn không thể đọc "
                    "được các câu sau:\n"
                    f"👉 Câu số: {failed_text}\n\n"
                    "Lý do có thể: Nội dung quá dài hoặc chứa ký tự cấm của Nền "
                    "tảng. Vui lòng sửa lại nội dung các câu này!"
                )

            log("🔄 Đang trộn âm thanh và đồng bộ vị trí Timeline...")
            timeline = _merge_original_audio(
                blocks, session_mp3_path, req_type, is_preview, speed, sync_timeline, mode_pro
            )
            if timeline_out is not None:
                timeline_out.extend(timeline)
            return True, "Thành công! Tệp âm thanh MASTER đã sẵn sàng."
    except Exception as exc:
        logger.exception("Vivibe PREMIUM workflow failed")
        return False, f"Lỗi System API: {exc}"
    finally:
        try:
            if os.path.exists(raw_wav_path):
                os.remove(raw_wav_path)
        except Exception:
            pass
        try:
            if os.path.exists(temp_chunks_dir):
                shutil.rmtree(temp_chunks_dir)
        except Exception:
            pass
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass


def run_premium_engine(
    text,
    voice_id,
    username,
    password,
    is_headless=True,
    speed="1.0",
    is_preview=False,
    mp3_path="",
    req_type="text",
    sync_timeline=True,
    mode_pro=False,
    progress_callback=None,
    log_callback=None,
):
    """Compatibility entry point matching CapAssistant's original signature."""
    return _run_premium_engine(
        text=text,
        voice_id=voice_id,
        username=username,
        password=password,
        is_headless=is_headless,
        speed=speed,
        is_preview=is_preview,
        mp3_path=mp3_path,
        req_type=req_type,
        sync_timeline=sync_timeline,
        mode_pro=mode_pro,
        progress_callback=progress_callback,
        log_callback=log_callback,
    )


def synthesize_batch(
    items: Sequence[tuple[str, str]],
    voice: str,
    progress_callback: Callable[[int, str], None] | None = None,
    master_output_path: str | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> bool | dict:
    """Run TubeCraft steps through one exact CapAssistant Vivibe session."""
    jobs = [
        (re.sub(r"\s*\n+\s*", " ", str(text)).strip(), os.fspath(path))
        for text, path in items
        if str(text).strip()
    ]
    if not jobs:
        return True

    username, password = load_credentials()
    if not username or not password:
        raise RuntimeError("Chưa cấu hình tài khoản Vivibe trong Cài đặt.")

    first_output_dir = os.path.dirname(os.path.abspath(jobs[0][1]))
    os.makedirs(first_output_dir, exist_ok=True)
    remove_master = master_output_path is None
    if remove_master:
        descriptor, master_output_path = tempfile.mkstemp(
            prefix=".vivibe_master_", suffix=".mp3", dir=first_output_dir
        )
        os.close(descriptor)
        os.remove(master_output_path)

    progress_messages = {
        5: "Đang mở Vivibe...",
        10: "Đang đăng nhập Vivibe...",
        15: "Đã đăng nhập Vivibe.",
    }

    def report(percent: int) -> None:
        if progress_callback:
            message = progress_messages.get(percent, f"Vivibe: {percent}%")
            progress_callback(percent, message)

    def report_log(message: str) -> None:
        logger.info(message)
        if log_callback:
            log_callback(message)

    srt, _slots, groups = build_capassistant_srt([text for text, _ in jobs])
    caption_timeline: list[dict] = []
    try:
        ok, message = _run_premium_engine(
            text=srt,
            voice_id=voice,
            username=username,
            password=password,
            is_headless=True,
            speed="1.0",
            is_preview=False,
            mp3_path=master_output_path,
            req_type="srt",
            sync_timeline=True,
            progress_callback=report,
            log_callback=report_log,
            timeline_out=caption_timeline,
        )
        if not ok:
            raise RuntimeError(message)
        ranges = []
        if caption_timeline and os.path.isfile(master_output_path):
            AudioSegment = _audio_segment()
            master = AudioSegment.from_file(master_output_path)
            offset = 0
            for (_text, destination), group in zip(jobs, groups):
                captions = caption_timeline[offset : offset + len(group)]
                if len(captions) != len(group):
                    raise RuntimeError("Timeline Vivibe không khớp số câu đã gửi.")
                start, end = captions[0]["start"], captions[-1]["end"]
                temp_path = os.path.abspath(os.fspath(destination)) + ".tmp"
                master[start:end].export(temp_path, format="mp3", bitrate="192k")
                _replace_with_retry(temp_path, os.path.abspath(os.fspath(destination)))
                ranges.append({"start": start / 1000, "end": end / 1000})
                offset += len(group)
        if progress_callback:
            progress_callback(95, "Vivibe đã tạo xong audio.")
        return {"ranges": ranges} if ranges else True
    finally:
        if remove_master and master_output_path:
            try:
                os.remove(master_output_path)
            except FileNotFoundError:
                pass
