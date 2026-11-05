"""site_a transport for `snapshot.coderreplay` (#34): the tree, the data pack and the jobs go to the holder jobs, the detection runs there, the results come back.

    python -m snapshot.coderreplay_remote setup  [--pack-local DIR]                       # once, and idempotent: the pack, the tree, the kit on every node; a smoke test per node
    python -m snapshot.coderreplay_remote run    <seal> --budget-s N                      # the jobs of <seal>/coder_replay/work/jobs.jsonl; results to .../work/results, then .../work/remote.json
    python -m snapshot.coderreplay_remote status                                          # which holder jobs answer

Only my own holder jobs are used (REPLAY_JOBS, default the four given for this job) and only their /tmp (RAM) and my 700 directory on scratch. Every ssh/srun call has a timeout; the whole run keeps
inside `--budget-s`; the worker stops starting jobs 150 s before it, so the results are packed and fetched in time. Whatever cannot be done is left undone and the table says why
(compute_unavailable, time_box): nothing here ever raises into the snapshot. stdout is totals and seconds only.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse    # noqa: E402
import json        # noqa: E402
import os          # noqa: E402
import subprocess  # noqa: E402
import tarfile     # noqa: E402
import tempfile    # noqa: E402
import time        # noqa: E402
from concurrent.futures import ThreadPoolExecutor    # noqa: E402
from pathlib import Path    # noqa: E402

from . import coderreplay as CR    # noqa: E402

CFG = Path(os.environ.get("REPLAY_SSH_CONFIG", "~/.secrets/icsa-2027/site_a-b/config"))
HOST = "host-27.invalid"
SC = os.environ.get("REPLAY_SCRATCH", "/net/scratch/site_bb/user_1/user_1/site_r/lane-replay")
KIT = "/net/scratch/site_bb/user_1/user_1/site_r/lane-snap"          # python 3.13 and the venv, read only (lane-snap5's kit)
JOBS = tuple(int(x) for x in os.environ.get("REPLAY_JOBS", "25695794,25695795,25695799,25695800").split(",") if x.strip())        # the interims: the four holders
FINAL_JOBS = tuple(int(x) for x in os.environ.get("REPLAY_FINAL_JOBS", "25695758").split(",") if x.strip())                       # the fixed snapshot (lead, 5 Nov): one node, to 6 Nov 20:38Z, nice, at most 16 cores
PACK_LOCAL = Path(os.environ.get("REPLAY_PACK", "/mnt/volume2/icsa-2027/snap-coder-replay-pack"))
PYREL = "py~/.local/share/uv/python/cpython-3.13.13-linux-x86_64-gnu/bin/python3.13"
SSH_OPTS = ["-F", str(CFG), "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ControlMaster=auto", "-o", "ControlPath=/tmp/lane-replay-cm-%C", "-o", "ControlPersist=120"]
TAIL_S = 150          # the worker stops starting jobs this long before the budget ends: pack, fetch


class RemoteError(Exception):
    pass


_TMP: Path | None = None       # a sealed directory for the files that carry coder-derived data (the jobs, the fetched tars); set by run_remote


def _tmpdir() -> str | None:
    return str(_TMP) if _TMP else None


def _env():
    return {**os.environ, "SSH_AUTH_SOCK": ""}


def ssh(cmd: str, *, timeout: float, stdin=None, stdout=None, check=True) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(["ssh", *SSH_OPTS, HOST, cmd], stdin=stdin, stdout=stdout if stdout else subprocess.PIPE, stderr=subprocess.PIPE, timeout=max(5.0, timeout), env=_env())
    except subprocess.TimeoutExpired as e:
        raise RemoteError("timeout") from e
    if check and r.returncode:
        raise RemoteError(f"rc={r.returncode}")
    return r


def srun(jid: int, script: str, args: list, *, mem: str, cpus: int, timeout: float) -> str:
    """Runs `script` (bash) as a step of holder job `jid`, on its node, with `args`."""
    with tempfile.NamedTemporaryFile("w", suffix=".sh") as fh:
        fh.write(script)
        fh.flush()
        with open(fh.name, "rb") as stdin:
            r = ssh(f"srun --jobid={jid} --overlap -N1 -n1 -c{cpus} --mem={mem} bash -s -- {' '.join(str(a) for a in args)}", timeout=timeout, stdin=stdin)
    return r.stdout.decode(errors="replace")[-400:]


NODE_SETUP = r'''
set -eu
JID=$1; CODE=$2; PSHA=$3
R=/tmp/lane-replay-$JID; SC=%(sc)s; KIT=%(kit)s
umask 077
if [ ! -f $R/py.ok ]; then rm -rf $R/py $R/work; mkdir -p $R/py $R/work; (cd $R/py && tar -xf $KIT/py313.tar) && (cd $R/work && tar -xf $KIT/venv.tar) && : > $R/py.ok; fi
if [ ! -f $R/tree-$CODE.ok ]; then rm -rf $R/tree $R/tree-*.ok; mkdir -p $R/tree; tar -xf $SC/tree-$CODE.tar -C $R/tree && : > $R/tree-$CODE.ok; fi
if [ ! -f $R/pack-$PSHA.ok ]; then rm -rf $R/pack $R/pack-*.ok; mkdir -p $R/pack; cp $SC/pack/*.npy $R/pack/; cp $SC/pack/SHA256SUMS $R/pack/; (cd $R/pack && sha256sum -c --quiet SHA256SUMS) && : > $R/pack-$PSHA.ok; fi
PY=$R/%(py)s
cd $R/tree
PYTHONPATH=$R/tree:$R/work/.venv/lib/python3.13/site-packages PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$R/nodata $PY -B -c "import snapshot.coderreplay as C; print('code', C.code_sha()[:16])"
''' % {"sc": SC, "kit": KIT, "py": PYREL}

NODE_RUN = r'''
set -eu
JID=$1; RUN=$2; DEADLINE=$3; LIMIT=$4; PROCS=$5
R=/tmp/lane-replay-$JID; SC=%(sc)s
umask 077
PY=$R/%(py)s
# at most PROCS processes, and no more than the cores the node has free right now (its load is someone else's work): the detection is the lowest priority on it
CORES=$(nproc --all); LOAD=$(cut -d' ' -f1 /proc/loadavg | cut -d. -f1); FREE=$(( CORES - LOAD )); [ $FREE -ge 2 ] || FREE=2; [ $PROCS -le $FREE ] || PROCS=$FREE
OUT=$R/out/$RUN; rm -rf $OUT; mkdir -p $OUT
find $R/out -mindepth 1 -maxdepth 1 -mmin +120 -exec rm -rf {} + 2>/dev/null || true       # an earlier run's results, long fetched
cd $R/tree
rc=0
PYTHONPATH=$R/tree:$R/work/.venv/lib/python3.13/site-packages PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$R/nodata \
  nice -n 15 timeout -k 20 $LIMIT $PY -B -m snapshot.coderreplay compute --jobs $SC/run/$RUN/jobs-$JID.jsonl --out $OUT --pack-dir $R/pack --procs $PROCS --deadline $DEADLINE || rc=$?
tar -C $OUT -cf $SC/run/$RUN/out-$JID.tar.tmp . && mv $SC/run/$RUN/out-$JID.tar.tmp $SC/run/$RUN/out-$JID.tar && rm -rf $OUT      # the tar on scratch (700) holds the results until they are fetched
echo "compute rc=$rc procs=$PROCS"
''' % {"sc": SC, "py": PYREL}


def tree_tar() -> Path:
    """The tree the detection runs from: icsa/, snapshot/ and data/instances/ of this checkout, named by the code's sha (so a changed file is a new tar)."""
    p = Path(tempfile.gettempdir()) / f"lane-replay-tree-{CR.code_sha()[:16]}.tar"
    if not p.exists():
        tmp = p.with_suffix(".tmp")
        subprocess.run(["tar", "-C", str(CR.ROOT), "--exclude=__pycache__", "--exclude=*.pyc", "-cf", str(tmp), "icsa", "snapshot", "data/instances"], check=True, timeout=300)
        os.replace(tmp, p)
    return p


