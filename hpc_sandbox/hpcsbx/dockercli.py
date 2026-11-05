"""`docker`, as far as the icsa-2027 sandbox harness uses it, on a site_a compute node (see README.md for the mapping and the departures).

Every subcommand and every `-f` template the harness uses is implemented, and nothing else: another one exits 2 and says so, because a guess at what a template means would put
a made-up value in a run record. What is not there to report (a MAC address, interface counters, a cgroup) is reported as not there, never as zero.

Containers:
  * a gate (`run -d` of a command): a detached supervisor (supervisor.py) runs `apptainer exec --containall` and keeps its log, its exit code and its times;
  * the agent (`run -d` of `sleep infinity`): no process at all, only a record. Each `exec` is its own `apptainer exec --containall` with the record's binds, environment and
    per-container /tmp and /dev/shm (fuse2fs filesystems of the sizes `--tmpfs` and `--shm-size` ask for);
  * a one-shot (`run --rm`, foreground): the same command, run now.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import images, procs, quota, synthcg
from .common import (APPTAINER, HOME, NEVER, PORT_OFFSET, SERVER_VERSION, STATE, TOOLS, ShimError, container_dir, container_names, ensure_dirs, flock, load_container,
                     now_iso, proc_stat, raise_nofile, read_json, resolve_container, write_json)

RUN_VALUE_FLAGS = {"--name", "--network", "--net", "--label", "-l", "--add-host", "--cap-drop", "--cap-add", "--security-opt", "--user", "-u", "--pids-limit", "--memory", "-m",
                   "--memory-swap", "--cpus", "--ulimit", "--tmpfs", "--shm-size", "-v", "--volume", "--mount", "--entrypoint", "-e", "--env", "--oom-score-adj", "--device", "-w",
                   "--workdir", "--hostname", "-h", "--restart", "--ipc", "--pid", "--stop-timeout", "--log-driver"}
RUN_BOOL_FLAGS = {"-d", "--detach", "--rm", "--init", "--read-only", "-i", "--interactive", "-t", "--tty", "--privileged"}
EXEC_CONNECT_WAIT_S = 20.0       # `docker exec` comes right after `docker run -d`: the server inside has to be up first (apptainer's start is under a second)
GATE_ADDR_WAIT_S = 3.0           # a container on `bridge` gets its address when the harness connects it to the sandbox network, a moment after `run -d`


def die(msg: str, code: int = 1):
    raise ShimError(msg, code)


# ---------------------------------------------------------------------------------------------- arguments
def split_flags(argv: list, value_flags: set, bool_flags: set) -> tuple:
    """(options, positional): options is a list of (flag, value-or-None) in order. Stops at the first positional, which is the image or the container; the rest is the command."""
    opts, i = [], 0
    while i < len(argv):
        a = argv[i]
        if not a.startswith("-") or a == "-":
            return opts, argv[i:]
        if a == "--":
            return opts, argv[i + 1:]
        flag, eq, val = a.partition("=") if a.startswith("--") else (a, "", "")
        if a.startswith("-") and not a.startswith("--") and len(a) > 2 and a[:2] in value_flags:     # -eK=V, -v/x:/y
            opts.append((a[:2], a[2:]))
        elif flag in value_flags:
            if eq:
                opts.append((flag, val))
            else:
                i += 1
                if i >= len(argv):
                    die(f"flag needs an argument: {flag}", 125)
                opts.append((flag, argv[i]))
        elif flag in bool_flags:
            opts.append((flag, None))
        else:
            die(f"unknown flag: {flag} (this docker stand-in implements only what the sandbox harness uses)", 125)
        i += 1
    return opts, []


def parse_volume(v: str) -> dict:
    parts = v.split(":")
    if len(parts) < 2 or not parts[0].startswith("/") or not parts[1].startswith("/"):
        die(f"invalid volume specification: {v!r} (only host-path binds)", 125)
    opts = parts[2].split(",") if len(parts) > 2 else []
    return {"src": parts[0], "dst": parts[1], "ro": "ro" in opts, "propagation": None}


def parse_mount(m: str) -> dict:
    kv = {}
    for item in m.split(","):
        k, _, v = item.partition("=")
        kv[k] = v
    if kv.get("type", "volume") != "bind":
        die(f"unsupported mount type {kv.get('type')!r}", 125)
    src, dst = kv.get("src") or kv.get("source"), kv.get("dst") or kv.get("destination") or kv.get("target")
    if not src or not dst:
        die(f"invalid mount: {m!r}", 125)
    return {"src": src, "dst": dst, "ro": "readonly" in kv or "ro" in kv, "propagation": kv.get("bind-propagation")}


# ---------------------------------------------------------------------------------------------- the container record
def new_id() -> str:
    return secrets.token_hex(32)


def build_spec(argv: list) -> dict:
    opts, rest = split_flags(argv, RUN_VALUE_FLAGS, RUN_BOOL_FLAGS)
    if not rest:
        die("docker run: requires at least 1 argument", 125)
    spec: dict = {"id": new_id(), "created": now_iso(), "labels": {}, "env": {}, "binds": [], "add_hosts": [], "networks": [], "tmpfs": {}, "shm_bytes": None, "detach": False,
                  "rm": False, "entrypoint": None, "user": None, "workdir": None, "name": None, "limits": {}}
    for flag, val in opts:
        if flag in ("-d", "--detach"):
            spec["detach"] = True
        elif flag == "--rm":
            spec["rm"] = True
        elif flag == "--name":
            spec["name"] = val
        elif flag in ("--network", "--net"):
            spec["networks"].append(val)
        elif flag in ("--label", "-l"):
            k, _, v = val.partition("=")
            spec["labels"][k] = v
        elif flag == "--add-host":
            n, _, ip = val.rpartition(":")
            spec["add_hosts"].append([n, "localhost" if ip == "host-gateway" else ip])
        elif flag in ("-e", "--env"):
            k, eq, v = val.partition("=")
            if eq:
                spec["env"][k] = v
            elif k in os.environ:
                spec["env"][k] = os.environ[k]
        elif flag in ("-v", "--volume"):
            spec["binds"].append(parse_volume(val))
        elif flag == "--mount":
            spec["binds"].append(parse_mount(val))
        elif flag == "--tmpfs":
            path, _, o = val.partition(":")
            kv = dict(x.partition("=")[::2] for x in o.split(",") if x)
            spec["tmpfs"][path] = {"size": quota.parse_size(kv["size"]) if "size" in kv else None, "mode": int(kv.get("mode", "1777"), 8)}
        elif flag == "--shm-size":
            spec["shm_bytes"] = quota.parse_size(val)
        elif flag == "--entrypoint":
            spec["entrypoint"] = val
        elif flag in ("--user", "-u"):
            spec["user"] = val
        elif flag in ("-w", "--workdir"):
            spec["workdir"] = val
        elif flag in ("--memory", "-m", "--memory-swap", "--cpus", "--pids-limit", "--ulimit", "--oom-score-adj"):
            spec["limits"][flag.lstrip("-")] = val           # recorded, not enforced: no cgroup of our own on this host
        # --cap-*, --security-opt, --device, --init, --read-only, -i/-t, --hostname, --restart: accepted; the SIF is read-only and Apptainer drops what it drops
    img = images.resolve(rest[0])
    spec["image"] = img["id"]
    cfg, cmd = img["config"], rest[1:]
    ep = [spec["entrypoint"]] if spec["entrypoint"] else list(cfg.get("Entrypoint") or [])
    spec["cmd"] = ep + (cmd if cmd else ([] if spec["entrypoint"] else list(cfg.get("Cmd") or [])))     # --entrypoint drops the image's Cmd, as Docker does
    if not spec["cmd"]:
        die("No command specified", 125)
    return spec


def is_idle(spec: dict) -> bool:
    """`docker run -d IMAGE sleep infinity`: the sandbox's agent container (and the control arm's), which Docker keeps alive for `docker exec` to run cells in."""
    return spec["cmd"] == ["sleep", "infinity"]


# `-S`: no `site`, so no `.pth` and no sitecustomize: the image loads the study's tracer into EVERY Python start (icsa_site_boot.pth), and the exec server is not a cell. With the tracer in it,
# its launches of `timeout` were recorded in the trace as launches without a start (the harness's own test, test_cell_start, found it) and it wrote a start marker of its own. Its children,
# the cells, are started by it with the container's environment and do load the tracer, as on Docker.
EXECD_CMD = ["python", "-S", "/opt/hpcsbx/execd.py"]
CTL_IN = "/hpcsbx-ctl"


def ctl_dir(spec: dict) -> Path:
    """A short path on the host (a unix socket path is at most 108 bytes; container names reach 70) whose directory is bound into the container at /hpcsbx-ctl."""
    return HOME / "s" / spec["id"][:10]


# ---------------------------------------------------------------------------------------------- the Apptainer command
def sandbox_ip(spec: dict, state: dict):
    return state.get("sandbox_ip")


def apptainer_cmd(spec: dict, cdir: Path, cmd: list, workdir: "str | None", extra_env: dict, state: dict) -> tuple:
    """(argv, env): what to run for `cmd` in this container. Image Env first, then the container's, then the exec's: later wins, as in Docker. The environment goes in as
    APPTAINERENV_* of the process, not as arguments: `--env` takes a comma-separated list, and a value may hold commas, and a token must not be in `ps`."""
    img = images.resolve(spec["image"])
    env = dict(images.env_list(img))
    env.update(spec["env"])
    env.update(extra_env)
    ip = state.get("sandbox_ip")
    gate_ips = sorted({a for _, a in spec["add_hosts"] if a.startswith("127.") and a != "localhost"})      # the agent's names all map to its gate's address
    portmap = bool(gate_ips) or bool(spec.get("is_gate") and ip)
    if portmap:
        # The network shim is configured by a FILE bound read-only into the container and loaded through /etc/ld.so.preload, not by environment variables and LD_PRELOAD: a cell that clears its
        # environment, or starts children with env={}, keeps it (portmap.c says what it still cannot stop).
        lines = ["mode agent" if gate_ips else "mode gate", f"offset {PORT_OFFSET}"]
        if gate_ips:
            lines += [f"gate {','.join(gate_ips)}"] + [f"deny_port {p}" for p in os.environ.get("HPCSBX_DENY_PORTS", "8443,30443").split(",") if p.strip().isdigit()]
        else:
            lines.append(f"bind {ip}")
        (cdir / "portmap.conf").write_text("\n".join(lines) + "\n")
        (cdir / "ld.so.preload").write_text("/opt/hpcsbx/portmap.so\n")
        (cdir / "resolv.conf").write_text("")            # an agent resolves only what /etc/hosts names (its gate); a gate keeps the node's resolver for its upstream
    wd = workdir or spec["workdir"] or img["config"].get("WorkingDir") or "/"
    argv = [APPTAINER, "-s", "exec", "--containall", "--pwd", wd]
    # $HOME: Apptainer ignores APPTAINERENV_HOME and sets it from --home. The image says HOME=/work (the agent's work disk): when that is a bind of this container, make it the home.
    home = env.get("HOME")
    home_bind = next((b for b in spec["binds"] if home and b["dst"] == home and not b["ro"]), None)
    argv += ["--home", f"{home_bind['src']}:{home_bind['dst']}"] if home_bind else ["--no-home"]
    for b in spec["binds"]:
        if b is not home_bind:
            argv += ["-B", f"{b['src']}:{b['dst']}" + (":ro" if b["ro"] else "")]
    for path in spec["tmpfs"]:
        argv += ["-B", f"{cdir / 'mnt' / path.strip('/').replace('/', '_')}:{path}"]
    if spec["shm_bytes"]:
        argv += ["-B", f"{cdir / 'mnt' / 'shm'}:/dev/shm"]
    argv += ["-B", f"{cdir / 'hosts'}:/etc/hosts:ro"]
    if spec.get("execd"):
        argv += ["-B", f"{ctl_dir(spec)}:{CTL_IN}", "-B", f"{TOOLS / 'hpcsbx' / 'execd.py'}:/opt/hpcsbx/execd.py:ro"]
    if portmap:
        argv += ["-B", f"{TOOLS / 'portmap' / 'portmap.so'}:/opt/hpcsbx/portmap.so:ro", "-B", f"{cdir / 'portmap.conf'}:/opt/hpcsbx/portmap.conf:ro",
                 "-B", f"{cdir / 'ld.so.preload'}:/etc/ld.so.preload:ro"]
        if gate_ips:
            argv += ["-B", f"{cdir / 'resolv.conf'}:/etc/resolv.conf:ro"]
    raise_nofile()          # inherited by what is started: the closest to the nofile the harness asks Docker for that this host allows
    env["HPCSBX_CID"] = f"{spec['name']}:{secrets.token_hex(6)}"     # the one marker procs.note_namespace looks for, to learn which pid namespace this start is
    penv = {k: v for k, v in os.environ.items() if not k.startswith(("APPTAINERENV_", "SINGULARITYENV_"))}
    penv.update({f"APPTAINERENV_{k}": v for k, v in env.items()})
    return argv + [images.sif_path(img), *cmd], penv


def preexec_for(spec: dict):
    """What `docker run --oom-score-adj N` does, for the processes started for this container (and only those: the `docker exec` client keeps the driver's score, which a test of the harness
    checks). A user may raise the value, never lower it. Returns the function for Popen's preexec_fn, or None."""
    adj = spec.get("limits", {}).get("oom-score-adj")
    if adj is None:
        return None

    def f():
        try:
            with open("/proc/self/oom_score_adj", "w") as fh:
                fh.write(str(int(adj)))
        except (OSError, ValueError):
            pass
    return f


