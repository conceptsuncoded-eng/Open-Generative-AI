#!/usr/bin/env python3
"""
Serves the production folder and proxies /api/v1/* to https://api.muapi.ai.

Use this when opening console.html from your own machine: the page then talks to
the API same-origin, so no CORS and no mixed-origin surprises. The key is sent
by your browser in the x-api-key header and passed straight through; this server
never logs or stores it.

    python3 serve.py            # http://localhost:8100/console.html
    PORT=9000 python3 serve.py
"""
import os
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
API = "https://api.muapi.ai"
PORT = int(os.environ.get("PORT", 8100))
PASS_HEADERS = {"content-type", "x-api-key", "accept", "range"}
DROP_HEADERS = {"host", "connection", "content-length", "accept-encoding", "origin", "referer"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s  %s\n" % (self.log_date_time_string(), fmt % args))

    # ---------- CORS ----------
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "x-api-key, content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    # ---------- routing ----------
    def _is_api(self):
        return self.path.startswith("/api/")

    def do_GET(self):
        if self._is_api():
            return self._proxy("GET")
        rng = self.headers.get("Range")
        if not rng or not rng.startswith("bytes="):
            return super().do_GET()
        # byte-range playback so browsers can seek in the film
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return self.send_error(404)
        size = os.path.getsize(path)
        try:
            spec = rng.split("=", 1)[1].split(",")[0].strip()
            a, _, b = spec.partition("-")
            start = int(a) if a else 0
            end = int(b) if b else size - 1
        except ValueError:
            return self.send_error(400)
        end = min(end, size - 1)
        if start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        with open(path, "rb") as f:
            f.seek(start)
            data = f.read(end - start + 1)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self._is_api():
            return self._proxy("POST")
        self.send_error(405)

    def do_HEAD(self):
        if self._is_api():
            return self._proxy("HEAD")
        return super().do_HEAD()

    def _proxy(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None

        req = urllib.request.Request(API + self.path, data=body, method=method)
        for k, v in self.headers.items():
            lk = k.lower()
            if lk in DROP_HEADERS:
                continue
            if lk in PASS_HEADERS or lk.startswith("x-"):
                req.add_header(k, v)
        if "x-api-key" not in {k.lower() for k in req.headers}:
            self._fail(401, "No x-api-key header reached the proxy.")
            return

        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
                self.send_response(r.status)
                ctype = r.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if method != "HEAD":
                    self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._fail(502, f"Cannot reach api.muapi.ai from this machine: {type(e).__name__}: {e}")

    def _fail(self, code, msg):
        payload = ('{"error": "%s"}' % msg.replace('"', "'")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"THE LAST 10 MINUTES — console + API proxy")
    print(f"  http://localhost:{PORT}/console.html")
    print(f"  proxying /api/v1/* -> {API}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
