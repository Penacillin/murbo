"""Static file server for ``web/`` with a tiny JSON API.

``GET /api/puzzles`` auto-lists ``web/puzzles/*.json`` (no manual manifest step
needed when developing) so dropping a freshly-solved puzzle into the folder makes
it appear in the gallery on the next refresh.
"""

from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from murbo.manifest import puzzle_summary


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, web_dir: Path, **kwargs):
        self._web_dir = web_dir
        super().__init__(*args, directory=str(web_dir), **kwargs)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") == "/api/puzzles":
            self._serve_puzzle_list()
            return
        super().do_GET()

    def _serve_puzzle_list(self):
        puzzles_dir = self._web_dir / "puzzles"
        summaries = []
        for path in sorted(puzzles_dir.glob("*.json")):
            if path.name == "manifest.json":
                continue
            try:
                summaries.append(puzzle_summary(json.loads(path.read_text())))
            except (json.JSONDecodeError, KeyError):
                continue
        body = json.dumps({"puzzles": summaries}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter logging
        pass


def serve(web_dir: str | Path, *, host: str = "localhost", port: int = 8000) -> None:
    web_dir = Path(web_dir)
    handler = partial(_Handler, web_dir=web_dir)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Murbo serving {web_dir} at http://{host}:{port}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        httpd.server_close()
