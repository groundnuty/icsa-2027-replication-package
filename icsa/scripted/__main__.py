"""Driver: python -m icsa.scripted <command> [...]  (unsandboxed: docker and the federation).

  reference --out DIR                     per-instance SST hashes from the local verified s1z copy
  smoke --out DIR [--instance I35]        one instance through all eight option x layout paths, in a seeded order
  pilot --out DIR [--instances ...] [--reps K] [--seed N] [--workers W] [--resume] [--untraced]
                                          single runs: instances x paths; traced unless --untraced
  baseline --out DIR [--instances I35,I37,I48] [--k 5] [--untraced-k 3] [--max-failures 2] [--resume] [--probe-files T=N,M=N]
                                          science's step A: traced runs of the 8 cells with the controls interleaved
  curve --out DIR --block 1 --baseline DIR.. [--levels 2,4,8,12,16] [--max-level N] [--dry-run] [--resume] [--stop first-fail] [--instances ...] [--mem-per-run-gib G] [--untraced]
                                          the concurrency curve, per block, as that block's mix of cells
  curve-multi --out DIR --block 1 --baseline DIR.. --hosts FILE --capacity a=N,b=M [--levels ..] [--resume] [curve's other options]
                                          the same curve across two run hosts (#34): up to a's capacity on a alone, above it on both at once
  curve-part --out DIR --block B --level L --slots i,j,k --host NAME [--solo] ...
                                          one host's share of one level: what curve-multi starts on each host (icsa/scripted/multihost.py)
  live-probe --shape T|M --out DIR --baseline DIR.. [--instance I35] [--untraced]
                                          amendment 25(e)'s probe: one scripted S1 cell, one JSON line (icsa/scripted/liveprobe.py); the campaign runs it
  report --out DIR --single DIR.. --curve DIR.. [--pipeline DIR..] [--overhead DIR..] [--tracer-compare DIR..] [--untraced]
                                          the dossier's scripted_pipeline and scripted_timing, the analysis's overhead file
Every command writes MANIFEST.json (code sha, image, seed) next to its runs, under `--out`.
Above level 16 is refused here: it needs an explicit decision. The audit-log state of a batch is ICSA_AUDIT_LOG (default off).
"""
from __future__ import annotations

import argparse
import contextlib
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

import numpy as np

from .. import opwrestart
from ..instances import load as L
from ..records import Layout, Option
from ..sandbox import earlyoom as EO
from ..sandbox import hostops as H
from ..sandbox.termination import exit_on_sigterm, wait_for_stop
from . import bundle, curve, federation as F, metrics, mgate, multihost, plans
from .compare import FrozenTruth, sha256_file
from .reference import load_or_build_reference
from .runner import OWN_CONTAINERS, Plan, cleanup_own_containers, run_one
from . import liveprobe

MAX_LEVEL = plans.MAX_LEVEL
DISK_MARGIN_GIB = 40.0
PACE_RETRY_S = 1.0          # duty-cycle curve: a padding run that found no free slot tries again after this
MIN_MEM_PER_RUN_GIB = 2.0       # a guess until the traced baselines measure it (--mem-per-run-gib)


def _manifest(out: Path, command: str, *, resume: bool = False, **kw) -> dict:
    sha = os.environ.get("ICSA_RUN_SHA")
    if not sha:
        raise SystemExit("set ICSA_RUN_SHA: runs come from a git-archive snapshot of that sha")
    image = os.environ.get("ICSA_SANDBOX_IMAGE")
    if not image:
        raise SystemExit("set ICSA_SANDBOX_IMAGE: this lane's own image tag, built from the snapshot")
    m = {"command": command, "code_sha": sha, "image": image,
         "image_id": H.image_id(image),
         "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "audit_log": os.environ.get("ICSA_AUDIT_LOG", "off"),
         "caches": "client caches fresh per run; provider page cache not controlled; host page cache not dropped",
         "refdet_source_sha256": bundle.source_sha256(), **kw}
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"MANIFEST_{command}.json"
    if p.exists():
        if not resume:
            raise SystemExit(f"{p} exists: use a new --out, or --resume")
        k = 2
        while (out / f"MANIFEST_{command}_resume{k}.json").exists():
            k += 1
        p = out / f"MANIFEST_{command}_resume{k}.json"
    p.write_text(json.dumps(m, indent=1, default=str))
    (out / "insandbox_script.py").write_text(bundle.script_source())
    return m


def _clean(path: Path) -> bool:
    """A record that is missing, empty or cut while it was written is an attempt that did not finish."""
    try:
        return json.loads(path.read_text()).get("ok") is True
    except (OSError, ValueError, AttributeError):
        return False


def _infrastructure(path: Path) -> bool:
    try:
        return bool(json.loads(path.read_text()).get("infrastructure"))
    except (OSError, ValueError, AttributeError):
        return False


def pending(plan_list: list[Plan], runs_dir: Path) -> list[Plan]:
    """What is left after an interruption: a plan with a clean run is done; one that failed or was cut gets the next
    attempt number, and its earlier attempts stay on the record."""
    out = []
    for p in plan_list:
        attempts = sorted(runs_dir.glob(f"{p.key().rsplit('-a', 1)[0]}-a*"))
        if any(_clean(d / "run.json") for d in attempts):
            continue
        next_attempt = max([int(d.name.rsplit("-a", 1)[1]) for d in attempts], default=0) + 1
        if next_attempt > MAX_ATTEMPTS and any(_infrastructure(d / "run.json") for d in attempts):
            continue                     # exhausted: no outcome (protocol/parameters.md); a resume adds no fourth attempt, even when the third was cut
        p.attempt = next_attempt
        out.append(p)
    return out


def _common(args):
    man = L.load_instances()
    recs = {r["instance"]["instance_id"]: r for r in man["instances"]}
    pilot = sorted(i for i, r in recs.items() if r["instance"]["pilot"])
    if tuple(pilot) != plans.PILOT:
        raise SystemExit(f"manifest's pilot set {pilot} differs from plans.PILOT")
    return man, recs, FrozenTruth(man)


def _one(plan: Plan, recs, truth, target, cfg, out: Path, refs, **kw) -> dict:
    if metrics.meminfo_available_gib() < MIN_MEM_PER_RUN_GIB + 5:
        raise SystemExit("host MemAvailable too low to start a run")
    return run_one(plan, recs[plan.instance_id], truth, lambda: F.data_config(target, plan.option), cfg, out,
                   expected_sst=refs[plan.instance_id], **kw)


def _say(r: dict) -> None:
    print(f"{time.strftime('%H:%M:%SZ', time.gmtime())} {r['run_key']} ok={r['ok']} wall={r.get('wall_s')} "
          f"between_sites={(r.get('bytes') or {}).get('between_sites_rx')} req={r.get('client_requests')} "
          f"listing={(r.get('script') or {}).get('listing_entries')} errors={r['errors'][:1]} "
          f"load={r['host_before']['load1']} others={r['host_before']['other_sandboxes']}", flush=True)


def cmd_reference(args) -> None:
    man, recs, _ = _common(args)
    print(json.dumps(load_or_build_reference(args.out, [recs[i] for i in plans.PILOT]), indent=1))


def cmd_paths(args, plan_list: list[Plan], command: str, **manifest_kw) -> list[dict]:
    _audit_note(command)
    man, recs, truth = _common(args)
    out = Path(args.out)
    workers = getattr(args, "workers", 1)
    if workers > MAX_LEVEL:
        raise SystemExit(f"more than {MAX_LEVEL} workers needs an explicit decision from the lane's parent")
    resume = getattr(args, "resume", False)
    m = _manifest(out, command, resume=resume, runs=[p.key() for p in plan_list], workers=workers, **manifest_kw)
    if resume:
        plan_list = pending(plan_list, out / "runs")
    refs = load_or_build_reference(out, [recs[i] for i in sorted({p.instance_id for p in plan_list})])
    instruments = manifest_kw.get("instruments")
    cfg = F.sandbox_config(F.MAIN, m["image"], instruments=instruments)

    def one(p: Plan) -> dict:
        r = _one(p, recs, truth, F.MAIN, cfg, out / "runs", refs, extra={"pool_workers": workers, "traced": bool(instruments)})
        _say(r)
        return r

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, plan_list))


def cmd_smoke(args) -> None:
    plan_list = plans.pilot_plan(args.seed, instances=(args.instance,), tag="smoke")
    if args.only:            # e.g. "D:S2,M:S1": only these option:layout paths, in the plan's order
        want = {tuple(x.split(":")) for x in args.only.split(",")}
        plan_list = [p for p in plan_list if (p.option.value, p.layout.value) in want]
        if len(plan_list) != len(want):
            raise SystemExit(f"--only {args.only}: no such path in {sorted(want)}")
    rs = cmd_paths(args, plan_list, "smoke", seed=args.seed)
    print(json.dumps({"ok": sum(r["ok"] for r in rs), "of": len(rs)}))


def cmd_pilot(args) -> None:
    plan_list = plans.pilot_plan(args.seed, instances=plans.parse_instances(args.instances), reps=args.reps)
    slot, rec = F.traced_slot() if not args.untraced else (None, None)
    rs = cmd_paths(args, plan_list, "pilot", seed=args.seed, instruments=slot, tracer=rec, traced=not args.untraced,
                   instances=args.instances, reps=args.reps)
    print(json.dumps({"ok": sum(r["ok"] for r in rs), "of": len(rs)}))


def cmd_perf(args) -> None:
    """M with `--log-read-write-perf`: request counts. Its overhead is unmeasured, so timed runs do not carry it."""
    man, recs, truth = _common(args)
    out = Path(args.out)
    plan_list = [Plan(i, Option.M, la, tag="perf") for i in plans.PILOT for la in plans.LAYOUTS]
    m = _manifest(out, "perf", runs=[p.key() for p in plan_list])
    refs = load_or_build_reference(out, [recs[i] for i in plans.PILOT])
    cfg = F.sandbox_config(F.MAIN, m["image"])
    for p in plan_list:
        r = run_one(p, recs[p.instance_id], truth,
                    lambda: F.data_config(F.MAIN, Option.M, perf_log=True),
                    cfg, out / "runs", expected_sst=refs[p.instance_id], perf=True)
        _say(r)


