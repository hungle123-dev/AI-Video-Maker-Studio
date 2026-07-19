# Release verification — 2026-07-18

## Result

Verified portable release:

`dist/TubeCraft-hardened-20260718-r2/TubeCraft.exe`

The release was built from the audited independent source tree. It does not copy, replace, or create a `data/` directory in the new release at build time.

## Evidence

| Gate | Result |
| --- | --- |
| Source regression suite | `126 passed, 1 warning` |
| Python dependency consistency | `python -m pip check` passed |
| Renderer syntax | `npm run check` passed |
| Python source syntax | `py_compile` passed for changed runtime modules |
| Portable build command | `./build.ps1 -OutputName TubeCraft-hardened-20260718-r2` exited `0` |
| Packaged runtime smoke | Bundled tools and Chromium passed |
| Packaged scene smoke | All 17 dynamically imported scene modules loaded |
| Packaged desktop smoke | Flet/UI startup imports loaded |
| Packaged render smoke | Node/Canvas/FFmpeg rendered a small MP4; FFprobe confirmed an audio stream |
| Existing release data | 49 files, 115,595,646 bytes; content fingerprint unchanged before/after build |
| New release layout | `TubeCraft.exe`, Node, Canvas, FFmpeg, FFprobe present; no bundled user `data/` |

The sole test warning is Python 3.12's upstream `audioop` deprecation warning from `pydub`; it does not fail the current runtime/test gates.

## Release-specific fixes validated

- PyInstaller explicitly includes all dynamic `core.scenes_td_*`, `core.scenes_wp_*`, and `core.scenes_mn_*` modules. This fixes the old portable bundle's missing-scene failure.
- Windowed EXE smoke tests wait for the actual process exit code, including timeout handling, instead of treating a launched GUI process as a successful test.
- Static preview work is request-scoped, cancellable, and cleans temporary frames; stale workers cannot overwrite the active preview.
- User fonts and generated thumbnail caches live below the portable data directory, while bundled assets stay read-only.
- The Neon Doodle template now asks the model for the safe local `neon_sprite_panel` scene rather than raw JavaScript. It renders the bundled sprite/panel locally.

## Product scope and operational limits

- Video illustrations are local procedural Canvas scenes. The application does not currently provide B-roll/stock footage or AI image generation; no test or release claim should imply otherwise.
- AI and cloud-TTS behavior still depends on the user's own provider account, quota, network, and valid key. Request text is sent to the selected provider when that feature is used.
- A Gemini API key was exposed during this work. It must be revoked/rotated in Google AI Studio/Cloud before normal use. Do not put replacement keys into source, build logs, or chat.

## How to use this release

Run `TubeCraft.exe` from inside the entire `TubeCraft-hardened-20260718-r2` folder. Keep its companion files/folders together. The old `dist/TubeCraft` directory remains untouched; use the new r2 folder for the validated build.
