#!/usr/bin/env python3
"""The M+ driver (science #34, 4 Nov 18:53Z): preflight, the barrier, as many of the 30 runs as fit by NOT_AFTER, then the tables. Run ON .23 under the frozen
tree's python, through `mplus-run.sh` (which sets the tree, PYTHONPATH and the working directory). DRY by default: it validates and prints; `--run` acts.

Stages: preflight -> barrier (2 pieces: S1 I48, S2 I48) -> resume (pieces, in the seeded order) -> tables (`mplus-report`).
A piece is one `mplus-measure --plan` call over a prefix of one layout's seeded order (see mplus_gate.py for why that is the smallest safe unit). Before each piece:
  * never a start at or after --not-after (07:30Z), never while $V/mplus/PAUSE exists, never after a failure;
  * with the barrier's figures, the largest prefix projected to END by --not-after minus --margin-s (the call's own overhead included).
A call is never killed: a transfer in flight cannot be cancelled and would leave site_f's replica unknown. SIGTERM to this driver finishes the piece in flight, then stops.
Done pieces are read from the run RECORDS (`done_steps`), never from run-log.jsonl, so a re-run skips what is finished.
It reads no outcome value and prints none: walls, counts and keys only.
"""
from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import os
import shlex
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mplus_gate as G  # noqa: E402

V = Path("/mnt/volume2/icsa-2027")
L = V / "launch"
MP = V / "mplus"
SEED = 20271201
INST = ["I35", "I37", "I48", "I01", "I06"]
LB = {"S1": 4254680853, "S2": 3785412176}          # fed.MAIN_S1_BYTES, MAIN_S2_BYTES, as mplus_project.py
LAYOUTS = ("S1", "S2")
SPACE_SHA256 = "6702e7ad9ee4e140848793da241aa265f7b6d8b9082e38725e712109dc5ad530"       # results/mplus-setup-20261102T164044Z/space.json
NOT_AFTER = "2026-11-06T07:30:00Z"
TABLES_BY = "2026-11-06T08:30:00Z"
STAMP = MP / "preflight-stamp.json"
PAUSE = MP / "PAUSE"
RUN_LOG = MP / "run-log.jsonl"
ICSA_PROCS = r"icsa\.(campaign|scripted|instruments|faults|harness)"
DEF_SITE_G = V / "baselines" / "f1c242a"                       # step A's quiet baselines: 3 traced M runs per layout, on site_g, head f1c242a
DEF_WAN = MP / "inputs" / "wan_20261101T161015Z"            # the WAN anchor committed at results/scripted/wan_20261101T161015Z (4 M runs: S1 x3, S2 x1)


@dataclasses.dataclass
class Ctx:
    a: argparse.Namespace
    dry: bool
    tree: Path
    py: str
    sha: str
    image: str
    out: Path
    frcmd: str
    stop: bool = False
    halt: str = ""
    dry_calls: int = 0
    seen_keys: set | None = None        # run keys and log length as the last piece's post-call snapshot left them: what appears after is a failure nobody has looked at
    seen_log: int | None = None

    @property
    def env(self) -> dict:
        e = {k: v for k, v in os.environ.items() if not k.startswith("ICSA_")}      # no token source, no audit log, no slot keys: M+ mints admin tokens (mplus.md, 5)
        e.update(ICSA_RUN_SHA=self.sha, ICSA_SANDBOX_IMAGE=self.image, ICSA_SITE_G_SETTINGS_CMD=self.frcmd, ICSA_SITE_G_RESTART_LOG=str(V / "site_g_restart_log.jsonl"),
                 PYTHONPATH=".", PYTHONUNBUFFERED="1")
        return e


def now_s(ctx: Ctx) -> float:
    return G.parse_utc(ctx.a.now) if (ctx.dry and ctx.a.now) else time.time()


def ev(ctx: Ctx, **kw) -> None:
    rec = {"utc": G.fmt_utc(time.time()), "head": ctx.sha[:7], **kw}
    print(json.dumps(rec, default=str), flush=True)
    if not ctx.dry:
        MP.mkdir(parents=True, exist_ok=True)
        with open(RUN_LOG, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())