def _audit_note(command: str) -> None:
    state = os.environ.get("ICSA_AUDIT_LOG", "off")
    print(f"{command}: ICSA_AUDIT_LOG={state}" + ("" if state == "on" else
          " (the audit log is ON at site_g since 1 Nov 20:55Z: set ICSA_AUDIT_LOG=on, or these runs are labelled off)"), file=sys.stderr, flush=True)


def require_audit_log(command: str) -> None:
    """The baselines and the curve run with the audit log ON (it is on at site_g since 1 Nov 20:55Z; science, #12/#85, 21:38Z): a warning
    scrolled past at 01:00Z is how that would get missed, so anything but `ICSA_AUDIT_LOG=on` refuses to start. The manifest records the
    state either way."""
    state = os.environ.get("ICSA_AUDIT_LOG")
    if state != "on":
        raise SystemExit(f"{command}: refusing to start: ICSA_AUDIT_LOG is {state!r}, not 'on'. The baselines and the curve run with the "
                         "audit log on; set ICSA_AUDIT_LOG=on (and check that the log is on at site_g).")


# The published fields `Production` reads: sha256 as reports/refdet/README.md records it (the md5 matches the publisher's).
BALMHW_SUPP_SHA256 = "29000d4cd30f23c5b366e4a7e2360fce1fe3020553a13d09a801dc8378482940"


def balmhw_supp_check() -> dict:
    """ref/bashiri/data/BALMHW_supp.nc exists and has the recorded sha256 (it was missing on both new VMs; Production fails without it)."""
    from .. import paths
    from ..refdet.data import SUPP_NAME
    f = paths.REF / "bashiri" / "data" / SUPP_NAME
    if not f.is_file() or f.stat().st_size == 0:
        raise RuntimeError(f"{f} is missing or empty")
    got = sha256_file(f)
    if got != BALMHW_SUPP_SHA256:
        raise RuntimeError(f"{f} has sha256 {got[:12]}.., recorded {BALMHW_SUPP_SHA256[:12]}..")
    return {"balmhw_supp_sha256": got}


def refdet_cache_check() -> dict:
    """The refdet field cache the reference detection reads: present, and valid for the current S1 files (check_ground_truth)."""
    from ..refdet import fieldcache, required_baseline_days
    from ..refdet.truth import DEFAULT_CACHE
    fieldcache.check_ground_truth(DEFAULT_CACHE, source=fieldcache.S1_SOURCE,
                                  source_fingerprint=fieldcache.s1_fingerprint(required_baseline_days()))
    for f in ("m90", "mclim", "finite_baseline"):          # check_ground_truth reads the record, not the arrays: open each one
        np.load(Path(DEFAULT_CACHE) / f"{f}.npy", mmap_mode="r")
    return {"cache": str(DEFAULT_CACHE)}
MAX_ATTEMPTS = 3      # protocol/parameters.md: an infrastructure failure restarts the run from scratch, at most 3 attempts


def with_infrastructure_retry(plan, attempt) -> dict:
    """A run whose record says host infrastructure (an earlyoom kill) runs again under its next attempt number; the earlier record stays."""
    r = attempt()
    while r.get("infrastructure") and plan.attempt < MAX_ATTEMPTS:
        plan.attempt += 1
        r = attempt()
    return r


def traced_import_smoke(image: str) -> dict:
    """One real sandbox with the campaign's tracer, running the script's import stage: no site_g, no token, no data. A traced run that cannot import its own
    sources dies in 2 s and looks like any failed run, as every one did until 2 Nov. Exit 0 is not enough: the tracer must really have been loaded, and
    the sources must be the bundle's."""
    from ..sandbox import DataConfig, Sandbox
    slot, _ = F.traced_slot()
    cfg = F.sandbox_config(F.MAIN, image, instruments=slot)
    zone, provider = "zone.preflight.invalid", "provider.preflight.invalid"
    nowhere = {"addr": "localhost", "port": 1, "tls": False}
    dc = DataConfig(onezone_host=zone, space_name="preflight", token="preflight-not-a-token", provider_hosts=[provider], upstream={zone: nowhere, provider: nowhere},
                    s1_path="s1z", s2_path="s2z/sst_s2.nc")
    sbx = Sandbox.start("preflight-traced-import", Option.T, Layout.S1, dc, cfg)
    try:
        r = sbx.exec(bundle.import_smoke_code(), 300, _record=False)
    finally:
        sbx.stop()
    if r.exit_code != 0:
        raise RuntimeError(f"the traced script does not import: exit {r.exit_code}: {r.stderr[-240:]}")
    got = json.loads(r.stdout.strip().splitlines()[-1])
    if not got["tracer_hooks"]:
        raise RuntimeError("the sandbox ran without the tracer, so this proves nothing about a traced run")
    if got.get("tracer_error"):      # sitecustomize swallows a failed start and leaves the hooks imported
        raise RuntimeError(f"the tracer did not start: {got['tracer_error'][-240:]}")
    if not got["refdet"].startswith(got["package_dir"]):
        raise RuntimeError(f"the script's sources did not come from its bundle: {got['refdet']}")
    return got


def preflight_baseline(args) -> dict:
    """Everything `baseline` needs, checked WITHOUT a token and with one unauthenticated request (the provider route: the open configuration endpoint on the configured port, certificate verified): the audit log, the slot-user token source, the pinned image,
    the tracer's instruments (built content-addressed, as a run would), that the script really imports in a sandbox with that tracer
    (the one sandbox this starts: `traced_import_smoke`), the slot pool and its credential files (existence only, never read), the plan, free
    memory and disk. Returns the report; `ok` is False if any check failed."""
    from . import tokens
    checks: dict = {}

    secret_env = [v for k, v in os.environ.items() if k in ("ICSA_TOKEN_SOURCE", "OD_TOKEN", "OD_READ_TOKEN") and v]

    def clean(msg: str) -> str:
        for v in secret_env:                       # an env value that is not what it should be may be a secret: never echoed
            msg = msg.replace(v, "<env>")
        return re.sub(r"gh[pousr]_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{15,}|MDA[xyz][A-Za-z0-9_-]{30,}", "<scrubbed>", msg)[:300]

    def check(name, fn):
        try:
            checks[name] = {"ok": True, **(fn() or {})}
        except SystemExit as e:
            checks[name] = {"ok": False, "why": clean(str(e))}
        except Exception as e:  # noqa: BLE001
            checks[name] = {"ok": False, "why": clean(f"{type(e).__name__}: {e}")}

    check("audit_log", lambda: require_audit_log("baseline"))
    check("slot_tokens", lambda: tokens.require_slot_tokens("baseline"))

    def run_sha():
        sha = os.environ.get("ICSA_RUN_SHA", "")
        if not re.fullmatch(r"[0-9a-f]{7,40}", sha):                  # a git sha; any other value is never echoed
            raise RuntimeError("ICSA_RUN_SHA is unset or not a git sha")
        return {"sha": sha}
    check("run_sha", run_sha)

    def image():
        img = os.environ.get("ICSA_SANDBOX_IMAGE")
        if not img:
            raise RuntimeError("ICSA_SANDBOX_IMAGE unset")
        return {"image": img, "image_id": H.image_id(img)}
    check("image", image)

    def instruments():
        slot, rec = F.traced_slot()
        d, mod = Path(slot["instruments_dir"]), slot["instrument_module"]
        if not d.is_dir() or not (d / f"{mod}.py").is_file():          # a damaged cache is reused by ensure_instruments
            raise RuntimeError(f"the instruments directory is missing its boot module {mod}.py")
        from ..harness.real_sandbox import instruments_hash
        if instruments_hash(d) != rec["instruments_sha256"]:
            raise RuntimeError("the instruments directory does not match its recorded sha256")
        return {"instruments_dir": str(d), **rec}
    check("instruments", instruments)

    def traced_import():
        if not (checks["image"]["ok"] and checks["instruments"]["ok"]):
            raise RuntimeError("not tried: it needs the image and the instruments")
        return traced_import_smoke(os.environ["ICSA_SANDBOX_IMAGE"])
    check("traced_import", traced_import)
    check("earlyoom_exempt", EO.require_driver_exempt)

    def pool():
        from ..harness import slot_lease
        from ..harness.slot_users import SECRETS_DIR
        sp = slot_lease.SlotPool()
        out = {}
        for opt in ("T", "T-unpaginated", "D", "M"):
            slots = sp.slots_of(opt)
            def usable(k):                          # a regular file, no group/other permission: what read_slot_password accepts (metadata only)
                f = Path(SECRETS_DIR) / f"{slot_lease._username(k, opt)}.pass"
                return f.is_file() and not f.stat().st_mode & 0o077 and os.access(f, os.R_OK)      # readable as this user
            missing = [k for k, _ in slots if not usable(k)]
            if not slots or missing:
                raise RuntimeError(f"{opt}: {len(slots)} slot users, {len(missing)} without a usable credential file (a regular file, mode 0600)")
            out[opt] = len(slots)
        return {"slot_users_per_option": out}
    check("slot_pool", pool)

    def frozen_truth():              # a host without these dies at its first baseline (2 Nov: both were missing on the new VM)
        man, _, truth = _common(args)        # FrozenTruth refuses a mask file that is missing or whose sha256 differs
        return {"cell_masks_sha256": truth.sha256}
    check("frozen_truth", frozen_truth)
    check("refdet_cache", refdet_cache_check)
    def code_version():              # a synced tree without .git and without a stamp records "unknown" on every run
        from .. import codestamp
        v = codestamp.require_known("baseline", Path(__file__).resolve().parents[2])
        return {"commit": v["commit"], "dirty": v["dirty"], "source": v["source"]}
    check("code_version", code_version)

    def site_g_settings_check():         # science, #2, 2 Nov 03:54Z: the Traefik and op_worker settings must be the frozen ones
        from .. import frsettings
        r = frsettings.check_from_env(required=True)
        if r["state"] != "match":
            raise RuntimeError(f"site_g settings {r['state']}: {r['why']}")
        return {"site_g_settings_sha256": r["hash"]}
    check("site_g_settings", site_g_settings_check)
    check("balmhw_supp", balmhw_supp_check)

    def output():
        out = Path(args.out)
        if (out / "MANIFEST_baseline.json").exists() and not args.resume:
            raise RuntimeError(f"{out}/MANIFEST_baseline.json exists: use a new --out, or --resume")
        anc = out
        while not (anc.exists() or anc.is_symlink()) and anc != anc.parent:   # a dangling symlink exists: mkdir would fail on it               # the nearest existing ancestor is where mkdir would write
            anc = anc.parent
        if not anc.is_dir() or not os.access(anc, os.W_OK | os.X_OK):
            raise RuntimeError(f"{anc} is not a writable directory: --out {out} cannot be created")
        return {"out": str(out), "resume": bool(args.resume and (out / "MANIFEST_baseline.json").exists())}
    check("output", output)

    def plan():
        inst = plans.parse_instances(args.instances)
        rows = _baseline_rows(args, inst)[0]
        arms: dict[str, int] = {}
        for _, a in rows:
            arms[a] = arms.get(a, 0) + 1
        return {"instances": list(inst), "runs": len(rows), "arms": arms}
    check("plan", plan)

    def limits():
        F.sandbox_limits_kw()                       # refuses an unset tracer headroom, as baseline's sandbox_config would
    check("sandbox_limits", limits)

    def provider_route():
        """The configured route answers from this host with a real request and its certificate verifies; a failure is named."""
        from ..sandbox import route
        from ..harness.real_sandbox import PROVIDER_HOST
        r = route.check_provider_port(PROVIDER_HOST, route.configured_provider_port())
        if not r["ok"]:
            raise RuntimeError(f"provider route ({r['path']}) failed at {r.get('stage')}: {r['why']}")
        return {k: r[k] for k in ("host", "port", "path", "status")}
    check("provider_route", provider_route)

    def host():
        from .. import paths
        mem, disk = metrics.meminfo_available_gib(), metrics.disk_free_gib(paths.DATA_ROOT)
        if mem < MIN_MEM_PER_RUN_GIB + 5:
            raise RuntimeError(f"MemAvailable {mem:.0f} GiB is too low to start a run")
        return {"mem_available_gib": round(mem, 1), "disk_free_gib": round(disk, 1)}
    check("host", host)
    return {"ok": all(v["ok"] for v in checks.values()), "checks": checks}


