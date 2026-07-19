"""
TubeCraft — TTS Audio Engine.
Generates per-step audio using edge-tts and captures word-level timing (WordBoundary).
"""
import os
import json
import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("TubeCraft.AudioEngine")

# Bản đóng gói là GUI KHÔNG có console → mỗi ffmpeg/ffprobe sinh ra sẽ bung một
# cửa sổ đen đè lên app. CREATE_NO_WINDOW chặn hẳn (xem thêm video_encoder.py).
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


async def _exec(*args, **kwargs):
    """asyncio.create_subprocess_exec + ẩn cửa sổ console trên Windows."""
    if os.name == "nt":
        kwargs.setdefault("creationflags", _CREATE_NO_WINDOW)
    return await asyncio.create_subprocess_exec(*args, **kwargs)


def _find_executable(name: str) -> str:
    """Find bundled or explicitly configured FFmpeg tools, then PATH."""
    import shutil
    from config import BASE_DIR

    for directory in (BASE_DIR / "tools", BASE_DIR / "ffmpeg" / "bin", BASE_DIR):
        exe_path = directory / (f"{name}.exe" if os.name == "nt" else name)
        if exe_path.is_file():
            return str(exe_path)
    configured = os.environ.get("TUBECRAFT_FFMPEG_DIR", "")
    if configured:
        exe_path = os.path.join(configured, f"{name}.exe" if os.name == "nt" else name)
        if os.path.isfile(exe_path):
            return exe_path
    found = shutil.which(name)
    if found:
        if "miniconda3" in found.lower():
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                if not path_dir or "miniconda3" in path_dir.lower():
                    continue
                exe_path = os.path.join(path_dir, f"{name}.exe")
                if os.path.exists(exe_path):
                    return exe_path
        return found
    return name


