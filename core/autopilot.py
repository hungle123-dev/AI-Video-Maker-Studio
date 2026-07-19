"""core/autopilot.py — Pipeline tạo tự động: ý tưởng → cả series video.

Người dùng nhập một ý tưởng, AI tự lo phần còn lại:
  1. Sinh dàn ý series (project + danh sách tập).
  2. Tạo project.
  3. Với từng tập: tạo lesson → sinh kịch bản đầy đủ → lưu.
  4. (tuỳ chọn) Xếp hàng TTS + Render cho từng tập.

Chạy trong thread nền, tiến trình lưu vào core.jobs (bền vững, theo dõi được
ở tab Hàng đợi Render). Phần media đẩy sang worker asyncio của render_service.
"""
import logging, threading
from core import jobs
from core.project_store import project_store
from core.script_generator import generate_outline, generate_lesson_script, QuotaWaitError; logger = logging.getLogger("TubeCraft.AutoPilot")
def run_autopilot(idea: str, lesson_count: int=5, *, aspect_ratio: str="9:16", lang: str="vi", ai_provider: str="gemini", ai_model: str="", tts_engine: str="edge", voice: str="vi-VN-HoaiMyNeural", min_steps: int=12, art_style: str="liquidglass", title_color: str="", font_family: str="", bg: str="", template: str="", auto_media: bool=False, subtitle_enabled: bool=True, subtitle_preset: str="", subtitle_font_scale: float=1.0, subtitle_y_pct=None) -> dict:
    job = jobs.create_job("autopilot", {"idea": idea[:120], "lesson_count": lesson_count}); style_opts = {"art_style": art_style, "title_color": title_color, "font_family": font_family, "bg": bg, "template": template, "subtitle_enabled": subtitle_enabled, "subtitle_preset": subtitle_preset, "subtitle_font_scale": subtitle_font_scale, "subtitle_y_pct": subtitle_y_pct}; t = threading.Thread(target=_worker, args=(job["id"], idea, lesson_count, aspect_ratio, lang, ai_provider, ai_model, tts_engine, voice, min_steps, style_opts, auto_media), daemon=True); t.start()
    return job

def cancel_autopilot(job_id: str) -> None:
    jobs.update_job(job_id, cancel=True)

def add_ai_lessons(project_id: str, idea: str, count: int=1, auto_media: bool=False) -> dict:
    job = jobs.create_job("add_lessons", {"project_id": project_id}); t = threading.Thread(target=_add_worker, args=(job["id"], project_id, idea, count, auto_media), daemon=True); t.start()
    return job

