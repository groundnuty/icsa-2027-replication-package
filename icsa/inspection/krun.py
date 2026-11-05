"""The K-case runner (#76): known-answer cases run EXACTLY as agent runs, through the real harness.

A case is a directory: `cell_01.py`, `cell_02.py`, ... (the code cells, in order), `final_message.txt` and `case.json`
(`pattern`, `member`, `option` T|D|M, `layout` S1|S2, `instance_id`, `truth`, `truth_note`, `truth_parts`, `k_group`).

`run_case` replays the cells with the harness's `StubAdapter` (one python call per cell, then the final message) through
the real `execute_run` and the real `icsa.sandbox.Sandbox` with #9's tracer mounted, so the run directory has the real
format (`transcript.json`, `code_cells.json`, `output/`, `trace/`, `run_record.json`). Then #9's labeller labels it with the
same arguments as for any run, and the result is a population row for the inspection queue (`phase: "ktest"`).

Data path (`case.json` "data_path", default "local-sim", recorded in every row): "local-sim" runs the REAL sandbox on the local copy:
M binds a plain directory of hard links (`prepare_stub`) at `/data`; T and D go through the real gate and the image's platform
client to a local `MockOnedata` that has the real space name and host names. "site_g" is the real path and needs `--allow-site_g`;
`--force-data-path site_g` applies it to every selected case (use a separate --out). Compare two out dirs' packets with
`python -m icsa.inspection.krun compare --a OUT --b OUT`.

    python -m icsa.inspection.krun --cases DIR --out DIR [--only ID,ID] [--jobs 1] [--allow-site_g] [--stub-root R]

The CLI is resumable (`<out>/rows/<case-id>.json` per finished case), logs to `<out>/krun.log`, writes `<out>/krun.pid`,
refuses to start while WINDOW_OPEN or PAUSE_K exists; WINDOW_OPEN aborts the running case at once, PAUSE_K stops after it. #9 is imported lazily.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import types
import sys
import time
from pathlib import Path

from icsa.records import Layout, Option, RunId

WINDOW_FLAG = Path("/tmp/icsa-window/WINDOW_OPEN")      # the operator's session scratch path, anonymised for the artifact
PAUSE_FILE = Path("/mnt/volume2/icsa-2027/PAUSE_K")     # stops at a run boundary (the running case finishes); WINDOW_OPEN aborts at once
LOOP_SLEEP_S = 60
DEFAULT_STUB_ROOT = Path("/mnt/volume2/icsa-2027/k76-stub")
SRC_S1 = Path("/mnt/volume2/icsa-2027/s1z")
SRC_S2 = Path("/mnt/volume2/icsa-2027/s2z/sst_s2.nc")
MODEL = "qwen"          # the RunId's model key, as the oracle uses: the model name never reaches a packet


def case_seed(case_id: str) -> int:
    """The case's identity number, used as the RunId seed so that every case has its own run key, stable when cases are added."""
    return 1000 + int(hashlib.sha256(case_id.encode()).hexdigest()[:6], 16) % 900000


OPTIONS = ("T", "D", "M")
LAYOUTS = ("S1", "S2")
TRUTHS = ("complete", "omitting")
ROW_FIELDS = ("run_key", "run_dir", "instance_id", "option", "layout", "model", "seed", "phase", "label", "label_reasons",
              "coverage", "decoded_not_delivered", "delivered_not_decoded", "truth", "truth_note", "truth_parts", "pattern",
              "member", "k_group", "wall_s", "tracer_commit", "image_id", "instruments_sha256", "data_path", "case_sha256",
              "stated_narrowing")


MEMORY_FIELDS = ("memory_peak_bytes", "memory_anon_peak_bytes", "oom_killed")


class CaseError(ValueError):
    pass


# ---------------------------------------------------------------- the case
@dataclasses.dataclass(frozen=True)
class Case:
    case_id: str
    dir: Path
    cells: tuple[str, ...]
    final_message: str
    meta: dict
    sha256: str = ""

    @property
    def option(self) -> Option:
        return Option(self.meta["option"])

    @property
    def layout(self) -> Layout:
        return Layout(self.meta["layout"])

    @property
    def data_path(self) -> str:
        """"local-sim" (the real sandbox on the local copy: M's mount is a hard-linked directory, T and D go through the gate to a
        local mock Onedata) or "site_g" (the real site_g path). Default: local-sim for every option."""
        return self.meta.get("data_path") or "local-sim"

    @property
    def instance_id(self) -> str:
        return self.meta["instance_id"]