# ------------------------------------------------------------------------------------------------------------------------------------ the tree
def load_tree(a) -> tuple[Path, str, str, str]:
    tree = V / "wt" / f"launch-{a.head}"
    st = json.loads((tree / ".code-stamp.json").read_text())
    sha = st["head"]
    if not sha.startswith(a.head) or len(sha) != 40:
        raise SystemExit(f"{tree}/.code-stamp.json names {sha}, not head {a.head}")
    return tree, str(tree / ".venv" / "bin" / "python"), sha, f"icsa-sandbox:oracle-{sha[:12]}"


def tree_mods():
    from icsa.records import Layout, Option
    from icsa.scripted import mplus as M
    from icsa.scripted.runner import Plan
    from icsa.scripted.summarize import load_runs
    return Layout, Option, M, Plan, load_runs


def seeded_orders() -> dict[str, list[str]]:
    Layout, _, M, _, _ = tree_mods()
    return {la: M.select_instances(INST, SEED, Layout(la), None) for la in LAYOUTS}


def read_state(ctx: Ctx):
    _, _, M, _, load_runs = tree_mods()
    runs = load_runs(ctx.out) if (ctx.out / "runs").is_dir() else []
    lp = ctx.out / "mplus_log.jsonl"
    log = [json.loads(x) for x in lp.read_text().splitlines()] if lp.exists() else []
    return runs, log, M.done_steps(runs)


def layout_figures(ctx: Ctx, layout: str, runs, log):
    _, _, M, _, _ = tree_mods()
    st = M.step_times(log, runs)[layout]
    pl = [e["seconds"] for e in log if e.get("event") == "provision" and e.get("layout") == layout and e.get("scope") == "layout" and e.get("confirmed_placed") is True]
    ml = [r["wall_s"] for r in runs if r.get("ok") and r.get("layout") == layout and (r.get("extra") or {}).get("variant") == "mplus" and r["extra"].get("scope") == "layout"]
    return G.figures(st, pl, ml, LB[layout])


def block_state(d: Path) -> str:
    rj = d / "run.json"
    if rj.exists():
        try:
            return f"run.json ok={json.loads(rj.read_text()).get('ok')}"
        except ValueError:
            return "run.json unreadable"
    n = sum(1 for _ in d.iterdir())
    return "EMPTY directory, no run.json: nothing recorded" if n == 0 else f"{n} file(s), no run.json: a cut attempt"


def blocked_steps(ctx: Ctx, layout: str, ids, done) -> list[tuple[str, Path, str]]:
    """(step, directory, state) of every step not done whose run directory already exists: `run_one` makes it with exist_ok=False and the attempt fixed at 1, so a
    retry crashes there. `run_one` makes the directory BEFORE it asks site_g's settings (frsettings.hash_for_record), so a refusal there (an ssh blip to site_g, an unlogged
    op_worker restart, a changed hash) leaves an EMPTY directory that blocks the step the same way. Never worked around by default: a failed run is a record."""
    Layout, Option, _, Plan, _ = tree_mods()
    out = []
    for j, iid in enumerate(ids):
        for step, opt, tag in (("cold-site_f", Option.M, f"cold-site_f-p{j}"), ("mplus-required", Option.M_PLUS, f"mplus-required-p{j}"), ("mplus-layout", Option.M_PLUS, f"mplus-layout-p{j}")):
            d = ctx.out / "runs" / Plan(iid, opt, Layout(layout), tag=tag).key()
            if (iid, layout, step) not in done and d.exists():
                out.append((f"{iid}/{layout}/{step}", d, block_state(d)))
    return out


def aside_empty(ctx: Ctx, blk) -> list[tuple[str, Path, str]]:
    """`--aside-empty`: an EMPTY blocking directory holds no record, so it is renamed into runs-aside/ (same volume, nothing deleted) and the step may run. A directory with
    anything in it, and every run.json, stays blocking."""
    keep = []
    for label, d, state in blk:
        if state.startswith("EMPTY"):
            dest = ctx.out / "runs-aside" / f"{d.name}-{G.fmt_utc(time.time()).replace(':', '')}"
            if not ctx.dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.rename(d, dest)
            ev(ctx, event="aside-empty" if not ctx.dry else "would-aside-empty", step=label, was=str(d), now=str(dest))
        else:
            keep.append((label, d, state))
    return keep