def _add_worker(job_id, pid, idea, count, auto_media):
    jobs.update_job(job_id, status="running", progress=3, message="AI đang lên ý cho các bài mới...")
    try:
        project = project_store.get_project(pid)
        if not project:
            raise RuntimeError("Không tìm thấy project.")
        provider = project.get("ai_provider", "")
        model = project.get("ai_model", "")
        min_steps = int(project.get("min_steps", 12))
        lang = project.get("lang", "vi")
        idea = (idea or "").strip()
        if not idea:
            jobs.update_job(job_id, message="AI đang xem các bài cũ để viết tiếp...")
            existing = project_store.list_lessons(pid)
            titles = [l.get("title", "") for l in existing if l.get("title")]
            listing = "\n".join((f"- {t}" for t in titles)) or "(chưa có bài nào)"
            idea = f"Đây là series '{project.get("title", "")}'. Các bài ĐÃ CÓ:\n{listing}\n\nHãy viết thêm {count} bài MỚI nối tiếp hợp lý, đào sâu/mở rộng chủ đề series, KHÔNG trùng lặp các bài đã có ở trên."
        outline = generate_outline(idea, count, lang=lang, provider=provider, model=model)
        items = outline.get("lessons", [])[:count]
        subject = outline.get("subject", "general")
        if not items:
            raise RuntimeError("AI không trả về bài nào.")
        from collections import Counter
        scene_counter = Counter()
        olds = project_store.list_lessons(pid)
        base_n = len(olds)
        for old in olds:
            full = project_store.get_lesson(pid, old["id"]) or {}
            scene_counter.update((full.get("script") or {}).get("scenes_used") or [])
        created = []
        n = len(items)
        for i, item in enumerate(items):
            if _is_cancelled(job_id):
                jobs.update_job(job_id, status="cancelled", message=f"⏹ Đã dừng — thêm {len(created)}/{n} bài.", result={"project_id": pid, "lessons": created})
                return None
            title = item.get("title", f"Bài mới {i + 1}")
            brief = item.get("brief", title)
            jobs.update_job(job_id, progress=8 + int(i / max(n, 1) * 80), message=f"Viết kịch bản {i + 1}/{n}: {title[:48]}...")
            lesson = project_store.create_lesson(pid, title)
            script = _gen_script_retry(f"{title}\n{brief}", subject, min_steps, lang, provider, model, project.get("template") or "", label=f"Bài mới {i + 1}", seed=len(scene_counter) + i, avoid=_overused(scene_counter), note=(lambda m: jobs.update_job(job_id, message=m)), series_info={"index": base_n + i + 1, "total": base_n + n})
            if script is not None:
                project_store.save_script(pid, lesson["id"], script)
                created.append(lesson["id"])
                scene_counter.update(script.get("scenes_used") or [])
                continue
            project_store.update_lesson_meta(pid, lesson["id"], status="error")
        if auto_media and created and not _is_cancelled(job_id):
            from core.render_service import queue_full_pipeline
            for lid in created:
                queue_full_pipeline(pid, lid)
        msg = f"✅ Đã thêm {len(created)}/{n} bài vào series."
        if auto_media and created:
            msg += " Đang render (xem Hàng đợi)."
        jobs.update_job(job_id, status="done", progress=100, message=msg, result={"project_id": pid, "lessons": created})
    except Exception as e:
        logger.exception("Add lessons lỗi")
        jobs.update_job(job_id, status="error", message=str(e)[:300])

def _is_cancelled(job_id: str) -> bool:
    j = jobs.get_job(job_id)
    return bool(j and j.get("cancel"))

