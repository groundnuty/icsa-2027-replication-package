"""The exec server of one sandbox's container: what makes `docker exec` possible where Apptainer cannot run instances.

It runs INSIDE the container as the container's command (started by the supervisor under `apptainer exec --containall`, bound read-only at /opt/hpcsbx/execd.py), and nothing else
does: every cell of the sandbox is a child of this process, in the container's one pid namespace, as every `docker exec` process is a child of the container's runtime on Docker. That is
what the sandbox needs and a fresh `apptainer exec` per cell could not give: pids that are unique over the life of the sandbox (the tracer names its per-process files and its start
markers by pid and opens them for append, so two cells that both had pid 12 would merge into one file), processes that survive their cell, one /tmp.

Protocol on the unix socket /hpcsbx-ctl/x.sock (a short host path bound there: sockun paths are at most 108 bytes). Every message is `type(1 byte) length(4 bytes, big endian) data`.
  client -> server: `H` a JSON header {"argv": [...], "env": {...}, "cwd": "/work", "stdin": true} first; then `I` stdin bytes, `C` end of stdin.
  server -> client: `O` stdout bytes, `E` stderr bytes, and last `X` with the exit status as a signed 32-bit integer (a death by signal N is 128+N, as Docker has it).
The cell is started in a session of its own, so its process-group kills do not reach this server. If the client goes away the cell goes on, and its output is read and dropped (a cell
must never get a SIGPIPE from a client that died: Docker's daemon keeps the container's streams). Standard library only: it runs under the image's Python.
"""
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

PIPE_GRACE_S = 1.0
SOCK = os.environ.get("HPCSBX_SOCK", "/hpcsbx-ctl/x.sock")


def recv_exact(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def recv_msg(conn):
    head = recv_exact(conn, 5)
    if head is None:
        return None, None
    kind, n = struct.unpack(">cI", head)
    data = recv_exact(conn, n) if n else b""
    return (kind, data) if data is not None else (None, None)


def serve(conn):
    lock = threading.Lock()
    gone = [False]

    def send(kind, data):
        if gone[0]:
            return
        try:
            with lock:
                conn.sendall(struct.pack(">cI", kind, len(data)) + data)
        except OSError:
            gone[0] = True

    try:
        kind, data = recv_msg(conn)
        if kind != b"H":
            return
        h = json.loads(data)
        env = dict(os.environ)
        env.update(h.get("env") or {})
        try:
            p = subprocess.Popen(h["argv"], env=env, cwd=h.get("cwd") or "/", stdin=subprocess.PIPE if h.get("stdin") else subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        except OSError as e:           # Docker's words for a runtime that could not start the command: the harness reads them (and the status) as infrastructure, not as the cell's own failure
            send(b"E", f"Error response from daemon: OCI runtime exec failed: exec failed: unable to start container process: {h['argv'][:1]}: {e}: unknown\n".encode())
            send(b"X", struct.pack(">i", 126))
            return

        def pump(src, tag):
            while True:
                chunk = os.read(src.fileno(), 1 << 16)
                if not chunk:
                    return
                send(tag, chunk)                      # dropped, not an error, once the client has gone: the cell must not be stopped by it

        pumps = [threading.Thread(target=pump, args=(p.stdout, b"O"), daemon=True), threading.Thread(target=pump, args=(p.stderr, b"E"), daemon=True)]
        for t in pumps:
            t.start()

        def feed():
            try:
                while True:
                    k, d = recv_msg(conn)
                    if k == b"I":
                        p.stdin.write(d)
                        p.stdin.flush()
                    else:                              # `C`, or the client's end: the cell sees end of input
                        break
            except (OSError, ValueError):
                pass
            finally:
                try:
                    p.stdin.close()
                except (OSError, ValueError, AttributeError):
                    pass
        if h.get("stdin"):
            threading.Thread(target=feed, daemon=True).start()
        rc = p.wait()
        end = time.monotonic() + PIPE_GRACE_S
        for t in pumps:
            t.join(max(0.0, end - time.monotonic()))   # what the cell wrote, and what its workers write at once; a worker that still holds the pipes after the grace (a detached one, as the
        send(b"X", struct.pack(">i", rc if rc >= 0 else 128 - rc))      # harness's own test starts) does not keep the exec waiting: Docker's exec returns when the command has exited too
    except Exception as e:  # noqa: BLE001 -- one bad connection never ends the container
        sys.stderr.write(f"hpcsbx-execd: connection failed: {type(e).__name__}: {e}\n")
        sys.stderr.flush()
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    try:
        os.unlink(SOCK)
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK)
    os.chmod(SOCK, 0o600)
    srv.listen(128)
    signal.signal(signal.SIGTERM, lambda *a: os._exit(143))
    print("hpcsbx-execd ready", flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            continue
        threading.Thread(target=serve, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