def _baseline_rows(args, instances) -> tuple[list, dict | None]:
    """(the baseline's runs, the probe's file counts). Without `--probe-files` it is `baseline_plan` as it always was; with it, ONLY the live probe's prefix cell
    (`plans.probe_baseline_plan`), for a directory of its own: the ordinary baseline is run without it."""
    text = getattr(args, "probe_files", None)
    if not text:
        return plans.baseline_plan(args.seed, instances, k=args.k, untraced_k=args.untraced_k, controls=args.controls), None
    if args.controls:
        raise SystemExit("baseline: --probe-files runs the probe's prefix cell alone; the overhead controls belong to the ordinary baseline")
    files = plans.parse_probe_files(text)
    return plans.probe_baseline_plan(args.seed, files, instances, k=args.k, untraced_k=args.untraced_k), files


def cmd_baseline(args) -> None:
    """Science's step A (#12, 1 Nov 17:30Z): 8 cells on 3 instances, traced, exact against the frozen truth, with the overhead
    controls interleaved per instance and cell. Stops after `--max-failures`: the runs are also the tracer's first
    real-size test, and hours of failing runs would tell nothing more."""
    from . import control as K
    from . import tokens
    if args.preflight:
        rep = preflight_baseline(args)
        print(json.dumps(rep, indent=1))
        raise SystemExit(0 if rep["ok"] else 2)
    require_audit_log("baseline")
    from .. import codestamp
    codestamp.require_known("baseline", Path(__file__).resolve().parents[2])      # a run must record which code made it
    from .. import frsettings
    r = frsettings.check_from_env(required=True)         # the Traefik and op_worker settings must be the frozen ones before the first run
    if r["state"] != "match":
        raise SystemExit(f"baseline: refusing to start: site_g settings {r['state']} ({r['why']})")
    from .. import frprobe
    rr = frprobe.check_configured()                     # the short fixed read before the block: a low rate stops it, an unreadable one holds it
    if rr["state"] != "ok":
        raise SystemExit(f"baseline: refusing to start: the pre-block site_g read check is {rr['state']} ({rr['why']})")
    tokens.require_slot_tokens("baseline")        # science, #2, 18:17Z: the baselines make criterion (v) true of the campaign's paths
    man, recs, truth = _common(args)
    out = Path(args.out)
    instances = plans.parse_instances(args.instances)
    rows, probe_files = _baseline_rows(args, instances)
    if args.resume:      # pending() renumbers the attempt of what is left, so it is matched by the key without it
        left = {p.key().rsplit("-a", 1)[0]: p for p in pending([p for p, _ in rows], out / "runs")}
        rows = [(left[p.key().rsplit("-a", 1)[0]], arm) for p, arm in rows if p.key().rsplit("-a", 1)[0] in left]
    slot, tracer = F.traced_slot()
    m = _manifest(out, "baseline", resume=args.resume, seed=args.seed, k=args.k, untraced_k=args.untraced_k, instances=instances,
                  tracer=tracer, runs=[[p.key(), arm] for p, arm in rows], **({} if probe_files is None else {"probe_files": probe_files}))
    refs = load_or_build_reference(out, [recs[i] for i in instances])
    cfg_traced = F.sandbox_config(F.MAIN, m["image"], instruments=slot)
    cfg_plain = F.sandbox_config(F.MAIN, m["image"])
    failures = 0
    t_base = time.time()
    for p, arm in rows:
        if metrics.meminfo_available_gib() < MIN_MEM_PER_RUN_GIB + 5:
            raise SystemExit("host MemAvailable too low to start a run")

        def attempt(arm=arm):
            if arm == "control":
                return K.run_control(p, recs[p.instance_id], truth, lambda o=p.option: F.data_config(F.MAIN, o), cfg_traced,
                                     out / "runs", expected_sst=refs[p.instance_id], extra={"arm": arm})
            return run_one(p, recs[p.instance_id], truth, lambda o=p.option: F.data_config(F.MAIN, o),
                           cfg_traced if arm == "enforced" else cfg_plain, out / "runs", expected_sst=refs[p.instance_id],
                           extra={"variant": "enforced", "arm": arm}, read_files=None if probe_files is None else probe_files[plans.probe_shape(p.option)])
        r = with_infrastructure_retry(p, attempt)
        _say(r)
        failures += not r["ok"]
        if failures >= args.max_failures:
            raise SystemExit(f"stopped after {failures} failed runs; the last: {r['run_key']}: {r['errors'][:1]}")
    cut = opwrestart.cut_by_restart(t_base)
    if cut:        # the baseline is redone whole: its reports are not written, and the marker says why
        (out / "CUT_BY_OP_WORKER_RESTART").write_text(cut + "\n")
        raise SystemExit(f"baseline {cut}: redo it whole under a new --out; no report written")
    if probe_files is None:           # the prefix cell is not a run and enters no report: the directory holds the probe's baseline and nothing else
        write_reports(out, single=[out], overhead=[out], tracer_compare=[out], pipeline=[out])


def _sem_has_room(sem) -> bool:
    """Whether a semaphore has a permit free now (taken and given back at once)."""
    if sem.acquire(blocking=False):
        sem.release()
        return True
    return False


