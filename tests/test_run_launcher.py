import zipfile

import run


def test_launcher_extracts_portable_runtime(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    monkeypatch.setattr(run, "TOOLS_DIR", tools)
    monkeypatch.setattr(run, "NODE_DIR", tools / "node")
    monkeypatch.setattr(run, "NODE_EXE", tools / "node.exe")
    monkeypatch.setattr(run, "NPM_CLI", tools / "node" / "node_modules" / "npm" / "bin" / "npm-cli.js")
    monkeypatch.setattr(run, "FFMPEG_EXE", tools / "ffmpeg.exe")
    monkeypatch.setattr(run, "FFPROBE_EXE", tools / "ffprobe.exe")

    node_archive = tmp_path / "node.zip"
    with zipfile.ZipFile(node_archive, "w") as archive:
        archive.writestr("node-v22/node.exe", b"node")
        archive.writestr("node-v22/node_modules/npm/bin/npm-cli.js", b"npm")
    run._extract_node(node_archive)

    ffmpeg_archive = tmp_path / "ffmpeg.zip"
    with zipfile.ZipFile(ffmpeg_archive, "w") as archive:
        archive.writestr("ffmpeg/bin/ffmpeg.exe", b"ffmpeg")
        archive.writestr("ffmpeg/bin/ffprobe.exe", b"ffprobe")
    run._extract_ffmpeg(ffmpeg_archive)

    assert run.NODE_EXE.read_bytes() == b"node"
    assert run.NPM_CLI.read_bytes() == b"npm"
    assert run.FFMPEG_EXE.read_bytes() == b"ffmpeg"
    assert run.FFPROBE_EXE.read_bytes() == b"ffprobe"
