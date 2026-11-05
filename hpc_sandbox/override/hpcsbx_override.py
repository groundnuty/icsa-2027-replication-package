"""The harness's reads of Docker's cgroups, pointed at the stand-in's records. Installed by the interpreter's start-up (hpcsbx.pth) when HPCSBX_OVERRIDE=1, like B's provider
override: outside the checked tree (`snapshot/codecheck.py` walks `icsa/`), so the code stamp never sees it.

The sandbox code reads four things that only Docker's cgroup layout provides: `teardown._cgroup_procs` (the container's processes: `Sandbox.quiesce`, `collect`),
`Sandbox._cgroup_dir` and `_other_cgroup_dir` (`memory.events`, `memory.peak`, `memory.stat`, `cgroup.procs`) and `Sandbox._oom_counters_of` (the gate's and sidecar's `oom_kill`).
Each is replaced by a function that returns the stand-in's own answer (hpcsbx.synthcg says what each file holds and what it does not). Nothing else in `icsa/` is replaced, and
`install` refuses to run if one of these four is not where it expects, so a changed harness cannot be silently half-covered.

It also adds a `hpc_sandbox` record to every sandbox's metadata: the departures from the Docker sandbox, in words, so no run on this host passes for one on a Docker host.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
DEPARTURES = {
    "backend": "hpcsbx: Apptainer (SIF, --containall) on a site_a compute node; `docker` and `sudo` are stand-ins (hpc_sandbox)",
    "network": "NO network isolation: every container shares the node's network (no network namespace exists for a user here). A shim (portmap.so, loaded into every dynamically linked process of the container "
               "through /etc/ld.so.preload and configured by a read-only file, so a cell cannot drop it by clearing its environment) lets the agent's processes connect() only to their own gate, to loopback "
               "(except the provider's port) and to AF_UNIX; every other destination fails ENETUNREACH; the resolver is empty, so only /etc/hosts names resolve. A STATIC binary or a raw connect(2) syscall "
               "(ctypes) is NOT stopped: a deliberate bypass is possible, and the agent holds the dataset token (ONEDATA_TOKEN), as on Docker. The gate's port 443 is 20443 on a loopback address of its own",
    "limits": "no kernel limits on memory, cpu, pids or open files (the operator accepts none; nofile is raised to the node's hard limit, 51200, not 1,048,576). The memory limit the harness "
              "gives Docker is enforced instead by the container's supervisor ten times a second (processes' anon+shmem over the limit: the process with the most of it is killed, oom and oom_kill counted), "
              "so a spike inside a tenth of a second is not caught. No cgroup per container: memory counters are sums of process RSS, not the kernel's",
    "user": "cells run as the host user, not uid 10001",
    "processes": "the agent container is one long-lived container with an exec server inside it (execd.py); every cell is a child of it in the container's one pid namespace, in a session of its own, so pids are unique over "
                 "the sandbox's life and a process a cell leaves running outlives its cell, as on Docker. The container has no pid 1 of its own that a cell cannot signal: the exec server is a process a cell could kill, "
                 "which ends the container (the next exec is refused as `not running`)",
    "disks": "work, trace, /tmp and /dev/shm are fuse2fs (ext4 image) filesystems of the sizes the harness asks for; fuse2fs reports 10% of a filesystem as not available, so the work disk is built 1/0.9 larger "
             "and statvfs then offers what the harness meant. The 10% is REAL for the images that are not enlarged (measured: writes stop at f_bavail): the trace disk, /tmp and /dev/shm offer ~10% less writable space than the size asked for (trace ~959 MB of 1 GiB against 1,050 MB on a VM)",
    "environment": "the agent's environment carries HPCSBX_CID, which Docker's does not, and its /proc shows the exec server and the other processes of its own container; /etc/ld.so.preload, /opt/hpcsbx and an empty /etc/resolv.conf are bound in",
    "byte_counters": "not available (no network namespace): between_sites_rx and registered_rx are None",
    "host_memory": "the dispatcher's host-memory hold reads the room left under the Slurm job's cgroup limit (hpcsbx/jobmem.py), not the node's MemAvailable; the sandboxes' disks are node RAM (tmpfs) and count against it",
    "earlyoom": "none on this host: an empty journal; memory kills are the kernel's, read from Slurm's step cgroup as a tripwire",
}


INSTALLED = False
_FACTS: dict = {}
S1_BYTES = 4254680853


def _sha256(path) -> "str | None":
    import hashlib
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def runtime_facts() -> dict:
    """What `hpc_runtime` in every run's sandbox record says: the departures, and which code ran (hashes of this module, of the shim, of the image archive), on which job and node. Computed once."""
    if _FACTS:
        return dict(_FACTS)
    import socket
    import subprocess
    home = Path(os.environ.get("HPCSBX_HOME") or f"/tmp/hpcsbx-{os.getuid()}")
    reg = {}
    try:
        import json
        reg = json.loads((home / "images" / "images.json").read_text())
    except (OSError, ValueError):
        pass
    try:
        ver = subprocess.run(["apptainer", "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        ver = None
    node = socket.gethostname().split(".")[0]
    _FACTS.update({
        "kind": "hpc_runtime",
        "isolation": "none (shared host network; see departures.network)",
        "limits": ("memory: the container runs in a Slurm step of its own whose cgroup the kernel limits (memory.max about 99% of the 17586 MiB asked for the agent: main's 17 GiB; 1035 MiB for the gate); "
                   "OOM kills are counted from the step's own memory.events; cpu: pinned by sched_setaffinity to 4 cores of its own (an affinity, not a quota: a cell could widen it); pids: none; "
                   "nofile: the node's hard limit") if os.environ.get("HPCSBX_POOL") == "1" else
                  "memory: the container supervisor kills the largest process over the limit, checked 10 times a second; cpu: none; pids: none; nofile: the node's hard limit",
        "pool": os.environ.get("HPCSBX_POOL") == "1",
        "backend": "apptainer",
        "apptainer_version": ver,
        "host": f"site_a/{node}",
        "node": node,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_step_id": os.environ.get("SLURM_STEP_ID"),
        "launch": os.environ.get("ICSA_B_PROVIDER"),
        "override_sha256": _sha256(__file__),
        "portmap_so_sha256": _sha256(TOOLS / "portmap" / "portmap.so"),
        "portmap_c_sha256": _sha256(TOOLS / "portmap" / "portmap.c"),
        "image_archive_sha256": reg.get("archive_sha256"),
        "image_ids": {i["name"]: {"manifest_digest": i["id"], "sif_sha256": i.get("sif_sha256")} for i in reg.get("images", [])},
        "provider_image": (lambda f: __import__("json").loads(f.read_text()) if f.exists() else None)(TOOLS / "provider_image.json"),
        "s1_bytes": S1_BYTES, "s1_bytes_source": "constant: sum of the sizes of the 15,340 files of the run VM's s1z copy (real_sandbox.S1_LOCAL_DIR is absent on a node)",
        "departures": dict(DEPARTURES),
    })
    return dict(_FACTS)


def install() -> None:
    global INSTALLED
    if INSTALLED:           # the .pth installs it at interpreter start and the module installs itself on import: once
        return
    sys.path.insert(0, str(TOOLS))
    from hpcsbx import synthcg
    from icsa.sandbox import sandbox as SB
    from icsa.sandbox import teardown as TD
    for mod, names in (("teardown", ["_cgroup_procs"]),):
        for n in names:
            if not hasattr(TD, n):
                raise RuntimeError(f"hpcsbx override: icsa.sandbox.{mod}.{n} is not there: the harness changed, this override must be read again")
    for n in ("_cgroup_dir", "_other_cgroup_dir", "_oom_counters_of", "start"):
        if not hasattr(SB.Sandbox, n):
            raise RuntimeError(f"hpcsbx override: Sandbox.{n} is not there: the harness changed, this override must be read again")

    def cgroup_procs(cid):
        name = synthcg.by_id(cid)
        if name is None:
            return None
        from hpcsbx import procs
        from hpcsbx.common import container_dir
        return procs.pids(container_dir(name))

    def cgroup_dir(self):
        return synthcg.refresh(self.name)

    def other_cgroup_dir(self, container):
        return synthcg.refresh(container)

    def oom_counters_of(cid):
        name = synthcg.by_id(cid)
        d = synthcg.refresh(name) if name else None
        if d is None or not (d / "memory.events").exists():
            return None
        ev = dict(ln.split() for ln in (d / "memory.events").read_text().splitlines())
        return {"oom": int(ev.get("oom", 0)), "oom_kill": int(ev.get("oom_kill", 0))}

    TD._cgroup_procs = cgroup_procs
    SB.Sandbox._cgroup_dir = cgroup_dir
    SB.Sandbox._other_cgroup_dir = other_cgroup_dir
    SB.Sandbox._oom_counters_of = staticmethod(oom_counters_of)
    real_start = SB.Sandbox.start.__func__

    def start(cls, *a, **kw):
        sbx = real_start(cls, *a, **kw)
        rt = runtime_facts()
        try:           # which Slurm steps (and so which cgroups, cores and limits) this sandbox's gate and agent ran in
            from hpcsbx.common import container_dir, read_json
            steps = {}
            for role, cname in (("agent", sbx.name), ("gate", sbx.name + "-gate")):
                st = read_json(container_dir(cname) / "state.json", {}) or {}
                steps[role] = {k: st.get(k) for k in ("pool_slot", "step_id", "step_node", "cores", "memory_max", "cgroup")}
            rt["steps"] = steps
        except Exception as e:  # noqa: BLE001 -- the stamp is evidence, its absence is recorded, the run goes on
            rt["steps"] = {"error": repr(e)[:200]}
        sbx._meta["hpc_runtime"] = rt
        return sbx

    SB.Sandbox.start = classmethod(start)
    # S1's size comes from the sum of the file sizes of a local copy at /mnt/volume2/icsa-2027/s1z (real_sandbox.S1_LOCAL_DIR), which a node does not have (15,340 files, 4.1 GiB): the limits derive
    # from min(S1, S2) and S2 is smaller, so the number only has to be the real one. Measured once on the run VM's copy: 15,340 files, 4,254,680,853 bytes.
    from icsa.harness import real_sandbox as RS
    RS.s1_bytes = lambda local_dir=None: S1_BYTES
    # the host-memory hold reads MemAvailable of the NODE; the kernel kills at the JOB's cgroup limit, and tmpfs (the sandboxes' disks) is charged to it: read the room left in the job
    from icsa.campaign import hostmem
    from hpcsbx import jobmem
    if jobmem.limit() is not None:
        hostmem.read_mem_available = jobmem.available
    if os.environ.get("HPCSBX_ICSA_BREAK") == "1":      # tests of the failure path (verify_override.sh)
        raise RuntimeError("HPCSBX_ICSA_BREAK=1")
    wr = os.environ.get("HPCSBX_WORK_ROOT")
    if wr:      # where the sandboxes' disks, gate logs and spool are (default: ICSA_DATA/sandboxes, i.e. the node's tmpfs, RAM). SandboxConfig.work_root is a dataclass default and reap.work_root() reads it too.
        from icsa.sandbox.config import SandboxConfig
        SandboxConfig.work_root = Path(wr)
        Path(wr).mkdir(parents=True, exist_ok=True)
    INSTALLED = True


EXIT_NOT_INSTALLED = 87      # as boverride.py's: a process of a run on this host that cannot get the override must not run, or it would read Docker's cgroups that are not there


def install_or_exit() -> None:
    try:
        install()
    except BaseException as e:  # noqa: BLE001
        try:
            os.write(2, f"hpcsbx_override: NOT INSTALLED in a process of a run on a site_a node: {e!r}\n".encode())
        finally:
            os._exit(EXIT_NOT_INSTALLED)


PTH_NAME = "zz_hpcsbx_override.pth"


def pth_line(override_dir: str) -> str:
    """The one line of the `.pth` that installs this module in EVERY Python of the node's venv started with HPCSBX_OVERRIDE=1 (the dispatcher and every child it starts: the live probe, the
    read check, ...), as boverride.py's does for B: the shims on PATH answer `docker` and `sudo` for any process, but the harness's reads of Docker's cgroups are replaced only here."""
    code = ("import os, sys\n"
            f"sys.path.insert(0, {override_dir!r})\n"
            "import hpcsbx_override as _h\n"
            "_h.install_or_exit()\n")
    return f"import os; (os.environ.get('HPCSBX_OVERRIDE') == '1' or os.environ.get('ICSA_HPC_SANDBOX') == '1') and exec({code!r})"


def write_pth(override_dir: str, site_packages: str | None = None) -> str:
    import sysconfig
    d = Path(site_packages or sysconfig.get_paths()["purelib"])
    f = d / PTH_NAME
    f.write_text(pth_line(override_dir) + "\n")
    return str(f)


if (os.environ.get("HPCSBX_OVERRIDE") == "1" or os.environ.get("ICSA_HPC_SANDBOX") == "1") and not INSTALLED:
    install_or_exit()