def write_hosts(spec: dict, cdir: Path) -> None:
    lines = ["localhost localhost", "ipv6-1 localhost ip6-localhost ip6-loopback"]
    for name, ip in spec["add_hosts"]:
        lines.append(f"{ip} {name}")
    (cdir / "hosts").write_text("\n".join(lines) + "\n")


def mount_scratch_fs(spec: dict, cdir: Path) -> None:
    """The container's /tmp and /dev/shm as size-limited filesystems (`Sandbox._check_capacity` measures them from inside)."""
    todo = [(p, t["size"], t["mode"], p.strip("/").replace("/", "_")) for p, t in spec["tmpfs"].items() if t["size"]]
    if spec["shm_bytes"]:
        todo.append(("/dev/shm", spec["shm_bytes"], 0o1777, "shm"))
    for path, size, mode, key in todo:
        img, mnt = cdir / f"{key}.img", cdir / "mnt" / key
        quota.make_image(img, size)
        quota.mount_image(img, mnt)
        os.chmod(mnt, mode)


GATELOG_BYTES = 8 * 1024 ** 3            # the gate's /var/gate: its request log and the spool of a whole-file transfer (up to S2, 3.8 GB); sparse, only what is written takes RAM


def mount_gate_disk(spec: dict, cdir: Path) -> None:
    """The gate's `/var/gate` (the sandbox's gatelog directory) is a fuse2fs-mounted ext4 image, not a plain tmpfs directory. The spool of a D transfer is file data the gate writes; on a tmpfs those
    pages are SHMEM charged to the writer's cgroup and cannot be reclaimed, so a 3.8 GB spool in the gate's 1 GiB step killed the gate (exit 137, seen on the first D runs of the pooled dispatchers and
    reproduced with a real-size transfer). On a disk filesystem the gate's own sync-and-drop of the spool (gate.py SPOOL_SYNC_BYTES) works as designed, and the bytes are held by the fuse2fs daemon,
    which is outside the gate's step. The mount is made over the directory the harness already created, before the gate starts."""
    for b in spec["binds"]:
        if b["dst"] == "/var/gate" and not b["ro"]:
            img = cdir / "gatelog.img"
            quota.make_image(img, GATELOG_BYTES)
            quota.mount_image(img, b["src"])
            spec.setdefault("extra_mounts", []).append(b["src"])


