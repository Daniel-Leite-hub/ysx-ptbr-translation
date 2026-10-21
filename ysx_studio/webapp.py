from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .web_api import WebApi


def run():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args, _ = parser.parse_known_args()
    frozen = bool(getattr(sys, "frozen", False))
    home = Path(sys.executable).parent if frozen else Path(__file__).resolve().parents[1]
    assets = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "frontend"
    api = WebApi(home)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, status, data, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            requested = self.path.split("?", 1)[0]
            path = assets / (requested.lstrip("/") or "index.html")
            path = path.resolve()
            if not path.is_relative_to(assets.resolve()) or not path.is_file():
                return self.respond(404, b"{}")
            return self.respond(200, path.read_bytes(), mimetypes.guess_type(path)[0] or "application/octet-stream")

        def do_POST(self):
            if self.headers.get("X-Studio-Token") != token:
                return self.respond(403, b'{"error":"Acesso recusado"}')
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length < 2_000_000:
                    raise ValueError("Pedido inválido ou muito grande.")
                payload = json.loads(self.rfile.read(length))
                result = api.call(self.path.removeprefix("/api/"), payload)
                data = json.dumps({"result": result}, ensure_ascii=False).encode("utf-8")
                self.respond(200, data)
            except Exception as exc:
                data = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
                self.respond(400, data)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/#{token}"
    if args.browser:
        print(url, flush=True); server.serve_forever(); return
    import webview
    threading.Thread(target=server.serve_forever, daemon=True).start()
    window = webview.create_window("YS X • Translation Studio v2.3.4", url, width=1480, height=940,
                                   min_size=(1120, 720), background_color="#11131b")
    api.window = window
    webview.start()
    api.stop.set(); server.shutdown()