def pack_sha(pack: Path) -> str:
    import hashlib
    return hashlib.sha256((pack / "SHA256SUMS").read_bytes()).hexdigest()[:16]


def ensure_scratch(*, timeout: float) -> None:
    ssh(f"umask 077; mkdir -p -m 700 {SC} {SC}/run {SC}/pack", timeout=timeout)


def ship_tree(*, timeout: float) -> str:
    code = CR.code_sha()[:16]
    t = tree_tar()
    if ssh(f"test -f {SC}/tree-{code}.tar", timeout=60, check=False).returncode:
        with open(t, "rb") as fh:
            ssh(f"umask 077; cat > {SC}/tree-{code}.tar.tmp && mv {SC}/tree-{code}.tar.tmp {SC}/tree-{code}.tar", timeout=timeout, stdin=fh)
    return code


def ship_pack(pack: Path, *, timeout: float) -> str:
    if not (pack / "SHA256SUMS").is_file():
        raise RemoteError("no_local_pack")
    r = subprocess.run(["rsync", "-a", "--timeout=120", "-e", "ssh " + " ".join(SSH_OPTS), f"{pack}/", f"{HOST}:{SC}/pack/"], capture_output=True, timeout=timeout, env=_env())
    if r.returncode:
        raise RemoteError(f"rsync rc={r.returncode}")
    return pack_sha(pack)