def run_mix(block, level, rep, recs, truth, refs, cfg, out: Path, *, seed, instances, target=F.MAIN,
            mem_per_run_gib: float = MIN_MEM_PER_RUN_GIB, pace=None, make_config=None, gate_report: dict | None = None, part=None) -> list[dict]:
    """`level` sandboxes looping over the block's cells in random order, all at once. Slots that finish their counted runs
    go on with padding runs, so that every counted run saw the full level from start to end; those are cancelled when the
    last counted run ends, and enter no statistic.

    With `pace` (a `duty.Pacer`: the duty-cycle curve) each run is followed by its idle gap, no barrier lines the slots up: each
    starts at its own seeded offset with one uncounted warm-up cycle, padding keeps the run-and-gap pattern, and the pacer's guards
    cap the sandboxes up at once (memory) and the M runs; a run that waited for them records it. `make_config(option)` replaces
    the federation's DataConfig (the mock in tests).

    Above 16 (`mgate.active`) M skip-ahead holds this host's M sandboxes at its share of M slot users: a slot whose next cell is M, with the host
    at its share, runs its next non-M cell first (`icsa/scripted/mgate.py`); `gate_report`, if given, receives the level's measured M report.

    `part` (the paced form only; `multihost.PacedPart`): this host's share of a level that runs on two hosts. It names the global slots to run
    (`slot_ids`), what to add to each record (`extra`), a `start()` that returns when both hosts are released together, a `dead()` that stops new
    counted runs, and, when the level ends on both hosts together, the `stop` event that replaces the local end and a `counted_done()` to tell the
    launcher this host's counted runs are over. None: the whole level on this host, as `cmd_curve` runs it."""
    ids = list(range(level)) if part is None else list(part.slot_ids)
    if part is not None and pace is None:
        raise ValueError("a host's share of a level (part) is run through the paced form only")
    local = len(ids)
    up = local if pace is None else min(local, pace.max_live)       # the most sandboxes up at once
    need = plans.disk_needed_gib(block, up, target.s2_bytes) + DISK_MARGIN_GIB
    free = metrics.disk_free_gib(cfg.work_root)
    if free < need:
        raise SystemExit(f"block {block} level {level}: {free:.0f} GiB free on the work disk, needs {need:.0f}")
    avail = metrics.meminfo_available_gib()
    if avail < up * mem_per_run_gib + 8:
        raise SystemExit(f"block {block} level {level}: {avail:.0f} GiB MemAvailable is too low "
                         f"({mem_per_run_gib} GiB per run + 8); set --mem-per-run-gib from the baselines' measured peaks")
    slots = plans.mix_slots(seed, block, level, rep, instances) if pace is None else plans.duty_slots(seed, block, level, rep, instances)   # duty: <= DUTY_MAX_LEVEL
    gate = mgate.gate_for(block, level)           # None at or below 16: the registered curve's range runs as it always did
    barrier, lock = threading.Barrier(level), threading.Lock()
    all_done = threading.Event() if part is None or part.stop is None else part.stop
    remaining = [local]
    done: list[dict] = []
    config = (lambda o: F.data_config(target, o)) if make_config is None else make_config

    def one(p, **kw):
        if pace is None:
            return run_one(p, recs[p.instance_id], truth, lambda o=p.option: config(o), cfg, out, expected_sst=refs[p.instance_id], **kw)
        with pace.guard(p, wait=not kw["extra"].get("padding")) as waited:
            if waited is None:          # padding finds the host or the M slots full: it would only hold back a counted run
                return None
            kw["extra"] = {**kw["extra"], "duty_profile": pace.id, "pace_wait_s": waited}
            return run_one(p, recs[p.instance_id], truth, lambda o=p.option: config(o), cfg, out, expected_sst=refs[p.instance_id], **kw)

    def slot_fn(k: int) -> None:
        base = {"level": level, "rep": rep, "block": block, "slot": k}
        if part is not None:
            base.update(part.extra)
        rng = np.random.default_rng([seed, block, level, rep, k])
        n = 0
        if pace is not None:
            prng = pace.rng(k)
            p = plans.padding_plan(rng, block, level, rep, k, n, instances)
            n += 1
            all_done.wait(pace.offset_s(p, prng))
            gx, w = {}, None
            for _try in range(2):     # a warm-up whose drawn cell is an M with no M room takes a non-M cell instead, so every slot warms up (review of
                ok = True             # f42b726, finding 2: a skipped warm-up left its slot idle through the warm-up cycle). One with no live room stays skipped.
                if gate is not None:
                    ok, gx = gate.padding_start(p)       # the warm-up is padding: never an M cell beyond the share
                if ok:
                    try:
                        w = one(p, extra={**base, "padding": True, "warmup": True, **gx}, cancel=all_done)
                    finally:
                        if gate is not None:
                            gate.padding_end(p)
                    if gate is not None:
                        gate.note(w)
                if w is not None or p.option.value != "M" or all_done.is_set():
                    break
                if ok and not (_sem_has_room(pace.live) and not _sem_has_room(pace.mounts)):
                    break             # not refused for its M (the live slots were full, or M had room): as before, nothing redrawn (delta pass, finding 5)
                for _ in range(64):
                    p = plans.padding_plan(rng, block, level, rep, k, n, instances)
                    n += 1
                    if p.option.value != "M":
                        break
            all_done.wait(PACE_RETRY_S if w is None else pace.gap_s(p, prng, w))
        r = None
        for i, p, gx in mgate.cells(gate, k, slots[k]):
            if part is not None and part.dead():          # the launcher is gone: nothing new starts
                break
            r = one(p, barrier=barrier if i == 0 and pace is None else None, extra={**base, **gx} if gx else base)
            if gate is not None:
                gate.note(r)
            _say(r)
            with lock:
                done.append(r)
            if pace is not None and i < len(slots[k]) - 1:
                all_done.wait(pace.gap_s(p, prng, r))
        with lock:
            remaining[0] -= 1
            if not remaining[0]:
                if part is not None:
                    part.counted_done()
                if part is None or part.stop is None:        # a share of a split level ends when BOTH hosts' counted runs have: `part.stop`
                    all_done.set()
        if pace is not None and not all_done.is_set():
            all_done.wait(pace.gap_s(p, prng, r))        # the last cell that ran (the plan's last one, unless M skip-ahead reordered them)
        while not all_done.is_set():
            p = plans.padding_plan(rng, block, level, rep, k, n, instances)
            gx = {}
            if gate is not None:
                ok, gx = gate.padding_start(p)
                if not ok:                    # an M cell beyond this host's share: the next draw
                    n += 1
                    continue
            try:
                ran = one(p, extra={**base, "padding": True, **gx}, cancel=all_done)
            finally:
                if gate is not None:
                    gate.padding_end(p)
            if gate is not None:
                gate.note(ran)
            n += 1
            if pace is not None:
                all_done.wait(pace.gap_s(p, prng, ran) if ran is not None else PACE_RETRY_S)

    if part is not None:
        part.start()                                      # both hosts released together: every slot's offset runs from this moment
    with cf.ThreadPoolExecutor(max_workers=local) as pool:
        list(pool.map(slot_fn, ids))
    if gate is not None and gate_report is not None:
        gate_report.update(gate.report("local" if part is None else part.host))
    return done


def background_queue(seed: int, hard_stop: str | None = None) -> dict:
    """From go (science, #2, 18:17Z): one background queue, ONE sandbox at a time, counted inside the global cap (the campaign's
    cap less one while it runs), lowest priority, detached and resumable, on the campaign's final code with its sha recorded apart
    from the baselines'. Nothing in it runs during the baselines, the curve, the pilot or the calibration. WAN pauses at a run
    boundary when the baselines start and resumes here, third in the order."""
    return {"concurrency": 1, "counts_inside_global_cap": True, "global_cap_reduced_by_while_running": 1, "priority": "lowest",
            "detached": True, "resumable": True, "sha": "recorded in each stage's manifest, apart from the baselines' (ICSA_RUN_SHA)",
            "forbidden_during": ["baseline", "curve", "pilot", "calibration"],
            "stages": [
                {"n": 1, "name": "overhead pairs and M+ with M cold on site_f", "from": "overhead and mplus sections above"},
                {"n": 2, "name": "rest of WAN", "command": "python -m icsa.scripted wan-run --out WAN_DIR --space WAN_DIR/space.json "
                                                            "--pause-file WAN_DIR/PAUSE (resume: icsa/scripted resume_wan.py pattern)",
                 "pause": "touch WAN_DIR/PAUSE; the batch stops before its next run; rm it to resume"},
                {"n": 3, "name": "one pass of the 40 non-pilot instances through T in S1 (the oracle's post set)",
                 "command": "python -m icsa.harness.oracle_real --set post --cells T:S1 --concurrency 1 "
                            "(origin/feat/8-oracle-post, 2a9be19; reports a mismatch at once)",
                 "note": "the oracle driver takes its tokens through lane-slots' lease (slot users) once feat/8-slot-tokens lands; this config assumes nothing about its token source"},
                {"n": 4, "name": "repeat of the off-site rate check on site_c and site_e, at Day-0's hour",
                 "command": "bash tools/scripted/rate_check.sh OUT_DIR site_c site_e (exclusive, tears its own spaces down, stops at a failure)",
                 "window_utc": "02:00-03:00, the first night after go (Day-0 measured site_c at about 02:07Z); never during the curve, the baselines, the pilot or the calibration",
                 "why": "off-site rates varied more than 20x between measurements; the repeat shows whether the hour explains it"}],
            "after_hard_stop": "the other 120 S1 cells at the cap, after the hard stop (`hard_stop_utc` "
                               + (f"{hard_stop}" if hard_stop else "of the launch config, not given to this command") + "; not in this queue)"}


def cmd_plan_campaign(args) -> None:
    """The work that moved into the campaign (science, 17:49Z), written as config and run by nothing here: the overhead table's
    controls and the k = 5 traced-against-untraced pairs, interleaved per instance and cell, to be run at the campaign's
    concurrency in a low-priority slot; and the M+ window, M+ on site_f with M cold on site_f alternating inside it."""
    instances = plans.parse_instances(args.instances)
    rows = plans.baseline_plan(args.seed, instances, k=args.k, untraced_k=args.k, controls=True)
    mplus_instances = plans.parse_instances(args.mplus_instances)
    hard_stop = None
    if getattr(args, "campaign_config", None):         # the hard stop is one setting, in the launch config: this text follows it
        from icsa.campaign.config import CampaignConfig
        hard_stop = CampaignConfig.from_json(args.campaign_config).hard_stop_utc
    cfg = {"format": "icsa-scripted-campaign-v1", "seed": args.seed, "label": "campaign-low-priority",
           "note": "run at the campaign's concurrency, in a low-priority slot; interleaved pairs, never a block per arm",
           "overhead": {"instances": instances, "k": args.k,
                        "runs": [{"key": p.key(), "instance": p.instance_id, "option": p.option.value, "layout": p.layout.value,
                                  "arm": arm, "label": "campaign-concurrency"} for p, arm in rows]},
           "mplus": {"instances": mplus_instances, "space": "icsa2027_mplus_*, supported by site_g and site_f",
                     "window": "M+ on site_f and M cold on site_f alternate per instance inside one window; never contended M+ against quiet M cold",
                     "rows": {"primary": "M+ site_f vs M cold site_f, same window",
                              "secondary": "M+ site_f vs M cold site_g (step A's M runs, k = 3), labelled 'different conditions'",
                              "bound": "the WAN anchor's M runs"},
                     "go_gate": False, "commands": ["mplus-setup", "mplus-measure", "mplus-report", "teardown"]},
           "queue": background_queue(args.seed, hard_stop)}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, indent=1))
    print(f"{out}: {len(rows)} overhead runs, M+ on {len(mplus_instances)} instances")


