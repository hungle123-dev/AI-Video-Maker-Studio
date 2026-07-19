from __future__ import annotations

from core import autopilot, jobs
from core.project_store import ProjectStore


def _script(title: str, count: int) -> dict:
    return {
        "title": title,
        "steps": [
            {"id": i + 1, "voice_text": f"Nội dung {i + 1}", "elements": []}
            for i in range(count)
        ],
        "scenes_used": ["mn_formula"],
    }


def _prepare(tmp_path, monkeypatch):
    store = ProjectStore(tmp_path / "projects")
    monkeypatch.setattr(autopilot, "project_store", store)
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path / "jobs")
    return store


def test_autopilot_series_then_add_lessons_and_queue_media(tmp_path, monkeypatch):
    store = _prepare(tmp_path, monkeypatch)
    outlines = iter(
        [
            {
                "project_title": "Series AI",
                "subject": "tech",
                "lessons": [
                    {"title": "Tập một", "brief": "A"},
                    {"title": "Tập hai", "brief": "B"},
                ],
            },
            {
                "project_title": "Series AI",
                "subject": "tech",
                "lessons": [{"title": "Tập ba", "brief": "C"}],
            },
        ]
    )
    monkeypatch.setattr(autopilot, "generate_outline", lambda *_a, **_k: next(outlines))
    monkeypatch.setattr(
        autopilot,
        "_gen_script_retry",
        lambda content, _subject, count, *_a, **_k: _script(content.splitlines()[0], count),
    )

    import core.render_service as render_service

    queued = []
    monkeypatch.setattr(
        render_service,
        "queue_full_pipeline",
        lambda pid, lid: queued.append((pid, lid)) or {"id": f"media-{len(queued)}"},
    )

    job = jobs.create_job("autopilot")
    autopilot._worker(
        job["id"],
        "Ý tưởng",
        2,
        "9:16",
        "vi",
        "gemini",
        "",
        "edge",
        "vi-VN-HoaiMyNeural",
        3,
        {"template": "", "art_style": "liquidglass"},
        True,
    )
    finished = jobs.get_job(job["id"])
    assert finished["status"] == "done"
    assert len(finished["result"]["lessons"]) == 2
    assert len(queued) == 2

    pid = finished["result"]["project_id"]
    add_job = jobs.create_job("add_lessons")
    autopilot._add_worker(add_job["id"], pid, "Viết tiếp", 1, True)
    assert jobs.get_job(add_job["id"])["status"] == "done"
    assert len(store.list_lessons(pid)) == 3
    assert len(queued) == 3


def test_autopilot_long_video_chunks_and_renumbers(tmp_path, monkeypatch):
    store = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        autopilot,
        "generate_outline",
        lambda *_a, **_k: {
            "project_title": "Video dài",
            "description": "D",
            "subject": "general",
            "lessons": [{"title": "Một video", "brief": "B"}],
        },
    )
    chunk_sizes = []

    def generate_part(content, _subject, count, *_args, **_kwargs):
        chunk_sizes.append(count)
        return _script(content.splitlines()[0], count)

    monkeypatch.setattr(autopilot, "_gen_script_retry", generate_part)
    job = jobs.create_job("autopilot")
    autopilot._worker(
        job["id"], "Video", 1, "16:9", "vi", "gemini", "", "edge", "voice", 21,
        {"template": ""}, False,
    )

    finished = jobs.get_job(job["id"])
    pid = finished["result"]["project_id"]
    lesson = store.get_lesson(pid, finished["result"]["lessons"][0])
    assert finished["status"] == "done"
    assert chunk_sizes == [7, 7, 7]
    assert [step["id"] for step in lesson["script"]["steps"]] == list(range(1, 22))


def test_autopilot_cancel_keeps_completed_lessons(tmp_path, monkeypatch):
    store = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        autopilot,
        "generate_outline",
        lambda *_a, **_k: {
            "project_title": "Dừng giữa chừng",
            "subject": "general",
            "lessons": [
                {"title": "Một", "brief": "A"},
                {"title": "Hai", "brief": "B"},
            ],
        },
    )
    job = jobs.create_job("autopilot")

    def generate_first(_content, _subject, count, *_args, **_kwargs):
        jobs.update_job(job["id"], cancel=True)
        return _script("Một", count)

    monkeypatch.setattr(autopilot, "_gen_script_retry", generate_first)
    autopilot._worker(
        job["id"], "Series", 2, "9:16", "vi", "gemini", "", "edge", "voice", 2,
        {"template": ""}, False,
    )

    finished = jobs.get_job(job["id"])
    assert finished["status"] == "cancelled"
    assert len(finished["result"]["lessons"]) == 1
    assert len(store.list_lessons(finished["result"]["project_id"])) == 1