async def _get_audio_duration(filepath: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        ffprobe_exe = _find_executable("ffprobe")
        proc = await _exec(
            ffprobe_exe, "-v", "quiet", "-print_format", "json", "-show_format", filepath,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode("utf-8", errors="replace"))
        return float(data.get("format", {}).get("duration", 0))
    except Exception as e:
        logger.warning(f"ffprobe failed for {filepath}: {e}")
        return 3.0


def _normalize_word(w: str) -> str:
    """Normalize a word for matching: lowercase, strip punctuation, remove thousands separators."""
    import re
    w = w.lower().strip()
    w = re.sub(r"[.,;:!?\"'()«»]", "", w)
    w = w.replace(".", "").replace(",", "")  # remove thousand separators
    return w


def _make_communicate(text: str, voice: str):
    """edge-tts >= 7.0 mặc định trả SentenceBoundary, KHÔNG còn WordBoundary.

    Renderer dựa vào timing từng chữ để highlight theo giọng đọc; thiếu nó thì
    chữ không chạy theo lời. Phải yêu cầu boundary='WordBoundary' tường minh.
    Bản edge-tts cũ chưa có tham số này → fallback về chữ ký cũ.
    """
    import edge_tts
    try:
        return edge_tts.Communicate(text, voice, boundary="WordBoundary")
    except TypeError:
        return edge_tts.Communicate(text, voice)


async def _generate_edge_tts_with_words(text: str, voice: str, output_path: str):
    """
    Generate audio using edge-tts and capture WordBoundary events.
    Returns (success: bool, words: list[{word, start, end}])
    """
    try:
        communicate = _make_communicate(text, voice)

        word_boundaries = []
        sentence_boundaries = []
        audio_chunks = []

        async for chunk in communicate.stream():
            ctype = chunk["type"]
            if ctype == "audio":
                audio_chunks.append(chunk["data"])
            elif ctype in ("WordBoundary", "SentenceBoundary"):
                # offset is in 100-nanosecond units, duration too
                start_sec = chunk["offset"] / 10_000_000.0
                dur_sec   = chunk["duration"] / 10_000_000.0
                item = {
                    "word":  chunk["text"],
                    "norm":  _normalize_word(chunk["text"]),
                    "start": round(start_sec, 3),
                    "end":   round(start_sec + dur_sec, 3),
                }
                (word_boundaries if ctype == "WordBoundary"
                 else sentence_boundaries).append(item)

        if not audio_chunks:
            return False, []

        with open(output_path, "wb") as f:
            for c in audio_chunks:
                f.write(c)

        # Không có timing từng chữ (giọng/bản edge-tts không hỗ trợ) → dùng tạm
        # timing từng câu, còn hơn không có gì.
        words = word_boundaries or sentence_boundaries
        if not word_boundaries and sentence_boundaries:
            logger.warning("edge-tts không trả WordBoundary — dùng SentenceBoundary "
                           "(chữ highlight theo câu, không theo từng chữ).")

        return os.path.getsize(output_path) > 100, words

    except Exception as e:
        logger.error(f"edge-tts stream error: {e}")
        return False, []


async def _generate_edge_tts(text: str, voice: str, output_path: str) -> bool:
    """Generate audio using edge-tts (simple, no word boundaries)."""
    success, _ = await _generate_edge_tts_with_words(text, voice, output_path)
    return success


def _generate_gtts_sync(text: str, output_path: str, lang: str) -> bool:
    """Generate an MP3 with gTTS; called in a worker thread by the async engine."""
    from gtts import gTTS

    language = (lang or "vi").split("-")[0]
    gTTS(text=text, lang=language).save(output_path)
    return os.path.isfile(output_path) and os.path.getsize(output_path) > 100


async def _generate_tts_internal(text: str, voice: str, output_path: str,
                                 engine: str = "edge", lang: str = "vi"):
    """
    Try internal TTS API first, fallback to direct edge-tts.
    Returns (success: bool, words: list)
    """
    if engine == "edge":
        return await _generate_edge_tts_with_words(text, voice, output_path)

    if engine == "gtts":
        ok = await asyncio.to_thread(_generate_gtts_sync, text, output_path, lang)
        return ok, []

    if engine == "deepgram":
        # /v1/speak chỉ trả audio → lấy timing từng chữ bằng chính STT của
        # Deepgram (xem core/tts_deepgram.py). Không có tiếng Việt.
        from core.tts_deepgram import synthesize as dg_synth
        return await asyncio.to_thread(dg_synth, text, voice, output_path,
                                       True, lang)

    if engine == "vivibe":
        from core.tts_vivibe import synthesize_batch
        ok = await asyncio.to_thread(synthesize_batch, [(text, output_path)], voice)
        return ok and os.path.getsize(output_path) > 100, []

    if engine == "everai":
        # Gọi thẳng engine EverAI; không cần dịch vụ TTS trung gian.
        # EverAI không trả word boundaries → words=[] (timing theo step).
        from core.tts_everai import synthesize
        result = await asyncio.to_thread(synthesize, text, voice, output_path)
        ok = result.get("status") == "success" and \
            os.path.getsize(output_path) > 100
        return ok, []

    # Try vibevoice/everai via internal TTS API
    try:
        import httpx, shutil
        # EverAI is slower (cloud+poll), give it more time
        poll_timeout = 360 if engine == "everai" else 180
        # Terminal success statuses (tts_routes sets "success" not "done")
        SUCCESS_STATUSES = {"success", "done"}
        ERROR_STATUSES   = {"error", "failed"}
        # In-progress statuses we should keep waiting
        WAIT_STATUSES    = {"running", "processing", "loading_model", "stitching", "pending", "queued"}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "http://localhost:5295/api/v1/tts/synthesize",
                json={"text": text, "voice": voice, "engine": engine, "preprocess_prompt": False},
            )
            if resp.status_code != 200:
                err_msg = f"HTTP {resp.status_code}"
                try:
                    err_msg += f": {resp.json().get('message')}"
                except Exception:
                    err_msg += f": {resp.text}"
                logger.warning(f"TTS synthesize failed: {err_msg}")
                raise RuntimeError(err_msg)

            data = resp.json()
            task_id = data.get("task_id")
            if not task_id:
                err_msg = data.get("message") or f"TTS synthesize returned no task_id: {data}"
                logger.warning(err_msg)
                raise RuntimeError(err_msg)

            logger.info(f"[audio_engine] TTS task {task_id} started (engine={engine})")

            for poll_n in range(poll_timeout):
                await asyncio.sleep(1)
                status_resp = await client.get(f"http://localhost:5295/api/v1/tts/status/{task_id}")
                if status_resp.status_code != 200:
                    continue

                sdata = status_resp.json()
                task_status = sdata.get("status", "")

                if task_status in SUCCESS_STATUSES:
                    result = sdata.get("result", {})
                    logger.info(f"[audio_engine] Task {task_id} done. result keys: {list(result.keys())}")

                    # TTS routes store the output file path directly in result["output"]
                    file_path = result.get("output") or result.get("output_path")
                    if file_path and os.path.isfile(file_path):
                        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                        shutil.copy2(file_path, output_path)
                        logger.info(f"[audio_engine] Copied {file_path} → {output_path}")
                        return os.path.getsize(output_path) > 100, []

                    # Fallback: some engines return relative audio_url
                    audio_url = result.get("audio_url", "")
                    if audio_url:
                        dl_resp = await client.get(f"http://localhost:5295{audio_url}")
                        if dl_resp.status_code == 200:
                            with open(output_path, "wb") as f:
                                f.write(dl_resp.content)
                            return True, []

                    logger.warning(f"[audio_engine] Task done but no file found. result={result}")
                    break

                elif task_status in ERROR_STATUSES:
                    err_res = sdata.get("result") or {}
                    err_msg = err_res.get("message") if isinstance(err_res, dict) else str(err_res)
                    if not err_msg:
                        err_msg = sdata.get("message") or "Unknown TTS engine error"
                    logger.warning(f"[audio_engine] TTS task {task_id} failed: {err_msg}")
                    raise RuntimeError(err_msg)

                elif task_status in WAIT_STATUSES:
                    if poll_n % 10 == 0:
                        logger.info(f"[audio_engine] Waiting for task {task_id}: {task_status} ({poll_n}s)")
                    continue
                else:
                    # Unknown status — keep waiting
                    logger.debug(f"[audio_engine] Unknown status '{task_status}' for {task_id}")

            return False, []

    except Exception as e:
        if engine != "edge":
            # Do not fallback to edge-tts if it's a dedicated engine that failed
            logger.error(f"Internal TTS API failed ({engine}): {e}")
            raise e
        logger.warning(f"Internal TTS API failed ({engine}): {e}, falling back to edge-tts")

    # Fallback to edge-tts with word boundaries
    return await _generate_edge_tts_with_words(text, voice, output_path)