def cmd_curve(args) -> None:
    """The curve of one block, as that block's mix (science's amendment). Each cell's wall time against its own single-run
    baseline; the 80% and no-errors rules, and no OOM kill. Block 1 searches from the top and stops at the first level that
    passes; block 2's result goes to the science agent before it is applied."""
    from . import curve as Cv
    levels = [int(x) for x in args.levels.split(",")]
    duty_mode = bool(getattr(args, "duty_profile", None))
    decision = getattr(args, "above_16_decision", None)
    if decision and not duty_mode:
        raise SystemExit("--above-16-decision is for the duty-cycle curve (--duty-profile) only")
    hard_max = plans.DUTY_MAX_LEVEL if decision else MAX_LEVEL       # above 16 only for the duty-cycle curve, with the decision named
    if max(levels) > hard_max:
        raise SystemExit(f"levels above {MAX_LEVEL} need an explicit decision from the lane's parent"
                         + (f"; the duty-cycle curve's limit is {plans.DUTY_MAX_LEVEL}" if decision else " (--above-16-decision, duty-cycle curve only)"))
    max_level = MAX_LEVEL if args.max_level is None else args.max_level
    if not 1 <= max_level <= hard_max:
        raise SystemExit(f"--max-level {max_level}: must be 1..{hard_max}")
    if args.stop == "first-pass":
        raise SystemExit("the curve searches upward and stops at the first failing level (--stop first-fail); first-pass was the old top-down search")
    try:
        levels = Cv.plan_levels(levels, max_level)
    except ValueError as e:
        raise SystemExit(str(e))
    if not levels:
        raise SystemExit(f"no level is at or below --max-level {max_level}")
    if args.dry_run:
        print(f"curve block {args.block}: upward plan {levels}, stop at the first failing level, cap = the last passing level "
              f"(--max-level {max_level}, hard maximum {MAX_LEVEL}); nothing is run", flush=True)
        return
    require_audit_log("curve")
    from .. import frsettings
    frsettings.require_restart_log("curve")      # a level cut by an op_worker restart is redone whole: that needs the restart log
    man, recs, truth = _common(args)
    if args.mem_per_run_gib is not None and not (0 < args.mem_per_run_gib < float("inf")):
        raise SystemExit(f"--mem-per-run-gib {args.mem_per_run_gib}: must be a finite number above zero")
    out = Path(args.out)
    instances = plans.parse_instances(args.instances)
    cells = [(o.value, la.value) for o, la in plans.BLOCK_CELLS[args.block]]
    traced = not args.untraced
    base = [r for r in _runs_of(args.baseline) if r["extra"].get("variant", "enforced") == "enforced"
            and bool(r["extra"].get("traced")) is traced]
    contended = sorted(r.get("run_key", "?") for r in base if (r["extra"].get("pool_workers") or 1) > 1 or "level" in r["extra"])
    if contended:
        raise SystemExit(f"--baseline holds runs under contention (a pool or a curve level), which would inflate the baseline: {contended[:5]}")
    own = Cv.single_run_walls(base)
    own_read = Cv.single_read_phases(base)
    missing = sorted(f"{o}/{la}/{i}" for o, la in cells for i in instances if (o, la, i) not in own)
    if missing:
        raise SystemExit(f"no clean single run ({'traced' if traced else 'untraced'}) for {missing[:6]}: each cell is compared with its own")
    per_run = args.mem_per_run_gib if args.mem_per_run_gib is not None else Cv.mem_per_run_gib(base)
    if per_run is None:
        raise SystemExit("a baseline run lacks a peak for one of its containers: pass --mem-per-run-gib, or use baselines that recorded peaks")
    avail = metrics.meminfo_available_gib()
    prof, max_live = None, None
    if duty_mode:       # the duty-cycle curve: a frozen profile, and no level dropped for memory: the pacer caps the sandboxes up at once instead
        from . import duty as DC
        try:
            prof = DC.load_profile(args.duty_profile, block=args.block, instances=instances, seed=args.seed, traced=traced)
        except (DC.DutyInputError, OSError, ValueError) as e:
            raise SystemExit(f"curve block {args.block}: {e}")
        if [int(x) for x in args.levels.split(",")] != prof["levels"]:
            raise SystemExit(f"curve block {args.block}: --levels {args.levels} differ from the levels frozen in the profile {prof['levels']}")
        max_live = Cv.levels_that_fit(range(1, max(levels) + 1), avail, per_run)
        max_live = max(max_live) if max_live else 0
        if max_live < 1:
            raise SystemExit(f"no sandbox fits: {avail:.0f} GiB MemAvailable, {per_run} GiB per run + {Cv.MEM_RESERVE_GIB} reserve")
    fit = levels if duty_mode else Cv.levels_that_fit(levels, avail, per_run)
    if not fit:
        raise SystemExit(f"no level in {levels} fits: {avail:.0f} GiB MemAvailable, {per_run} GiB per run + {Cv.MEM_RESERVE_GIB} reserve")
    dropped = [lv for lv in levels if lv not in fit]
    if dropped:
        print(f"levels {dropped} dropped: they do not fit in {avail:.0f} GiB MemAvailable at {per_run} GiB per run; "
              f"the top level is {max(fit)}", flush=True)
    levels = fit
    slot, tracer = F.traced_slot() if traced else (None, None)
    m = _manifest(out, f"curve_block{args.block}", resume=args.resume, seed=args.seed, block=args.block, levels=levels, levels_dropped_for_memory=dropped, mem_per_run_gib=per_run,
                  mem_available_gib=round(avail, 1), stop=args.stop, rep=args.rep,
                  baseline=args.baseline, instances=instances, traced=traced, tracer=tracer,
                  **({"duty_profile": str(args.duty_profile), "duty_profile_id": prof["profile_id"], "above_16_decision": decision,
                      "max_live": max_live, "max_m_runs": prof["max_m_runs"]} if duty_mode else {}))
    from . import duty as DC
    if (why := DC.baseline_image_problem(args.baseline, m.get("image_id"))):
        raise SystemExit(why)
    refs = load_or_build_reference(out, [recs[i] for i in instances])
    cfg = F.sandbox_config(F.MAIN, m["image"], instruments=slot)

    bid = Cv.baseline_id(own, own_read)
    if duty_mode:
        bid = DC.composed_id(bid, prof["profile_id"])
    try:
        decided = Cv.decided_levels(out / "curve_decisions.jsonl", args.block, args.rep, traced=traced, baseline=bid)
    except ValueError as e:
        raise SystemExit(f"curve block {args.block}: {e}; use a new --out")

    def passes(level: int) -> bool:
        if level in decided:
            print(f"level {level}: already decided ({'pass' if decided[level] else 'fail'}) in curve_decisions.jsonl, not re-run", flush=True)
            return decided[level]
        moved = Cv.set_aside_partial(out / "runs", out / "runs.superseded", args.block, level, args.rep,
                                  utc=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
        if moved:
            print(f"level {level}: {len(moved)} run directories of an interrupted attempt moved to runs.superseded/", flush=True)
        t0 = time.time()
        pace = DC.Pacer(prof, level=level, rep=args.rep, max_live=max_live) if duty_mode else None
        gate_report: dict = {}
        with (DC.HostWatch(pace) if duty_mode else contextlib.nullcontext()) as host:
            rs = run_mix(args.block, level, args.rep, recs, truth, refs, cfg, out / "runs", seed=args.seed, instances=instances,
                         mem_per_run_gib=per_run, pace=pace, gate_report=gate_report)
        cut = opwrestart.cut_by_restart(t0)
        if cut:        # redone whole: no decision line, so a resume runs this level again (its partial runs are set aside then)
            raise SystemExit(f"curve block {args.block}: level {level} {cut}; nothing is recorded for it; rerun with --resume to redo it whole")
        table = Cv.level_table(own, rs, single_read=own_read, duty=duty_mode)       # the duty-cycle form judges the medians (amendment 25(b)), the registered form the maxima
        row = Cv.cap(table, cells, [level], own, own_read)
        passed, kills = Cv.level_verdict(row, level, t0)
        if gate_report:          # above 16: more M up at once than the host's share (measured from the records) is not a pass
            passed = passed and gate_report["within_share"]
        rec = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "block": args.block, "level": level, "rep": args.rep, "passed": passed,
               "failing_cells": row["failing"].get(level, []), "runs": len(rs), "not_clean": sum(not Cv.clean(r) for r in rs),
               "earlyoom_kills": kills, "traced": traced, "baseline_id": bid, **({"m_gate": gate_report} if gate_report else {})}
        if duty_mode:       # the level's table and the runs the guards held back: a wait means the offered load was capped there
            waits = DC.paced_waits(rs)
            gaps = DC.level_gaps(rs, args.block, level, args.rep)       # every planned counted run recorded, and at least 3 reads in each cell (the report applies the same)
            rec.update(duty_profile_id=prof["profile_id"], measured_cycles=plans.duty_cycles(level, len(cells)),
                       warmup_cycles=1, reads_per_cell={f"{o}/{la}": sum(1 for r in rs if (r["option"], r["layout"]) == (o, la)) for o, la in cells}, table=table, paced_waits=waits, host=host.summary(), cycle_overruns=pace.overruns,
                       **DC.level_record(prof, Cv.counted(rs), own_read, {"local": level}, False, (gate_report or {}).get("share")))      # its ladder, where it ran, each mount's reads
            passed = DC.apply_verdict(rec, passed, waits, DC.m_idle_waits(rs), gaps)      # guard waits, M's idle waits and a gap in the plan: not a pass; failed_on says which
        Cv.append_decision(out / "curve_decisions.jsonl", rec)
        print(json.dumps(rec), flush=True)
        return passed

    sequence = duty_mode and (prof.get("climb") is not None or prof.get("floor_level") is not None)
    if sequence:        # science, #34, 3 Nov 00:33Z: the climb, and the step-downs after a failure (`curve.sequence_state`); the registered curve never comes here
        if args.stop != "first-fail":
            raise SystemExit("a profile with a climb and step-downs ends at the first failing climb level (--stop first-fail)")
        climb = [c for c in DC.ladder_of(prof)["climb"] if c in levels or c == prof.get("floor_level")]
        if not climb:
            raise SystemExit(f"curve block {args.block}: no level of the climb {prof.get('climb')} is at or below --max-level {max_level}")
        results, state = Cv.run_sequence(levels, climb, prof.get("floor_level"), passes)
        result = state["cap"]
    else:
        results = Cv.search(levels, args.stop, passes)
        result = Cv.cap_of(results)
    tail = {"block": args.block, "cap": result, "tried": [lv for lv, _ in results], "max_level": max_level,
            "cap_is_max_level": result == max_level,
            "reason": ("every level down the ladder failed: no cap" if sequence else "the first level failed: no cap") if result is None else "last passing level"}
    if duty_mode:       # what the lines say of the cap, beside the driver's own: whether M's bound set it, and that the two readings agree
        try:
            rd = DC.cap_from_decisions(out / "curve_decisions.jsonl", args.block, args.rep, traced=traced, profile=prof)
            tail.update(cap_bound_by=rd["cap_bound_by"], m_bound=rd["cap_bound_by"] == "m_bound", capped_by_level=rd["capped_by_level"], cap_read_from_lines=rd["cap"],
                        cap_read_agrees=rd["cap"] == result, cap_final=rd["final"])
        except DC.DutyInputError as e:
            tail["cap_read_error"] = str(e)
    (out / f"curve_cap_block{args.block}.json").write_text(json.dumps(tail, indent=1))
    print(json.dumps(tail), flush=True)
    if result is None:
        raise SystemExit(f"curve block {args.block}: level {results[0][0]} failed the rule: NO CAP (nothing is applied)")