def unmount_scratch_fs(cdir: Path) -> None:
    mnt = cdir / "mnt"
    if mnt.is_dir():
        for m in sorted(mnt.iterdir()):
            quota.unmount(m)
    spec = read_json(cdir / "spec.json", {}) or {}
    for m in spec.get("extra_mounts", []):
        quota.unmount(m)


# ---------------------------------------------------------------------------------------------- networks
def net_path(name: str) -> Path:
    return STATE / "networks" / f"{name}.json"


def net_load(name: str) -> dict:
    n = read_json(net_path(name))
    if n is None:
        die(f"network {name} not found")
    return n


def all_networks() -> list:
    d = STATE / "networks"
    return [x for x in (read_json(p) for p in sorted(d.glob("*.json"))) if x]


def address_in(subnet: str, offset: int) -> str:
    """The sandbox's loopback address from its subnet: 10.200.a.b/28 -> 127.200.a.(b+offset). The subnets of two sandboxes never overlap, so neither do their addresses."""
    import ipaddress
    net = ipaddress.ip_network(subnet, strict=False)
    a = [int(x) for x in str(net.network_address).split(".")]
    return f"127.{a[1]}.{a[2]}.{a[3] + offset}"


def cmd_network(args: list) -> None:
    if not args:
        die("docker network: requires a subcommand", 125)
    sub, rest = args[0], args[1:]
    if sub == "create":
        opts, pos = split_flags(rest, {"--opt", "-o", "--subnet", "--label", "--driver", "-d", "--gateway", "--ip-range"}, {"--internal"})
        if len(pos) != 1:
            die("docker network create: requires exactly 1 argument", 125)
        name, subnet, labels = pos[0], None, {}
        for f, v in opts:
            if f == "--subnet":
                subnet = v
            elif f == "--label":
                labels[v.partition("=")[0]] = v.partition("=")[2]
        if not subnet:
            die("docker network create: this stand-in needs --subnet (the sandbox's loopback address comes from it)", 125)
        import ipaddress
        want = ipaddress.ip_network(subnet, strict=False)
        with flock(STATE / "networks.lock"):
            if net_path(name).exists():
                die(f"network with name {name} already exists")
            for n in all_networks():
                if ipaddress.ip_network(n["subnet"]).overlaps(want):
                    die("invalid pool request: Pool overlaps with other one on this address space")
            write_json(net_path(name), {"id": new_id(), "name": name, "subnet": str(want), "labels": labels, "containers": {}, "created": now_iso()})
        print(name)
    elif sub == "ls":
        opts, _ = split_flags(rest, {"--filter", "-f", "--format"}, {"-q", "--quiet", "--no-trunc"})
        flt = [v for f, v in opts if f in ("--filter", "-f")]
        ids = []
        for n in all_networks():
            ok = True
            for x in flt:
                k, _, v = x.partition("=")
                if k == "driver":
                    ok = ok and v == "none"          # no bridge networks here: the harness asks for Docker's own bridges and gets none
                elif k == "label":
                    lk, eq, lv = v.partition("=")
                    ok = ok and lk in n["labels"] and (not eq or n["labels"][lk] == lv)
                else:
                    die(f"network ls: filter {k!r} not implemented", 2)
            if ok:
                ids.append(n["id"][:12])
        print("\n".join(ids))
    elif sub == "inspect":
        opts, pos = split_flags(rest, {"-f", "--format"}, set())
        fmt = next((v for f, v in opts if f in ("-f", "--format")), None)
        found = []
        for ref in pos:
            n = next((n for n in all_networks() if n["name"] == ref or n["id"].startswith(ref)), None)
            if n is None:
                die(f"network {ref} not found")
            found.append(n)
        for n in found:
            if fmt is None:
                print(json.dumps([net_doc(n)], indent=1))
            elif fmt == "{{json .IPAM.Config}}":
                print(json.dumps([{"Subnet": n["subnet"]}]))
            elif fmt == "{{range .Containers}}{{.Name}} {{end}}":
                print("".join(f"{c} " for c in n["containers"]))
            elif fmt == '{{.Name}}\t{{index .Labels "org.icsa.owner"}}':
                print(f"{n['name']}\t{n['labels'].get('org.icsa.owner', '')}")
            else:
                die(f"network inspect: template {fmt!r} not implemented", 2)
    elif sub == "connect":
        _, pos = split_flags(rest, {"--ip"}, set())
        if len(pos) != 2:
            die("docker network connect: requires exactly 2 arguments", 125)
        connect(pos[0], resolve_container(pos[1]))
    elif sub == "disconnect":
        _, pos = split_flags(rest, set(), {"-f", "--force"})
        if len(pos) == 2:
            with flock(STATE / "networks.lock"):
                n = read_json(net_path(pos[0]))
                if n:
                    n["containers"].pop(pos[1], None)
                    write_json(net_path(pos[0]), n)
    elif sub == "rm":
        _, pos = split_flags(rest, set(), {"-f", "--force"})
        for ref in pos:
            with flock(STATE / "networks.lock"):
                n = next((x for x in all_networks() if x["name"] == ref or x["id"].startswith(ref)), None)
                if n is None:
                    die(f"network {ref} not found")
                if n["containers"]:
                    die(f"error while removing network: network {ref} id {n['id'][:12]} has active endpoints")
                net_path(n["name"]).unlink()
            print(ref)
    else:
        die(f"docker network {sub}: not implemented", 2)