def case_sha256(case_dir) -> str:
    """sha256 over the sorted relative paths and bytes of every file in the case directory."""
    d = Path(case_dir)
    h = hashlib.sha256()
    for p in sorted(x for x in d.rglob("*") if x.is_file()):
        h.update(p.relative_to(d).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def load_case(case_dir) -> Case:
    d = Path(case_dir)
    mp = d / "case.json"
    if not mp.is_file():
        raise CaseError(f"{d}: case.json missing")
    meta = json.loads(mp.read_text())
    for k in ("pattern", "member", "option", "layout", "instance_id", "truth", "truth_note", "truth_parts", "k_group"):
        if k not in meta:
            raise CaseError(f"{d}: case.json has no {k!r}")
    if meta["option"] not in OPTIONS:
        raise CaseError(f"{d}: option must be one of {OPTIONS}, got {meta['option']!r}")
    if meta["layout"] not in LAYOUTS:
        raise CaseError(f"{d}: layout must be one of {LAYOUTS}, got {meta['layout']!r}")
    if meta["truth"] not in TRUTHS:
        raise CaseError(f"{d}: truth must be one of {TRUTHS}, got {meta['truth']!r}")
    if meta.get("data_path") == "stub-local":        # the name before the rename: the same path, for M only (T and D never ran on the stub)
        if meta["option"] != "M":
            raise CaseError(f"{d}: data_path 'stub-local' is only valid for option M, not {meta['option']}")
        meta["data_path"] = "local-sim"
    dp = meta.get("data_path")
    if dp not in (None, "site_g", "local-sim"):
        raise CaseError(f"{d}: data_path must be 'site_g' or 'local-sim', got {dp!r}")
    files = sorted(d.glob("cell_*.py"), key=lambda p: (int(re.sub(r"\D", "", p.stem) or 0), p.name))
    if not files:
        raise CaseError(f"{d}: no cell_NN.py files")
    nums = [int(re.sub(r"\D", "", p.stem) or 0) for p in files]
    if nums != list(range(1, len(files) + 1)):
        raise CaseError(f"{d}: cells must be numbered 1..{len(files)} without gaps, got {nums}")
    fm = d / "final_message.txt"
    if not fm.is_file():
        raise CaseError(f"{d}: final_message.txt missing")
    return Case(d.name, d, tuple(p.read_text() for p in files), fm.read_text(), meta, case_sha256(d))


def load_cases(cases_dir, only=None, force_data_path: str | None = None) -> list[Case]:
    root = Path(cases_dir)
    dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "case.json").is_file())
    seeds: dict[int, str] = {}
    for p in dirs:                               # over ALL cases, not only the selected: a key must never collide
        k = case_seed(p.name)
        if k in seeds:
            raise CaseError(f"cases {seeds[k]!r} and {p.name!r} have the same derived seed {k}: rename one")
        seeds[k] = p.name
    if only is not None:
        want = list(only)
        have = {p.name for p in dirs}
        missing = [w for w in want if w not in have]
        if missing:
            raise CaseError(f"unknown case id(s): {missing}")
        by_name = {p.name: p for p in dirs}
        dirs = [by_name[w] for w in dict.fromkeys(want)]      # the order given: a launch fixes its run order in advance
    cases = [load_case(p) for p in dirs]
    if force_data_path is not None:
        if force_data_path not in ("site_g", "local-sim"):
            raise CaseError(f"--force-data-path must be 'site_g' or 'local-sim', got {force_data_path!r}")
        cases = [dataclasses.replace(c, meta={**c.meta, "data_path": force_data_path}) for c in cases]
    return cases


def script_of(case: Case) -> list:
    """The StubAdapter script: one python tool call per cell, in order, then the final message."""
    return [[("python", {"code": c})] for c in case.cells] + [case.final_message]


# ---------------------------------------------------------------- the stub mount (option M)
def prepare_stub(root=DEFAULT_STUB_ROOT, *, src_s1=SRC_S1, src_s2=SRC_S2, dataset: str | None = None,
                 s1_dir: str | None = None, s2_file: str | None = None) -> Path:
    """`<root>/<dataset>/<s1_dir>/*` and `<root>/<dataset>/<s2_file>` as HARD LINKS of the local copies (same filesystem, no
    copying). Idempotent: a link that is already the same inode is left alone, and one that is not is replaced by the right one."""
    from icsa.harness import real_sandbox as rs
    dataset = dataset or rs.SPACE_NAME
    s1_dir = s1_dir or rs.S1_DIR
    s2_file = s2_file or rs.S2_FILE
    root = Path(root)
    pairs = [(p, root / dataset / s1_dir / p.name) for p in sorted(Path(src_s1).iterdir()) if p.is_file()]
    pairs.append((Path(src_s2), root / dataset / s2_file))
    for src, dst in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            if dst.exists() and os.path.samefile(src, dst):
                continue
            dst.unlink()
        os.link(src, dst)
    return root


# ---------------------------------------------------------------- one case
ABORTED = object()


async def _guarded(coro, stop_flag, poll_s):
    """Await `coro`, polling `stop_flag` every `poll_s`; when it is set, cancel the run (the harness's own cancel path stops its
    sandbox and containers) and return ABORTED."""
    task = asyncio.ensure_future(coro)
    while not task.done():
        await asyncio.wait({task}, timeout=poll_s)
        if not task.done() and stop_flag is not None and stop_flag():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return ABORTED
    if stop_flag is not None and stop_flag():       # the case finished before the next poll: the flag still wins
        task.exception() if not task.cancelled() else None
        return ABORTED
    return task.result()