# ------------------------------------------------------------------------------------------------------------------------------------ argv
def measure_argv(ctx: Ctx, plan_path: Path) -> list[str]:
    argv = [ctx.py, "-m", "icsa.scripted", "mplus-measure", "--out", str(ctx.out), "--space", str(ctx.out / "space.json"), "--plan", str(plan_path)]
    # `_manifest` refuses an existing MANIFEST_mplus.json without --resume and writes MANIFEST_mplus_resume<k>.json with it: the first call has none, every later one has it.
    # In a dry run no manifest exists, so the first call shown has none and the ones after it show what they will carry once the first has run.
    if (ctx.out / "MANIFEST_mplus.json").exists() or (ctx.dry and ctx.dry_calls > 0):
        argv.append("--resume")
    ctx.dry_calls += 1 if ctx.dry else 0
    return ([str(V / "bin" / "memcap"), str(ctx.a.memcap_gib)] if ctx.a.memcap_gib else []) + argv


def report_argv(ctx: Ctx) -> list[str]:
    argv = [ctx.py, "-m", "icsa.scripted", "mplus-report", "--out", str(ctx.out)]
    if ctx.a.site_g_dir:
        argv += ["--site_g-dir", ctx.a.site_g_dir]
    if ctx.a.wan_dir:
        argv += ["--wan-dir", ctx.a.wan_dir]
    return argv


def parse_check(argv: list[str]) -> str:
    """The CLI's own parser on the exact arguments: no side effect (build_parser only builds)."""
    from icsa.scripted import __main__ as CLI
    i = argv.index("icsa.scripted") + 1
    ns = CLI.build_parser().parse_args(argv[i:])
    return f"parsed: cmd={ns.cmd} seed={ns.seed} resume={getattr(ns, 'resume', None)} plan={getattr(ns, 'plan', None)}"


def piece_plan(ctx: Ctx, name: str, layout: str, ids: list[str], order: dict) -> Path:
    inst = {la: (list(ids) if la == layout else []) for la in LAYOUTS}
    p = ctx.out / "pieces" / f"{name}.json"
    body = {"seed": SEED, "instances": inst, "seeded_order": order, "source": f"mplus_run.py piece {name}: a prefix of the seeded order for {layout}, [] for the other layout"}
    if not ctx.dry:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(body, indent=1) + "\n")
    return p


def validate_plan_files(order: dict) -> list[str]:
    """The lead's plan files against the seeded order the tree computes: the barrier is the first of each, `all` is the whole order, `reduced` the first 3."""
    want = {"mplus-barrier-plan.json": {la: order[la][:1] for la in LAYOUTS}, "mplus-resume-all.json": order, "mplus-resume-reduced.json": {la: order[la][:3] for la in LAYOUTS}}
    out = []
    for f, inst in want.items():
        d = json.loads((L / f).read_text())
        ok = d.get("seed") == SEED and d.get("instances") == inst and d.get("seeded_order") == order
        out.append(f"{'OK  ' if ok else 'BAD '}{f}: {d.get('instances')}")
    return out


# ------------------------------------------------------------------------------------------------------------------------------------ preflight
def sh(argv, timeout=30):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError) as e:
        return 127, f"{type(e).__name__}"