async def _merge_audio_files(audio_files: list, output_path: str, gaps: list = None):
    """Merge multiple audio files with optional gaps using ffmpeg."""
    if not audio_files:
        return

    if len(audio_files) == 1:
        import shutil
        shutil.copy2(audio_files[0], output_path)
        if os.path.getsize(output_path) <= 100:
            raise RuntimeError("Audio merge tạo file rỗng.")
        return

    inputs = []
    filter_parts = []
    idx = 0

    for i, af in enumerate(audio_files):
        inputs.extend(["-i", af])
        filter_parts.append(f"[{idx}:a]")
        idx += 1

        if i < len(audio_files) - 1:
            gap_dur = 0.5
            if gaps and i < len(gaps):
                gap_dur = gaps[i]
            if gap_dur > 0:
                inputs.extend(["-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=24000:duration={gap_dur}"])
                filter_parts.append(f"[{idx}:a]")
                idx += 1

    filter_str = "".join(filter_parts) + f"concat=n={len(filter_parts)}:v=0:a=1[out]"

    ffmpeg_exe = _find_executable("ffmpeg")
    cmd = [ffmpeg_exe, "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "128k",
        output_path
    ]

    proc = await _exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        detail = stderr.decode("utf-8", "replace")[-300:]
        raise RuntimeError(f"Audio merge failed: {detail}")
    if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 100:
        raise RuntimeError("Audio merge không tạo được file hợp lệ.")