def setup(pack: Path = PACK_LOCAL, *, budget_s: float = 1800, nodes: tuple = JOBS) -> dict:
    t0 = time.time()
    left = lambda: budget_s - (time.time() - t0)      # noqa: E731
    ensure_scratch(timeout=60)
    if not (pack / "SHA256SUMS").is_file():
        CR.build_pack(pack)
    code, psha = ship_tree(timeout=left()), ship_pack(pack, timeout=left())

    def one(jid):
        out = srun(jid, NODE_SETUP, [jid, code, psha], mem="16G", cpus=1, timeout=left())
        return out.strip().endswith(f"code {CR.code_sha()[:16]}")
    with ThreadPoolExecutor(max(1, len(nodes))) as ex:
        res = list(ex.map(lambda j: _safe(one, j), nodes))
    return {"nodes": len(nodes), "ready": sum(r is True for r in res), "seconds": round(time.time() - t0, 1), "code": code}


def _safe(fn, *a):
    try:
        return fn(*a)
    except (RemoteError, OSError, subprocess.SubprocessError):
        return False


def split_jobs(jobs: list[dict], k: int) -> list[list[dict]]:
    """Instances to k parts, balanced by work (a `full` counts 3 extents); an instance is never split (its reference is built per chunk of one part)."""
    by: dict[str, list[dict]] = {}
    for j in jobs:
        by.setdefault(j["instance_id"], []).append(j)
    parts, load = [[] for _ in range(k)], [0] * k
    for iid in sorted(by, key=lambda i: -sum(3 if j["digest"] == "full" else 1 for j in by[i])):
        w = sum(3 if j["digest"] == "full" else 1 for j in by[iid])
        a = load.index(min(load))
        parts[a].extend(by[iid])
        load[a] += w
    return parts


def fetch(jid: int, run: str, staging: Path, *, timeout: float) -> int:
    """The node's results into `staging`, each file placed whole (extracted aside, then renamed in): a fetch killed at the deadline leaves complete files only."""
    n = 0
    Path(staging).mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(staging, 0o700)
    with tempfile.TemporaryDirectory(dir=_tmpdir(), prefix=".fetch-") as td:
        tdir = Path(td)
        with open(tdir / "out.tar", "wb") as fh:
            ssh(f"cat {SC}/run/{run}/out-{jid}.tar", timeout=timeout, stdout=fh)
        (tdir / "x").mkdir(mode=0o700)
        with tarfile.open(tdir / "out.tar") as tf:
            tf.extractall(tdir / "x", filter="data")
        for src in sorted((tdir / "x").rglob("*")):
            if src.is_file():
                dest = Path(staging) / src.relative_to(tdir / "x")
                dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.chmod(src, 0o600)
                os.replace(src, dest)
                n += 1
    return n