def preflight(ctx: Ctx) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    add = lambda n, s, d: rows.append((n, s, d))      # noqa: E731
    # 1. main's dispatcher: exited, or paused by its quiet window with nothing in flight (a bare zero count is not a drain: see G.judge_dispatcher)
    rc, o = sh(["pgrep", "-af", r"icsa\.campaign run"])
    disp = [l for l in o.splitlines() if "pgrep" not in l]
    n = quiet = None
    if disp:
        try:
            c = sqlite3.connect(f"file:{V / 'runs' / 'campaign' / 'state.sqlite'}?mode=ro", uri=True, timeout=5)
            n = c.execute("select count(*) from attempts where state='running'").fetchone()[0]
            q = c.execute("select value from meta where key='quiet_window'").fetchone()
            quiet = json.loads(q[0]) if q and q[0] else {}
            c.close()
        except Exception:      # noqa: BLE001
            n = quiet = None
    st, why = G.judge_dispatcher(bool(disp), n, quiet, (V / "QUIET_WINDOW_RELEASE").exists())
    add("main dispatcher", st, why + (f" (pid {disp[0].split()[0]})" if disp else ""))
    # 2. nothing else timed on .23
    rc, o = sh(["pgrep", "-af", ICSA_PROCS])
    other = [l for l in o.splitlines() if "pgrep" not in l and "icsa.campaign run" not in l]
    add("other icsa processes on .23", "PASS" if not other else "FAIL", "none" if not other else f"{len(other)}: " + "; ".join(sorted({l.split()[0] + ' ' + (l.split(' -m ')[-1].split(' --')[0][:40]) for l in other}))[:300])
    rc, o = sh(["docker", "ps", "--format", "{{.Names}}"])
    sbx = [n for n in o.split() if n.startswith("icsa-sbx")]
    add("sandboxes on .23", ("PASS" if not sbx else "FAIL") if rc == 0 else "UNKNOWN", f"{len(sbx)} icsa-sbx container(s), {len(o.split())} container(s) in all" if rc == 0 else "docker ps failed")
    # 3. the stamp: site_g solo, .8 idle, site_f restarted (from the lead's host: neither site_g nor .8 is readable from here)
    try:
        s = json.loads(STAMP.read_text())
        age = time.time() - G.parse_utc(s["utc"])
        for key, label in (("site_g_solo", "site_g solo"), ("host8_idle", ".8 idle"), ("site_f_restart_ok", "site_f restarted, settings hashes equal")):
            v = s.get(key)
            add(label + " (stamp)", "PASS" if (v is True and age <= ctx.a.stamp_max_age_s) else ("UNKNOWN" if v is None else "FAIL"),
                f"{key}={v}, stamp {age:.0f} s old (max {ctx.a.stamp_max_age_s:.0f}), by {s.get('by')}")
    except (OSError, ValueError, KeyError) as e:
        for label in ("site_g solo", ".8 idle", "site_f restarted"):
            add(label + " (stamp)", "UNKNOWN", f"no usable stamp {STAMP}: {type(e).__name__}; run mplus-preflight-local.sh --write on the lead's host")
    # 4. the tree, image, key files
    add("tree head", "PASS", f"{ctx.tree} stamps {ctx.sha}")
    rc, o = sh(["docker", "image", "inspect", "-f", "{{.Id}}", ctx.image])
    add("sandbox image", "PASS" if rc == 0 else "FAIL", f"{ctx.image} -> {o.strip()[:19]}" if rc == 0 else f"{ctx.image} not loaded")
    op = Path("~/.secrets/icsa-2027/onedata.pass")
    add("onedata.pass", "PASS" if op.is_file() and (op.stat().st_mode & 0o777) == 0o600 else "FAIL", "present, mode 600 (never read)" if op.is_file() else "missing")
    sp = ctx.out / "space.json"
    got = hashlib.sha256(sp.read_bytes()).hexdigest() if sp.is_file() else None
    add("space.json", "PASS" if got == ctx.a.space_sha256 else "FAIL", f"{sp}: sha256 {'= the setup copy' if got == ctx.a.space_sha256 else (got or 'missing')}")
    for f in ("site_g_settings.frozen", "site_g_restart_log.jsonl"):
        add(f, "PASS" if (V / f).is_file() else "FAIL", str(V / f))
    try:
        key = ctx_frkey(ctx)
        add("site_g settings command", "PASS" if os.access(key, os.R_OK) else "FAIL", f"forced-command ssh, key {key} {'readable' if os.access(key, os.R_OK) else 'NOT readable'} (not run)")
    except Exception as e:      # noqa: BLE001
        add("site_g settings command", "FAIL", f"{type(e).__name__}: {e}")
    ha = Path("/etc/icsa-2027/host_aliases.toml").read_text() if Path("/etc/icsa-2027/host_aliases.toml").exists() else ""
    add("host_aliases (site_f .19, site_g .20)", "PASS" if ("198.51.100.23" in ha and "198.51.100.24" in ha) else "FAIL", "both internal addresses present" if ("198.51.100.23" in ha and "198.51.100.24" in ha) else "missing")
    # 5. the ICSA_* environment the child gets
    add("child ICSA_* env", "PASS" if not ({"ICSA_TOKEN_SOURCE", "ICSA_AUDIT_LOG", "ICSA_SLOT_KEYS"} & set(k for k in ctx.env)) else "FAIL",
        "only " + ",".join(sorted(k for k in ctx.env if k.startswith("ICSA_"))) + " (no token source, audit log or slot keys)")
    for label, d in (("site_g-dir (cold-site_g row)", ctx.a.site_g_dir), ("wan-dir (scripted-WAN row)", ctx.a.wan_dir)):
        if not d:
            add("tables input: " + label, "INFO", "not given: that row is `missing` in the report")
        else:
            n = len(list(Path(d).glob("runs/*/run.json"))) if Path(d).is_dir() else -1
            add("tables input: " + label, "PASS" if n > 0 else "FAIL", f"{d}: {n} run records" if n > 0 else f"{d}: no records")
    add("memcap", "PASS" if (V / "bin" / "memcap").is_file() else "FAIL", f"{ctx.a.memcap_gib} GiB around each call" if ctx.a.memcap_gib else "off")
    if not ctx.dry and ctx.a.memcap_gib:
        rc, _ = sh([str(V / "bin" / "memcap"), "1", "true"])
        add("memcap runs", "PASS" if rc == 0 else "FAIL", f"memcap 1 true exit {rc}")
    return rows


