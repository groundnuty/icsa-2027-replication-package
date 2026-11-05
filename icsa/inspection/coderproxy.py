"""Allowlisting HTTP CONNECT proxy for the blind coder's container (stdlib only: runs as `python3 -I /proxy.py`).

A client gets a tunnel only for `CONNECT <allowed host>:443`. Anything else (another method, port or host, an IP literal
that is not listed, a malformed line, a head over 16 KiB) is answered 403 and logged; the client never resolves a name or
opens a socket of its own, since the proxy resolves and connects. Every decision is one JSONL line (see `Log`).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time

UPSTREAM_PORT = 443          # the only port a tunnel may use; the CONNECT line must say :443 (a test may patch this)
HEAD_CAP = 16 * 1024
HEAD_TIMEOUT_S = 30
CONNECT_TIMEOUT_S = 15
FORBIDDEN = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
BAD_GATEWAY = b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
ESTABLISHED = b"HTTP/1.1 200 Connection established\r\n\r\n"


def _norm(host: str) -> str:
    host = host.strip().lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host.rstrip(".")


def parse_allow(text: str) -> set[str]:
    return {h for h in (_norm(x) for x in text.split(",")) if h}


def decide(request_line: str, allow: set[str]) -> tuple[bool, str, str]:
    """(allowed, target, why): allowed only for `CONNECT <host in allow>:443` (method case-sensitive, host exact).

    `target` is the normalised `host:443` when allowed, else the raw target cut to 200 characters.
    """
    parts = request_line.split()
    if len(parts) != 3 or not parts[2].startswith("HTTP/"):
        return False, request_line[:200], "malformed request line"
    method, target, _ = parts
    if method != "CONNECT":
        return False, target[:200], f"method {method[:20]} not allowed"
    raw_host, sep, port = target.rpartition(":")
    if not sep or not raw_host or (":" in raw_host and not raw_host.startswith("[")):
        return False, target[:200], "malformed CONNECT target"
    if port != "443":
        return False, target[:200], "port not allowed"
    host = _norm(raw_host)
    if not host or host not in {_norm(a) for a in allow}:
        return False, target[:200], "host not allowed"
    return True, f"{host}:443", "allowed"


class Log:
    """JSONL, one line per event, line-buffered and appended; writes are under a lock. No path: stderr."""

    def __init__(self, path: str | None = None):
        self._f = open(path, "a", buffering=1, encoding="utf-8") if path else sys.stderr
        self._lock = threading.Lock()

    def __call__(self, event: str, client: str = "", **fields) -> None:
        line = json.dumps({"event": event, "t": time.time(), "client": client, **fields})
        with self._lock:
            self._f.write(line + "\n")
            self._f.flush()


def _read_head(conn: socket.socket) -> tuple[bytes, bytes]:
    """The request head and any bytes after it. ValueError: over the cap; OSError: timeout or early close."""
    deadline, buf = time.monotonic() + HEAD_TIMEOUT_S, b""
    while (end := buf.find(b"\r\n\r\n")) < 0:
        if len(buf) > HEAD_CAP:
            raise ValueError(f"request head over {HEAD_CAP} bytes")
        left = deadline - time.monotonic()
        if left <= 0:
            raise socket.timeout("head timeout")
        conn.settimeout(left)
        chunk = conn.recv(4096)
        if not chunk:
            raise ConnectionError("closed before the end of the head")
        buf += chunk
    if end > HEAD_CAP:
        raise ValueError(f"request head over {HEAD_CAP} bytes")
    return buf[:end], buf[end + 4:]


def _send(conn: socket.socket, data: bytes) -> None:
    try:
        conn.sendall(data)
    except OSError:
        pass


def _pump(src: socket.socket, dst: socket.socket, counts: dict, key: str) -> None:
    """Copy src to dst until either side closes, then shut both so the other direction ends too."""
    try:
        while data := src.recv(65536):
            dst.sendall(data)
            counts[key] += len(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _handle(conn: socket.socket, addr, allow: set[str], log: Log) -> None:
    client, up = (f"{addr[0]}:{addr[1]}" if isinstance(addr, tuple) else "unix"), None
    try:
        with conn:
            try:
                head, rest = _read_head(conn)
            except ValueError as e:
                log("deny", client, method="", target="", why=str(e))
                _send(conn, FORBIDDEN)
                return
            except OSError as e:
                log("error", client, target="", why=f"reading request head: {type(e).__name__}")
                return
            line = head.split(b"\r\n", 1)[0].decode("latin-1")
            ok, target, why = decide(line, allow)
            if not ok:
                log("deny", client, method=(line.split() or [""])[0][:32], target=target, why=why)
                _send(conn, FORBIDDEN)
                return
            try:
                up = socket.create_connection((target.rsplit(":", 1)[0], UPSTREAM_PORT), timeout=CONNECT_TIMEOUT_S)
            except OSError as e:
                log("error", client, target=target, why=f"connect failed: {type(e).__name__}: {e}")
                _send(conn, BAD_GATEWAY)
                return
            log("allow", client, target=target)
            conn.sendall(ESTABLISHED)
            conn.settimeout(None)
            up.settimeout(None)          # create_connection's timeout stays on the socket
            counts, t0 = {"up": len(rest), "down": 0}, time.monotonic()
            if rest:
                up.sendall(rest)
            t = threading.Thread(target=_pump, args=(conn, up, counts, "up"), daemon=True)
            t.start()
            _pump(up, conn, counts, "down")
            t.join()
            log("close", client, target=target, up_bytes=counts["up"], down_bytes=counts["down"],
                seconds=round(time.monotonic() - t0, 3))
    except OSError as e:
        log("error", client, target="", why=f"{type(e).__name__}: {e}")
    finally:
        if up is not None:
            up.close()


def bind(listen: str) -> socket.socket:
    """`HOST:PORT`, or `unix:/path` (the coder, on no network at all, reaches the proxy only through this socket)."""
    if listen.startswith("unix:"):
        path = listen[len("unix:"):]
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(path)
        os.chmod(path, 0o666)
        srv.listen(128)
        return srv
    host, _, port = listen.rpartition(":")
    return socket.create_server((host or "localhost", int(port)), backlog=128)


def serve(srv: socket.socket, allow: set[str], log: Log) -> None:
    """Log `ready` (the socket is already listening), then one thread per connection until `srv` is closed."""
    name = srv.getsockname()
    log("ready", allow=sorted(allow), listen=f"{name[0]}:{name[1]}" if isinstance(name, tuple) else f"unix:{name}")
    while True:
        try:
            conn, addr = srv.accept()
        except OSError:
            return
        threading.Thread(target=_handle, args=(conn, addr, allow, log), daemon=True).start()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Allowlisting HTTP CONNECT proxy (port 443 only).")
    ap.add_argument("--listen", default="localhost:3128", help="HOST:PORT")
    ap.add_argument("--allow", default="", help="comma-separated host names; empty denies everything")
    ap.add_argument("--log", help="JSONL file, appended; default stderr")
    a = ap.parse_args(argv)
    try:
        serve(bind(a.listen), parse_allow(a.allow), Log(a.log))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