def net_doc(n: dict) -> dict:
    return {"Name": n["name"], "Id": n["id"], "Created": n["created"], "Driver": "none", "Internal": True, "IPAM": {"Config": [{"Subnet": n["subnet"]}]},
            "Containers": {i: {"Name": c, "IPv4Address": ip + "/32"} for c, (i, ip) in ((c, (v["id"], v["ip"])) for c, v in n["containers"].items())}, "Labels": n["labels"]}


def connect(netname: str, cname: str) -> None:
    c = load_container(cname)
    with flock(STATE / "networks.lock"):
        n = net_load(netname)
        used = {v["ip"] for v in n["containers"].values()}
        offset = 2
        while address_in(n["subnet"], offset) in used:
            offset += 1
        ip = address_in(n["subnet"], offset)
        n["containers"][cname] = {"id": c["spec"]["id"], "ip": ip}
        write_json(net_path(netname), n)
    with flock(c["dir"] / "state.lock"):
        st = read_json(c["dir"] / "state.json", {})
        st.setdefault("networks", {})[netname] = ip
        st["sandbox_ip"] = st.get("sandbox_ip") or ip          # a sandbox's own network is the one whose address decides its place on loopback; `bridge` has none
        write_json(c["dir"] / "state.json", st)


# ---------------------------------------------------------------------------------------------- run / exec
def cmd_run(args: list) -> int:
    if os.environ.get("HPCSBX_OVERRIDE") != "1" and os.environ.get("ICSA_HPC_SANDBOX") != "1" and os.environ.get("HPCSBX_ALLOW_PLAIN") != "1":
        # a process that starts sandboxes here without the harness override would read Docker's cgroups, which are not here: its runs would end as infrastructure errors, silently and at scale.
        # Refusing the first container makes it fail at the start. (HPCSBX_ALLOW_PLAIN=1 is for the stand-in's own hand tests.)
        die("this docker stand-in starts containers only for a process with HPCSBX_OVERRIDE=1 (the harness override, hpc_sandbox/override); see README.md", 125)
    spec = build_spec(args)
    name = spec["name"] or ("hpcsbx_" + secrets.token_hex(4))
    spec["name"] = name
    spec["is_gate"] = any(os.path.basename(a) == "gate.py" for a in spec["cmd"])
    if is_idle(spec):                      # the agent: the exec server is its command (execd.py says why), so every cell is a child of it in one pid namespace
        spec["execd"], spec["cmd"], spec["detach"] = True, list(EXECD_CMD), True
    cdir = container_dir(name)
    with flock(STATE / "containers.lock"):
        if (cdir / "spec.json").exists():
            die(f'Conflict. The container name "/{name}" is already in use by container "{read_json(cdir / "spec.json")["id"]}". You have to remove (or rename) that container to be able to reuse that name.')
        (cdir / "mnt").mkdir(parents=True, exist_ok=True)
        os.chmod(cdir, 0o700)
        write_json(cdir / "spec.json", spec)
        write_json(cdir / "state.json", {"status": "created", "running": False, "exit_code": 0, "started_at": NEVER, "finished_at": NEVER, "networks": {}, "sandbox_ip": None,
                                         "oom_baseline": synthcg.step_oom_kills()})
    try:
        write_hosts(spec, cdir)
        if spec.get("execd"):
            ctl_dir(spec).mkdir(parents=True, exist_ok=True)
            os.chmod(ctl_dir(spec), 0o700)
        mount_scratch_fs(spec, cdir)
        mount_gate_disk(spec, cdir)
        write_json(cdir / "spec.json", spec)
        for n in spec["networks"]:
            if n not in ("bridge", "none", "host"):          # Docker's own: there is no network namespace here to put a container in or to cut it off from
                connect(n, name)
    except BaseException:
        remove(name)
        raise
    if spec["detach"]:
        # Docker's `run -d` returns with the container running. Here it is "running" from now (StartedAt is set once, now, and never again: infradeath compares it), though a gate
        # that has no address yet is only started by its supervisor when the harness has connected it to its sandbox network, which comes after this returns.
        with flock(cdir / "state.lock"):
            st = read_json(cdir / "state.json")
            st.update(status="running", running=True, started_at=now_iso())
            write_json(cdir / "state.json", st)
        out, err = open(cdir / "out.log", "ab"), open(cdir / "err.log", "ab")
        subprocess.Popen([sys.executable, str(TOOLS / "bin" / "hpcsbx-supervisor"), name], stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, close_fds=True)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not read_json(cdir / "state.json", {}).get("supervisor_pid"):
            time.sleep(0.02)
        if not read_json(cdir / "state.json", {}).get("supervisor_pid"):
            remove(name)
            die("the supervisor did not start within 15 s")
        print(spec["id"])
        return 0
    # a one-shot: run it now, here
    try:
        st = read_json(cdir / "state.json")
        argv, penv = apptainer_cmd(spec, cdir, spec["cmd"], None, {}, st)
        p = subprocess.Popen(argv, env=penv, stdin=subprocess.DEVNULL, preexec_fn=preexec_for(spec))
        t = threading.Thread(target=procs.note_namespace, args=(cdir, penv["APPTAINERENV_HPCSBX_CID"], 20.0, lambda: p.poll() is not None), daemon=True)
        t.start()
        return p.wait()
    finally:
        if spec["rm"]:
            remove(name)


