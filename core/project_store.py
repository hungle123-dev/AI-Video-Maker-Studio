"""File-backed projects and lessons, with strict per-project boundaries."""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import shutil
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from config import PROJECTS_DIR
from core.aspect_ratios import VALID_ASPECT_RATIOS, normalize_aspect_ratio
from core.schema import default_script, validate_script

logger = logging.getLogger("TubeCraft.Store")

_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_VIDEO_PATH_FIELDS = {
    "rendered_video_path",
    "rendered_video_path_16_9",
    "rendered_video_path_9_16",
}
_VISUAL_PROJECT_FIELDS = {
    "theme", "bg", "template", "art_style", "text_color", "title_color",
    "aspect_ratio", "font_family", "subtitle_y_pct", "subtitle_preset",
    "subtitle_enabled", "subtitle_max_lines", "subtitle_font_scale",
}
_AUDIO_PROJECT_FIELDS = {"voice", "tts_engine", "lang"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _read_json(path: Path | str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path | str, data) -> None:
    """Atomically replace one JSON file; a crash never leaves half JSON behind."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _normalize_project_values(values: dict) -> dict:
    """Keep persisted project preferences as renderer-facing ids, never UI labels."""
    normalized = dict(values or {})
    from core.backgrounds import normalize_id as normalize_background
    from core.fonts import font_options
    from core.subtitles import normalize_preset_id
    from core.templates import TITLE_COLOR_OPTIONS, normalize_id as normalize_template, normalize_style

    if "bg" in normalized:
        normalized["bg"] = normalize_background(normalized["bg"])
    if "template" in normalized:
        normalized["template"] = normalize_template(normalized["template"])
    if "art_style" in normalized:
        normalized["art_style"] = normalize_style(normalized["art_style"])
    if "subtitle_preset" in normalized:
        normalized["subtitle_preset"] = normalize_preset_id(normalized["subtitle_preset"])
    if "title_color" in normalized:
        colors = {key for key, _label in TITLE_COLOR_OPTIONS}
        normalized["title_color"] = str(normalized["title_color"] or "").strip()
        if normalized["title_color"] not in colors:
            normalized["title_color"] = ""
    if "font_family" in normalized:
        fonts = {key: key for key, _label in font_options()}
        fonts.update({label: key for key, label in font_options()})
        normalized["font_family"] = fonts.get(str(normalized["font_family"] or "").strip(), "")
    return normalized


def script_has_content(script: dict) -> bool:
    if not isinstance(script, dict):
        return False
    for step in script.get("steps", []):
        if not isinstance(step, dict):
            continue
        if (step.get("voice_text") or "").strip() or step.get("elements"):
            return True
    return False


def timing_has_content(timing: dict) -> bool:
    if not isinstance(timing, dict):
        return False
    steps = timing.get("steps", [])
    if not steps:
        return False
    if any((step.get("words") for step in steps if isinstance(step, dict))):
        return True
    # Engines without word boundaries (for example gTTS/Vivibe fallbacks) can
    # produce a perfectly valid one- or two-second narration.  The caller
    # separately verifies both a real script and a nonempty audio file, so a
    # positive timeline is sufficient here; a 2.5-second cutoff made those
    # legitimate lessons permanently unrenderable.
    return float(timing.get("total_duration", 0) or 0) > 0


def audio_has_content(timing: dict, audio_path) -> bool:
    try:
        return timing_has_content(timing) and Path(audio_path).stat().st_size > 0
    except (OSError, TypeError):
        return False


def _revision(meta: dict, field: str, default: int) -> int:
    try:
        return max(0, int(meta.get(field, default)))
    except (TypeError, ValueError, AttributeError):
        return default


def audio_source_revision(meta: dict) -> int:
    return _revision(meta, "audio_source_revision", 1)


def render_source_revision(meta: dict) -> int:
    return _revision(meta, "render_source_revision", 1)


def audio_bundle_revision(meta: dict) -> int:
    # Existing projects predate revisions. Treat their on-disk audio as the
    # initial version until a source input is changed, then persist strict IDs.
    return _revision(meta, "audio_bundle_revision", audio_source_revision(meta))


def video_source_revision(meta: dict) -> int:
    return _revision(meta, "video_source_revision", render_source_revision(meta))


def audio_is_current(meta: dict, timing: dict, audio_path) -> bool:
    return (
        audio_bundle_revision(meta) == audio_source_revision(meta)
        and audio_has_content(timing, audio_path)
    )


def video_is_current(meta: dict, video_path) -> bool:
    try:
        return (
            video_source_revision(meta) == render_source_revision(meta)
            and Path(video_path).is_file()
        )
    except (OSError, TypeError):
        return False


class ProjectStore:
    """Owns all paths below ``projects`` and only accepts opaque safe IDs."""

    def __init__(self, root: Path = PROJECTS_DIR, outputs_root: Path | None = None):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.outputs_root = Path(
            outputs_root if outputs_root is not None else self.root.parent / "outputs"
        ).expanduser().resolve()
        self._lock = threading.RLock()

    @staticmethod
    def _inside(base: Path, *parts: str) -> Optional[Path]:
        """Return a child only when all existing symlinks still stay in ``base``."""
        candidate = base.joinpath(*parts)
        try:
            candidate.resolve(strict=False).relative_to(base.resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            return None
        return candidate

    def _project_dir(self, project_id: str) -> Optional[Path]:
        if not _safe_id(project_id):
            return None
        return self._inside(self.root, project_id)

    def _lesson_dir(self, project_id: str, lesson_id: str) -> Optional[Path]:
        if not _safe_id(lesson_id):
            return None
        project_dir = self._project_dir(project_id)
        if project_dir is None:
            return None
        lessons_dir = self._inside(project_dir, "lessons")
        return self._inside(lessons_dir, lesson_id) if lessons_dir else None

    def _project_json(self, project_id: str) -> Optional[Path]:
        project_dir = self._project_dir(project_id)
        return self._inside(project_dir, "project.json") if project_dir else None

    def _lesson_file(self, project_id: str, lesson_id: str, *parts: str) -> Optional[Path]:
        lesson_dir = self._lesson_dir(project_id, lesson_id)
        return self._inside(lesson_dir, *parts) if lesson_dir else None

    def _valid_project_meta(self, project_id: str) -> Optional[dict]:
        path = self._project_json(project_id)
        meta = _read_json(path) if path else None
        if not isinstance(meta, dict) or meta.get("id") != project_id:
            return None
        # Legacy/imported metadata is untrusted.  Return a safe value even
        # before a later normal write persists it.
        meta["aspect_ratio"] = normalize_aspect_ratio(meta.get("aspect_ratio"))
        return _normalize_project_values(meta)

    def _valid_lesson_meta(self, project_id: str, lesson_id: str) -> Optional[dict]:
        path = self._lesson_file(project_id, lesson_id, "lesson.json")
        meta = _read_json(path) if path else None
        if not isinstance(meta, dict):
            return None
        if meta.get("id") != lesson_id or meta.get("project_id") != project_id:
            return None
        return meta

    def _load_script(
        self, project_id: str, lesson_id: str, *, persist: bool = False
    ) -> tuple[dict, List[str]]:
        """Read a normalized safe view of a script without mutating by default.

        A transparent rewrite can change a legacy script while its old media
        is still marked current.  Explicit import/editor writes therefore go
        through ``save_script()``, which invalidates revisions first.
        """
        path = self._lesson_file(project_id, lesson_id, "lesson_script.json")
        raw = _read_json(path) if path else None
        missing = raw is None
        original = copy.deepcopy(raw) if isinstance(raw, dict) else raw
        normalized, errors = validate_script(raw if raw is not None else default_script())
        if missing:
            errors = ["Thiếu lesson_script.json; đã tạo script mặc định.", *errors]
        if persist and path and (missing or normalized != original):
            _write_json(path, normalized)
        return normalized, errors

    @staticmethod
    def _remove_path(path: Optional[Path]) -> None:
        if path is None or not path.exists() and not path.is_symlink():
            return
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)

    def _clear_video_meta(self, meta: dict) -> bool:
        changed = False
        for field in _VIDEO_PATH_FIELDS:
            if meta.pop(field, None) is not None:
                changed = True
        if _revision(meta, "video_source_revision", 0):
            meta["video_source_revision"] = 0
            changed = True
        return changed

    @staticmethod
    def _init_revisions(meta: dict) -> None:
        """Migrate legacy lesson metadata lazily without trusting old media later."""
        meta.setdefault("audio_source_revision", 1)
        meta.setdefault("render_source_revision", 1)
        meta.setdefault("audio_bundle_revision", 1)
        meta.setdefault(
            "video_source_revision",
            1 if any(meta.get(field) for field in _VIDEO_PATH_FIELDS) else 0,
        )

    def _advance_revisions(self, meta: dict, *, audio: bool) -> None:
        self._init_revisions(meta)
        if audio:
            meta["audio_source_revision"] = audio_source_revision(meta) + 1
            meta["audio_bundle_revision"] = 0
        meta["render_source_revision"] = render_source_revision(meta) + 1
        meta["video_source_revision"] = 0

    def _invalidate_lesson(self, project_id: str, lesson_id: str, *, audio: bool) -> bool:
        """Make generated artifacts unreachable after an input change.

        Old output files are deliberately not deleted outside the owned lesson
        directory. Their metadata is cleared, so they cannot be opened/rendered
        as if they matched the new inputs.
        """
        meta = self._valid_lesson_meta(project_id, lesson_id)
        lesson_dir = self._lesson_dir(project_id, lesson_id)
        if meta is None or lesson_dir is None:
            return False
        self._advance_revisions(meta, audio=audio)
        if audio:
            self._remove_path(self._inside(lesson_dir, "timing_map.json"))
            self._remove_path(self._inside(lesson_dir, "audio"))
        self._clear_video_meta(meta)
        script, _ = self._load_script(project_id, lesson_id, persist=False)
        new_status = "ready" if script_has_content(script) else "draft"
        if meta.get("status") != new_status:
            meta["status"] = new_status
        # Revisions are the stale-job guard.  Persist them even when this
        # lesson happens to have no existing MP4 to clear: an in-flight render
        # may otherwise publish under a changed visual/audio configuration.
        meta["updated_at"] = _now()
        path = self._lesson_file(project_id, lesson_id, "lesson.json")
        if path:
            _write_json(path, meta)
        return True

    def _invalidate_project(self, project_id: str, *, audio: bool) -> None:
        for lesson in self.list_lessons(project_id):
            self._invalidate_lesson(project_id, lesson["id"], audio=audio)

    def _safe_video_path(self, value: object) -> Optional[Path]:
        if not isinstance(value, str) or not value.strip():
            return None
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.outputs_root / candidate
        try:
            candidate.resolve(strict=False).relative_to(self.outputs_root)
        except (OSError, RuntimeError, ValueError):
            return None
        return candidate

    def _output_project_dir(self, project_id: str) -> Optional[Path]:
        """Return the owned output directory for one project only."""
        if not _safe_id(project_id):
            return None
        return self._inside(self.outputs_root, project_id)

    def _previews_root(self) -> Optional[Path]:
        """Preview cache belongs beside this store's projects directory."""
        return self._inside(self.root.parent, "previews")

    @staticmethod
    def _path_is_inside(path: Path, base: Path) -> bool:
        try:
            path.resolve(strict=False).relative_to(base.resolve(strict=False))
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _output_path_belongs_to_project(self, path: Path, project_id: str) -> bool:
        output_dir = self._output_project_dir(project_id)
        return bool(output_dir and self._path_is_inside(path, output_dir))

    def _lesson_id_is_used_by_another_project(self, project_id: str, lesson_id: str) -> bool:
        """Fail closed before removing a legacy ``previews/<lesson_id>`` cache.

        Older static previews were keyed by lesson ID alone.  Those IDs were
        short enough to collide across projects, so deleting that directory is
        only safe when no surviving project owns the same lesson ID.
        """
        if not _safe_id(project_id) or not _safe_id(lesson_id):
            return True
        try:
            for project_dir in self.root.iterdir():
                if not project_dir.is_dir() or project_dir.is_symlink():
                    continue
                other_project_id = project_dir.name
                if other_project_id == project_id or not _safe_id(other_project_id):
                    continue
                lesson_dir = self._lesson_dir(other_project_id, lesson_id)
                if (
                    lesson_dir is not None
                    and lesson_dir.is_dir()
                    and not lesson_dir.is_symlink()
                    and self._valid_lesson_meta(other_project_id, lesson_id) is not None
                ):
                    return True
        except OSError as exc:
            logger.warning("Không kiểm tra được cache preview cũ an toàn: %s", exc)
            return True
        return False

    def _output_is_referenced_by_another_lesson(
        self, project_id: str, lesson_id: str, output_path: Path
    ) -> bool:
        """Do not delete a project-local legacy output shared by another lesson."""
        for other in self.list_lessons(project_id):
            if other.get("id") == lesson_id:
                continue
            for field in _VIDEO_PATH_FIELDS:
                candidate = self._safe_video_path(other.get(field))
                if candidate is None:
                    continue
                try:
                    if candidate.resolve(strict=False) == output_path.resolve(strict=False):
                        return True
                except (OSError, RuntimeError):
                    continue
        return False

    def _best_effort_remove(self, path: Optional[Path], label: str) -> None:
        try:
            self._remove_path(path)
        except OSError as exc:
            logger.warning("Không xoá được %s: %s", label, exc)

    def _remove_lesson_outputs(self, project_id: str, lesson_id: str, meta: Optional[dict]) -> None:
        """Remove only artifacts owned by one deleted lesson.

        A published renderer output is named with both opaque IDs.  Metadata
        from old versions can point to a differently named project-local file,
        so that file is also removed unless another lesson explicitly uses it.
        Paths outside this project's output directory are never trusted here.
        """
        output_dir = self._output_project_dir(project_id)
        if output_dir is None or output_dir.is_symlink() or not output_dir.is_dir():
            return

        if isinstance(meta, dict):
            for field in _VIDEO_PATH_FIELDS:
                output_path = self._safe_video_path(meta.get(field))
                if (
                    output_path is None
                    or not self._output_path_belongs_to_project(output_path, project_id)
                    or self._output_is_referenced_by_another_lesson(
                        project_id, lesson_id, output_path
                    )
                ):
                    continue
                if output_path.is_file() or output_path.is_symlink():
                    self._best_effort_remove(output_path, "video đã xuất của lesson")

        # Rendered MP4s and interrupted render intermediates all include the
        # exact project+lesson prefix.  This removes unpublished files too,
        # without making assumptions about another lesson's metadata.
        render_prefix = f"edu_{project_id}_{lesson_id}_"
        generated_prefixes = (
            render_prefix,
            f"raw_{render_prefix}",
            f"temp_chunks_{render_prefix}",
        )
        try:
            children = list(output_dir.iterdir())
        except OSError as exc:
            logger.warning("Không đọc được thư mục output của lesson: %s", exc)
            return
        for child in children:
            if child.name.startswith(generated_prefixes):
                self._best_effort_remove(child, "output render tạm của lesson")
        try:
            output_dir.rmdir()
        except OSError:
            pass

    def _remove_lesson_preview_cache(self, project_id: str, lesson_id: str) -> None:
        """Clean known per-lesson preview paths without deleting another project cache."""
        preview_root = self._previews_root()
        if preview_root is None:
            return

        # New cache layout: data/previews/<project>/<lesson>/...
        scoped = self._inside(preview_root, project_id, lesson_id)
        self._best_effort_remove(scoped, "preview scoped của lesson")

        # Current/legacy layout: data/previews/<lesson>/... .  It is only
        # deleted when the ID is unambiguous across surviving projects.
        legacy = self._inside(preview_root, lesson_id)
        if not self._lesson_id_is_used_by_another_project(project_id, lesson_id):
            self._best_effort_remove(legacy, "preview cũ của lesson")

    def _remove_project_preview_cache(self, project_id: str) -> None:
        """Remove project-scoped and subtitle-dialog previews for a deleted project."""
        preview_root = self._previews_root()
        if preview_root is None:
            return

        # Future/project-scoped static previews.  A legacy lesson ID can
        # theoretically equal a project ID, so retain it if another project
        # still owns that lesson ID.
        scoped = self._inside(preview_root, project_id)
        if not self._lesson_id_is_used_by_another_project(project_id, project_id):
            self._best_effort_remove(scoped, "preview scoped của project")

        dialog_dir = self._inside(preview_root, "subtitle_dialog")
        if dialog_dir is None or dialog_dir.is_symlink() or not dialog_dir.is_dir():
            return
        pattern = re.compile(rf"^{re.escape(project_id)}_\d+_")
        try:
            children = list(dialog_dir.iterdir())
        except OSError as exc:
            logger.warning("Không đọc được cache preview phụ đề: %s", exc)
            return
        for child in children:
            if pattern.match(child.name):
                self._best_effort_remove(child, "preview phụ đề của project")

    def _subtitle_thumb_paths_for(self, project: dict, script: dict) -> set[Path]:
        """Return this store's cache files for one subtitle-preview context.

        Subtitle thumbnail filenames are content hashes, not IDs.  Rebuild the
        names through the same helper used by the picker, but anchor them to
        this store's data root so isolated stores never touch another app's
        cache.
        """
        thumb_root = self._inside(self.root.parent, "subtitle_thumbs")
        if thumb_root is None:
            return set()
        try:
            from core import subtitle_thumbs, subtitles

            context = subtitle_thumbs.context(project, script)
            paths: set[Path] = set()
            for preset in subtitles.list_presets():
                preset_id = preset.get("id") if isinstance(preset, dict) else None
                if not isinstance(preset_id, str) or not preset_id:
                    continue
                for source in (
                    subtitle_thumbs.thumb_path(preset_id, context),
                    subtitle_thumbs.card_path(preset_id, context),
                ):
                    path = self._inside(thumb_root, Path(source).name)
                    if path is not None:
                        paths.add(path)
            return paths
        except Exception as exc:
            logger.warning("Không xác định được cache thumbnail phụ đề: %s", exc)
            return set()

    def _remove_subtitle_thumb_cache(
        self,
        contexts: List[tuple[dict, dict]],
        excluded_lessons: set[tuple[str, str]],
    ) -> None:
        """Drop only subtitle thumbnails no surviving lesson can still use."""
        targets: set[Path] = set()
        for project, script in contexts:
            targets.update(self._subtitle_thumb_paths_for(project, script))
        if not targets:
            return

        shared: set[Path] = set()
        for project in self.list_projects():
            project_id = project.get("id")
            if not isinstance(project_id, str):
                continue
            for lesson in self.list_lessons(project_id):
                lesson_id = lesson.get("id")
                if not isinstance(lesson_id, str) or (project_id, lesson_id) in excluded_lessons:
                    continue
                script, _ = self._load_script(project_id, lesson_id, persist=False)
                shared.update(self._subtitle_thumb_paths_for(project, script) & targets)
                if shared == targets:
                    break
            if shared == targets:
                break

        for path in targets - shared:
            self._best_effort_remove(path, "thumbnail phụ đề của dữ liệu đã xoá")
        thumb_root = self._inside(self.root.parent, "subtitle_thumbs")
        if thumb_root is not None and thumb_root.is_dir() and not thumb_root.is_symlink():
            try:
                thumb_root.rmdir()
            except OSError:
                pass

    @staticmethod
    def _job_belongs_to(
        job: object, project_id: str, lesson_id: Optional[str] = None
    ) -> bool:
        if not isinstance(job, dict):
            return False
        meta = job.get("meta") if isinstance(job.get("meta"), dict) else {}
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        has_project = (
            meta.get("project_id") == project_id
            or result.get("project_id") == project_id
        )
        if not has_project:
            return False
        if lesson_id is None:
            return True
        if meta.get("lesson_id") == lesson_id or result.get("lesson_id") == lesson_id:
            return True
        # A completed one-lesson autopilot result is unambiguously tied to the
        # deleted lesson.  Multi-lesson project jobs are retained because they
        # still describe valid surviving lessons.
        lessons = result.get("lessons")
        return isinstance(lessons, list) and len(lessons) == 1 and lessons[0] == lesson_id

    def _purge_related_jobs(self, project_id: str, lesson_id: Optional[str] = None) -> None:
        """Delete durable job records that point at deleted project data.

        ``core.jobs`` already exposes a process-wide lock and stores one JSON
        document per job.  Taking that lock prevents a concurrent progress
        update from recreating a record immediately after deletion.
        """
        try:
            from core import jobs

            job_dir = Path(jobs.JOBS_DIR)
            job_lock = getattr(jobs, "_lock", None)
        except Exception:
            return
        if job_lock is None or job_dir.is_symlink() or not job_dir.is_dir():
            return
        try:
            with job_lock:
                root = job_dir.resolve(strict=False)
                for job_path in job_dir.glob("*.json"):
                    if job_path.is_symlink() or not job_path.is_file():
                        continue
                    if not self._path_is_inside(job_path, root):
                        continue
                    job = _read_json(job_path)
                    if self._job_belongs_to(job, project_id, lesson_id):
                        job_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Không dọn được job liên quan dữ liệu đã xoá: %s", exc)

    def list_projects(self) -> List[dict]:
        out = []
        for project_dir in sorted(self.root.iterdir()):
            if not project_dir.is_dir() or project_dir.is_symlink():
                continue
            project_id = project_dir.name
            if not _safe_id(project_id) or self._project_dir(project_id) is None:
                continue
            meta = self._valid_project_meta(project_id)
            if meta is None:
                continue
            meta["lesson_count_actual"] = self._count_lessons(project_id)
            out.append(meta)
        out.sort(key=lambda project: project.get("updated_at", ""), reverse=True)
        return out

    def migrate_legacy_preferences(self) -> int:
        """Persist safe ids for old UI labels and repair never-applied templates."""
        migrated = 0
        with self._lock:
            for project_dir in self.root.iterdir():
                if not project_dir.is_dir() or project_dir.is_symlink() or not _safe_id(project_dir.name):
                    continue
                project_id = project_dir.name
                path = self._project_json(project_id)
                raw = _read_json(path) if path else None
                if not isinstance(raw, dict) or raw.get("id") != project_id:
                    continue
                normalized = _normalize_project_values(raw)
                from core.backgrounds import normalize_id as normalize_background
                from core.templates import get_template

                template_id = normalized.get("template", "")
                template = get_template(template_id) if template_id else None
                # ponytail: repair only the unmistakable never-applied template shape;
                # intentional project-level overrides remain untouched.
                if (template and template.get("art_style") != "default"
                        and raw.get("art_style") == "default"
                        and str(raw.get("bg") or "").strip() != normalize_background(raw.get("bg"))
                        and not normalized.get("title_color") and not normalized.get("font_family")):
                    normalized.update({
                        "art_style": template["art_style"],
                        "title_color": template.get("title_color", ""),
                        "text_color": template.get("text_color", ""),
                        "font_family": template.get("font_family", ""),
                    })
                changed = {
                    key: value for key, value in normalized.items()
                    if key in _VISUAL_PROJECT_FIELDS | _AUDIO_PROJECT_FIELDS and raw.get(key) != value
                }
                if not changed:
                    continue
                if set(changed) & _AUDIO_PROJECT_FIELDS:
                    self._invalidate_project(project_id, audio=True)
                elif set(changed) & _VISUAL_PROJECT_FIELDS:
                    self._invalidate_project(project_id, audio=False)
                raw.update(changed)
                raw["updated_at"] = _now()
                _write_json(path, raw)
                migrated += 1
        return migrated

    def _count_lessons(self, project_id: str) -> int:
        project_dir = self._project_dir(project_id)
        lessons_dir = self._inside(project_dir, "lessons") if project_dir else None
        if lessons_dir is None or not lessons_dir.is_dir() or lessons_dir.is_symlink():
            return 0
        return sum(
            1
            for lesson_dir in lessons_dir.iterdir()
            if lesson_dir.is_dir()
            and not lesson_dir.is_symlink()
            and _safe_id(lesson_dir.name)
            and self._valid_lesson_meta(project_id, lesson_dir.name) is not None
        )

    def create_project(self, title: str, **opts) -> dict:
        opts = _normalize_project_values(opts)
        project_id = uuid.uuid4().hex[:8]
        while self._project_dir(project_id) and self._project_dir(project_id).exists():
            project_id = uuid.uuid4().hex[:8]
        meta = {
            "id": project_id,
            "title": title or "Project mới",
            "theme": opts.get("theme", "dark"),
            "voice": opts.get("voice", "vi-VN-HoaiMyNeural"),
            "tts_engine": opts.get("tts_engine", "edge"),
            "ai_provider": opts.get("ai_provider", "gemini"),
            "ai_model": opts.get("ai_model", ""),
            "min_steps": int(opts.get("min_steps", 12)),
            "lang": opts.get("lang", "vi"),
            "aspect_ratio": normalize_aspect_ratio(opts.get("aspect_ratio", "9:16")),
            "art_style": opts.get("art_style", "default"),
            "bg": opts.get("bg", ""),
            "template": opts.get("template", ""),
            "title_color": opts.get("title_color", ""),
            "text_color": opts.get("text_color", ""),
            "font_family": opts.get("font_family", ""),
            "subtitle_enabled": bool(opts.get("subtitle_enabled", True)),
            "subtitle_preset": opts.get("subtitle_preset", ""),
            "subtitle_font_scale": float(opts.get("subtitle_font_scale", 1.0)),
            "subtitle_y_pct": opts.get("subtitle_y_pct"),
            "created_at": _now(),
            "updated_at": _now(),
            "status": "draft",
            "audio_source_revision": 1,
            "audio_bundle_revision": 0,
            "render_source_revision": 1,
            "video_source_revision": 0,
        }
        path = self._project_json(project_id)
        if path is None:  # Defensive: generated UUID must always be valid.
            raise RuntimeError("Không tạo được đường dẫn project an toàn.")
        _write_json(path, meta)
        return meta

    def get_project(self, project_id: str) -> Optional[dict]:
        return self._valid_project_meta(project_id)

    def update_project(self, project_id: str, **fields) -> Optional[dict]:
        with self._lock:
            fields = _normalize_project_values(fields)
            meta = self._valid_project_meta(project_id)
            path = self._project_json(project_id)
            if meta is None or path is None:
                return None
            if "aspect_ratio" in fields and fields["aspect_ratio"] not in VALID_ASPECT_RATIOS:
                return None
            allowed = {
                "bg", "lang", "theme", "title", "voice", "status", "ai_model", "template",
                "art_style", "min_steps", "text_color", "tts_engine", "ai_provider", "font_family",
                "title_color", "aspect_ratio", "subtitle_y_pct", "subtitle_preset", "subtitle_enabled",
                "subtitle_max_lines", "subtitle_font_scale",
            }
            changed = {key for key, value in fields.items() if key in allowed and meta.get(key) != value}
            if not changed:
                return meta
            # Invalidate dependent lesson metadata before publishing a new
            # project configuration. A crash can then leave extra work to do,
            # never a new visual/audio setting paired with an old MP4.
            if changed & _AUDIO_PROJECT_FIELDS:
                self._invalidate_project(project_id, audio=True)
            elif changed & _VISUAL_PROJECT_FIELDS:
                self._invalidate_project(project_id, audio=False)
            for key in changed:
                meta[key] = fields[key]
            meta["updated_at"] = _now()
            _write_json(path, meta)
            return self._valid_project_meta(project_id)

    def delete_project(self, project_id: str) -> bool:
        # Serialize deletion with TTS/video commits.  _write_json creates
        # parent directories, so an unlocked deletion could be resurrected by
        # a late worker that had already validated lesson metadata.
        with self._lock:
            project_dir = self._project_dir(project_id)
            if project_dir is None or project_dir.is_symlink() or not project_dir.is_dir():
                return False
            lessons = self.list_lessons(project_id)
            lesson_ids = [lesson["id"] for lesson in lessons]
            project_meta = self._valid_project_meta(project_id)
            thumbnail_contexts = []
            if project_meta is not None:
                for lesson_id in lesson_ids:
                    script, _ = self._load_script(project_id, lesson_id, persist=False)
                    thumbnail_contexts.append((project_meta, script))
            shutil.rmtree(project_dir)
            # A project owns its whole output directory; unlike an input
            # invalidation, an explicit user deletion is expected to remove
            # rendered media too.
            self._best_effort_remove(
                self._output_project_dir(project_id), "thư mục output của project"
            )
            self._remove_project_preview_cache(project_id)
            for lesson_id in lesson_ids:
                self._remove_lesson_preview_cache(project_id, lesson_id)
            self._remove_subtitle_thumb_cache(
                thumbnail_contexts,
                {(project_id, lesson_id) for lesson_id in lesson_ids},
            )
            self._purge_related_jobs(project_id)
            return True

    def _valid_import_layout(self, source: Path, project_id: str) -> bool:
        """Reject symlinks and metadata that could later turn an ID into a path."""
        try:
            if any(item.is_symlink() for item in source.rglob("*")):
                return False
            lessons_dir = source / "lessons"
            if not lessons_dir.exists():
                return True
            if not lessons_dir.is_dir():
                return False
            for lesson_dir in lessons_dir.iterdir():
                if not lesson_dir.is_dir() or lesson_dir.is_symlink() or not _safe_id(lesson_dir.name):
                    return False
                lesson_meta = _read_json(lesson_dir / "lesson.json")
                if not isinstance(lesson_meta, dict):
                    return False
                if lesson_meta.get("id") != lesson_dir.name or lesson_meta.get("project_id") != project_id:
                    return False
        except OSError:
            return False
        return True

    def import_external_project(self, src_dir: str) -> Optional[dict]:
        """Copy an external project after validating its IDs and scripts.

        Script validation is intentionally repeated after the copy. This makes
        imported raw JavaScript harmless even when an older exporter produced it.
        Validation notes are kept in ``import_audit.json`` beside the project.
        """
        try:
            source = Path(src_dir).expanduser().resolve()
        except (OSError, RuntimeError, TypeError):
            return None
        meta = _read_json(source / "project.json")
        if not source.is_dir() or not isinstance(meta, dict) or not _safe_id(meta.get("id")):
            return None
        original_id = meta["id"]
        if not self._valid_import_layout(source, original_id):
            return None

        imported = dict(meta)
        imported["aspect_ratio"] = normalize_aspect_ratio(imported.get("aspect_ratio"))
        destination_id = original_id
        destination = self._project_dir(destination_id)
        if destination is None:
            return None
        if destination.exists():
            destination_id = uuid.uuid4().hex[:8]
            destination = self._project_dir(destination_id)
            if destination is None:
                return None
        imported["id"] = destination_id
        try:
            shutil.copytree(source, destination)
            _write_json(self._inside(destination, "project.json"), imported)
            audit = []
            lessons_dir = self._inside(destination, "lessons")
            if lessons_dir and lessons_dir.is_dir():
                for lesson_dir in lessons_dir.iterdir():
                    lesson_id = lesson_dir.name
                    lesson_meta = _read_json(self._inside(lesson_dir, "lesson.json"))
                    if not isinstance(lesson_meta, dict):
                        raise RuntimeError("Lesson import không hợp lệ sau khi copy.")
                    lesson_meta["project_id"] = destination_id
                    self._init_revisions(lesson_meta)
                    self._clear_video_meta(lesson_meta)
                    lesson_meta["updated_at"] = _now()
                    _write_json(self._inside(lesson_dir, "lesson.json"), lesson_meta)
                    script, errors = self._load_script(destination_id, lesson_id)
                    # Persist any imported normalization through the ordered
                    # editor-save path.  This prevents a raw legacy scene that
                    # was removed during validation from inheriting old media.
                    saved, save_errors = self.save_script(destination_id, lesson_id, script)
                    if not saved:
                        raise RuntimeError("Không thể chuẩn hóa script import an toàn.")
                    if errors:
                        audit.append({"lesson_id": lesson_id, "warnings": errors + save_errors})
            if audit:
                _write_json(self._inside(destination, "import_audit.json"), {
                    "imported_at": _now(), "warnings": audit,
                })
            return self._valid_project_meta(destination_id)
        except Exception:
            logger.exception("Import project thất bại")
            if destination and destination.exists() and self._project_dir(destination_id) == destination:
                self._remove_path(destination)
            return None

    def list_lessons(self, project_id: str) -> List[dict]:
        project_dir = self._project_dir(project_id)
        lessons_dir = self._inside(project_dir, "lessons") if project_dir else None
        if self._valid_project_meta(project_id) is None or lessons_dir is None or not lessons_dir.is_dir():
            return []
        out = []
        for lesson_dir in sorted(lessons_dir.iterdir()):
            lesson_id = lesson_dir.name
            if not lesson_dir.is_dir() or lesson_dir.is_symlink() or not _safe_id(lesson_id):
                continue
            meta = self._valid_lesson_meta(project_id, lesson_id)
            if meta is None:
                continue
            script, errors = self._load_script(project_id, lesson_id)
            timing = _read_json(self._lesson_file(project_id, lesson_id, "timing_map.json"))
            audio_path = self._lesson_file(project_id, lesson_id, "audio", "full_audio.mp3")
            meta["has_script"] = script_has_content(script)
            meta["has_audio"] = (
                not errors
                and meta["has_script"]
                and audio_is_current(meta, timing, audio_path)
            )
            video_path = self._safe_video_path(meta.get("rendered_video_path", ""))
            meta["has_video"] = bool(
                not errors and video_path and video_is_current(meta, video_path)
            )
            if errors:
                meta["script_validation_errors"] = errors
            out.append(meta)
        out.sort(key=lambda lesson: (lesson.get("index", 999), lesson.get("created_at", "")))
        return out

    def create_lesson(self, project_id: str, title: str) -> Optional[dict]:
        with self._lock:
            if self._valid_project_meta(project_id) is None:
                return None
            # The previous 24-bit suffix could overwrite a real lesson after
            # a collision.  Keep IDs opaque but use the full UUID and retry
            # defensively for imported/manual IDs or a mocked UUID source.
            lesson_dir = None
            lesson_id = ""
            for _ in range(64):
                candidate_id = f"lesson_{uuid.uuid4().hex}"
                candidate_dir = self._lesson_dir(project_id, candidate_id)
                if candidate_dir is None:
                    return None
                if candidate_dir.exists() or candidate_dir.is_symlink():
                    continue
                lesson_id = candidate_id
                lesson_dir = candidate_dir
                break
            if lesson_dir is None:
                logger.error("Không tạo được lesson ID không trùng cho project %s", project_id)
                return None
            meta = {
                "id": lesson_id,
                "project_id": project_id,
                "title": title or "Bài mới",
                "index": len(self.list_lessons(project_id)),
                "intro_template": "none",
                "outro_template": "none",
                "created_at": _now(),
                "updated_at": _now(),
                "status": "draft",
                "audio_source_revision": 1,
                "audio_bundle_revision": 0,
                "render_source_revision": 1,
                "video_source_revision": 0,
            }
            _write_json(self._inside(lesson_dir, "lesson.json"), meta)
            _write_json(self._inside(lesson_dir, "lesson_script.json"), default_script(title))
            return meta

    def get_lesson(self, project_id: str, lesson_id: str) -> Optional[dict]:
        meta = self._valid_lesson_meta(project_id, lesson_id)
        if meta is None:
            return None
        script, errors = self._load_script(project_id, lesson_id)
        timing = _read_json(self._lesson_file(project_id, lesson_id, "timing_map.json"))
        meta["script"] = script
        meta["timing"] = timing
        if errors:
            meta["script_validation_errors"] = errors
        return meta

    def get_render_snapshot(self, project_id: str, lesson_id: str) -> Optional[dict]:
        """Return one coherent project/lesson input set for a long render.

        Project visual settings and lesson revisions change under the same
        RLock.  Reading them independently can combine an old theme with a new
        revision, allowing an old render to publish as if it matched the new
        configuration.  The publication method verifies these revisions again
        after the renderer has finished.
        """
        with self._lock:
            project = self._valid_project_meta(project_id)
            meta = self._valid_lesson_meta(project_id, lesson_id)
            lesson_dir = self._lesson_dir(project_id, lesson_id)
            if project is None or meta is None or lesson_dir is None:
                return None
            script, errors = self._load_script(project_id, lesson_id, persist=False)
            timing = _read_json(self._inside(lesson_dir, "timing_map.json"))
            paths = {
                "dir": self._inside(lesson_dir),
                "script": self._inside(lesson_dir, "lesson_script.json"),
                "timing": self._inside(lesson_dir, "timing_map.json"),
                "audio_dir": self._inside(lesson_dir, "audio"),
                "full_audio": self._inside(lesson_dir, "audio", "full_audio.mp3"),
            }
            if any(path is None for path in paths.values()):
                return None
            lesson = copy.deepcopy(meta)
            lesson["script"] = script
            lesson["timing"] = timing
            if errors:
                lesson["script_validation_errors"] = errors
            return {
                "project": copy.deepcopy(project),
                "lesson": lesson,
                "paths": {key: str(path) for key, path in paths.items()},
                "audio_source_revision": audio_source_revision(meta),
                "render_source_revision": render_source_revision(meta),
            }

    def update_lesson_meta(
        self,
        project_id: str,
        lesson_id: str,
        *,
        expected_render_revision: int | None = None,
        **fields,
    ) -> Optional[dict]:
        with self._lock:
            meta = self._valid_lesson_meta(project_id, lesson_id)
            path = self._lesson_file(project_id, lesson_id, "lesson.json")
            if meta is None or path is None:
                return None
            if (
                expected_render_revision is not None
                and render_source_revision(meta) != expected_render_revision
            ):
                return None
            allowed = {
                "index", "title", "status", "intro_template", "outro_template", *_VIDEO_PATH_FIELDS,
            }
            changed = False
            wrote_video = False
            for key, value in fields.items():
                if key not in allowed:
                    continue
                if key in _VIDEO_PATH_FIELDS and value and self._safe_video_path(value) is None:
                    logger.warning("Bỏ qua video path ngoài data/outputs cho lesson %s", lesson_id)
                    continue
                if meta.get(key) != value:
                    meta[key] = value
                    changed = True
                    wrote_video = wrote_video or key in _VIDEO_PATH_FIELDS
            if wrote_video:
                self._init_revisions(meta)
                meta["video_source_revision"] = render_source_revision(meta)
            if changed:
                meta["updated_at"] = _now()
                _write_json(path, meta)
            return meta

    def save_script(self, project_id: str, lesson_id: str, script: dict) -> tuple[bool, List[str]]:
        with self._lock:
            if self._valid_lesson_meta(project_id, lesson_id) is None:
                return False, ["Lesson không tồn tại hoặc ID không hợp lệ."]
            previous, _ = self._load_script(project_id, lesson_id, persist=False)
            normalized, errors = validate_script(copy.deepcopy(script))
            changed = normalized != previous
            lesson_dir = self._lesson_dir(project_id, lesson_id)
            script_path = self._lesson_file(project_id, lesson_id, "lesson_script.json")
            meta = self._valid_lesson_meta(project_id, lesson_id)
            meta_path = self._lesson_file(project_id, lesson_id, "lesson.json")
            if lesson_dir is None or script_path is None or meta is None or meta_path is None:
                return False, ["Không tạo được đường dẫn lesson an toàn."]
            if changed:
                # Persist invalidation before the new script. If a process dies
                # between atomic file replacements, the safe state is an old
                # script needing regeneration, never a new script with old media.
                self._advance_revisions(meta, audio=True)
                self._clear_video_meta(meta)
                meta["status"] = "ready" if script_has_content(normalized) else "draft"
                meta["title"] = normalized.get("title", "")
                meta["updated_at"] = _now()
                _write_json(meta_path, meta)
                self._remove_path(self._inside(lesson_dir, "timing_map.json"))
                self._remove_path(self._inside(lesson_dir, "audio"))
            _write_json(script_path, normalized)
            if not changed:
                meta["title"] = normalized.get("title", "")
                meta["updated_at"] = _now()
                _write_json(meta_path, meta)
            return True, errors

    def save_timing(
        self,
        project_id: str,
        lesson_id: str,
        timing: dict,
        *,
        expected_audio_revision: int | None = None,
    ) -> bool:
        """Commit timing only after the audio bundle has been atomically activated."""
        with self._lock:
            meta = self._valid_lesson_meta(project_id, lesson_id)
            if meta is None or not isinstance(timing, dict):
                return False
            if (
                expected_audio_revision is not None
                and audio_source_revision(meta) != expected_audio_revision
            ):
                return False
            path = self._lesson_file(project_id, lesson_id, "timing_map.json")
            meta_path = self._lesson_file(project_id, lesson_id, "lesson.json")
            if path is None or meta_path is None:
                return False
            # A timing map is part of the narrated render contract.  Advance
            # both source revisions before writing it so a render/TTS already
            # in flight cannot publish against the previous timing map.
            # If the process dies during the atomic writes below, the media is
            # stale and needs regeneration rather than being mismatched.
            self._advance_revisions(meta, audio=True)
            self._clear_video_meta(meta)
            meta["audio_bundle_revision"] = 0
            meta["status"] = "ready"
            meta["updated_at"] = _now()
            _write_json(meta_path, meta)
            _write_json(path, timing)
            meta["audio_bundle_revision"] = audio_source_revision(meta)
            meta["updated_at"] = _now()
            _write_json(meta_path, meta)
            return True

    def begin_tts_generation(self, project_id: str, lesson_id: str) -> Optional[dict]:
        """Reserve fresh audio/render revisions before a long-running TTS job.

        Existing audio files stay on disk until a complete replacement is ready,
        but their old revision is no longer considered renderable.
        """
        with self._lock:
            meta = self._valid_lesson_meta(project_id, lesson_id)
            meta_path = self._lesson_file(project_id, lesson_id, "lesson.json")
            if meta is None or meta_path is None:
                return None
            script, _ = self._load_script(project_id, lesson_id, persist=False)
            self._advance_revisions(meta, audio=True)
            self._clear_video_meta(meta)
            meta["status"] = "ready" if script_has_content(script) else "draft"
            meta["updated_at"] = _now()
            _write_json(meta_path, meta)
            return {
                "audio_source_revision": audio_source_revision(meta),
                "render_source_revision": render_source_revision(meta),
            }

    def _owned_audio_job_dir(
        self, project_id: str, lesson_id: str, bundle_dir: str | Path
    ) -> Optional[Path]:
        lesson_dir = self._lesson_dir(project_id, lesson_id)
        if lesson_dir is None:
            return None
        try:
            candidate = Path(bundle_dir).expanduser()
            if not candidate.is_absolute():
                candidate = lesson_dir / candidate
            candidate = candidate.resolve(strict=False)
            candidate.relative_to(lesson_dir.resolve(strict=False))
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
        if candidate.name == "audio" or not candidate.name.startswith(".audio-job-"):
            return None
        return candidate

    @staticmethod
    def _activate_audio_bundle(staged_dir: Path, final_dir: Path) -> None:
        """Atomically replace canonical audio, restoring it if activation fails."""
        backup_dir = final_dir.parent / f".{final_dir.name}.previous-{uuid.uuid4().hex}"
        moved_old = False
        try:
            if final_dir.exists() or final_dir.is_symlink():
                os.replace(final_dir, backup_dir)
                moved_old = True
            os.replace(staged_dir, final_dir)
        except BaseException:
            if moved_old and backup_dir.exists() and not final_dir.exists():
                os.replace(backup_dir, final_dir)
            raise
        if backup_dir.exists() or backup_dir.is_symlink():
            shutil.rmtree(backup_dir, ignore_errors=True)

    def commit_audio_bundle(
        self,
        project_id: str,
        lesson_id: str,
        bundle_dir: str | Path,
        timing: dict,
        *,
        expected_audio_revision: int,
    ) -> bool:
        """Publish a completed TTS bundle only if its inputs are still current."""
        with self._lock:
            meta = self._valid_lesson_meta(project_id, lesson_id)
            lesson_dir = self._lesson_dir(project_id, lesson_id)
            staged_dir = self._owned_audio_job_dir(project_id, lesson_id, bundle_dir)
            if meta is None or lesson_dir is None or staged_dir is None:
                return False
            if audio_source_revision(meta) != expected_audio_revision:
                self._remove_path(staged_dir)
                return False
            full_audio = self._inside(staged_dir, "full_audio.mp3")
            final_audio = self._inside(lesson_dir, "audio")
            timing_path = self._inside(lesson_dir, "timing_map.json")
            meta_path = self._inside(lesson_dir, "lesson.json")
            if (
                full_audio is None
                or final_audio is None
                or timing_path is None
                or meta_path is None
                or not isinstance(timing, dict)
                or not full_audio.is_file()
                or full_audio.stat().st_size <= 100
            ):
                self._remove_path(staged_dir)
                return False
            self._activate_audio_bundle(staged_dir, final_audio)
            # Metadata still says the old audio is stale until both canonical
            # artifacts below are atomically written.
            _write_json(timing_path, timing)
            self._init_revisions(meta)
            self._clear_video_meta(meta)
            meta["audio_bundle_revision"] = expected_audio_revision
            meta["status"] = "ready"
            meta["updated_at"] = _now()
            _write_json(meta_path, meta)
            return True

    def discard_audio_bundle(self, project_id: str, lesson_id: str, bundle_dir: str | Path) -> None:
        """Remove an uncommitted TTS job directory inside its owning lesson."""
        with self._lock:
            staged_dir = self._owned_audio_job_dir(project_id, lesson_id, bundle_dir)
            self._remove_path(staged_dir)

    def publish_rendered_video(
        self,
        project_id: str,
        lesson_id: str,
        video_path: str,
        aspect_ratio: str,
        *,
        expected_render_revision: int,
        expected_audio_revision: int,
    ) -> bool:
        """Publish a render only when its script, visuals and audio still match."""
        with self._lock:
            meta = self._valid_lesson_meta(project_id, lesson_id)
            meta_path = self._lesson_file(project_id, lesson_id, "lesson.json")
            safe_video = self._safe_video_path(video_path)
            timing_path = self._lesson_file(project_id, lesson_id, "timing_map.json")
            audio_path = self._lesson_file(project_id, lesson_id, "audio", "full_audio.mp3")
            if (
                meta is None
                or meta_path is None
                or safe_video is None
                or not safe_video.is_file()
                or timing_path is None
                or audio_path is None
            ):
                return False
            if (
                render_source_revision(meta) != expected_render_revision
                or audio_source_revision(meta) != expected_audio_revision
                or audio_bundle_revision(meta) != expected_audio_revision
            ):
                return False
            if not audio_is_current(meta, _read_json(timing_path, {}), audio_path):
                return False
            self._init_revisions(meta)
            suffix = str(aspect_ratio or "9:16").replace(":", "_")
            meta[f"rendered_video_path_{suffix}"] = str(safe_video)
            meta["rendered_video_path"] = str(safe_video)
            meta["video_source_revision"] = expected_render_revision
            meta["status"] = "done"
            meta["updated_at"] = _now()
            _write_json(meta_path, meta)
            return True

    def delete_lesson(self, project_id: str, lesson_id: str) -> bool:
        # Uses the same RLock as publish/commit; after this returns, a worker
        # in this app process can only observe missing metadata, never recreate
        # the lesson through an atomic JSON write.
        with self._lock:
            lesson_dir = self._lesson_dir(project_id, lesson_id)
            if lesson_dir is None or lesson_dir.is_symlink() or not lesson_dir.is_dir():
                return False
            meta = self._valid_lesson_meta(project_id, lesson_id)
            project_meta = self._valid_project_meta(project_id)
            script, _ = self._load_script(project_id, lesson_id, persist=False)
            self._remove_lesson_outputs(project_id, lesson_id, meta)
            shutil.rmtree(lesson_dir)
            self._remove_lesson_preview_cache(project_id, lesson_id)
            if project_meta is not None:
                self._remove_subtitle_thumb_cache(
                    [(project_meta, script)], {(project_id, lesson_id)}
                )
            self._purge_related_jobs(project_id, lesson_id)
            return True

    def lesson_paths(self, project_id: str, lesson_id: str) -> dict:
        lesson_dir = self._lesson_dir(project_id, lesson_id)
        paths = {
            "dir": lesson_dir,
            "script": self._lesson_file(project_id, lesson_id, "lesson_script.json"),
            "timing": self._lesson_file(project_id, lesson_id, "timing_map.json"),
            "audio_dir": self._lesson_file(project_id, lesson_id, "audio"),
            "full_audio": self._lesson_file(project_id, lesson_id, "audio", "full_audio.mp3"),
        }
        if any(path is None for path in paths.values()):
            raise ValueError("Project hoặc lesson ID không hợp lệ, hoặc đường dẫn thoát sandbox.")
        return {key: str(path) for key, path in paths.items()}


project_store = ProjectStore()