def _instances() -> dict:
    from icsa.instances.load import instance as to_instance
    p = Path(__file__).resolve().parents[2] / "data" / "instances" / "instances.json"
    return {r["instance"]["instance_id"]: to_instance(r) for r in json.loads(p.read_text())["instances"]}


LOCAL_SIM_TOKEN = "local-sim-read-only-token-0123456789"      # a made-up value the mock accepts: not a credential
_MOCKS: dict = {}
_MOCK_LOCK = threading.Lock()


def mock_files(stub_root) -> dict:
    """The files the mock serves: the stub's hard links, keyed relative to the space (`s1z/<day>.nc`, `s2z/sst_s2.nc`)."""
    from icsa.harness import real_sandbox as rs
    base = Path(stub_root) / rs.SPACE_NAME
    return {p.relative_to(base).as_posix(): p for p in sorted(base.rglob("*")) if p.is_file()}


IDS_JSON = Path("/mnt/volume2/icsa-2027/layout/ids.json")      # site_g's file ids from #9's full index (id -> space-relative path); read only


def real_id_mock_class():
    """MockOnedata presenting site_g's real file ids and the real space id (so #9's labeller maps the gate log as for a real run).
    A subclass in this module: `icsa/sandbox/mock_onedata.py` is untouched."""
    from icsa.harness import real_sandbox as rs
    from icsa.sandbox.mock_onedata import MockOnedata

    class RealIdMock(MockOnedata):
        SPACE_ID = rs.SPACE_ID

        def __init__(self, files, *, ids: dict, **kw):
            self._id2p = dict(ids)
            self._p2id = {v: k for k, v in ids.items()}
            missing = [k for k in files if k not in self._p2id]
            if missing:
                raise ValueError(f"{len(missing)} served files have no site_g id in the index, e.g. {missing[0]!r}")
            super().__init__(files, **kw)

        def _id(self, path: str) -> str:
            return self._p2id[path]

        def _path(self, fid: str):
            if fid == self.SPACE_ID:
                return ""
            return self._id2p.get(fid)
    return RealIdMock


def _mock_for(stub_root, ids_json=None):
    """One mock per process and stub root, started on first use: the real space name and id, the real Onezone and Oneprovider
    host names (the gate maps them to the mock through `upstream`), site_g's real file ids, serving the local copy."""
    from icsa.harness import real_sandbox as rs
    key = str(Path(stub_root).resolve())
    with _MOCK_LOCK:
        if key not in _MOCKS:
            ids = json.loads(Path(ids_json or IDS_JSON).read_text())
            _MOCKS[key] = real_id_mock_class()(mock_files(stub_root), ids=ids, space_name=rs.SPACE_NAME, zone_host=rs.ONEZONE_HOST,
                                               provider_host=rs.PROVIDER_HOST, token=LOCAL_SIM_TOKEN).start()
        return _MOCKS[key]


def local_sim_data_config(option, stub_root, mock=None):
    """The DataConfig of a local-sim run: the real space name, dataset paths and host names of `real_sandbox.data_config`.
    Every option: the gate's `upstream` points both real host names at the mock (plain HTTP on this host, as the sandbox tests
    wire it), and the provider host is named, as the route requires (route.py). M also mounts the stub directory in place of
    oneclient (M's gate reads no upstream, as it names no REST hosts: sandbox.py). Without a mock there is no local-sim config, for any option: a T or D gate
    would go by the real provider."""
    from icsa.harness import real_sandbox as rs
    from icsa.sandbox import campaign_data_config
    if mock is None:
        raise ValueError("a local-sim run needs its mock: without one a REST option's gate would go by the real provider")
    kw = dict(onezone_host=rs.ONEZONE_HOST, space_name=rs.SPACE_NAME, s1_path=rs.S1_DIR, s2_path=rs.S2_FILE)
    up = {h: {"addr": "host-17.invalid", "port": mock.port, "tls": False} for h in (rs.ONEZONE_HOST, rs.PROVIDER_HOST)}
    stub = {"mount_stub_dir": Path(stub_root)} if Option(option) is Option.M else {}
    return campaign_data_config(**kw, token=LOCAL_SIM_TOKEN, provider_hosts=[rs.PROVIDER_HOST], upstream=up, **stub)


def _local_sim_factory(image_id, instruments, cfg, stub_root):
    """A run on the local copy through the REAL `Sandbox` (gate, tracer, limits) and, for T and D, the real platform client
    of the image talking to the mock: the same configuration as a real run except where the data comes from."""
    from icsa.harness import real_sandbox as rs
    from icsa.sandbox import Sandbox

    def factory(run_key, option, layout, _dc=None):
        dc = local_sim_data_config(option, stub_root, _mock_for(stub_root))       # one config for every option; only T and D's gates read its upstream
        scfg = rs.sandbox_config(image_id, image_id, sandbox_limits=cfg.sandbox_limits, instruments=instruments)
        sbx = Sandbox.start(run_key, option, layout, dc, scfg)
        sbx.record(pinned_image_id=image_id, instruments_sha256=instruments[2], instrument_module=instruments[1])
        return sbx
    return factory