def cmd_exec(args: list) -> int:
    opts, pos = split_flags(args, {"-u", "--user", "-w", "--workdir", "-e", "--env"}, {"-i", "--interactive", "-t", "--tty", "-d", "--detach", "--privileged"})
    if len(pos) < 2:
        die("docker exec: requires at least 2 arguments", 125)
    name = resolve_container(pos[0])
    c = load_container(name)
    if not c["state"].get("running"):
        die(f"Container {c['spec']['id']} is not running", 1)
    cmd = pos[1:]
    if is_interface_probe(cmd):
        # metrics._IFACES reads the interfaces of the container's network namespace. There is none: every container shares the node's, so the counters would be the node's, and a number
        # that is not the sandbox's is worse than none. A failed exec is "not known" to the caller (`bytes_moved` records None).
        sys.stderr.write("no network namespace on this host: interface counters would be the node's, not this sandbox's\n")
        return 1
    workdir, extra = None, {}
    for f, v in opts:
        if f in ("-w", "--workdir"):
            workdir = v
        elif f in ("-e", "--env"):
            k, eq, val = v.partition("=")
            if eq:
                extra[k] = val
            elif k in os.environ:
                extra[k] = os.environ[k]
    interactive = any(f in ("-i", "--interactive") for f, _ in opts)
    if c["spec"].get("execd"):
        return exec_via_server(c, cmd, workdir or c["spec"]["workdir"] or images.resolve(c["spec"]["image"])["config"].get("WorkingDir") or "/", extra, interactive)
    argv, penv = apptainer_cmd(c["spec"], c["dir"], cmd, workdir, extra, c["state"])
    return relay(c, argv, penv, interactive=interactive)


def exec_via_server(c: dict, cmd: list, cwd: str, extra: dict, interactive: bool) -> int:
    """`docker exec` as a client of the container's exec server (execd.py has the protocol): the cell is a child of the server, in the container's own pid namespace. If this client dies the
    cell goes on and its output is dropped, as on Docker. A container whose server is not there (it has exited, or the container is not running) is reported as Docker reports it, which
    `Sandbox._docker_failed` routes as infrastructure."""
    import json as _json
    import socket
    import struct
    path = str(ctl_dir(c["spec"]) / "x.sock")
    deadline = time.monotonic() + EXEC_CONNECT_WAIT_S
    sock = None
    while sock is None:
        st = read_json(c["dir"] / "state.json", {})
        if not st.get("running"):
            die(f"Container {c['spec']['id']} is not running", 1)
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(path)
            sock = s
        except OSError:
            s.close()
            if time.monotonic() > deadline:
                die(f"Container {c['spec']['id']} is not running: its exec server did not answer within {EXEC_CONNECT_WAIT_S:.0f} s", 1)
            time.sleep(0.05)

    def send(kind: bytes, data: bytes = b"") -> None:
        sock.sendall(struct.pack(">cI", kind, len(data)) + data)

    def recv_exact(n: int):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf
    not_running = f"Error response from daemon: Container {c['spec']['id']} is not running: the exec server ended before the command did\n"
    try:
        send(b"H", _json.dumps({"argv": cmd, "env": extra, "cwd": cwd, "stdin": interactive}).encode())
    except OSError:
        sys.stderr.write(not_running)
        return 1
    if interactive:
        def feed():
            try:
                while True:
                    chunk = sys.stdin.buffer.read1(1 << 16)
                    if not chunk:
                        break
                    send(b"I", chunk)
                send(b"C")
            except (OSError, ValueError):
                pass
        threading.Thread(target=feed, daemon=True).start()
    try:
        while True:
            head = recv_exact(5)
            if head is None:
                break
            kind, n = struct.unpack(">cI", head)
            data = recv_exact(n) if n else b""
            if data is None:
                break
            if kind == b"O":
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            elif kind == b"E":
                sys.stderr.buffer.write(data)
                sys.stderr.buffer.flush()
            elif kind == b"X":
                return struct.unpack(">i", data)[0]
    except BrokenPipeError:
        return 141                          # the harness stopped reading
    except OSError:
        pass                                # the connection was reset: the server went with the container
    sys.stderr.write(not_running)
    return 1


def relay(c: dict, argv: list, penv: dict, interactive: bool) -> int:
    """`docker exec` for a container WITHOUT an exec server (a gate, a sidecar: commands run beside the container's own, which is not a pid-namespace holder here): one `apptainer exec`
    in the container's binds and environment, its output carried to this process's stdout and stderr. The command does not hold the caller's pipes (its output goes to two unlinked files this
    process reads as they grow), so killing this client closes them at once and the command goes on, as on Docker. An exit of 255 with a line `FATAL:` on stderr is Apptainer failing to start
    the command, reported as Docker reports a runtime that could not run its command (exit 126, `OCI runtime exec failed`), which `Sandbox._docker_failed` reads as infrastructure.
    A command that keeps writing after this client has gone leaves its output in those files (tmpfs) until it ends: the commands run this way are the harness's short probes."""
    token = penv["APPTAINERENV_HPCSBX_CID"].split(":", 1)[1]
    out_p, err_p = c["dir"] / f"x.{token}.out", c["dir"] / f"x.{token}.err"
    out_w, err_w = open(out_p, "wb"), open(err_p, "wb")
    out_r, err_r = open(out_p, "rb"), open(err_p, "rb")
    out_p.unlink()
    err_p.unlink()
    try:
        p = subprocess.Popen(argv, env=penv, stdin=subprocess.PIPE if interactive else subprocess.DEVNULL, stdout=out_w, stderr=err_w, preexec_fn=preexec_for(c["spec"]))
    except OSError as e:
        sys.stderr.write(f"Error response from daemon: OCI runtime exec failed: {e}\n")
        return 126
    finally:
        out_w.close()
        err_w.close()
    threading.Thread(target=procs.note_namespace, args=(c["dir"], penv["APPTAINERENV_HPCSBX_CID"], 20.0, lambda: p.poll() is not None), daemon=True).start()
    if interactive:
        def feed():
            try:
                while True:
                    chunk = sys.stdin.buffer.read1(1 << 16)
                    if not chunk:
                        break
                    p.stdin.write(chunk)
                    p.stdin.flush()
            except (OSError, ValueError):
                pass
            finally:
                try:
                    p.stdin.close()
                except OSError:
                    pass
        threading.Thread(target=feed, daemon=True).start()
    tail = b""

    def pump() -> None:
        nonlocal tail
        for src, dst, keep in ((out_r, sys.stdout.buffer, False), (err_r, sys.stderr.buffer, True)):
            while True:
                data = src.read(1 << 16)
                if not data:
                    break
                dst.write(data)
                dst.flush()
                if keep:
                    tail = (tail + data)[-8192:]
    try:
        while p.poll() is None:
            pump()
            time.sleep(0.01)
        pump()
    except BrokenPipeError:
        pass                                     # the harness stopped reading: what the command does from here is not this process's to say
    rc = p.returncode
    if rc == 255 and b"FATAL:" in tail:
        sys.stderr.write("Error response from daemon: OCI runtime exec failed: exec failed: the container runtime could not start the command (apptainer said FATAL above)\n")
        sys.stderr.flush()
        return 126
    return rc if rc >= 0 else 128 - rc


