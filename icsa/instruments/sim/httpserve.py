"""Local HTTP Range/listing server whose request log is the ground-truth proxy log.

Endpoints (localhost only):
  GET/HEAD /data/<relpath>   file bytes; single Range (a-b, a-, -n) -> 206; none -> 200;
                             unsatisfiable or multi-range (comma) -> 416.
  GET /list/<reldir>?limit=&token=    JSON listing paginated like Onedata's REST
                             `children` endpoint: {"children": [...], "isLast",
                             "nextPageToken"}; default limit 1000, maximum 10,000
                             (400 badValueNotInRange beyond, as measured in #10).

Each request appends one JSON line to ``log_path``, before the response is sent
(so a client never sees a response whose log line is not yet written):
  {"t", "method", "path", "kind": content|list|head, "status", "range": [start, end_incl]|null, "bytes"}
Listing lines also carry the listing-trace fields (DESIGN.md, "Trace schemas"):
  "limit": int|null (as sent), "token": str|null (as sent), "is_last": bool|null,
  "next_token": str|null (as returned), "entries": int, "first": str|null, "last": str|null
"""
from __future__ import annotations

import base64
import json
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
DEFAULT_LIMIT, MAX_LIMIT = 1000, 10000


def _token(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def _offset(token: str) -> int | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    return int(raw[2:]) if raw.startswith("o:") and raw[2:].isdigit() else None


def parse_range(header: str, size: int) -> tuple[int, int] | None:
    """Return inclusive (start, end) clamped to size, or None if unsatisfiable/unsupported."""
    m = _RANGE_RE.match(header.strip())  # a comma (multi-range) fails the match -> None
    if not m:
        return None
    a, b = m.groups()
    if a == "" and b == "":
        return None
    if a == "":  # suffix
        n = int(b)
        if n == 0 or size == 0:
            return None
        return max(size - n, 0), size - 1
    start = int(a)
    if start >= size:
        return None
    if b == "":
        return start, size - 1
    end = int(b)
    if end < start:
        return None
    return start, min(end, size - 1)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # silence stderr
        pass

    def _record(self, kind, path, status, rng, nbytes, **extra):
        self.server.record(  # type: ignore[attr-defined]
            {"t": time.time(), "method": self.command, "path": path, "kind": kind,
             "status": status, "range": list(rng) if rng else None, "bytes": nbytes, **extra})
        # the same request in the real gate's log format (icsa/sandbox/gate.py), for the
        # cross-check, which runs on both paths
        parts = urlsplit(self.path)
        tag = {"content": "content", "list": "children"}.get(kind)
        self.server.record_gate(  # type: ignore[attr-defined]
            {"host": "local", "method": self.command, "path": parts.path, "query": parts.query,
             "range": self.headers.get("Range"), "decision": "allow", "reason": "allowed", "tag": tag,
             "status": status, "bytes": nbytes, "t": time.time()})

    def _send(self, status, body=b"", headers=None, send_body=True, length=None):
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body) if length is None else length))
        self.end_headers()
        if send_body and body:
            self.wfile.write(body)

    def _resolve(self, rel: str) -> Path | None:
        root: Path = self.server.root  # type: ignore[attr-defined]
        p = (root / rel).resolve()
        if p != root and root not in p.parents:
            return None
        return p

    def _handle(self):
        parts = urlsplit(self.path)
        route = parts.path
        head = self.command == "HEAD"
        if route.startswith("/data/"):
            rel = unquote(route[len("/data/"):])
            kind = "head" if head else "content"
            p = self._resolve(rel)
            if p is None or not p.is_file():
                self._record(kind, rel, 404, None, 0)
                self._send(404, b"not found", send_body=not head)
                return
            size = p.stat().st_size
            if head:
                self._record(kind, rel, 200, None, 0)
                self._send(200, headers={"Accept-Ranges": "bytes"}, length=size, send_body=False)
                return
            hdr = self.headers.get("Range")
            if hdr is None:
                data = p.read_bytes()
                self._record(kind, rel, 200, None, len(data))
                self._send(200, data, {"Accept-Ranges": "bytes"})
                return
            rng = parse_range(hdr, size)
            if rng is None:
                self._record(kind, rel, 416, None, 0)
                self._send(416, b"", {"Content-Range": f"bytes */{size}"})
                return
            s, e = rng
            with open(p, "rb") as f:
                f.seek(s)
                data = f.read(e - s + 1)
            self._record(kind, rel, 206, rng, len(data))
            self._send(206, data, {"Content-Range": f"bytes {s}-{e}/{size}", "Accept-Ranges": "bytes"})
            return
        if route.startswith("/list/") or route == "/list":
            rel = unquote(route[len("/list"):].lstrip("/"))
            q = parse_qs(parts.query)
            limit_s, token = q.get("limit", [None])[0], q.get("token", [None])[0]
            sent = {"limit": int(limit_s) if limit_s and limit_s.lstrip("-").isdigit() else limit_s,
                    "token": token}
            p = self._resolve(rel)
            if p is None or not p.is_dir():
                self._record("list", rel, 404, None, 0, **sent, is_last=None, next_token=None,
                             entries=0, first=None, last=None)
                self._send(404, b"not found", send_body=not head)
                return
            limit = DEFAULT_LIMIT if limit_s is None else sent["limit"]
            offset = 0 if token is None else _offset(token)
            if not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT or offset is None:
                body = json.dumps({"error": {"id": "badValueNotInRange"}}).encode()
                self._record("list", rel, 400, None, len(body), **sent, is_last=None, next_token=None,
                             entries=0, first=None, last=None)
                self._send(400, body, {"Content-Type": "application/json"}, send_body=not head)
                return
            names = sorted(c.name for c in p.iterdir())
            if self.server.merge_pages:      # type: ignore[attr-defined]  # T-unpaginated: as the real gate
                limit = max(len(names), 1)   # (gatepolicy merge_pages), one whole listing, isLast
            page = names[offset:offset + limit]
            children = []
            for n in page:
                c = p / n
                isdir = c.is_dir()
                children.append({"name": n, "size": 0 if isdir else c.stat().st_size,
                                 "type": "DIR" if isdir else "REG"})
            nxt = offset + len(page)
            is_last = nxt >= len(names)
            # Onedata returns a continuation token with every page, the last one included.
            next_token = _token(nxt)
            body = json.dumps({"children": children, "isLast": is_last, "nextPageToken": next_token}).encode()
            self._record("list", rel, 200, None, 0 if head else len(body), **sent, is_last=is_last,
                         next_token=next_token, entries=len(page),
                         first=page[0] if page else None, last=page[-1] if page else None)
            self._send(200, body, {"Content-Type": "application/json"}, send_body=not head)
            return
        self._record("content", route, 404, None, 0)
        self._send(404, b"not found", send_body=not head)

    do_GET = _handle
    do_HEAD = _handle


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, root, log_path, merge_pages=False):
        super().__init__(addr, _Handler)
        self.root = root
        self.merge_pages = merge_pages
        self._log_lock = threading.Lock()
        self._log = open(log_path, "a", buffering=1)
        self._gate_log = open(Path(log_path).with_name("gate_requests.jsonl"), "a", buffering=1)
        self._conns: dict[object, threading.Thread] = {}       # each open connection and the thread serving it
        self._conns_lock = threading.Lock()

    def process_request_thread(self, request, client_address):
        with self._conns_lock:
            self._conns[request] = threading.current_thread()
        super().process_request_thread(request, client_address)

    def shutdown_request(self, request):
        with self._conns_lock:
            self._conns.pop(request, None)
        super().shutdown_request(request)

    def close_connections(self, timeout: float = 5.0) -> None:
        """Ends what a client left open. HTTP/1.1 keeps a connection for the next request, and its thread waits on it for as long
        as the client lives: a stopped server would leave one thread per client, and a later fork would copy their locks."""
        with self._conns_lock:
            open_now = dict(self._conns)
        for sock in open_now:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        for thread in open_now.values():
            thread.join(timeout)

    def record(self, entry: dict):
        with self._log_lock:
            self._log.write(json.dumps(entry) + "\n")
            self._log.flush()

    def record_gate(self, entry: dict):
        with self._log_lock:
            self._gate_log.write(json.dumps(entry) + "\n")
            self._gate_log.flush()

    def close_log(self):
        with self._log_lock:
            self._log.close()
            self._gate_log.close()


class RangeServer:
    def __init__(self, root: Path, log_path: Path, *, merge_pages: bool = False):
        """merge_pages: T-unpaginated, as the real gate: one whole listing for any request. A
        second log, gate_requests.jsonl next to log_path, has the real gate's format."""
        self.root = Path(root).resolve()
        self.log_path = Path(log_path)
        self.merge_pages = merge_pages
        self._srv: _Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._srv is not None, "server not started"
        return f"http://localhost:{self._srv.server_address[1]}"

    def start(self) -> "RangeServer":
        self._srv = _Server(("localhost", 0), self.root, self.log_path, self.merge_pages)
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._srv is None:
            return
        self._srv.shutdown()
        self._srv.server_close()
        self._srv.close_connections()
        self._srv.close_log()
        self._thread.join(timeout=5)
        self._srv = None

    def __enter__(self) -> "RangeServer":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