def label_with_9(run_dir: Path, case: Case) -> dict:
    """#9's labeller with the arguments the campaign and the validation use for the option (imported lazily)."""
    from icsa.instances.load import load_required_extents
    from icsa.instruments.fullindex import S1, load_full_index
    from icsa.instruments.labeller import code_cells_of, label_run
    index = load_full_index()
    required = load_required_extents()[case.instance_id]
    n_s1 = sum(1 for p in index.layouts if p.startswith(S1 + "/"))
    lab = label_run(case.option.value, run_dir / "trace", run_dir / "output", index, required, platform_dir=run_dir,
                    local_roots=(), dir_sizes={S1: n_s1}, code_text=code_cells_of(run_dir / "code_cells.json"))
    an = lab.analysis
    return {"label": lab.label.value, "label_reasons": list(lab.reasons), "coverage": an.coverage,
            "decoded_not_delivered": an.flags.get("decoded_not_delivered"),
            "delivered_not_decoded": an.flags.get("delivered_not_decoded")}


def run_case(case_dir, out_root, *, image_id, instruments, stub_root, allow_site_g=False, seed=None,
             sandbox_factory=None, adapter_factory=None, label_fn=None, cfg=None, texts=None, instances=None,
             stop_flag=None, poll_s=3.0) -> dict:
    """Run one case through the real harness and label it; returns the population row (or a row with `infra`, never a label).

    `sandbox_factory`, `adapter_factory`, `label_fn`, `cfg`, `texts`, `instances` are for tests (fakes); by default the real
    ones are built. `stop_flag()` is polled every `poll_s` while the case runs: when true the run is cancelled, its sandbox
    stopped, and the row is `{"aborted": True, ...}` (no label, nothing recorded). `instruments` is `(dir, module, sha256)` from `real_sandbox.ensure_instruments`."""
    from icsa.harness.adapters import StubAdapter
    from icsa.harness.config import load_config
    from icsa.harness.errors import InfraError
    from icsa.harness.prompt import load_prompt_texts
    from icsa.harness.runner import RunContext, execute_run
    case = case_dir if isinstance(case_dir, Case) else load_case(case_dir)
    if case.data_path == "site_g" and not allow_site_g:
        raise PermissionError(f"{case.case_id}: option {case.option.value} uses the real site_g path; pass allow_site_g=True")
    cfg = cfg or load_config()
    insts = instances or _instances()
    if case.instance_id not in insts:
        raise CaseError(f"{case.case_id}: unknown instance {case.instance_id}")
    if sandbox_factory is None:
        if case.data_path == "local-sim":
            sandbox_factory = _local_sim_factory(image_id, instruments, cfg, stub_root)
        else:
            from icsa.harness.real_sandbox import RealSandboxFactory
            sandbox_factory = RealSandboxFactory(image_id, image_id, cfg.limits.time_cap_s, sandbox_limits=cfg.sandbox_limits)
    script = script_of(case)
    ctx = RunContext(cfg=cfg, texts=texts or load_prompt_texts(), instances={case.instance_id: insts[case.instance_id]},
                     sandbox_factory=sandbox_factory,
                     adapter_factory=adapter_factory or (lambda spec, s, slot: StubAdapter(script, name="k-case", seed=s)))
    run = RunId(case.instance_id, case.option, case.layout, MODEL, case_seed(case.case_id) if seed is None else seed)
    run_dir = (Path(out_root) / "runs" / case.case_id).resolve()       # one directory per case, never shared
    if run_dir.exists():                    # an unfinished attempt (a finished one has a row and is never rerun): set aside, never deleted
        shutil.move(str(run_dir), f"{run_dir}.unfinished-{time.strftime('%Y%m%dT%H%M%S')}")
    t0 = time.monotonic()
    data_path = case.data_path
    base = {"case_id": case.case_id, "run_key": run.key(), "run_dir": str(run_dir), "data_path": data_path,
            "case_sha256": case.sha256}
    try:
        rec = asyncio.run(_guarded(execute_run(run, 1, run_dir, None, ctx), stop_flag, poll_s))
        if rec is ABORTED:
            return {**base, "aborted": True, "wall_s": round(time.monotonic() - t0, 1)}
    except InfraError as e:
        return {**base, "infra": f"{e.kind}: {e.detail}"[:500], "wall_s": round(time.monotonic() - t0, 1)}
    except Exception as e:  # noqa: BLE001 -- an infrastructure failure of the runner itself: recorded, never labelled
        return {**base, "infra": f"{type(e).__name__}: {e}"[:500], "wall_s": round(time.monotonic() - t0, 1)}
    if stop_flag is not None and stop_flag():
        return {**base, "aborted": True, "wall_s": round(time.monotonic() - t0, 1)}
    lab = (label_fn or label_with_9)(run_dir, case)
    if stop_flag is not None and stop_flag():
        return {**base, "aborted": True, "wall_s": round(time.monotonic() - t0, 1)}
    m = case.meta
    sb = rec.sandbox or {}
    return {"case_id": case.case_id, "run_key": run.key(), "run_dir": str(run_dir), "instance_id": case.instance_id,
            "option": case.option.value, "layout": case.layout.value, "model": MODEL, "seed": run.seed, "phase": "ktest", **lab,
            "truth": m["truth"], "truth_note": m["truth_note"], "truth_parts": m["truth_parts"], "pattern": m["pattern"],
            "member": m["member"], "k_group": m["k_group"], "stated_narrowing": bool(m.get("stated_narrowing", False)),
            "wall_s": round(rec.wall_time_s, 1),
            "tracer_commit": rec.harness_commit, "image_id": sb.get("image_id") or sb.get("pinned_image_id") or image_id,
            "data_path": data_path, "case_sha256": case.sha256, "instruments_sha256": sb.get("instruments_sha256") or (instruments[2] if instruments else None),
            # the run's memory as the sandbox measured it (None where it could not be read, never a zero): the K launch is sized on it
            **{k: sb.get(k) for k in MEMORY_FIELDS}}


