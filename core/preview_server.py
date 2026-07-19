"""core/preview_server.py — HTTP server nội bộ phục vụ trang preview live.

WebView cần một URL http:// (file:// bị chặn fetch/CORS). Server này:
  - Chạy nền một lần, cổng tự chọn (loopback).
  - Phục vụ static (HTML/JS/font) trong engines/web/.
  - /script/<token> trả JSON script hiện tại (đăng ký runtime, không đụng đĩa).
  - /audio/<token> stream file audio để player phát tiếng.

Dùng http.server chuẩn thư viện — không thêm phụ thuộc.
"""
import json, logging, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path; logger = logging.getLogger("TubeCraft.PreviewSrv")
from config import ENGINES_DIR; WEB_DIR = Path(ENGINES_DIR) / "web"; _server = None; _port = None; _lock = threading.Lock(); _payloads = {}; _MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".ttf": "font/ttf", ".png": "image/png", ".mp3": "audio/mpeg"}
class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    
    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Cache-Control", "no-store"); self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass
    
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/script/"):
            token = path[len("/script/"):]
            p = _payloads.get(token, {})
            data = {"script": p.get("script") or {}, "timing": p.get("timing"), "audio": bool(p.get("audio"))}
            self._send(200, json.dumps(data, ensure_ascii=False).encode("utf-8"), _MIME[".json"])
            return None
        elif path.startswith("/audio/"):
            token = path[len("/audio/"):]
            audio = _payloads.get(token, {}).get("audio")
            if audio and Path(audio).is_file():
                body = Path(audio).read_bytes()
                self._send(200, body, _MIME[".mp3"])
                return None
            self._send(404, b"no audio", "text/plain")
            return None
        rel = path.lstrip("/") or "preview.html"; fp = (WEB_DIR / rel).resolve()
        
        try:
            fp.relative_to(WEB_DIR.resolve())
            if fp.is_file():
                ext = fp.suffix.lower()
                self._send(200, fp.read_bytes(), _MIME.get(ext, "application/octet-stream"))
                return None
            self._send(404, b"not found", "text/plain")
        except ValueError:
            self._send(403, b"forbidden", "text/plain")

def ensure_server() -> int:
    global _port
    global _server
    with _lock:
        if _server is not None:
            return _port
        srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler); _port = srv.server_address[1]; _server = srv; threading.Thread(target=srv.serve_forever, daemon=True).start(); logger.info(f"Preview server chạy tại http://127.0.0.1:{_port}")
        return _port

def register(token: str, script: dict, timing: dict=None, audio_path: str=None) -> None:
    # Browser preview has its own canvas runtime, so apply the same declarative
    # scene boundary before a payload can reach it.
    from core.schema import validate_script
    clean_script, errors = validate_script(script)
    if errors:
        logger.warning("Preview payload normalized: %s", "; ".join(errors[:2]))
    _payloads[token] = {"script": clean_script, "timing": timing, "audio": audio_path}

def preview_url(token: str, theme="dark", aspect="9:16", style="default", title_color="", text_color="", font="") -> str:
    from urllib.parse import quote; port = ensure_server(); extra = ""
    if title_color:
        extra += f"&titleColor={quote(title_color)}"
    if text_color:
        extra += f"&textColor={quote(text_color)}"
    if font:
        extra += f"&font={quote(font)}"
    return f"http://127.0.0.1:{port}/preview.html?token={token}&theme={theme}&aspect={aspect}&style={style}{extra}"
