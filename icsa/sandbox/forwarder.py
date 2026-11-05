"""A plain TCP forwarder from 443 to the provider route's port, for the no-gate control arm (#34, science's ruling of 2 Nov).

The T, T-unpaginated and D controls have no gate: the client dials the provider by the name Onezone gives, on 443. To put them on
the same route as every other run, a forwarder container on the control's bridge listens on 443 and relays the bytes to
`<provider>:<provider_port>`; the control's `/etc/hosts` points the provider's NAME at the forwarder. Nothing in the client changes:
it still connects to the provider's name on 443 and verifies the certificate by that name, which op_worker presents unchanged
(the relay never touches the bytes). Enforcement stays the only difference between the arms.

The relay runs in the campaign image itself (python), so no other image is involved. `ProviderForwarder` is a context manager with
callable `start()` / `stop()` so its cost can be measured on its own; `python -m icsa.sandbox.forwarder IMAGE HOST PORT` starts one,
prints its address and stops it on SIGTERM/SIGINT.
"""
from __future__ import annotations

import signal
import time

from icsa.sandbox import hostops as H
from icsa.sandbox.config import host_alias_args

# The relay: argv = listen_port target_host target_port. One thread per direction per connection; a half-close is passed on.
RELAY = r'''
import socket, sys, threading
lp, th, tp = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
def pump(a, b):
    try:
        while True:
            d = a.recv(1 << 20)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s, how in ((b, socket.SHUT_WR), (a, socket.SHUT_RD)):
            try:
                s.shutdown(how)
            except OSError:
                pass
def serve(c):
    try:
        u = socket.create_connection((th, tp), timeout=60)
        u.settimeout(None)
    except OSError:
        c.close()
        return
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    u.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    t = threading.Thread(target=pump, args=(u, c), daemon=True)
    t.start()
    pump(c, u)
    t.join()
    c.close()
    u.close()
l = socket.socket()
l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
l.bind(("localhost", lp))
l.listen(512)
print("READY", flush=True)
while True:
    c, _ = l.accept()
    threading.Thread(target=serve, args=(c,), daemon=True).start()
'''


def redirected_alias_args(aliases: dict[str, str], hosts, ip: str) -> list[str]:
    """`--add-host` args: the host's aliases as `host_alias_args` gives them, but every name in `hosts` points at `ip`."""
    return host_alias_args({**aliases, **{h: ip for h in hosts}})


class ProviderForwarder:
    def __init__(self, image: str, name: str, target_host: str, target_port: int, aliases: dict[str, str] | None = None,
                 listen_port: int = 443):
        self.image, self.name, self.target_host, self.target_port = image, name, target_host, int(target_port)
        self.aliases, self.listen_port, self.ip = dict(aliases or {}), listen_port, ""

    def start(self, ready_timeout_s: float = 30.0) -> str:
        """Start the container and return its address on the bridge; raises when it is not listening in time."""
        H.docker("rm", "-f", self.name, check=False)
        H.docker("run", "-d", "--rm", "--name", self.name, "--network", "bridge", "--user", "0", "--memory", "512m", "--pids-limit", "4096",
                 *host_alias_args(self.aliases), "--entrypoint", "python", self.image, "-u", "-c", RELAY,
                 str(self.listen_port), self.target_host, str(self.target_port))
        t0 = time.monotonic()
        try:
            while "READY" not in H.docker("logs", self.name, check=False).stdout:
                if time.monotonic() - t0 > ready_timeout_s:
                    raise RuntimeError(f"forwarder {self.name} is not listening after {ready_timeout_s:.0f} s")
                time.sleep(0.2)
            self.ip = H.docker("inspect", "-f", "{{.NetworkSettings.Networks.bridge.IPAddress}}", self.name).stdout.strip()
            if not self.ip:
                raise RuntimeError(f"forwarder {self.name} has no bridge address")
        except BaseException:
            self.stop()
            raise
        return self.ip

    def stop(self) -> None:
        H.docker("rm", "-f", self.name, check=False)

    def __enter__(self) -> "ProviderForwarder":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


if __name__ == "__main__":
    import sys
    from icsa.sandbox.config import default_host_aliases
    image, host, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
    fwd = ProviderForwarder(image, f"icsa-forwarder-{int(time.time())}", host, port, default_host_aliases())
    done = []
    for sg in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sg, lambda *a: done.append(1))
    try:
        print(fwd.start(), flush=True)
        while not done:
            time.sleep(0.5)
    finally:
        fwd.stop()