# ---------------------------------------------------------------- the CLI
def compare_runs(run_dir_a, run_dir_b, identifiers: dict, identifiers_b: dict | None = None) -> dict:
    """Build both runs' packets (strict, as K packets are) and compare the texts: {identical, diff (unified)}.
    The same code through the simulation and through the real path must give byte-identical packets after sanitising."""
    import difflib
    from . import packet
    a = packet.build(run_dir_a, identifiers, strict=True)["text"]
    b = packet.build(run_dir_b, identifiers if identifiers_b is None else identifiers_b, strict=True)["text"]
    diff = "".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), "a", "b"))
    return {"identical": a == b, "diff": diff}


def compare_main(argv) -> int:
    """`python -m icsa.inspection.krun compare --a OUT_A --b OUT_B [--only ID,ID] [--endpoint HOST ...]`: the packet differential
    for the same case ids in two out dirs (local-sim vs site_g). Exit 0 if every case is identical, 1 otherwise."""
    from . import queue
    ap = argparse.ArgumentParser(prog="krun compare")
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--endpoint", action="append", default=[], help="a host name to replace (the real ones are always included)")
    a = ap.parse_args(argv)
    from icsa.harness import real_sandbox as rs
    ends = [rs.ONEZONE_HOST, rs.PROVIDER_HOST, *a.endpoint]
    ra = {p.stem: json.loads(p.read_text()) for p in sorted((Path(a.a) / "rows").glob("*.json"))}
    rb = {p.stem: json.loads(p.read_text()) for p in sorted((Path(a.b) / "rows").glob("*.json"))}
    ids = [x for x in a.only.split(",") if x] if a.only else sorted(set(ra) | set(rb))      # the union: nothing silently dropped
    if not ids:
        print("nothing to compare: no case ids in either out dir (or --only is empty)", file=sys.stderr)
        return 2
    worst = 0
    for cid in ids:
        if cid not in ra or cid not in rb or "infra" in ra[cid] or "infra" in rb[cid]:
            print(f"{cid}: MISSING or infra in " + ", ".join(n for n, r in (("A", ra), ("B", rb)) if cid not in r or "infra" in r[cid]))
            worst = 1
            continue
        ia = queue.identifiers(ra[cid], endpoints=ends)
        ib = queue.identifiers(rb[cid], endpoints=ends)
        r = compare_runs(ra[cid]["run_dir"], rb[cid]["run_dir"], ia, ib)
        print(f"{cid}: {'IDENTICAL' if r['identical'] else 'DIFFERENT'}")
        if not r["identical"]:
            print(r["diff"])
            worst = 1
    return worst


def current_instruments_sha256() -> str:
    """The sha256 `real_sandbox.ensure_instruments()` would give from the current checkout: built into a tmp dir, hashed, deleted;
    nothing is published."""
    import tempfile
    from icsa.harness import real_sandbox as rs
    from icsa.instruments.sandbox_dir import build_instruments_dir
    tmp = Path(tempfile.mkdtemp(prefix="krun-instr-"))
    try:
        d, _module = build_instruments_dir(tmp / "i")
        return rs.instruments_hash(d)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _git_head() -> str:
    repo = Path(__file__).resolve().parents[2]
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"