def ctx_frkey(ctx: Ctx) -> str:
    cmd = shlex.split(ctx.frcmd)
    return cmd[cmd.index("-i") + 1]


# ------------------------------------------------------------------------------------------------------------------------------------ pieces
STOP_EVENTS = ("mplus_stopped", "transfer_not_ended")


def run_piece(ctx: Ctx, name: str, layout: str, target_n: int, order: dict, kind: str) -> None:
    ids_all = order[layout]
    base = {"stage": kind, "piece": name, "layout": layout, "target_n": target_n}
    if ctx.halt:
        ev(ctx, event="skip", why=f"halted: {ctx.halt}", **base); return
    try:
        runs, log, done = read_state(ctx)
    except (ValueError, OSError) as e:      # a damaged run.json or log line (JSONDecodeError is a ValueError): no figures, no `done`: nothing may start on it
        ctx.halt = f"{name}: the records cannot be read ({type(e).__name__}: {str(e)[:160]}); no further measurement"
        ev(ctx, event="refuse", why=ctx.halt, **base); return
    if ctx.seen_keys is not None:           # a failure or stop event that appeared after the last piece's snapshot (nothing of ours writes there between pieces)
        late = sorted(r["run_key"] for r in runs if r["run_key"] not in ctx.seen_keys and not r.get("ok"))
        late_ev = [e["event"] for e in log[ctx.seen_log:] if e.get("event") in STOP_EVENTS]
        if late or late_ev:
            ctx.halt = f"{name}: since the last piece: failed runs {late}, events {late_ev}; no further measurement"
            ev(ctx, event="refuse", why=ctx.halt, **base); return
    fig, missing = layout_figures(ctx, layout, runs, log)
    d = G.choose_prefix(layout, ids_all, target_n, done, fig, now_s(ctx), G.parse_utc(ctx.a.not_after), ctx.a.call_overhead_s, ctx.a.margin_s)
    base["decision"] = dataclasses.asdict(d)
    if fig is not None:
        base["figures_s"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in fig.items()}
    elif missing:
        base["figures_missing"] = missing
    if ctx.stop or PAUSE.exists():
        ctx.halt = "stop requested" if ctx.stop else f"pause file {PAUSE}"
        ev(ctx, event="skip", why=ctx.halt, **base); return
    if not d.run:
        ev(ctx, event="skip", why=d.reason, **base); return
    ids = ids_all[:d.n]
    blk = blocked_steps(ctx, layout, ids, done)
    if blk and ctx.a.aside_empty:
        blk = aside_empty(ctx, blk)
    if blk:
        ctx.halt = (f"{name}: a prior attempt's run directory blocks a retry (run_one: mkdir exist_ok=False): " + "; ".join(f"{label} [{state}]" for label, _, state in blk)
                    + ("" if ctx.a.aside_empty else "; an EMPTY one holds no record: --aside-empty moves it into runs-aside/"))
        ev(ctx, event="refuse", why=ctx.halt, **base); return
    plan = piece_plan(ctx, name, layout, ids, order)
    argv = measure_argv(ctx, plan)
    if ctx.dry:
        ev(ctx, event="would-run", n=d.n, instances=ids, remaining_steps=len(G.remaining(layout, ids, done)), argv=argv, parse=parse_check(argv), **base); return
    before = {r["run_key"] for r in runs}
    n_log = len(log)
    logf = ctx.out / "logs" / f"{name}-{G.fmt_utc(time.time()).replace(':', '')}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    lf = open(logf, "ab")
    ev(ctx, event="start", n=d.n, instances=ids, remaining_steps=len(G.remaining(layout, ids, done)), logfile=str(logf), **base)
    # the decision above is a moment old (state read, plan file, log fsync): the clock, a signal and PAUSE are looked at again right before the call, with no I/O in between
    closed = now_s(ctx) >= G.parse_utc(ctx.a.not_after)
    if closed or ctx.stop or PAUSE.exists():
        lf.close()
        why = f"the window closed at {ctx.a.not_after} before the call was launched" if closed else ("stop requested" if ctx.stop else f"pause file {PAUSE}")
        if not closed:
            ctx.halt = why
        ev(ctx, event="abort-before-launch", why=why, stage=kind, piece=name)
        return
    t0 = time.time()
    with lf:
        rc = subprocess.Popen(argv, cwd=ctx.tree, env=ctx.env, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True).wait()
    wall = round(time.time() - t0, 1)
    try:
        runs2, log2, done2 = read_state(ctx)
    except (ValueError, OSError) as e:      # the child died mid-write, say: a halt and the tables, not a crash
        ctx.halt = f"{name}: exit {rc}; the records cannot be read afterwards ({type(e).__name__}: {str(e)[:160]}); no further measurement"
        ev(ctx, event="end", rc=rc, wall_s=wall, records_unreadable=True, **base)
        ev(ctx, event="halt", why=ctx.halt, stage=kind, piece=name)
        return
    ctx.seen_keys, ctx.seen_log = {r["run_key"] for r in runs2}, len(log2)
    new = [{"key": r["run_key"], "ok": bool(r.get("ok")), "wall_s": r.get("wall_s")} for r in runs2 if r["run_key"] not in before]
    stopped = [e["event"] for e in log2[n_log:] if e.get("event") in STOP_EVENTS]
    failed = [r["key"] for r in new if not r["ok"]]
    ev(ctx, event="end", rc=rc, wall_s=wall, new_runs=new, failed_runs=failed, stop_events=stopped,
       steps_done_now=len(done2), steps_left_in_piece=len(G.remaining(layout, ids, done2)), **base)
    if rc != 0 or failed or stopped:
        ctx.halt = f"{name}: exit {rc}, failed runs {failed}, events {stopped}: site_f's replica may be changing or a run directory blocks a retry; no further measurement"
        ev(ctx, event="halt", why=ctx.halt, stage=kind, piece=name)