def _gen_script_retry(content, subject, min_steps, lang, provider, model, template, label="Tập", tries=2, seed=None, avoid=None, note=None, part_info=None, series_info=None):
    import time
    _note = note or (lambda m: None)
    last = ""
    for attempt in range(tries):
        try:
            script, _errs = generate_lesson_script(content, subject=subject, step_count=min_steps, lang=lang, provider=provider, model=model, template=template or "", variety_seed=seed, avoid_effects=avoid, part_info=part_info, series_info=series_info)
            if script and script.get("steps"):
                return script
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
        except QuotaWaitError as ex:
            mins = max(1, ex.reset_seconds // 60)
            logger.warning(f"{label}: mọi provider đều cạn quota (hồi sau ~{mins} phút) — bỏ qua.")
            _note(f"⚠️ {label}: mọi AI đều cạn quota (hồi sau ~{mins} phút) — bỏ qua tập này, lát bấm 'Viết kịch bản AI' tạo lại.")
            return None
        except Exception as ex:
            last = str(ex)
            logger.warning(f"{label} thử {attempt + 1}/{tries} lỗi: {ex}")
            if attempt < tries - 1:
                _note(f"⚠️ {label} lỗi ({str(ex)[:90]}) — thử lại {attempt + 2}/{tries}...")
                time.sleep(1.5 * (attempt + 1))
    logger.warning(f"{label} bỏ cuộc sau {tries} lần. Lỗi cuối: {last}")
    _note(f"❌ {label} bỏ cuộc sau {tries} lần: {last[:120]}")
    return None

def _overused(counter, min_count=2, cap=8):
    return [k for k, v in counter.most_common(cap * 2) if v >= min_count][:cap]

def _worker(job_id, idea, lesson_count, aspect_ratio, lang, ai_provider, ai_model, tts_engine, voice, min_steps, style_opts, auto_media):
    jobs.update_job(job_id, status="running", progress=2, message="AI đang lên khung series...")
    try:
        plan_steps = None
        if lesson_count == 1 and int(min_steps) <= 0:
            from core.script_generator import generate_long_plan
            jobs.update_job(job_id, progress=4, message="AI đang lên dàn ý video dài (tự quyết số step)...")
            plan = generate_long_plan(idea, lang=lang, provider=ai_provider, model=ai_model)
            plan_steps = plan.get("steps") or []
            outline = {"project_title": plan.get("title", "Video dài"), "description": plan.get("description", ""),
                       "subject": plan.get("subject", "general"),
                       "lessons": [{"title": plan.get("title", "Video dài"), "brief": ""}]}
            jobs.update_job(job_id, message=f"Dàn ý xong: {len(plan_steps)} step.")
        else:
            outline = generate_outline(idea, lesson_count, lang=lang, provider=ai_provider, model=ai_model)
        lessons = outline["lessons"][:lesson_count]
        subject = outline.get("subject", "general")
        project = project_store.create_project(outline.get("project_title", "Series mới"), aspect_ratio=aspect_ratio,
                                               lang=lang, ai_provider=ai_provider, ai_model=ai_model,
                                               min_steps=min_steps, tts_engine=tts_engine, voice=voice, **style_opts)
        pid = project["id"]
        jobs.update_job(job_id, progress=8, result={"project_id": pid}, message=f"Đã tạo series '{project["title"]}' — {len(lessons)} tập.")
        if lesson_count == 1:
            total_steps = len(plan_steps) if plan_steps else max(int(min_steps), 6)
            CHUNK = 10
            parts = max(1, -(-total_steps // CHUNK))
            sizes = [total_steps // parts + (1 if i < total_steps % parts else 0) for i in range(parts)]
            title1 = (outline.get("lessons") or [{}])[0].get("title", outline.get("project_title", "Video dài"))
            briefs = [l.get("brief", "") for l in outline.get("lessons") or []]
            brief1 = " ".join(b for b in briefs if b)[:400] or idea[:400]
            lesson = project_store.create_lesson(pid, title1)
            from collections import Counter
            scene_counter = Counter()
            merged, prev = [], ""
            ok = True
            for k in range(parts):
                if _is_cancelled(job_id):
                    jobs.update_job(job_id, status="cancelled", message="⏹ Đã dừng giữa chừng video dài.", result={"project_id": pid})
                    return None
                jobs.update_job(job_id, progress=10 + int(k / parts * (70 if auto_media else 85)), message=f"Viết phần {k + 1}/{parts} (step {len(merged) + 1}–{len(merged) + sizes[k]}/{total_steps})...")
                content_k = f"{title1}\n{brief1}"
                if plan_steps is not None:
                    chunk_plan = plan_steps[len(merged):len(merged) + sizes[k]]
                    listing = "\n".join((f"{len(merged) + j + 1}) {s.get("title", "")} — {s.get("brief", "")}" for j, s in enumerate(chunk_plan)))
                    content_k = f"{title1}\nWrite EXACTLY these steps, in order, one step each:\n{listing}"
                part = _gen_script_retry(content_k, subject, sizes[k], lang, ai_provider, ai_model, style_opts.get("template") or "", label=f"Phần {k + 1}", seed=k * 7 + 1, avoid=_overused(scene_counter), note=(lambda m: jobs.update_job(job_id, message=m)), part_info={"index": k + 1, "count": parts, "prev": prev, "offset": len(merged), "total": total_steps})
                if part is None:
                    ok = False
                    break
                steps_k = part.get("steps") or []
                merged.extend(steps_k)
                scene_counter.update(part.get("scenes_used") or [])
                snips = [(st.get("voice_text") or "")[:50] for st in steps_k]
                prev = ((prev + " | " if prev else "") + " · ".join(snips))[-400:]
            if not ok or not merged:
                project_store.update_lesson_meta(pid, lesson["id"], status="error")
                raise RuntimeError("Không viết trọn được video dài — thử lại hoặc giảm số step.")
            for idx, st in enumerate(merged):
                st["id"] = idx + 1
            final = {"title": title1, "description": outline.get("description", ""), "subject": subject, "total_steps": len(merged), "steps": merged, "scenes_used": list(scene_counter.keys())}
            project_store.save_script(pid, lesson["id"], final)
            media_jobs = []
            if auto_media and not _is_cancelled(job_id):
                from core.render_service import queue_full_pipeline
                jobs.update_job(job_id, progress=88, message="Xếp hàng giọng đọc + render video dài...")
                mj = queue_full_pipeline(pid, lesson["id"])
                media_jobs.append(mj["id"])
            jobs.update_job(job_id, status="done", progress=100, message=f"✅ Xong video dài '{title1}': {len(merged)} step." + (" Đang render (xem Hàng đợi)." if media_jobs else " Mở project để render."), result={"project_id": pid, "lessons": [lesson["id"]], "media_jobs": media_jobs, "failed": 0})
            return None
        from collections import Counter
        scene_counter = Counter()
        created_lessons = []
        n = len(lessons)
        for i, item in enumerate(lessons):
            if _is_cancelled(job_id):
                jobs.update_job(job_id, status="cancelled", progress=0, message=f"⏹ Đã dừng — giữ {len(created_lessons)}/{n} tập đã viết.", result={"project_id": pid, "lessons": created_lessons})
                return None
            title = item.get("title", f"Tập {i + 1}")
            brief = item.get("brief", title)
            jobs.update_job(job_id, progress=8 + int(i / max(n, 1) * (72 if auto_media else 88)), message=f"Viết kịch bản {i + 1}/{n}: {title[:50]}...")
            lesson = project_store.create_lesson(pid, title)
            script = _gen_script_retry(f"{title}\n{brief}", subject, min_steps, lang, ai_provider, ai_model, style_opts.get("template") or "", label=f"Tập {i + 1}", seed=i, avoid=_overused(scene_counter), note=(lambda m: jobs.update_job(job_id, message=m)), series_info={"index": i + 1, "total": n})
            if script is not None:
                project_store.save_script(pid, lesson["id"], script)
                created_lessons.append(lesson["id"])
                scene_counter.update(script.get("scenes_used") or [])
                continue
            project_store.update_lesson_meta(pid, lesson["id"], status="error")
        media_jobs = []
        if auto_media and created_lessons and not _is_cancelled(job_id):
            from core.render_service import queue_full_pipeline
            for i, lid in enumerate(created_lessons):
                jobs.update_job(job_id, progress=80 + int(i / len(created_lessons) * 18), message=f"Xếp hàng giọng đọc + render {i + 1}/{len(created_lessons)}...")
                mj = queue_full_pipeline(pid, lid)
                media_jobs.append(mj["id"])
        failed = n - len(created_lessons)
        if len(created_lessons) == 0:
            raise RuntimeError(f"Không viết được kịch bản cho tập nào ({n} tập lỗi) — kiểm tra key AI / mạng / model. Series đã tạo nhưng các tập còn rỗng.")
        done_msg = f"✅ Xong series '{project["title"]}': {len(created_lessons)}/{n} tập." + (f" ⚠️ {failed} tập lỗi kịch bản — mở project tạo lại." if failed else "") + (f" Đang render {len(media_jobs)} video (xem Hàng đợi)." if media_jobs else " Mở project để render.")
        jobs.update_job(job_id, status="done", progress=100, message=done_msg, result={"project_id": pid, "lessons": created_lessons, "media_jobs": media_jobs, "failed": failed})
    except Exception as e:
        logger.exception("AutoPilot lỗi")
        jobs.update_job(job_id, status="error", message=str(e)[:300])