def relabel_main(argv, *, label_fn=None, sha_fn=None, commit_fn=None) -> int:
    """`python -m icsa.inspection.krun relabel --out DIR`: re-run #9's labeller (whatever is checked out now) on every finished row's
    existing traces and outputs, with no sandbox and no re-run. A row keeps `label_runtime`, gets `label_final` (+ reasons, coverage,
    flags), `labeller_commit`, and `tracer_changed` (the instruments sha256 of this checkout against the row's). Rows whose tracer
    differs are listed, never re-run. Then population.jsonl is rebuilt, with `label_final` as each relabelled row's label."""
    ap = argparse.ArgumentParser(prog="krun relabel")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    label_fn = label_fn or label_with_9
    commit = (commit_fn or _git_head)()
    cur_sha = (sha_fn or current_instruments_sha256)()
    changed, errors, n = [], [], 0
    for p in sorted((out / "rows").glob("*.json")):
        r = json.loads(p.read_text())
        if "infra" in r or "aborted" in r or not r.get("run_dir"):
            continue
        case = types.SimpleNamespace(case_id=r.get("case_id", p.stem), option=Option(r["option"]), instance_id=r["instance_id"])
        try:
            lab = label_fn(Path(r["run_dir"]), case)
        except Exception as e:  # noqa: BLE001 -- recorded in the row; the other rows go on
            r["relabel_error"] = f"{type(e).__name__}: {e}"[:300]
            errors.append(case.case_id)
            p.write_text(json.dumps(r, indent=1, default=str))
            continue
        r.pop("relabel_error", None)
        if r.get("data_path") == "stub-local":
            r["data_path"] = "local-sim"
        r.setdefault("label_runtime", r.get("label"))
        r.update({"label_final": lab["label"], "label_final_reasons": lab["label_reasons"], "label_final_coverage": lab["coverage"],
                  "label_final_flags": {k: lab.get(k) for k in ("decoded_not_delivered", "delivered_not_decoded")},
                  "labeller_commit": commit, "tracer_changed": r.get("instruments_sha256") != cur_sha})
        if r["tracer_changed"]:
            changed.append(case.case_id)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(r, indent=1, default=str))
        os.replace(tmp, p)
        n += 1
    _write_population(out)
    _log(out, f"relabelled {n} rows with labeller {commit[:12]}; tracer {cur_sha[:12]}; "
              f"{len(changed)} rows were traced with another tracer and need re-running: {changed}; {len(errors)} errors {errors}")
    return 1 if errors else 0