def tables(ctx: Ctx) -> None:
    argv = report_argv(ctx)
    base = {"stage": "tables", "piece": "mplus-report", "site_g_dir": ctx.a.site_g_dir or None, "wan_dir": ctx.a.wan_dir or None, "tables_by": ctx.a.tables_by}
    if ctx.dry:
        ev(ctx, event="would-run", argv=argv, parse=parse_check(argv), note="a dir not given leaves its row `missing` (cold-site_g: --site_g-dir, scripted WAN: --wan-dir)", **base); return
    if not (ctx.out / "mplus_log.jsonl").exists():
        ev(ctx, event="skip", why="no mplus_log.jsonl: nothing was measured", **base); return
    t0 = time.time()
    late = max(0.0, time.time() - G.parse_utc(ctx.a.tables_by))
    ev(ctx, event="start", late_s=round(late), **base)
    logf = ctx.out / "logs" / f"tables-{G.fmt_utc(time.time()).replace(':', '')}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, "ab") as lf:
        rc = subprocess.Popen(argv, cwd=ctx.tree, env=ctx.env, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT).wait()
    be = ctx.out / "breakeven.json"
    rows = None
    if rc == 0 and be.exists():
        d = json.loads(be.read_text())
        rows = {"rows": len(d.get("break_even", {})), "missing_rows": sum(1 for v in d.get("break_even", {}).values() if "missing" in v)}      # counts only
    ev(ctx, event="end", rc=rc, wall_s=round(time.time() - t0, 1), breakeven_written=bool(rc == 0 and be.exists()), counts=rows, late_s=round(late), **base)
    if rc != 0:
        ctx.halt = ctx.halt or "tables failed"