def cmd_duty_profile(args) -> None:
    """The duty-cycle curve's schedule, frozen before it starts (`duty.py`), from the pilot's agent runs and the registered curve's
    single-run baselines. Offline: no sandbox, no federation. A profile already written is never overwritten."""
    from . import curve as Cv
    from . import duty as DC
    if (why := DC.baseline_image_problem(args.baseline)):       # no sandbox starts here: only a mix of images refuses
        raise SystemExit(why)
    instances = plans.parse_instances(args.instances)
    cells = [(o.value, la.value) for o, la in plans.BLOCK_CELLS[args.block]]
    traced = not args.untraced
    base = [r for r in _runs_of(args.baseline) if r["extra"].get("variant", "enforced") == "enforced"
            and bool(r["extra"].get("traced")) is traced]
    contended = sorted(r.get("run_key", "?") for r in base if (r["extra"].get("pool_workers") or 1) > 1 or "level" in r["extra"])
    if contended:
        raise SystemExit(f"--baseline holds runs under contention (a pool or a curve level): {contended[:5]}")
    own_total, own_read = DC.single_totals(base), Cv.single_read_phases(base)
    out = Path(args.out)
    try:
        DC.refuse_inside_code_tree(out, "--out")        # the frozen profile is set after the code's hash is taken: never inside what that hash covers
    except DC.DutyInputError as e:
        raise SystemExit(f"duty-profile: {e}")
    path = out / f"duty_profile_block{args.block}.json"
    if args.check_against and args.rerun_against:
        raise SystemExit("duty-profile: give one of --check-against and --rerun-against")
    against = args.check_against or args.rerun_against
    if path.exists() and not against:
        raise SystemExit(f"{path} exists: a frozen profile is never rewritten; use a new --out")
    given = args.given_shares
    if given and (args.pilot or against):
        raise SystemExit("duty-profile: --given-shares builds the profile from given shares: not with --pilot, --check-against or --rerun-against")
    if not given and not args.pilot:
        raise SystemExit("duty-profile: --pilot is required (unless --given-shares)")
    if not against and not args.levels:
        raise SystemExit("duty-profile: --levels is required")
    try:
        if given:
            shares = DC.given_shares(given, cells)
            rows, left = [], {}
        else:
            rows, left = DC.pilot_runs(args.pilot)
            rates = DC.scripted_rates(base)
            share_from = dict(x.split("=", 1) for x in args.share_from)
            if against:         # amendment 25(d) names T-unpaginated's rule (it has neither kind of run), so the check and the rerun apply it unasked
                for cell, src in DC.REGISTERED_SHARE_FROM.items():
                    if cell in [f"{o}/{la}" for o, la in cells] and cell not in share_from:
                        share_from[cell] = src
            shares = DC.cell_shares(rows, cells, rates, share_from)
        if against:
            return _duty_check(args, DC, shares, rows, left, cells, instances, traced, own_total, own_read)
        prof = DC.build_profile(shares, own_total, own_read, block=args.block, cells=cells, instances=instances, seed=args.seed,
                                traced=traced, levels=[int(x) for x in args.levels.split(",")], max_m_runs=args.max_m_runs,
                                shares_kind="given" if given else None,
                                climb=[int(x) for x in args.climb.split(",")] if args.climb else None, floor_level=args.floor_level)
    except DC.DutyInputError as e:
        raise SystemExit(f"duty-profile: {e}")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"duty_shares_block{args.block}.json").write_text(json.dumps(
        {"profile_id": prof["profile_id"], "pilot": [str(d) for d in args.pilot or []], "baseline": [str(d) for d in args.baseline],
         "left_out": left, "runs": rows, **({"given_shares": str(given), "given_shares_sha256": DC.file_sha256(given)} if given else {})}, indent=1, default=str))
    path.write_text(json.dumps(prof, indent=1))
    print(json.dumps({"profile": str(path), "profile_id": prof["profile_id"], "levels": prof["levels"],
                      **({"shares_kind": "given"} if given else {}),
                      "cells": {c: ({"share": round(v["share"], 4), "source": v["source"]} if given else
                                    {"share": round(v["share"], 4), "runs": v["runs"], "median": round(v["median"], 4), "p90": round(v["p90"], 4)})
                                for c, v in prof["shares"].items()},
                      "gaps_s": {k: v["gap_s"] for k, v in prof["gaps"].items()},
                      "loaded_above_share": sorted(k for k, v in prof["gaps"].items() if v["loaded_above_share"])}, indent=1))