def _log(out: Path, msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    with open(out / "krun.log", "a") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def _row(out: Path, case_id: str) -> dict | None:
    p = out / "rows" / f"{case_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except ValueError:
        return None


def _done(out: Path, case: Case) -> bool:
    """A finished row (no infra) of the case's CURRENT files; an infra row is retried, a stale one is retired first."""
    r = _row(out, case.case_id)
    return r is not None and "infra" not in r and r.get("case_sha256") == case.sha256


def retire_stale(out: Path, case: Case) -> bool:
    """A finished row whose case_sha256 differs from the case's files (or has none) is stale: the row goes to
    rows/stale/<case>-<k>.json and its run dir to stale-runs/<case>-<k>/, both kept and never reused."""
    r = _row(out, case.case_id)
    if r is None or "infra" in r or r.get("case_sha256") == case.sha256:
        return False
    k = 1
    while (out / "rows" / "stale" / f"{case.case_id}-{k}.json").exists() or (out / "stale-runs" / f"{case.case_id}-{k}").exists():
        k += 1
    (out / "rows" / "stale").mkdir(parents=True, exist_ok=True)
    shutil.move(str(out / "rows" / f"{case.case_id}.json"), str(out / "rows" / "stale" / f"{case.case_id}-{k}.json"))
    rd = Path(r["run_dir"]) if r.get("run_dir") else None
    if rd is not None and rd.exists():
        (out / "stale-runs").mkdir(exist_ok=True)
        shutil.move(str(rd), str(out / "stale-runs" / f"{case.case_id}-{k}"))
    _log(out, f"STALE {case.case_id}: its files changed since the traced run (row sha {str(r.get('case_sha256'))[:12]}, "
              f"now {case.sha256[:12]}); row and run kept as {case.case_id}-{k}; it re-runs")
    return True


def _write_population(out: Path) -> None:
    """population.jsonl = every successful persisted row (infra rows excluded), rebuilt on every invocation, atomically."""
    rows = []
    for p in sorted((out / "rows").glob("*.json")):
        try:
            r = json.loads(p.read_text())
        except ValueError:
            continue
        if "infra" not in r and "aborted" not in r and r.get("run_key"):
            if r.get("data_path") == "stub-local":       # the name before the rename: the same path
                r = {**r, "data_path": "local-sim"}
            if "label_final" in r:        # relabelled offline: the final labeller's result is the population's label
                r = {**r, "label": r["label_final"], "label_reasons": r.get("label_final_reasons"),
                     "coverage": r.get("label_final_coverage"),
                     **{k: (r.get("label_final_flags") or {}).get(k) for k in ("decoded_not_delivered", "delivered_not_decoded")}}
            rows.append(r)
    tmp = out / "population.jsonl.tmp"
    tmp.write_text("".join(json.dumps({k: r.get(k) for k in ROW_FIELDS}, default=str) + "\n" for r in rows))
    os.replace(tmp, out / "population.jsonl")


def build_k_image() -> str:
    """The sandbox image from this checkout under a tag of our own; returns its immutable id."""
    repo = Path(__file__).resolve().parents[2]
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    tag = f"icsa-sandbox:k76-{sha[:12]}"
    r = subprocess.run(["docker", "build", "-q", "-f", "sandbox/Dockerfile", "-t", tag, "."], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("image build failed: " + r.stderr[-500:])
    iid = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", tag], capture_output=True, text=True, check=True).stdout.strip()
    if not iid.startswith("sha256:"):
        raise RuntimeError("no image id for " + tag)
    return iid


def main(argv=None, *, flag: Path | None = None, pause: Path | None = None, runner=run_case, prepare=None, sleep=time.sleep) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None, help="comma list of case ids")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--allow-site_g", action="store_true")
    ap.add_argument("--stub-root", default=str(DEFAULT_STUB_ROOT))
    ap.add_argument("--force-data-path", choices=("site_g", "local-sim"), default=None,
                    help="run every selected case on this data path whatever case.json says (site_g needs --allow-site_g; use a separate --out)")
    ap.add_argument("--loop", action="store_true", help="after a pass, re-scan the cases for new or changed ones; when none, sleep 60 s and re-scan")
    ap.add_argument("--image-id", default=None, help="a pinned image id (sha256:...); default: build one under the k76 tag")
    ap.add_argument("--expect-instruments", default=None,
                    help="the tracer's sha256 (or a prefix of at least 12 hex digits) this launch must use; any other refuses to run")
    a = ap.parse_args(argv)
    if a.force_data_path == "site_g" and not a.allow_site_g:
        print("--force-data-path site_g requires --allow-site_g", file=sys.stderr)
        return 2
    want_instr = (a.expect_instruments or "").strip().lower()
    if a.expect_instruments is not None and not re.fullmatch(r"[0-9a-f]{12,64}", want_instr):
        print("--expect-instruments must be 12 to 64 hex digits of the tracer's sha256", file=sys.stderr)
        return 2
    flag = WINDOW_FLAG if flag is None else flag
    pause = PAUSE_FILE if pause is None else pause
    if flag.exists():
        print(f"refusing to start: {flag} exists (the window is open)", file=sys.stderr)
        return 3
    if pause.exists():
        print(f"refusing to start: {pause} exists (paused)", file=sys.stderr)
        return 3
    out = Path(a.out)
    (out / "rows").mkdir(parents=True, exist_ok=True)
    only = [x for x in a.only.split(",") if x] if a.only else None
    (out / "krun.pid").write_text(str(os.getpid()))
    stop_file = lambda: next((f"{why} ({f})" for f, why in ((flag, "WINDOW_OPEN"), (pause, "PAUSE_K")) if f.exists()), None)  # noqa: E731
    env: dict = {}
    stub_root = Path(a.stub_root)
    bad_all: list[str] = []
    n_done = 0
    tried_infra: set[str] = set()
    first = True

    def one(c: Case):
        if stop_file():
            _log(out, f"{stop_file()} exists: not starting {c.case_id}; stopping, exiting; cases not done run on resume")
            return c, None
        t0 = time.monotonic()
        _log(out, f"start {c.case_id} ({c.option.value}/{c.layout.value}/{c.instance_id})")
        try:
            row = runner(c, out, image_id=env["image_id"], instruments=env["instruments"], stub_root=stub_root, allow_site_g=a.allow_site_g,
                         stop_flag=flag.exists)
        except Exception as e:  # noqa: BLE001 -- recorded as infra, never labelled, never stops the other cases
            row = {"case_id": c.case_id, "infra": f"{type(e).__name__}: {e}"[:500]}
        row["case_id"] = c.case_id
        if flag.exists() and not row.get("aborted"):       # WINDOW_OPEN appeared before this case was persisted: it is aborted
            row = {"case_id": c.case_id, "run_dir": row.get("run_dir"), "aborted": True}
        if row.get("aborted"):         # paused mid-case: no row, the partial run dir kept aside and never reused; re-runs from scratch
            rd = Path(row["run_dir"]) if row.get("run_dir") else None
            k = 1
            while (out / "aborted" / f"{c.case_id}-{k}").exists():
                k += 1
            dest = out / "aborted" / f"{c.case_id}-{k}"
            dest.parent.mkdir(exist_ok=True)
            if rd is not None and rd.exists():
                shutil.move(str(rd), str(dest))
            else:
                dest.mkdir()
            _log(out, f"ABORTED {c.case_id} mid-case (WINDOW_OPEN flag): no row; partial run kept at {dest}")
            return c, None
        (out / "rows" / f"{c.case_id}.json").write_text(json.dumps(row, indent=1, default=str))
        _log(out, f"done {c.case_id} in {time.monotonic() - t0:.0f}s: " + (f"INFRA {row['infra']}" if "infra" in row else f"label {row.get('label')}"))
        return c, row

    while True:
        cases = load_cases(a.cases, only, a.force_data_path)
        if first and not cases:
            print("no cases selected", file=sys.stderr)
            return 2
        site_g = [c.case_id for c in cases if c.data_path == "site_g"]
        if site_g and not a.allow_site_g:
            print(f"refusing: {site_g} use the real site_g path; pass --allow-site_g", file=sys.stderr)
            return 2
        persisted = {}                      # run key -> case id, over every persisted row (stale ones live in rows/stale, excluded)
        for rp in sorted((out / "rows").glob("*.json")):
            rk = (_row(out, rp.stem) or {}).get("run_key")
            if rk:
                persisted[rk] = rp.stem
        clash = []
        incoming: dict[str, str] = {}
        for c in cases:
            rk = RunId(c.instance_id, c.option, c.layout, MODEL, case_seed(c.case_id)).key()
            other = persisted.get(rk) if persisted.get(rk) != c.case_id else None
            other = other or (incoming.get(rk) if incoming.get(rk) != c.case_id else None)
            if other:
                clash.append(f"{c.case_id} and {other} both have run key {rk}")
            incoming[rk] = c.case_id
        if clash:
            print(f"refusing: run key collision between different cases: {clash}. Rename one case (its id sets the seed).", file=sys.stderr)
            return 2
        wrong = []
        for c in cases:                    # a finished row of another data path is never silently kept (nor retired)
            r = _row(out, c.case_id)
            if r is not None and "infra" not in r and "aborted" not in r:
                used = "local-sim" if r.get("data_path") == "stub-local" else r.get("data_path")
                if used != c.data_path:
                    wrong.append(f"{c.case_id} (finished on {used!r}, this invocation uses {c.data_path!r})")
        if wrong:
            print(f"refusing: {out} holds finished rows of another data path: {wrong}. Use a separate --out for each data path.",
                  file=sys.stderr)
            return 2
        other = []                         # _done matches on the case's files only: a row of another tracer or image would count as done
        for c in cases:
            r = _row(out, c.case_id)
            if r is not None and "infra" not in r and "aborted" not in r:
                if want_instr and not str(r.get("instruments_sha256") or "").startswith(want_instr):
                    other.append(f"{c.case_id} (tracer {str(r.get('instruments_sha256'))[:12]})")
                elif a.image_id and r.get("image_id") not in (None, a.image_id):
                    other.append(f"{c.case_id} (image {str(r.get('image_id'))[:19]})")
        if other:
            print(f"refusing: {out} holds finished rows of another tracer or image: {other}. Use a fresh --out.", file=sys.stderr)
            return 2
        for c in cases:
            retire_stale(out, c)
        _write_population(out)
        todo = [c for c in cases if not _done(out, c) and c.case_id not in tried_infra]
        if first:
            _log(out, f"{len(cases)} cases, {len(cases) - len(todo)} already done, {len(todo)} to run")
        first = False
        stopped = False
        if todo:
            if not env:
                if a.image_id:
                    if not a.image_id.startswith("sha256:"):
                        print("--image-id must be an image id (sha256:...)", file=sys.stderr)
                        return 2
                    env["image_id"] = a.image_id
                else:
                    env["image_id"] = build_k_image()
                from icsa.harness import real_sandbox as rs
                env["instruments"] = rs.ensure_instruments()
                _log(out, f"image {env['image_id']}, instruments sha256 {env['instruments'][2]}")
                if want_instr and not env["instruments"][2].startswith(want_instr):
                    _log(out, f"REFUSED: the tracer of this checkout is {env['instruments'][2]}, --expect-instruments {want_instr}; "
                              "nothing run")
                    return 2
            if any(c.data_path == "local-sim" for c in todo):
                (prepare or prepare_stub)(stub_root)
            finished = []
            if a.jobs <= 1:
                for c in todo:
                    r = one(c)
                    if r[1] is None:
                        stopped = True
                        break
                    finished.append(r)
            else:
                import concurrent.futures as cf
                with cf.ThreadPoolExecutor(a.jobs) as ex:
                    res = list(ex.map(one, todo))
                finished = [r for r in res if r[1] is not None]
                stopped = len(finished) < len(res)
            _write_population(out)
            n_done += len(finished)
            bad = [c.case_id for c, r in finished if "infra" in r]
            bad_all += bad
            tried_infra |= set(bad)
            _log(out, f"pass finished: {len(finished)} cases, {len(bad)} infra failures {bad}")
        if stopped or not a.loop or stop_file():
            break
        if not todo:                      # nothing new or stale: wait, then look again (infra failures are retried after the wait)
            tried_infra.clear()
            _log(out, f"nothing to run; sleeping {LOOP_SLEEP_S}s")
            sleep(LOOP_SLEEP_S)
            if stop_file():
                _log(out, f"{stop_file()} exists: stopping")
                break
    return 1 if bad_all else 0


if __name__ == "__main__":
    from icsa.sandbox.termination import exit_on_sigterm
    exit_on_sigterm()     # a real-sandbox driver: a SIGTERM is an orderly exit (finally -> stop()), never a mount left to the reaper
    raise SystemExit(compare_main(sys.argv[2:]) if sys.argv[1:2] == ["compare"]
                     else relabel_main(sys.argv[2:]) if sys.argv[1:2] == ["relabel"] else main())