def run_remote(jobs_path: Path, staging: Path, *, budget_s: float, run: str, procs: int = 16, nodes: tuple | None = None) -> dict:
    """Runs the jobs on the holder jobs, one part each. Never raises: the summary says what happened."""
    global _TMP
    t0 = time.time()
    end = t0 + budget_s
    left = lambda: end - time.time()      # noqa: E731
    _TMP = Path(staging).parent / "tmp"
    _TMP.mkdir(mode=0o700, parents=True, exist_ok=True)
    jobs = [json.loads(x) for x in Path(jobs_path).read_text().splitlines() if x.strip()]
    nodes = tuple(nodes) if nodes else JOBS
    sm = {"jobs": len(jobs), "nodes": len(nodes), "nodes_ok": 0, "nodes_failed": 0, "time_box": False, "error": "", "rounds": 0}
    if not jobs:
        return {**sm, "seconds": 0.0}
    staging.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        ensure_scratch(timeout=min(60, left()))
        code, psha = ship_tree(timeout=min(600, left())), ship_pack(PACK_LOCAL, timeout=min(900, left()))
        ssh(f"umask 077; mkdir -p -m 700 {SC}/run/{run}", timeout=min(60, left()))
    except (RemoteError, OSError, subprocess.SubprocessError) as e:
        return {**sm, "error": f"ship:{e}", "seconds": round(time.time() - t0, 1)}
    todo, alive = jobs, list(nodes)
    while todo and alive and left() > TAIL_S + 60 and sm["rounds"] < 2:
        sm["rounds"] += 1
        parts = split_jobs(todo, len(alive))

        def one(args):
            jid, part = args
            if not part:
                return jid, True
            try:
                srun(jid, NODE_SETUP, [jid, code, psha], mem="16G", cpus=1, timeout=min(900, max(10, left() - TAIL_S)))
                with tempfile.NamedTemporaryFile("w", suffix=".jsonl", dir=_tmpdir()) as fh:
                    fh.write("".join(json.dumps(j, sort_keys=True) + "\n" for j in part))
                    fh.flush()
                    with open(fh.name, "rb") as stdin:
                        ssh(f"umask 077; cat > {SC}/run/{run}/jobs-{jid}.jsonl", timeout=min(300, max(10, left())), stdin=stdin)
                dl = end - TAIL_S
                srun(jid, NODE_RUN, [jid, run, int(dl), int(max(30, dl - time.time())), procs], mem="24G", cpus=procs, timeout=max(30, left() - 60))
                fetch(jid, run, staging, timeout=min(300, max(20, left())))
                ssh(f"rm -f {SC}/run/{run}/out-{jid}.tar {SC}/run/{run}/jobs-{jid}.jsonl", timeout=60, check=False)         # coder-derived data does not stay on scratch once it is here
                return jid, True
            except (RemoteError, OSError, subprocess.SubprocessError, tarfile.TarError):
                return jid, False
        with ThreadPoolExecutor(len(alive)) as ex:
            res = list(ex.map(one, zip(alive, parts)))
        alive = [j for j, ok in res if ok]
        sm["nodes_ok"], sm["nodes_failed"] = len(alive), len(nodes) - len(alive)
        have = {(p.parent.name, p.stem) for p in staging.glob("*/*") if p.suffix in (".npz", ".err")}
        todo = [j for j in todo if (j["instance_id"], j["digest"]) not in have]
    sm["time_box"] = bool(todo) and left() <= TAIL_S + 60
    if todo and not alive:
        sm["error"] = "no_node_answered"
    return {**sm, "unfinished": len(todo), "seconds": round(time.time() - t0, 1)}


def _run_cmd(a) -> int:
    seal = Path(a.seal)
    work = seal / "coder_replay" / "work"
    os.umask(0o077)
    run = f"{seal.name}-{int(time.time())}"
    final = CR.snapshot_final(seal) == "true"            # the fixed snapshot runs on the final's node, the interims on the holders
    sm = run_remote(work / "jobs.jsonl", work / "results", budget_s=a.budget_s, run=run, nodes=FINAL_JOBS if final else JOBS)
    (work / "remote.json").write_text(json.dumps({**sm, "run": run, "finished_at": time.time()}, sort_keys=True))
    os.chmod(work / "remote.json", 0o600)
    print(json.dumps({k: sm[k] for k in ("jobs", "nodes_ok", "nodes_failed", "unfinished", "time_box", "error", "seconds") if k in sm}, sort_keys=True))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.coderreplay_remote", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("--pack-local", default=str(PACK_LOCAL))
    s.add_argument("--budget-s", type=float, default=1800)
    s.add_argument("--final", action="store_true", help="set up the final's node (REPLAY_FINAL_JOBS) instead of the interims' holders")
    r = sub.add_parser("run")
    r.add_argument("seal")
    r.add_argument("--budget-s", type=float, required=True)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "setup":
            print(json.dumps(setup(Path(a.pack_local), budget_s=a.budget_s, nodes=FINAL_JOBS if a.final else JOBS), sort_keys=True))
            return 0
        if a.cmd == "run":
            return _run_cmd(a)
        for j in (*JOBS, *FINAL_JOBS):
            r = ssh(f"squeue -h -j {j} -o '%T'", timeout=60, check=False)
            print(j, r.stdout.decode().strip() or "gone")
        return 0
    except (RemoteError, OSError, subprocess.SubprocessError) as e:
        print(f"coderreplay_remote: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