def _duty_check(args, DC, measured, rows, left, cells, instances, traced, own_total, own_read) -> None:
    """`duty-profile --check-against PROFILE`: the measured p90 shares (as the measured mode forms them) against the given profile's. Writes and prints
    the comparison; exits 3 if any cell's measured share exceeds its given one. Modifies no profile.

    `--rerun-against PROFILE` (amendment 25(d)): the same check, and if a cell is over, a NEW frozen profile, `duty_profile_block<N>_rerun.json`, with each
    cell's share at the larger of its value in the given profile and its measured p90 (no share falls), its provenance naming both figures and the given
    profile's hash, and the given profile's levels unless `--levels` names others. Exit 3 either way when a rerun is needed; when no cell is over it writes
    no profile, says so, and exits 0. The given profile is never touched, and an existing rerun profile is never overwritten."""
    against = args.check_against or args.rerun_against
    prof = DC.load_profile(against, block=args.block, instances=instances, seed=args.seed, traced=traced)
    if prof["cells"] != [f"{o}/{la}" for o, la in cells]:
        raise DC.DutyInputError(f"{against}: made for other cells")
    res = DC.check_against(prof, measured)
    res.update(profile=str(against), pilot=[str(d) for d in args.pilot], left_out=left)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.rerun_against:
        res["rerun_needed"] = bool(res["exceeds"])
        if not res["exceeds"]:
            res["message"] = "no cell's measured p90 share exceeds its given share (amendment 28): no rerun is needed, and no profile was written"
        else:
            new_path = out / f"duty_profile_block{args.block}_rerun.json"
            if new_path.exists():
                raise SystemExit(f"{new_path} exists: a frozen profile is never rewritten; use a new --out")
            rerun_seq: dict = {}
            if prof.get("climb") is not None or prof.get("floor_level") is not None:
                # science, #34, 3 Nov 00:33Z: "25(d) reruns only the cap's level, stepping down until one passes": the rerun's climb is the first curve's cap
                # alone, over the same frozen levels and floor, so it steps down from there (`curve.sequence_state`) and never above
                if not args.first_curve:
                    raise SystemExit("duty-profile --rerun-against: the given profile has a climb and step-downs, so the rerun starts at the first curve's cap: give --first-curve DIR")
                first = DC.cap_from_decisions(Path(args.first_curve) / "curve_decisions.jsonl", args.block, args.rep, traced=traced, profile=prof)
                if not first["final"] or first["cap"] is None:
                    raise SystemExit(f"duty-profile --rerun-against: the first curve has {'no cap' if first['final'] else 'not finished (more is due: ' + str(first['next_level_due']) + ')'}: "
                                     f"there is no cap level to rerun")
                rerun_seq = {"climb": [first["cap"]], "floor_level": prof.get("floor_level")}
            new = DC.build_profile(DC.rerun_shares(prof, measured), own_total, own_read, block=args.block, cells=cells, instances=instances, seed=args.seed,
                                   traced=traced, levels=[int(x) for x in args.levels.split(",")] if args.levels else prof["levels"], jitter=prof["jitter"],
                                   max_m_runs=prof["max_m_runs"], shares_kind="rerun", **rerun_seq,
                                   provenance={"amendment": "25(d)", "rerun_of_profile_id": prof["profile_id"], "cells_over": res["exceeds"],
                                               "rule": "each cell's share is the larger of its given share (25(c) as corrected by amendment 28) and its measured p90; no cell's share falls",
                                               **({"first_cap": rerun_seq["climb"][0], "rerun_levels": "the first curve's cap, then each frozen level below it until one passes"} if rerun_seq else {})})
            (out / f"duty_shares_block{args.block}_rerun.json").write_text(json.dumps(
                {"profile_id": new["profile_id"], "rerun_of_profile_id": prof["profile_id"], "pilot": [str(d) for d in args.pilot],
                 "baseline": [str(d) for d in args.baseline], "left_out": left, "runs": rows}, indent=1, default=str))
            new_path.write_text(json.dumps(new, indent=1))
            res.update(rerun_profile=str(new_path), rerun_profile_id=new["profile_id"],
                       message=f"a rerun is needed: cells over {res['exceeds']}; the rerun profile is written and the given one is untouched",
                       rerun_shares={c: round(v["share"], 4) for c, v in new["shares"].items()})
    (out / f"duty_check_block{args.block}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    if res["exceeds"]:
        raise SystemExit(3)


def _runs_of(dirs) -> list[dict]:
    """The analysed runs. An attempt that host infrastructure ended is on record and not analysed: protocol/parameters.md, "the first that ends without an
    infrastructure failure"; a run all of whose attempts ended so has no outcome."""
    from .summarize import load_runs
    return [r for d in (dirs or []) for r in load_runs(d) if not r.get("infrastructure") and (r.get("extra") or {}).get("probe_files") is None]     # a live probe's prefix read is no run of the study


def write_reports(out: Path, *, single=(), curve=(), pipeline=(), overhead=(), tracer_compare=(), traced: bool = True) -> None:
    """Everything the other lanes read, from finished batches: no sandbox, no federation. The cap rests on one kind of run:
    the timing files take the enforced runs in one tracing state, and their absence reads as MISSING."""
    from . import control as K
    from . import curve as Cv
    from . import emit as E
    out.mkdir(parents=True, exist_ok=True)
    kind = lambda r: r["extra"].get("variant", "enforced") == "enforced" and bool(r["extra"].get("traced")) is traced  # noqa: E731
    sing, cur = [r for r in _runs_of(single) if kind(r)], [r for r in _runs_of(curve) if kind(r)]
    if sing or cur:
        try:
            hr = Cv.find_host_ratios(curve)     # the curve was judged with host references: the report recomputes its table from the runs, and judges them the same way
        except ValueError as e:
            raise SystemExit(f"report: {e}")
        timing = E.scripted_timing(sing, cur, audit_log=E.audit_state(*single, *curve), level_vetoes=Cv.earlyoom_vetoes(curve, traced=traced),
                                   duty_decisions=Cv.duty_decisions(curve, traced=traced), host_ratios=hr,
                                   duty_ladders=Cv.duty_ladders(curve, traced=traced))     # a duty level cmd_curve failed (or never finished) is not a cap here
        (out / "scripted_timing.json").write_text(json.dumps(timing, indent=1))
        print("scripted_timing: blocks", {b: (e["cap"], e["cap_dossier_rule"]) for b, e in timing["blocks"].items()},
              "audit log", timing["audit_log"])
    pipe = [r for r in _runs_of(pipeline) if kind(r)]
    if pipe:
        d = E.scripted_pipeline(pipe)
        (out / "scripted_pipeline.json").write_text(json.dumps(d, indent=1))
        print("scripted_pipeline:", {f"{c['option']}/{c['layout']}": (c["completed"], c["correct"]) for c in d["cells"]})
    if overhead:
        d = K.analysis_overhead(_runs_of(overhead), traced=traced)
        (out / "enforcement_overhead.json").write_text(json.dumps(d, indent=1))
        print("enforcement overhead rows", len(d["rows"]), "below k", len(d["below_min_k"]))
    if tracer_compare:
        d = K.traced_overhead(_runs_of(tracer_compare))
        (out / "traced_overhead.json").write_text(json.dumps(d, indent=1))
        print("traced overhead rows", len(d["rows"]), "below k", len(d["below_min_k"]))


def cmd_report(args) -> None:
    write_reports(Path(args.out), single=args.single, curve=args.curve, pipeline=args.pipeline or args.single,
                  overhead=args.overhead, tracer_compare=args.tracer_compare, traced=not args.untraced)


def _admin(out: Path):
    from . import provision as V
    od = F.od_module(changes=out / "changes.jsonl")
    import importlib
    return V.AdminOD(od), importlib.import_module("odsafe")


def cmd_mplus_setup(args) -> None:
    from . import mplus as M
    from .. import paths
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    o, safe = _admin(out)
    sp = M.setup_space(o, safe, out, Path(args.manifests), paths.DATA_ROOT / "s1z", paths.DATA_ROOT / "s2z" / "sst_s2.nc")
    print(sp)


def cmd_mplus_measure(args) -> None:
    from . import mplus as M
    from .. import paths
    from .summarize import load_runs
    man, recs, truth = _common(args)
    out = Path(args.out)
    instances = plans.parse_instances(args.instances)
    only_layout = plans.parse_instances(args.layout_instances) if args.layout_instances else None
    if args.probe and args.plan:
        raise SystemExit("--probe and --plan are two steps of the quiet window (science, #34, 01:03Z): the probe first, then the plan it writes")
    m = _manifest(out, "mplus", resume=args.resume, seed=args.seed, space=args.space, instances=instances, layout_instances=only_layout,
                  probe=args.probe, plan=args.plan)
    o, _ = _admin(out)
    sp = M.MplusSpace.load(args.space)
    camp = M.Campaign(o, sp, out / "mplus_log.jsonl")
    M.transfer_health(camp)
    refs = load_or_build_reference(out, [recs[i] for i in plans.PILOT])
    cfg = F.sandbox_config(sp.target("site_f"), m["image"])
    s2_path = paths.DATA_ROOT / "s2z" / "sst_s2.nc"
    if not (args.probe or args.plan):
        M.measure(camp, recs, truth, refs, cfg, out / "runs", s2_path, instances=instances, layout_instances=only_layout)
        return
    layouts = {"S1": Layout.S1, "S2": Layout.S2}
    if args.probe:        # real step times first, from the gap before main: one M cold and one M+ per layout, the seeded order's first instance, no layout scope
        for name, la in layouts.items():
            M.measure(camp, recs, truth, refs, cfg, out / "runs", s2_path, instances=M.select_instances(instances, args.seed, la, 1),
                      layouts=(la,), layout_instances=(), done=M.done_steps(load_runs(out)))
        runs = load_runs(out)
        log = [json.loads(x) for x in (out / "mplus_log.jsonl").read_text().splitlines()]
        layout_bytes = {name: sum(ln for rs in camp.wanted(la, None, None).values() for _, ln in rs) for name, la in layouts.items()}
        plan = M.plan_window(instances, args.seed, M.step_times(log, runs), layout_bytes, M.done_steps(runs), limit_s=args.limit_h * 3600)
        (out / "window_plan.json").write_text(json.dumps(plan, indent=1))
        print(json.dumps({k: plan[k] for k in ("rule", "instances", "projected_all_s", "projected_chosen_s")}, indent=1))
        return
    plan = json.loads(Path(args.plan).read_text())       # the window: the plan's instances per layout, what the probe made not repeated
    for name, la in layouts.items():
        M.measure(camp, recs, truth, refs, cfg, out / "runs", s2_path, instances=plan["instances"][name], layouts=(la,),
                  done=M.done_steps(load_runs(out)))


def cmd_mplus_report(args) -> None:
    from . import mplus as M
    M.report(Path(args.out), seed=args.seed, wan_dir=Path(args.wan_dir) if args.wan_dir else None,
             site_g_dir=Path(args.site_g_dir) if args.site_g_dir else None)


def cmd_wan_setup(args) -> None:
    from . import wan as W
    from .. import paths
    man, recs, _ = _common(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    o, safe = _admin(out)
    print(W.setup_space(o, safe, out, Path(args.manifests), paths.DATA_ROOT / "s1z", paths.DATA_ROOT / "s2z" / "sst_s2.nc", recs))


def cmd_wan_run(args) -> None:
    from . import wan as W
    man, recs, truth = _common(args)
    out = Path(args.out)
    m = _manifest(out, "wan", seed=args.seed, space=args.space)
    sp = W.WanSpace(**json.loads(Path(args.space).read_text()))
    refs = load_or_build_reference(out, [recs[i] for i in plans.WAN])
    cfg = F.sandbox_config(sp.target(), m["image"])
    o, _ = _admin(out)
    W.run(sp, W.wan_plan(args.seed), recs, truth, refs, cfg, out / "runs", o=o, say=_say,
          pause_file=Path(args.pause_file) if args.pause_file else None)


def cmd_teardown(args) -> None:
    from . import provision as V
    out = Path(args.out)
    o, safe = _admin(out)
    sid = json.loads(Path(args.space).read_text())["space_id"]
    res = V.teardown(o, safe, sid, args.providers.split(","))
    print(json.dumps(res))
    if not res["ok"]:
        raise SystemExit(3)         # a refused or failed teardown (files left, a disk that could not be checked, a non-2xx) is never an exit 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m icsa.scripted")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("reference", "smoke", "pilot", "perf", "baseline", "curve", "report", "plan-campaign", "mplus-setup", "mplus-measure", "mplus-report", "wan-setup",
                 "wan-run", "teardown", "duty-profile", "curve-multi", "curve-part", "live-probe"):
        s = sub.add_parser(name)
        s.add_argument("--out", required=True)
        s.add_argument("--seed", type=int, default=20271201)
        if name in ("curve-multi", "curve-part"):
            multihost.add_arguments(name, s)
        if name == "live-probe":
            liveprobe.add_arguments(s)
        if name == "smoke":
            s.add_argument("--instance", default="I35")
            s.add_argument("--only", default="", help="option:layout paths, comma-separated (e.g. D:S2)")
        if name == "pilot":
            s.add_argument("--instances", default=",".join(plans.PILOT))
            s.add_argument("--reps", type=int, default=1)
            s.add_argument("--workers", type=int, default=1)
            s.add_argument("--resume", action="store_true")
            s.add_argument("--untraced", action="store_true", help="plain runs, for the comparison only")
        if name == "baseline":
            s.add_argument("--instances", default=",".join(plans.BASELINE_INSTANCES))
            s.add_argument("--k", type=int, default=3, help="enforced runs per cell, cycling the instances: 3 = one per instance, 24 in all")
            s.add_argument("--untraced-k", type=int, default=1)
            s.add_argument("--controls", action="store_true", help="the overhead controls too: they moved into the campaign (17:49Z)")
            s.add_argument("--probe-files", default=None, metavar="T=N,M=N", help="run ONLY the live probe's prefix cell (the first N files of T's and of M's S1 cell, --k runs each), into this --out alone; default: the ordinary baseline")
            s.add_argument("--max-failures", type=int, default=2)
            s.add_argument("--resume", action="store_true")
            s.add_argument("--preflight", action="store_true", help="check the environment, image, instruments, slot pool and plan; run nothing")
        if name == "curve":
            s.add_argument("--block", type=int, required=True, choices=sorted(plans.BLOCK_CELLS))
            s.add_argument("--instances", default=",".join(plans.BASELINE_INSTANCES))
            s.add_argument("--untraced", action="store_true", help="plain runs, for the comparison only")
            s.add_argument("--baseline", nargs="+", required=True, help="the results directories holding the single runs")
            s.add_argument("--levels", default=",".join(map(str, curve.DEFAULT_LEVELS)), help="strictly ascending: the search goes upward")
            s.add_argument("--stop", choices=("first-pass", "first-fail", "none"), default="first-fail")
            s.add_argument("--max-level", type=int, default=None, help=f"never run a level above this (the site_g capacity benchmark's safe level); default and limit {MAX_LEVEL}")
            s.add_argument("--dry-run", action="store_true", help="print the upward plan and exit")
            s.add_argument("--resume", action="store_true", help="after an interruption: levels already in curve_decisions.jsonl are not run again")
            s.add_argument("--rep", type=int, default=1)
            s.add_argument("--mem-per-run-gib", type=float, default=None,
                           help="default: the baselines' largest measured run (agent + gate + sidecar peaks) x 1.15; a level that does not fit is dropped")
            s.add_argument("--duty-profile", default=None, help="the duty-cycle curve: a profile frozen by duty-profile (runs with idle gaps; use a new --out)")
            s.add_argument("--above-16-decision", default=None, help="duty-cycle curve only: the decision (URL) that allows levels above 16")
        if name == "duty-profile":
            s.add_argument("--block", type=int, required=True, choices=sorted(plans.BLOCK_CELLS))
            s.add_argument("--instances", default=",".join(plans.BASELINE_INSTANCES), help="the curve's instances (the gaps are per instance)")
            s.add_argument("--baseline", nargs="+", required=True, help="the registered curve's single-run results directories")
            s.add_argument("--pilot", nargs="+", default=None,
                           help="the campaign directories holding the pilot's and the calibration's runs (every run_record.json under them is read); required unless --given-shares")
            s.add_argument("--given-shares", default=None, metavar="FILE",
                           help='shares before the pilot, taken as given with their provenance and not recomputed (amendment 25(c) as corrected by amendment 28: made by '
                                'python -m icsa.scripted.duty shares): JSON {"T/S1": {"share": 0.21, "source": "..."}, ...}, one per cell, each in (0, 1]; the profile records shares_kind "given"')
            s.add_argument("--check-against", default=None, metavar="PROFILE",
                           help="the check before main: compare the measured p90 shares (--pilot) with this given profile's; writes duty_check_block<N>.json, exits 3 if any measured share exceeds its given one; writes no profile")
            s.add_argument("--rerun-against", default=None, metavar="PROFILE",
                           help="amendment 25(d): --check-against, and if a cell is over, also write duty_profile_block<N>_rerun.json (each cell's share at the larger of its given value and its measured p90, "
                                "provenance naming both and the given profile's hash; levels from the given profile unless --levels); exit 3 if a rerun is needed, 0 with no profile written if not")
            s.add_argument("--share-from", action="append", default=[], metavar="CELL=SOURCE",
                           help="a cell with no runs takes the largest share of the cells named: T-unpaginated/S1=T/S1,D/S1,M/S1, science's choice (all recorded in the profile; without it, such a cell fails)")
            s.add_argument("--untraced", action="store_true", help="for an untraced curve: untraced baselines")
            s.add_argument("--max-m-runs", type=int, default=16, help="M runs up at once; more wait (science's ruling: M x 16 shown on site_g, 2 Nov)")
            s.add_argument("--levels", default=None, help="required unless --check-against or --rerun-against: the levels the duty-cycle curve will try, strictly ascending, frozen in the profile "
                                                          "(science's ladder: 4,8,12,16,24,32,42)")
            s.add_argument("--climb", default=None, help="the levels that run in order, a subset of --levels (science, #34, 3 Nov: 8,16,24,32,42); a failure tests the frozen level below it. "
                                                         "Omitted: every level in order, stopping at the first failure")
            s.add_argument("--floor-level", type=int, default=None, help="the one level below the first of --levels, run only if that fails (science: 2); frozen in the profile")
            s.add_argument("--first-curve", default=None, metavar="DIR",
                           help="--rerun-against a profile with a climb: the first curve's --out; the rerun starts at its cap and steps down (25(d))")
            s.add_argument("--rep", type=int, default=1, help="the first curve's rep, for --first-curve")
        if name == "wan-run":
            s.add_argument("--pause-file", default="", help="stop at the next run boundary while this file exists")
        if name == "plan-campaign":
            s.add_argument("--instances", default=",".join(plans.BASELINE_INSTANCES))
            s.add_argument("--k", type=int, default=5)
            s.add_argument("--mplus-instances", default="I35,I37,I48,I01,I06")
            s.add_argument("--campaign-config", default=None, help="the campaign's launch config: its hard_stop_utc is named in the queue's text")
        if name == "report":
            for flag in ("single", "curve", "pipeline", "overhead", "tracer-compare"):
                s.add_argument(f"--{flag}", nargs="*", default=[], help="results directories")
            s.add_argument("--untraced", action="store_true")
        if name in ("mplus-setup", "wan-setup"):
            s.add_argument("--manifests", required=True, help="the directory of #3's s1_sha256.txt and s2_sha256.txt")
        if name in ("mplus-measure", "wan-run", "teardown"):
            s.add_argument("--space", required=True, help="space.json written by the setup step")
        if name == "mplus-measure":
            from .mplus import WINDOW_LIMIT_S
            s.add_argument("--instances", default="I35,I37,I48,I01,I06", help="each gets one M cold on site_f and one M+ on site_f, interleaved")
            s.add_argument("--layout-instances", default="", help="instances run on the whole layout (default: the same)")
            s.add_argument("--probe", action="store_true",
                           help="real step times first (science, #34, 01:03Z): one M cold on site_f and one M+ per layout, the seeded order's first instance, no layout scope; "
                                "then writes OUT/window_plan.json (the size rule on the projected window) and prints it")
            s.add_argument("--plan", default=None, help="the window: OUT/window_plan.json from --probe; runs its instances per layout, with --resume in the same OUT, "
                                                        "and does not repeat what the probe made")
            s.add_argument("--limit-h", type=float, default=WINDOW_LIMIT_S / 3600, help="--probe: all instances if the projected window is at most this many hours, else the first 3 per layout")
            s.add_argument("--resume", action="store_true", help="the window after the probe, in the probe's OUT")
        if name == "mplus-report":
            s.add_argument("--wan-dir", default="", help="the WAN anchor's results: its M runs give the scripted bound")
            s.add_argument("--site_g-dir", default="", help="a batch whose M runs on site_g count as cold-site_g (the pilot pass)")
        if name == "teardown":
            s.add_argument("--providers", required=True)
    return ap


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()

    exit_on_sigterm()          # SystemExit(143): finally-blocks stop the sandboxes, and a blocked exec is released
    if args.cmd in ("baseline", "curve", "pilot", "perf", "smoke", "mplus-measure", "wan-run", "live-probe") and not getattr(args, "preflight", False):
        EO.require_driver_exempt()
    try:
        {"reference": cmd_reference, "smoke": cmd_smoke, "pilot": cmd_pilot, "perf": cmd_perf, "baseline": cmd_baseline,
         "curve": cmd_curve, "report": cmd_report, "plan-campaign": cmd_plan_campaign,
         "mplus-setup": cmd_mplus_setup, "mplus-measure": cmd_mplus_measure, "mplus-report": cmd_mplus_report,
         "wan-setup": cmd_wan_setup, "wan-run": cmd_wan_run, "teardown": cmd_teardown, "duty-profile": cmd_duty_profile,
         "curve-multi": lambda a: multihost.cmd_curve_multi(a, sys.modules[__name__]),     # curve-part does its own driver check and cleanup, only on its real path
         "curve-part": lambda a: multihost.cmd_curve_part(a, sys.modules[__name__]),
         "live-probe": lambda a: liveprobe.cmd_live_probe(a, sys.modules[__name__])}[args.cmd](args)
    finally:
        wait_for_stop(600)     # the leftovers are what the SIGTERM's own stops did not remove
        left = cleanup_own_containers() if args.cmd in ("smoke", "pilot", "perf", "baseline", "curve", "mplus-measure",
                                                        "wan-run") and not getattr(args, "preflight", False) else []
        if left:
            print(f"removed leftover containers: {left}", file=sys.stderr)


if __name__ == "__main__":
    main()