def summary(ctx: Ctx, order: dict) -> None:
    try:
        runs, _, done = read_state(ctx)
    except (ValueError, OSError) as e:
        ev(ctx, event="summary", stage="summary", records_unreadable=f"{type(e).__name__}: {str(e)[:160]}", halted=ctx.halt or None); return
    per = {la: {"done": len({s for s in G.expected_steps(la, order[la]) if s in done}), "of": 3 * len(order[la]),
                "not_run": sorted(f"{i}/{s}" for (i, _, s) in G.remaining(la, order[la], done))} for la in LAYOUTS}
    ev(ctx, event="summary", stage="summary", per_layout=per, failed_runs=[r["run_key"] for r in runs if not r.get("ok")], halted=ctx.halt or None)


# ------------------------------------------------------------------------------------------------------------------------------------ main
def selftest(ctx: Ctx, order: dict) -> None:
    """The gate on SYNTHETIC step times (invented, not predictions), to show its decisions: plenty of time, a tight window, a closed one."""
    fig = {"evict_s": 20.0, "cold_s": 400.0, "prov_req_s": 150.0, "req_s": 250.0, "prov_layout_s": 600.0, "layout_run_s": 250.0}
    done = {("I48", la, s) for la in LAYOUTS for s in G.STEPS}
    na = G.parse_utc(ctx.a.not_after)
    print("gate illustration on SYNTHETIC figures (evict 20 s, cold 400, required prov 150, M+ 250, layout prov 600, layout M+ 250), barrier done, overhead "
          f"{ctx.a.call_overhead_s:.0f} s, margin {ctx.a.margin_s:.0f} s, not after {ctx.a.not_after}:")
    for label, now in (("6 Nov 00:00Z", G.parse_utc("2026-11-06T00:00:00Z")), ("6 Nov 05:30Z", G.parse_utc("2026-11-06T05:30:00Z")), ("6 Nov 06:40Z", G.parse_utc("2026-11-06T06:40:00Z")),
                       ("6 Nov 07:30Z", na)):
        for la in LAYOUTS:
            d = G.choose_prefix(la, order[la], 5, done, fig, now, na, ctx.a.call_overhead_s, ctx.a.margin_s)
            print(f"  now {label} {la}: run={d.run} n={d.n} rule={d.rule}: {d.reason}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)      # mplus-run.sh reads --head itself: no abbreviations
    ap.add_argument("--run", action="store_true", help="act (default: dry: validate and print only, no run started, no site_g or site_f read)")
    ap.add_argument("--head", default="f1c242a", help="the frozen head (7 hex): its tree wt/launch-<head> and image icsa-sandbox:oracle-<12>; outputs in mplus/<head>/")
    ap.add_argument("--stages", default="preflight,barrier,resume,tables")
    ap.add_argument("--not-after", default=NOT_AFTER, help="no piece starts, and none is projected to end, after this (science #34, 4 Nov 18:53Z: 07:30Z)")
    ap.add_argument("--tables-by", default=TABLES_BY)
    ap.add_argument("--order", choices=("literal", "balanced"), default="balanced",
                    help="balanced (science #34, 4 Nov 19:21Z: the ruled order, a departure from the literal order): 3 of 5 per layout first, then the rest; "
                         "literal: S1's 5 instances, then S2's (the registered order of mplus.measure)")
    ap.add_argument("--margin-s", type=float, default=900.0, help="safety before --not-after for a piece's projected end")
    ap.add_argument("--call-overhead-s", type=float, default=900.0, help="added to a piece's projection: Campaign init (15,340-entry listing), transfer_health, wait_for_stop (<= 600 s)")
    ap.add_argument("--memcap-gib", type=int, default=32)
    ap.add_argument("--site_g-dir", default=None, help=f"mplus-report --site_g-dir: the batch whose M runs on site_g count as cold-site_g (step A's quiet baselines, per icsa/scripted/README.md). Default {DEF_SITE_G} if it exists; "
                    "--site_g-dir '' runs the report without that row")
    ap.add_argument("--wan-dir", default=None, help=f"mplus-report --wan-dir: the WAN anchor's results (results/scripted/wan_20261101T161015Z in the repo, copied to .23). Default {DEF_WAN} if it exists; "
                    "--wan-dir '' runs the report without the scripted-WAN row")
    ap.add_argument("--launch-config", default=str(L / "launch-main-09ecc2c.json"), help="its site_g_settings_cmd is the check every run makes")
    ap.add_argument("--aside-empty", action="store_true",
                    help="before a piece, rename EMPTY run directories (no file in them: an site_g-settings refusal makes one) into runs-aside/, nothing deleted; any directory with a file or a run.json still blocks")
    ap.add_argument("--stamp-max-age-s", type=float, default=600.0)
    ap.add_argument("--space-sha256", default=SPACE_SHA256)
    ap.add_argument("--now", default="", help="dry only: pretend the clock is this UTC time (YYYY-MM-DDTHH:MM:SSZ)")
    a = ap.parse_args(argv)
    if a.site_g_dir is None:
        a.site_g_dir = str(DEF_SITE_G) if DEF_SITE_G.is_dir() else ""
    if a.wan_dir is None:
        a.wan_dir = str(DEF_WAN) if DEF_WAN.is_dir() else ""
    if a.now and a.run:
        raise SystemExit("--now is for the dry run only")
    tree, py, sha, image = load_tree(a)
    frcmd = shlex.join(json.loads(Path(a.launch_config).read_text())["site_g_settings_cmd"])
    ctx = Ctx(a, not a.run, tree, py, sha, image, MP / a.head, frcmd)
    stages = a.stages.split(",")
    if sys.executable != py and not ctx.dry:
        raise SystemExit(f"run under the tree's python ({py}), as mplus-run.sh does")
    order = seeded_orders()
    print(f"{'DRY RUN (nothing started, site_g and site_f not read)' if ctx.dry else 'RUN'}: head {sha}, image {image}, out {ctx.out}, not after {a.not_after}, tables by {a.tables_by}, order {a.order}")
    if ctx.dry:
        print("seeded order:", json.dumps(order))
        for l in validate_plan_files(order):
            print(" ", l)
        selftest(ctx, order)
    if not ctx.dry:
        MP.mkdir(parents=True, exist_ok=True)
        lock = open(MP / "run.lock", "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SystemExit("another mplus-run.sh holds run.lock")
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: (setattr(ctx, "stop", True), ev(ctx, event="signal", why="finishing the piece in flight, then stopping")))
        ctx.out.mkdir(parents=True, exist_ok=True)
        ev(ctx, event="driver-start", stages=stages, not_after=a.not_after, order=a.order, argv=sys.argv[1:])
    # a real start of measurement always runs the preflight (no way to skip it); `tables` alone (after a halt) reads files only and needs none
    rows = preflight(ctx) if (ctx.dry and "preflight" in stages) or (not ctx.dry and ("barrier" in stages or "resume" in stages)) else []
    for n, s, d in rows:
        print(f"  preflight {s:8} {n}: {d}")
    bad = [r for r in rows if r[1] not in ("PASS", "INFO")]
    if not ctx.dry:
        ev(ctx, event="preflight", stage="preflight", results=[{"check": n, "state": s} for n, s, _ in rows])
        if bad:
            ev(ctx, event="refuse", stage="preflight", why=f"{len(bad)} preflight check(s) not PASS: " + ", ".join(f"{n}={s}" for n, s, _ in bad))
            return 2
    elif bad:
        print(f"  ({len(bad)} preflight check(s) not PASS: expected in a dry run while main and the fault calibration run, and without a stamp)")
    def guarded(stage: str, fn, *args) -> None:
        """A real run turns an unexpected exception into a halt, a `crash` event and the stages after it (the tables, the summary), not a traceback that ends the driver with
        a call still running unobserved. A dry run lets it raise."""
        if ctx.dry:
            fn(*args); return
        try:
            fn(*args)
        except Exception as e:      # noqa: BLE001
            ctx.halt = ctx.halt or f"{stage}: driver error {type(e).__name__}: {str(e)[:300]}"
            ev(ctx, event="crash", stage=stage, why=f"{type(e).__name__}: {str(e)[:300]}")

    if "barrier" in stages:
        for la in LAYOUTS:
            guarded("barrier", run_piece, ctx, f"barrier-{la}", la, 1, order, "barrier")
    if "resume" in stages:
        for k, (la, n) in enumerate(G.rounds(a.order)):
            guarded("resume", run_piece, ctx, f"resume-{k}-{la}-n{n}", la, n, order, "resume")
    if "tables" in stages:
        guarded("tables", tables, ctx)
    if not ctx.dry:
        guarded("summary", summary, ctx, order)
    return 1 if ctx.halt else 0


if __name__ == "__main__":
    sys.exit(main())