def is_interface_probe(cmd: list) -> bool:
    return len(cmd) >= 3 and cmd[0] == "sh" and cmd[1] == "-c" and "/sys/class/net/" in cmd[2]


# ---------------------------------------------------------------------------------------------- inspect
def main_pid_of(c: dict) -> int:
    """The container's command (the gate; the exec server), recorded by its supervisor with its start time: a pid that has since been given to another process is not it."""
    return procs.recorded_main(c["state"]) or 0


def inspect_doc(c: dict) -> dict:
    spec, st = c["spec"], c["state"]
    nets = {}
    for nn, ip in (st.get("networks") or {}).items():
        nets[nn] = {"IPAddress": ip, "MacAddress": "", "NetworkID": ""}
    if "bridge" in spec["networks"] and "bridge" not in nets:
        nets["bridge"] = {"IPAddress": "", "MacAddress": "", "NetworkID": ""}       # no MAC: `bridge_mac` raises, the counters are recorded as unknown
    return {"Id": spec["id"], "Created": spec["created"], "Name": "/" + spec["name"], "Image": spec["image"], "RestartCount": 0,
            "State": {"Status": st.get("status", "created"), "Running": bool(st.get("running")), "Paused": False, "Restarting": False, "OOMKilled": False, "Dead": False,
                      "Pid": main_pid_of(c), "ExitCode": st.get("exit_code", 0), "Error": st.get("error", ""), "StartedAt": st.get("started_at", NEVER),
                      "FinishedAt": st.get("finished_at", NEVER)},
            "Config": {"Labels": spec["labels"], "Image": spec["image"], "Env": [f"{k}={v}" for k, v in {**images.env_list(images.resolve(spec["image"])), **spec["env"]}.items()]},
            "Mounts": [{"Type": "bind", "Source": b["src"], "Destination": b["dst"], "Mode": "ro" if b["ro"] else "", "RW": not b["ro"], "Propagation": b["propagation"] or "rprivate"}
                       for b in spec["binds"]],
            "NetworkSettings": {"Networks": nets}}


def render(doc: dict, fmt: str) -> str:
    """Exactly the templates the harness passes. Anything else is refused (exit 2)."""
    s, st, ns = doc, doc["State"], doc["NetworkSettings"]["Networks"]
    simple = {
        "{{.Id}}": lambda: s["Id"],
        "{{.State.Running}}": lambda: str(st["Running"]).lower(),
        "{{.State.Pid}}": lambda: str(st["Pid"]),
        "{{.State.Pid}}|{{.Id}}|{{.State.Running}}": lambda: f"{st['Pid']}|{s['Id']}|{str(st['Running']).lower()}",
        "{{.State.Running}}|{{.State.ExitCode}}|{{.RestartCount}}": lambda: f"{str(st['Running']).lower()}|{st['ExitCode']}|{s['RestartCount']}",
        "{{.State.OOMKilled}}|{{.State.Status}}|{{.State.ExitCode}}": lambda: f"{str(st['OOMKilled']).lower()}|{st['Status']}|{st['ExitCode']}",
        "{{.State.StartedAt}} {{.State.Pid}} {{.Id}} {{.Image}}": lambda: f"{st['StartedAt']} {st['Pid']} {s['Id']} {s['Image']}",
        "{{json .NetworkSettings.Networks}}": lambda: json.dumps(ns),
        "{{json .Config.Env}}": lambda: json.dumps(doc["Config"]["Env"]),
        "{{.NetworkSettings.Networks.bridge.IPAddress}}": lambda: ns.get("bridge", {}).get("IPAddress", ""),
    }
    if fmt in simple:
        return simple[fmt]()
    m = re.fullmatch(r'\{\{\(index \.NetworkSettings\.Networks "([^"]+)"\)\.IPAddress\}\}', fmt)
    if m:
        if m.group(1) not in ns:
            raise ShimError(f"template: executing {fmt!r}: map has no entry for key {m.group(1)!r}")
        return ns[m.group(1)]["IPAddress"]
    m = re.fullmatch(r'\{\{range \.Mounts\}\}\{\{if eq \.Destination "([^"]+)"\}\}\{\{\.Source\}\}\{\{end\}\}\{\{end\}\}', fmt)
    if m:
        return "".join(x["Source"] for x in s["Mounts"] if x["Destination"] == m.group(1))
    raise ShimError(f"inspect: template {fmt!r} is not one the sandbox harness uses; this stand-in will not guess what it means", 2)


def cmd_inspect(args: list, kind: "str | None" = None) -> int:
    opts, pos = split_flags(args, {"-f", "--format", "--type"}, {"-s", "--size"})
    fmt = next((v for f, v in opts if f in ("-f", "--format")), None)
    typ = kind or next((v for f, v in opts if f == "--type"), None)
    rc, docs = 0, []
    for ref in pos:
        try:
            if typ == "network":
                die(f"network {ref} not found")
            docs.append((ref, inspect_doc(load_container(resolve_container(ref)))))
        except ShimError as e:
            msg = str(e)
            if kind is None and typ is None:        # plain `docker inspect x` says it differently
                sys.stderr.write(f"Error response from daemon: {msg}\n" if "No such container" not in msg else f"Error: No such object: {ref}\n")
            else:
                sys.stderr.write(f"Error response from daemon: {msg}\n")
            rc = 1
    if fmt is None:
        print(json.dumps([d for _, d in docs], indent=1))
    else:
        for _, d in docs:
            print(render(d, fmt))
    return rc


