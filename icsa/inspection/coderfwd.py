"""Inside the coder's container, which has no network at all: forwards localhost:PORT to the proxy's Unix socket, so codex
can use an ordinary HTTPS_PROXY. Stdlib only (runs as `python3 -I /fwd.py`). Writes READY_FILE once listening.

    python3 -I /fwd.py <port> <unix socket path> <ready file>
"""
import socket
import sys
import threading


def _pump(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _serve(c, path):
    try:
        u = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        u.connect(path)
    except OSError:
        c.close()
        return
    threading.Thread(target=_pump, args=(u, c), daemon=True).start()
    _pump(c, u)
    c.close()
    u.close()


def main(argv=None):
    port, path, ready = (argv or sys.argv[1:])[:3]
    srv = socket.create_server(("localhost", int(port)), backlog=64)
    open(ready, "w").close()
    while True:
        c, _ = srv.accept()
        threading.Thread(target=_serve, args=(c, path), daemon=True).start()


if __name__ == "__main__":
    main()