def _valid_audio_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 100
    except OSError:
        return False


def _activate_audio_bundle(staging_dir: Path, output_dir: Path) -> None:
    """Replace a whole audio bundle without exposing partial step files.

    The previous complete bundle stays available if synthesis fails.  This is
    safe because callers invalidate it first whenever script/voice inputs
    change; a manual re-try for unchanged inputs does not destroy good media.
    """
    backup_dir = output_dir.parent / f".{output_dir.name}.previous-{uuid.uuid4().hex}"
    moved_old = False
    try:
        if output_dir.exists() or output_dir.is_symlink():
            os.replace(output_dir, backup_dir)
            moved_old = True
        os.replace(staging_dir, output_dir)
    except Exception:
        if moved_old and backup_dir.exists() and not output_dir.exists():
            os.replace(backup_dir, output_dir)
        raise
    if backup_dir.exists() or backup_dir.is_symlink():
        shutil.rmtree(backup_dir, ignore_errors=True)


async def generate_tts_for_script(
    script: dict,
    output_dir: str,
    voice: str = "vi-VN-HoaiMyNeural",
    tts_engine: str = "edge",
    lang: str = "vi",
    progress_callback: Optional[Callable] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Generate a complete TTS bundle in staging, then atomically activate it."""
    final_dir = Path(output_dir)
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    # Vivibe creates further temporary files below this directory.  Do not
    # include the (often long) final job name here or Windows can exceed MAX_PATH.
    staging_dir = final_dir.parent / f".tts-{uuid.uuid4().hex}"
    try:
        result = await _generate_tts_for_script_into(
            script,
            str(staging_dir),
            voice=voice,
            tts_engine=tts_engine,
            lang=lang,
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
        if not _valid_audio_file(staging_dir / "full_audio.mp3"):
            raise RuntimeError("TTS không tạo được audio bundle hợp lệ.")
        _activate_audio_bundle(staging_dir, final_dir)
        return result
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


async def _generate_tts_for_script_into(
    script: dict,
    output_dir: str,
    voice: str = "vi-VN-HoaiMyNeural",
    tts_engine: str = "edge",
    lang: str = "vi",                 # Deepgram cần biết ngôn ngữ để lấy word timing
    progress_callback: Optional[Callable] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Generate TTS audio for each step and build timing map with word-level boundaries."""
    os.makedirs(output_dir, exist_ok=True)
    merged_path = os.path.join(output_dir, "full_audio.mp3")
    steps = script.get("steps", [])
    total = len(steps)
    vivibe_master_ready = False
    vivibe_slots = {}
    vivibe_ranges = {}

    if tts_engine == "vivibe":
        from core.tts_vivibe import build_capassistant_srt, synthesize_batch
        batch = []
        for index, step in enumerate(steps):
            text = str(step.get("voice_text") or "").strip()
            if text:
                step_id = step.get("id", index + 1)
                batch.append((text, os.path.join(output_dir, f"step_{step_id:03d}.mp3")))
        _, slots, _groups = build_capassistant_srt([text for text, _path in batch])
        vivibe_slots = {
            step.get("id", index + 1): slot
            for (index, step), slot in zip(
                ((index, step) for index, step in enumerate(steps) if str(step.get("voice_text") or "").strip()),
                slots,
            )
        }
        if log_callback:
            vivibe_result = await asyncio.to_thread(
                synthesize_batch, batch, voice, progress_callback, merged_path, log_callback
            )
        else:
            vivibe_result = await asyncio.to_thread(
                synthesize_batch, batch, voice, progress_callback, merged_path
            )
        if isinstance(vivibe_result, dict):
            ranges = vivibe_result.get("ranges") or []
            for (index, step), timing in zip(
                ((index, step) for index, step in enumerate(steps) if str(step.get("voice_text") or "").strip()),
                ranges,
            ):
                try:
                    start, end = float(timing["start"]), float(timing["end"])
                except (KeyError, TypeError, ValueError):
                    continue
                if end >= start:
                    vivibe_ranges[step.get("id", index + 1)] = (start, end)
        vivibe_master_ready = (
            bool(batch)
            and len(batch) == len(steps)
            and os.path.isfile(merged_path)
            and os.path.getsize(merged_path) > 100
        )

    timing_steps = []
    audio_files = []
    current_offset = 0.0
    # CapAssistant's PREMIUM engine inserts exactly 200 ms between text blocks.
    GAP = 0.2 if tts_engine == "vivibe" else 0.0

    for i, step in enumerate(steps):
        voice_text = step.get("voice_text", "").strip()
        step_id = step.get("id", i + 1)

        if progress_callback:
            pct = int((i / total) * 90)
            progress_callback(pct, f"Generating audio step {i+1}/{total}...")

        if not voice_text:
            duration = 2.0
            # Generate silent audio file so merged audio stays in sync with timing
            audio_filename = f"step_{step_id:03d}.mp3"
            audio_path = os.path.join(output_dir, audio_filename)
            try:
                ffmpeg_exe = _find_executable("ffmpeg")
                silence_cmd = [
                    ffmpeg_exe, "-y", "-f", "lavfi", "-i",
                    f"anullsrc=channel_layout=mono:sample_rate=24000:duration={duration}",
                    "-c:a", "libmp3lame", "-b:a", "32k", audio_path
                ]
                proc = await _exec(
                    *silence_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                if proc.returncode == 0 and os.path.exists(audio_path):
                    audio_files.append(audio_path)
            except Exception as e:
                logger.warning(f"Failed to create silence for step {step_id}: {e}")

            timing_steps.append({
                "id": step_id,
                "start": round(current_offset, 3),
                "end": round(current_offset + duration, 3),
                "audio": audio_filename,
                "duration": duration,
                "words": [],
            })
            current_offset += duration + GAP
            continue

        audio_filename = f"step_{step_id:03d}.mp3"
        audio_path = os.path.join(output_dir, audio_filename)

        if i > 0 and tts_engine != "vivibe":
            await asyncio.sleep(0.3)  # Tiny rate-limit prevention delay

        success = tts_engine == "vivibe" and os.path.isfile(audio_path) and os.path.getsize(audio_path) > 100
        word_boundaries = []
        last_error = "Vivibe không trả audio." if tts_engine == "vivibe" else "Unknown error"
        if tts_engine != "vivibe":
            MAX_TRIES = 5
            for attempt in range(MAX_TRIES):
                try:
                    success, word_boundaries = await _generate_tts_internal(
                        voice_text, voice, audio_path, tts_engine, lang)
                    if success and os.path.exists(audio_path) and os.path.getsize(audio_path) > 100:
                        break
                except Exception as ex:
                    last_error = str(ex)
                    logger.warning(f"TTS attempt {attempt+1}/{MAX_TRIES} failed for step {step_id}: {ex}")
                if attempt < MAX_TRIES - 1:
                    # backoff tăng dần (1.5s → 6s) để edge-tts hồi phục lỗi tạm thời
                    await asyncio.sleep(min(1.5 * (attempt + 1), 6.0))
            else:
                success = False

        if success and os.path.exists(audio_path):
            duration = await _get_audio_duration(audio_path)
            if duration < 0.5:
                duration = max(len(voice_text) * 0.08, 2.0)
        else:
            raise RuntimeError(f"TTS generation failed for step {step_id}: {last_error}")

        # Shift word boundaries by current_offset so they're absolute times
        shifted_words = []
        for wb in word_boundaries:
            shifted_words.append({
                "word": wb["word"],
                "norm": wb["norm"],
                "start": round(wb["start"] + current_offset, 3),
                "end":   round(wb["end"] + current_offset, 3),
            })

        if tts_engine == "vivibe":
            start, end = vivibe_ranges.get(step_id, (None, None))
            if start is None:
                start_ms, end_ms = vivibe_slots[step_id]
                start, end = start_ms / 1000, end_ms / 1000
        else:
            start, end = current_offset, current_offset + duration
        timing_steps.append({
            "id": step_id,
            "start": round(start, 3),
            "end": round(end, 3),
            "audio": audio_filename,
            "duration": round(end - start, 3),
            "words": shifted_words,
        })

        if audio_path:
            audio_files.append(audio_path)

        current_offset = end if tts_engine == "vivibe" else end + GAP

    # current_offset includes the post-step increment; the final audio has no
    # trailing gap, matching CapAssistant's pydub merge loop.
    total_duration = round(
        max(0.0, current_offset - (GAP if timing_steps else 0.0)), 3
    )

    # Merge all audio into one file
    if audio_files:
        if progress_callback:
            progress_callback(92, "Merging audio files...")
        if tts_engine == "vivibe":
            if not vivibe_master_ready:
                from core.tts_vivibe import merge_step_audio_files

                await asyncio.to_thread(
                    merge_step_audio_files, audio_files, merged_path
                )
        else:
            gaps = [GAP] * (len(audio_files) - 1)
            await _merge_audio_files(audio_files, merged_path, gaps=gaps)

    if tts_engine == "vivibe" and vivibe_master_ready:
        total_duration = round(await _get_audio_duration(merged_path), 3)
        if timing_steps and not vivibe_ranges:
            timing_steps[-1]["end"] = total_duration
            timing_steps[-1]["duration"] = round(total_duration - timing_steps[-1]["start"], 3)

    timing_map = {
        "steps": timing_steps,
        "total_duration": total_duration,
        "merged_audio": "audio/full_audio.mp3" if os.path.exists(merged_path) else None,
        "voice": voice,
        "tts_engine": tts_engine,
    }

    if progress_callback:
        progress_callback(100, "Audio generation complete!")

    logger.info(f"TTS complete: {len(timing_steps)} steps, {total_duration:.1f}s total")
    return timing_map


async def generate_tts_for_step(
    step_id: int,
    voice_text: str,
    output_dir: str,
    voice: str = "vi-VN-HoaiMyNeural",
    tts_engine: str = "edge",
    lang: str = "vi",
) -> tuple[bool, float, list]:
    """Generate TTS audio for a single step. Returns (success, duration, word_boundaries)."""
    os.makedirs(output_dir, exist_ok=True)
    audio_filename = f"step_{step_id:03d}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)
    
    if not voice_text:
        duration = 2.0
        try:
            ffmpeg_exe = _find_executable("ffmpeg")
            silence_cmd = [
                ffmpeg_exe, "-y", "-f", "lavfi", "-i",
                f"anullsrc=channel_layout=mono:sample_rate=24000:duration={duration}",
                "-c:a", "libmp3lame", "-b:a", "32k", audio_path
            ]
            proc = await _exec(
                *silence_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if proc.returncode == 0 and os.path.exists(audio_path):
                return True, duration, []
        except Exception as e:
            logger.warning(f"Failed to create silence for step {step_id}: {e}")
        return False, 0.0, []

    success = False
    word_boundaries = []
    last_error = "Unknown error"
    for attempt in range(3):
        try:
            success, word_boundaries = await _generate_tts_internal(
                voice_text, voice, audio_path, tts_engine, lang)
            if success and os.path.exists(audio_path) and os.path.getsize(audio_path) > 100:
                break
        except Exception as ex:
            last_error = str(ex)
            logger.warning(f"TTS single step attempt {attempt+1} failed for step {step_id}: {ex}")
        if attempt < 2:
            await asyncio.sleep(0.8 * (attempt + 1))
            
    if success and os.path.exists(audio_path):
        duration = await _get_audio_duration(audio_path)
        return True, round(duration, 3), word_boundaries
        
    raise RuntimeError(f"TTS single step generation failed: {last_error}")