# ---------------------------------------------------------------------------------------------- the rest
def cmd_logs(args: list) -> int:
    _, pos = split_flags(args, {"--tail", "-n", "--since"}, {"-f", "--follow", "-t", "--timestamps"})
    c = load_container(resolve_container(pos[0]))
    for fn, stream in (("out.log", sys.stdout), ("err.log", sys.stderr)):
        try:
            stream.write((c["dir"] / fn).read_text(errors="replace"))
        except OSError:
            pass
        stream.flush()
    return 0


def cmd_ps(args: list) -> int:
    opts, _ = split_flags(args, {"--filter", "-f", "--format"}, {"-a", "--all", "-q", "--quiet", "--no-trunc"})
    allc = any(f in ("-a", "--all") for f, _ in opts)
    quiet = any(f in ("-q", "--quiet") for f, _ in opts)
    fmt = next((v for f, v in opts if f == "--format"), None)
    flt = [v for f, v in opts if f in ("--filter", "-f")]
    rows = []
    for n in container_names():
        c = read_json(container_dir(n) / "spec.json")
        st = read_json(container_dir(n) / "state.json", {})
        if c is None or not (allc or st.get("running")):
            continue
        ok = True
        for x in flt:
            k, _, v = x.partition("=")
            if k == "label":
                lk, eq, lv = v.partition("=")
                ok = ok and lk in c["labels"] and (not eq or c["labels"][lk] == lv)
            elif k == "name":
                ok = ok and re.search(v, c["name"]) is not None
            else:
                die(f"ps: filter {k!r} not implemented", 2)
        if ok:
            rows.append(c)
    for c in rows:
        if quiet:
            print(c["id"][:12])
        elif fmt == "{{.Names}}":
            print(c["name"])
        elif fmt is not None:
            m = re.fullmatch(r'\{\{\.ID\}\}\t\{\{\.Names\}\}\t\{\{\.Label "([^"]+)"\}\}', fmt)
            if not m:
                die(f"ps: format {fmt!r} not implemented", 2)
            print(f"{c['id'][:12]}\t{c['name']}\t{c['labels'].get(m.group(1), '')}")
        else:
            print(f"{c['id'][:12]}  {c['name']}")
    return 0


def host_of(c: dict, cpath: str) -> "str | None":
    """The host path behind a container path, through the longest bind that holds it; None when no bind does (the image's own files are not copied from)."""
    best = None
    for b in c["spec"]["binds"]:
        d = b["dst"].rstrip("/")
        if (cpath == d or cpath.startswith(d + "/")) and (best is None or len(d) > len(best[0])):
            best = (d, b["src"])
    return None if best is None else os.path.join(best[1], cpath[len(best[0]):].lstrip("/"))


def container_path(c: dict, path: str) -> str:
    """A path inside the container as a path on the host, resolving symlinks AS THE CONTAINER SEES THEM: an absolute link target is a container path (`/work/results`), not a host
    path, and a link that leaves every bind is not followed out of the sandbox. Docker's `cp` resolves inside the container the same way; a plain `os.path.realpath` on the host path
    would read an absolute target against the host and could copy another run's files."""
    comps = [x for x in path.split("/") if x]
    cur: list = []
    i = hops = 0
    while i < len(comps):
        name = comps[i]
        if name == ".":
            i += 1
            continue
        if name == "..":
            cur = cur[:-1]
            i += 1
            continue
        cand = cur + [name]
        host = host_of(c, "/" + "/".join(cand))
        if host is not None and os.path.islink(host):
            hops += 1
            if hops > 40:
                die(f"Could not find the file {path} in container {c['spec']['name']}: too many levels of symbolic links")
            target = os.readlink(host)
            if target.startswith("/"):
                cur = []
            comps = [x for x in target.split("/") if x] + comps[i + 1:]
            i = 0
            continue
        cur = cand
        i += 1
    host = host_of(c, "/" + "/".join(cur))
    if host is None:
        die(f"Could not find the file {path} in container {c['spec']['name']}")
    return host


def cmd_cp(args: list) -> int:
    _, pos = split_flags(args, set(), {"-a", "-L", "--archive", "--follow-link"})
    if len(pos) != 2 or ":" not in pos[0] or ":" in pos[1]:
        die("docker cp: only CONTAINER:SRC to a host DEST is implemented", 2)
    cname, _, path = pos[0].partition(":")
    c = load_container(resolve_container(cname))
    src = container_path(c, path)
    if not os.path.exists(src):
        die(f"Could not find the file {path} in container {cname}")
    r = subprocess.run(["cp", "-r", src, pos[1]], capture_output=True, text=True)
    if r.returncode != 0:
        die(r.stderr.strip()[:300])
    return 0


def cmd_kill(args: list) -> int:
    opts, pos = split_flags(args, {"-s", "--signal"}, set())
    sig = next((v for f, v in opts if f in ("-s", "--signal")), "KILL")
    num = getattr(signal, "SIG" + sig.upper().removeprefix("SIG"), None) if not sig.isdigit() else int(sig)
    if num is None:
        die(f"Error response from daemon: Invalid signal: {sig}")
    for ref in pos:
        c = load_container(resolve_container(ref))
        if not c["state"].get("running"):
            die(f"Cannot kill container: {ref}: Container {c['spec']['id']} is not running")
        mp = procs.recorded_main(c["state"])
        if mp is None:
            procs.signal_all(c["dir"], num)
        else:
            os.kill(mp, num)
        print(ref)
    return 0


def cmd_stop(args: list) -> int:
    opts, pos = split_flags(args, {"-t", "--time", "-s", "--signal"}, set())
    t = float(next((v for f, v in opts if f in ("-t", "--time")), "10"))
    for ref in pos:
        name = resolve_container(ref)
        c = load_container(name)
        if c["state"].get("running"):
            mp = procs.recorded_main(c["state"])
            if mp:
                os.kill(mp, signal.SIGTERM)
            deadline = time.monotonic() + t
            while time.monotonic() < deadline and read_json(c["dir"] / "state.json", {}).get("running"):
                time.sleep(0.05)
            if read_json(c["dir"] / "state.json", {}).get("running"):
                procs.kill_all(c["dir"], 10.0)
                wait_exited(c["dir"], 10.0)
        print(ref)
    return 0


def mark_exited(cdir: Path, code: int) -> None:
    with flock(cdir / "state.lock"):
        st = read_json(cdir / "state.json", {})
        st.update(status="exited", running=False, exit_code=code, finished_at=now_iso())
        write_json(cdir / "state.json", st)


def wait_exited(cdir: Path, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and read_json(cdir / "state.json", {}).get("running"):
        time.sleep(0.05)


def remove(name: str) -> None:
    cdir = container_dir(name)
    if not (cdir / "spec.json").exists() and not cdir.exists():
        return
    left = procs.kill_all(cdir, 10.0)
    st = read_json(cdir / "state.json", {})
    sup = st.get("supervisor_pid")
    if sup and (proc_stat(sup) or (None,) * 4)[3] == st.get("supervisor_start"):      # the same process, not one that has since been given its pid
        try:
            os.kill(sup, signal.SIGKILL)
        except OSError:
            pass
    unmount_scratch_fs(cdir)
    for n in all_networks():
        if name in n["containers"]:
            with flock(STATE / "networks.lock"):
                x = read_json(net_path(n["name"]))
                if x:
                    x["containers"].pop(name, None)
                    write_json(net_path(n["name"]), x)
    mnt = cdir / "mnt"
    extra = (read_json(cdir / "spec.json", {}) or {}).get("extra_mounts", [])
    if left or (mnt.is_dir() and any(quota.is_fuse_mount(m) for m in mnt.iterdir())) or any(quota.is_fuse_mount(m) for m in extra):
        raise ShimError(f"container {name} could not be removed: processes or mounts are left")
    spec = read_json(cdir / "spec.json", {}) or {}
    cid = spec.get("id")
    extra = ([str(synthcg.cg_dir(cid))] if cid else []) + ([str(ctl_dir(spec))] if spec.get("execd") else [])
    subprocess.run(["rm", "-rf", "--one-file-system", str(cdir), *extra], check=False)


def cmd_rm(args: list) -> int:
    _, pos = split_flags(args, set(), {"-f", "--force", "-v", "--volumes"})
    rc = 0
    for ref in pos:
        try:
            name = resolve_container(ref)
        except ShimError as e:
            sys.stderr.write(f"Error response from daemon: {e}\n")
            rc = 1
            continue
        remove(name)
        print(ref)
    return rc


def cmd_image(args: list) -> int:
    if not args or args[0] != "inspect":
        die("docker image: only inspect is implemented", 2)
    opts, pos = split_flags(args[1:], {"-f", "--format"}, set())
    fmt = next((v for f, v in opts if f in ("-f", "--format")), None)
    for ref in pos:
        try:
            img = images.resolve(ref)
        except ShimError as e:
            sys.stderr.write(f"Error response from daemon: {e}\n")
            return 1
        if fmt is None:
            print(json.dumps([{"Id": img["id"], "RepoTags": img["tags"], "RootFS": {"Type": "layers", "Layers": img["diff_ids"]}, "Config": img["config"]}], indent=1))
        elif fmt == "{{.Id}}":
            print(img["id"])
        elif fmt == "{{json .RootFS.Layers}}":
            print(json.dumps(img["diff_ids"]))
        else:
            die(f"image inspect: template {fmt!r} not implemented", 2)
    return 0


def cmd_info(args: list) -> int:
    opts, _ = split_flags(args, {"-f", "--format"}, set())
    fmt = next((v for f, v in opts if f in ("-f", "--format")), None)
    ver = subprocess.run([APPTAINER, "--version"], capture_output=True, text=True).stdout.strip().replace("apptainer version ", "")
    vals = {"ServerVersion": f"{SERVER_VERSION} {ver}", "Driver": "sif-squashfuse+fuse2fs", "CgroupDriver": "none (slurm step)", "CgroupVersion": "2"}
    if fmt == "{{.ServerVersion}}|{{.Driver}}|{{.CgroupDriver}}|{{.CgroupVersion}}":
        print("|".join(vals[k] for k in ("ServerVersion", "Driver", "CgroupDriver", "CgroupVersion")))
    elif fmt == "{{.Server.Version}}" or fmt == "{{.ServerVersion}}":
        print(vals["ServerVersion"])
    elif fmt is None:
        print("Server Version: " + vals["ServerVersion"])
    else:
        die(f"info: template {fmt!r} not implemented", 2)
    return 0


def main(argv: list) -> int:
    ensure_dirs()
    if not argv:
        die("docker: no command", 125)
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "run":
            return cmd_run(rest)
        if cmd == "exec":
            return cmd_exec(rest)
        if cmd == "inspect":
            return cmd_inspect(rest)
        if cmd == "container" and rest and rest[0] == "inspect":
            return cmd_inspect(rest[1:], "container")
        if cmd == "logs":
            return cmd_logs(rest)
        if cmd == "ps":
            return cmd_ps(rest)
        if cmd == "cp":
            return cmd_cp(rest)
        if cmd == "kill":
            return cmd_kill(rest)
        if cmd == "stop":
            return cmd_stop(rest)
        if cmd == "rm":
            return cmd_rm(rest)
        if cmd == "network":
            cmd_network(rest)
            return 0
        if cmd == "image":
            return cmd_image(rest)
        if cmd == "info":
            return cmd_info(rest)
        if cmd == "build":
            # nothing is built on a node. The tests ask for a build of the tree's Dockerfile under a tag of their own; with HPCSBX_BUILD_AS naming a registered image (the campaign's pinned
            # one), that tag becomes another name of it and its id is printed as `docker build -q` prints one. Without it a build is refused.
            opts, _ = split_flags(rest, {"-f", "--file", "-t", "--tag"}, {"-q", "--quiet"})
            as_name = os.environ.get("HPCSBX_BUILD_AS")
            if not as_name:
                die("docker build: the images are built once, elsewhere (ociunpack.py, build_images.py); set HPCSBX_BUILD_AS=<image> to alias a tag to one", 2)
            img = None
            for f, v in opts:
                if f in ("-t", "--tag"):
                    img = images.alias(v, as_name)
            print(img["id"] if img else images.load()["images"][0]["id"])
            return 0
        die(f"docker {cmd}: not implemented by this stand-in (it implements only what the sandbox harness uses)", 2)
    except ShimError as e:
        sys.stderr.write(f"Error response from daemon: {e}\n")
        return e.code
