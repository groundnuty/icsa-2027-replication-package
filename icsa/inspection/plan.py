"""The main block's coding plan (amendment 26; science, #76, 2-3 Nov, on the operator's word).

    python -m icsa.inspection.plan build --campaign-root DIR --seed S --out plan.json      # before the block's results exist
    python -m icsa.inspection.run    --plan plan.json --sealed SEALED --work WORK [--input-root /mnt/volume2/icsa-2027/coding-mirror] [--passes N ...]
    python -m icsa.inspection.report --pair-plan plan.json --sealed SEALED --unseal --population POP --work WORK --out OUT   # after the block
    python -m icsa.inspection.coverage ... --sealed SEALED --unseal ...                                                       # after the block

The rule. No Codex API: the Codex coder is the subscription CLI only.
1. Every site_j SUBJECT run first, coded by Sol + Opus. A subject model never judges its own runs, so a Sonnet run may never
   get Opus + Sonnet.
2. Then the rest, in one seeded order over the PLANNED matrix, balanced per option x layout x model. Sol + Opus code until the ChatGPT
   plan's window reaches 95% used (the quota gate, `QuotaGate`). Then: no new Sol dispatch; the closing is posted once; the gate waits about
   an hour (`--gate-wait-s`) for a reset, probing the quota through the real isolated launcher every 10 min (`--probe-s`); a reading below 95
   reopens Sol where the order stands. No reset: the next dispatches get Opus + Sonnet, a Sonnet subject run waits for Sol instead, and a
   probe every 30 min (`--probe-slow-s`) still looks for a reset, which resumes Sol for the runs not yet dispatched. A run already dispatched
   keeps its pair always. A blind reading or a Codex limit error closes the gate the same way.
3. The pair is recorded per run (`answers/<packet>/pair.json`), before any call, and never changed afterwards. Every table marks the pair.

When the coders run: DURING the main block, on finished runs as they finish, on a host that does not run the campaign (amendment 29(d), replacing
26(j)'s "when the main block ends"), in PASSES (science, #34, 3 Nov 00:18Z). Coding STOPS at `stop_at`, fixed in the plan file before any main
run (amendment 29(c): 6 Nov 06:00Z by default, `plan build --stop-at`; it is not read from a run and cannot move after one has started, because a
second build with another time refuses): no new dispatch after it, calls in flight may finish, anything uncoded stays as the instrument left it
(`unknown` where it was), and the pass counts it at the end. The order is fixed and never changes. A pass walks it from
the first position: a run that has already been dispatched is finished off from its record; a run that is not finished is skipped IN PLACE and
picked up on a later pass; a finished run is dispatched. The ONLY thing a pass reads about a run is finished-or-not, from the run's status and
its directory (`StoreRunSource`: the store's status, the attempt's termination `report`, and the run directory's own pull marker `<dir>.pulled.json`,
whose file count and bytes must match the directory: no marker means not finished, and a partial copy never counts as finished). Never its label, its report or any record of the outcome. A run that ended without finishing (a cap,
an error) is terminal: it gets no packet in the main block and is never picked up. A run whose directory has not arrived, or arrived without
its marker, is not finished yet and is looked at again on the next pass. The runner codes EVERY finished run in the order, whatever it is
labelled, and builds each packet itself (`packet.build`, no label anywhere in its metadata). Sets R and C are assigned only at the report, after
the block, from the sealed answers (`build_report_key`, `queue.assign_sets`); a coded run that falls in neither is coded and unused, counted
there and nowhere before.

Sealed. Nothing per packet is visible during the main block. Everything per packet (packets, metadata, answers, pair records, the waiting
list, the per-packet log) is under the `--sealed` directory, created mode 700 with a marker, and a file that cannot be sealed refuses the run.
What is written outside it (standard output, `plan-events.jsonl`, `gate.json`, the operator queue file) carries totals only: packets coded,
tokens, quota readings. No label, verdict, option, layout or model, and no per-packet line. `report.py` and `coverage.py` refuse a sealed
directory unless given `--unseal`.
Who reads it. Under amendment 29(c) the SCIENCE agent alone runs snapshots and reads their tables; no lane that runs the campaign computes a
contrast, and `--unseal` is the science agent's, not this lane's. That rests on instruction, not on a lock: every session shares a host and a
user, so mode 700 guards against accidents only and is not access control. The Sonnet gate of 18(e) no longer reads the coders' spend
(29(d)); nothing here feeds it.

What decides the pair, and what never does. A run's second coder depends ONLY on its place in the seeded order, its subject model and
the plan's quota reading. Never on a label, a verdict, an answer, a packet's size or how long a run took. So:
- `build_order` reads the seven plan columns (`PLAN_FIELDS`) of the PLANNED rows and nothing else (a caller's extra fields are dropped at the
  door), the campaign store's `runs` table without its `status`. The order is fixed before the main block's results exist, seeded, and written
  once to a plan file with its seed and hash: a second build must match it byte for byte or refuse.
- The runner (`run.run_plan`) decides a run's pair when it is dispatched, from the gate alone; the gate reads only the rate-limit field Codex
  writes into each answer's session file, a probe's, and a Codex limit error.
- The only later change of a pair is the one the rule names: a Codex limit error and no valid Sol answer, for a run whose subject is not
  Sonnet, moves it to Opus + Sonnet (`reassign_if_quota_failed`; the reason is recorded). It reads the limit error, never an answer.

Balance. The strata (option x layout x model) are not equal (150 runs per main cell, 50 per pagination cell), so "balanced" is the quota
condition: in every prefix of a section, a stratum's count c satisfies |c - n * size / total| < 1 (for equal strata: the counts differ by at
most one). `_interleave` meets it by earliest-deadline scheduling over each stratum's k-th run's window, and checks it before it returns.
Assumptions stated: the plan covers the blocks `main` and `pagination` (the pilot keeps Sol + Opus and K is untouched, `--pair`); the
sections are "the runs whose subject model is site_j" and "the rest".
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import heapq
import json
import math
import os
import random
import sqlite3
import stat
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

FORMAT_PLAN = "icsa-inspection-plan-v1"
FORMAT_PAIR = "icsa-inspection-pair-v1"
FORMAT_GATE = "icsa-inspection-quota-gate-v1"
PLAN_BLOCKS = ("main", "pagination")                      # queue.MAIN_PHASES: the blocks whose coded runs the plan pairs
PLAN_FIELDS = ("run_key", "block", "instance_id", "option", "layout", "model", "seed")
SECTIONS = ("sonnet_first", "rest")
DEFAULT_STOP_AT = "2026-11-06T06:00:00Z"                  # amendment 29(c): coding of the snapshot's runs stops here; fixed in the plan file
CODING_SEED = 20261103                                     # amendment 30(l): the coding order's seed
GATE_PERCENT = 95.0                                       # amendment 26: the ChatGPT plan's window used
SONNET_HARD_STOP_PERCENT = 99.0                           # science, #34, 4 Nov 20:22Z: a Sonnet-subject run keeps using Sol past GATE_PERCENT, up to here
SONNET_EXCEPTION_WHY = "gate closed at the threshold, Sonnet-subject exception: Sol until the hard stop"
BLIND_AFTER = 3                                           # answers running with no readable reading
SOL_PAIR = ("codex", "claude")                            # Sol + Opus
FALLBACK_PAIR = ("sonnet", "claude")                      # Opus + Sonnet
PAIR_NAMES = {SOL_PAIR: "sol+opus", FALLBACK_PAIR: "opus+sonnet"}


class PlanError(ValueError):
    """A plan or pair record that cannot be used: stops the run before any call."""


class PlanMismatch(PlanError):
    """A second build of the plan differs from the one on file."""


class PairError(PlanError):
    """A pair that breaks the rule (a subject model judging its own run, a changed pair, a record that does not fit its run)."""


def pair_name(pair) -> str | None:
    return None if pair is None else PAIR_NAMES.get(tuple(pair))


def is_sonnet_subject(model) -> bool:
    """A subject run of site_j. Matched on the word, not the exact id, because the one error that must never happen is Sonnet
    coding a Sonnet run: a spelling this code did not foresee has to count as Sonnet."""
    return "sonnet" in str(model or "").lower()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(obj) -> str:
    return hashlib.sha256(_canon(obj).encode()).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso(t) -> str:
    """One fixed-width UTC form, so that times compare as strings."""
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    else:
        d = dt.datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise PlanError(f"{t!r} has no time zone")
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _create_new(path: Path, text: str) -> None:
    """Write `path` only if it does not exist (atomic): FileExistsError otherwise."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.link(tmp, path)          # fails if `path` exists
    finally:
        Path(tmp).unlink(missing_ok=True)


# ----------------------------------------------------------------------------- the planned matrix

def planned_from_manifest(rows) -> list[dict]:
    """Plan rows from `icsa.campaign.manifest.ManifestRow`s (the campaign's own plan, before it is stored)."""
    return [{"run_key": r.run_key, "block": r.block, "instance_id": r.run.instance_id, "option": r.run.option.value,
             "layout": r.run.layout.value, "model": r.run.model, "seed": r.run.seed} for r in rows]


def planned_from_store(campaign_root, blocks=PLAN_BLOCKS) -> tuple[list[dict], dict]:
    """(plan rows, progress) from the campaign store `state.sqlite`, read-only. Only the seven plan columns are selected: a run's `status`
    is how it went, and the order may not know. `progress` counts the in-scope runs by status, for the provenance sidecar only."""
    path = Path(campaign_root) / "state.sqlite"
    if not path.is_file():
        raise PlanError(f"no campaign store at {path}")
    q = ",".join("?" * len(blocks))
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        rows = [dict(zip(PLAN_FIELDS, r)) for r in db.execute(
            f"SELECT {', '.join(PLAN_FIELDS)} FROM runs WHERE block IN ({q}) ORDER BY run_key", tuple(blocks))]
        progress = dict(db.execute(f"SELECT status, COUNT(*) FROM runs WHERE block IN ({q}) GROUP BY status", tuple(blocks)).fetchall())
    except sqlite3.Error as e:
        raise PlanError(f"campaign store {path}: {type(e).__name__}: {e}") from e
    finally:
        db.close()
    return rows, progress


def _select(planned, blocks) -> list[dict]:
    """The in-scope rows, each reduced to PLAN_FIELDS and sorted by run key. Anything else a caller's row carries (a label, a status, a
    verdict) stops here."""
    out, seen = [], set()
    for r in planned:
        if r.get("block") not in blocks:
            continue
        row = {f: r.get(f) for f in PLAN_FIELDS}
        for f in ("run_key", "option", "layout", "model"):
            if not isinstance(row[f], str) or not row[f]:
                raise PlanError(f"a planned run has no {f}: {r.get('run_key')!r}")
        if row["run_key"] in seen:
            raise PlanError(f"run {row['run_key']} appears twice in the planned matrix")
        seen.add(row["run_key"])
        out.append(row)
    out.sort(key=lambda x: x["run_key"])
    return out


def stratum_of(row) -> str:
    return f"{row['option']}|{row['layout']}|{row['model']}"


# ----------------------------------------------------------------------------- the order

def _interleave(rows: list[dict], seed, section: str) -> list[dict]:
    """The rows of one section in a seeded order whose every prefix meets the quota condition per stratum.

    Stratum s has n runs of T. Its k-th run may stand at position t only where the count stays within the quota, floor(t*n/T) <= c <= ceil(t*n/T):
    from R = floor((k-1)*T/n) + 1 to D = ceil(k*T/n). Unit jobs with release times and deadlines: earliest deadline first is optimal, and a feasible
    schedule exists (Tijdeman's chairman assignment, discrepancy below 1). Ties go to a seeded stratum rank, and within a stratum the runs are a
    seeded shuffle of the sorted run keys. Everything is integer arithmetic."""
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[stratum_of(r)].append(r)
    strata = sorted(by)
    ranked = list(strata)
    random.Random(f"{seed}|plan|strata|{section}").shuffle(ranked)
    rank = {s: i for i, s in enumerate(ranked)}
    for s in strata:
        random.Random(f"{seed}|plan|rows|{section}|{s}").shuffle(by[s])
    total = len(rows)
    jobs = []
    for s in strata:
        n = len(by[s])
        for k in range(1, n + 1):
            jobs.append(((k - 1) * total // n + 1, -(-k * total // n), rank[s], s, k))
    jobs.sort()
    heap, i, taken, out = [], 0, {s: 0 for s in strata}, []
    for t in range(1, total + 1):
        while i < len(jobs) and jobs[i][0] <= t:
            _, dl, rk, s, k = jobs[i]
            heapq.heappush(heap, (dl, rk, s, k))
            i += 1
        if not heap:
            raise PlanError(f"{section}: no run is due at position {t}: the quota windows cannot be met")
        dl, _, s, k = heapq.heappop(heap)
        if dl < t or k != taken[s] + 1:
            raise PlanError(f"{section}: stratum {s}'s run {k} misses its window at position {t}")
        taken[s] = k
        out.append(by[s][k - 1])
    return out


def max_prefix_discrepancy(strata_in_order: list[str]) -> float:
    """The largest |count - n * size / total| over every prefix and every stratum of a sequence of strata (tests and the report use it; it
    does not use the windows above)."""
    total = len(strata_in_order)
    size = Counter(strata_in_order)
    seen: Counter = Counter()
    worst = 0.0
    for n, s in enumerate(strata_in_order, 1):
        seen[s] += 1
        for g in size:
            worst = max(worst, abs(seen[g] - n * size[g] / total))
    return worst


def build_order(planned, seed, blocks=PLAN_BLOCKS) -> list[dict]:
    """The plan's fixed list: Sonnet subject runs first, then the rest, each section stratified so that every prefix is balanced.
    A function of the seed and the planned rows' seven plan columns alone. Each item: run_key, block, section, stratum, option, layout, model."""
    rows = _select(planned, tuple(blocks))
    if not rows:
        raise PlanError("the planned matrix has no run in " + ", ".join(blocks))
    parts = {"sonnet_first": [r for r in rows if is_sonnet_subject(r["model"])],
             "rest": [r for r in rows if not is_sonnet_subject(r["model"])]}
    order = []
    for name in SECTIONS:
        for r in (_interleave(parts[name], seed, name) if parts[name] else []):
            order.append({"run_key": r["run_key"], "block": r["block"], "section": name, "stratum": stratum_of(r),
                          "option": r["option"], "layout": r["layout"], "model": r["model"]})
    return order


def build_plan(planned, seed, blocks=PLAN_BLOCKS, stop_at=DEFAULT_STOP_AT) -> dict:
    rows = _select(planned, tuple(blocks))
    order = build_order(rows, seed, blocks)
    strata = {sec: dict(sorted(Counter(i["stratum"] for i in order if i["section"] == sec).items())) for sec in SECTIONS}
    plan = {"format": FORMAT_PLAN, "seed": seed, "blocks": list(blocks), "stop_at": _iso(_epoch(stop_at)),
            "rule": "Sonnet subject runs first (Sol + Opus), then the rest, in one seeded order balanced per option x layout x model; "
                    "Sol + Opus until the plan's window reaches the gate, then Opus + Sonnet; a Sonnet subject run never gets Opus + Sonnet",
            "gate": {"percent": GATE_PERCENT, "blind_after": BLIND_AFTER},
            "n_planned": len(rows), "sections": {sec: sum(strata[sec].values()) for sec in SECTIONS}, "strata": strata,
            "planned_sha256": _sha(rows), "order": order, "order_sha256": _sha(order)}
    plan["plan_sha256"] = _sha(plan)
    return plan


def plan_text(plan: dict) -> str:
    return json.dumps(plan, sort_keys=True, indent=1) + "\n"


def write_plan(plan: dict, path) -> str:
    """Write the plan once. "created", or "unchanged" when the file holds exactly this plan; a different one on file raises PlanMismatch."""
    path = Path(path)
    text = plan_text(plan)
    try:
        _create_new(path, text)
        return "created"
    except FileExistsError:
        have = path.read_text()
        if have == text:
            return "unchanged"
        try:
            old = json.loads(have).get("plan_sha256")
        except ValueError:
            old = "unreadable"
        raise PlanMismatch(f"{path} holds another plan (sha256 {old}); this build is {plan['plan_sha256']}: a second build must match "
                           "the first byte for byte, so the seed or the planned matrix changed") from None


def load_plan(path) -> dict:
    """The plan on file, its three hashes checked."""
    plan = json.loads(Path(path).read_text())
    if not isinstance(plan, dict) or plan.get("format") != FORMAT_PLAN:
        raise PlanError(f"{path} is not an inspection plan (format {plan.get('format') if isinstance(plan, dict) else None!r})")
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    if _sha(body) != plan.get("plan_sha256") or _sha(plan.get("order")) != plan.get("order_sha256"):
        raise PlanError(f"{path}: its hash does not match its content (edited after it was built)")
    if not plan.get("stop_at"):
        raise PlanError(f"{path}: the plan has no coding stop time (amendment 29(c)): build it again")
    keys = [i["run_key"] for i in plan["order"]]
    if len(set(keys)) != len(keys) or len(keys) != plan.get("n_planned"):
        raise PlanError(f"{path}: the order is not the planned runs, each once")
    return plan


# ----------------------------------------------------------------------------- the quota gate

GATE_WAIT_S = 3600.0        # science, #76, 3 Nov 00:02Z: about an hour for a reset (a parameter)
PROBE_S = 600.0             # a probe every 10 minutes while the gate holds (a parameter)
PROBE_SLOW_S = 1800.0       # and every 30 minutes after the switch (a parameter)
POST_RETRY_S = 60.0
TOUCH_S = 60.0
PROBE_MESSAGE = "Reply with the single word: ok"
QUEUE_KEY = "codex_quota_95"
FORMAT_DEFERRED = "icsa-inspection-deferred-v1"


def _number(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) and v >= 0 else None


def reading_of(rate_limits) -> dict | None:
    """The plan's use as one Codex answer saw it: `primary.used_percent` with its window, from the flat `detail["ran"]["rate_limits"]`
    that coders.rollout_context records. None when the field is absent or not a plain non-negative number."""
    if not isinstance(rate_limits, dict):
        return None
    u = _number(rate_limits.get("primary.used_percent"))
    if u is None:
        return None
    out = {"used_percent": u, "window_minutes": rate_limits.get("primary.window_minutes"), "resets_at": None, "resets_at_iso": None,
           "limit_id": rate_limits.get("limit_id"), "plan_type": rate_limits.get("plan_type")}
    ra = rate_limits.get("primary.resets_at")
    if isinstance(ra, (int, float)) and not isinstance(ra, bool) and math.isfinite(ra):
        out["resets_at"] = ra
        try:
            out["resets_at_iso"] = _iso(ra)
        except (OverflowError, OSError, ValueError):
            pass
    return out


def _epoch(t) -> float:
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        return float(t)
    d = dt.datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise PlanError(f"{t!r} has no time zone")
    return d.timestamp()


class GateError(RuntimeError):
    pass


class QuotaGate:
    """The plan's Codex quota gate (amendment 26 and science, #76, 3 Nov 00:02Z). It has three modes:

    - `open`: Sol codes. It leaves `open` for `holding` when a reading is at or above `percent` (`threshold`), when `blind_after` answers in a
      row show no readable `primary.used_percent` (`blind`: never run on blind), or when Codex returns a limit error before the gate saw the
      threshold (`quota_error`). That is one EPISODE; it is posted once (`GateKeeper`). In-flight Sol calls finish.
    - `holding`: no new Sol dispatch, and no new dispatch at all, for `wait_s` after the closing; a probe through the real isolated launcher
      reads the quota every `probe_s`. A probe reading below `percent` reopens the gate. In-flight Sol answers are logged but never reopen it
      (their reading is older than the probe's).
    - `switched`: the wait ended with no reset. The next dispatches take Opus + Sonnet (a Sonnet subject run waits for Sol instead), and a probe
      every `probe_slow_s` still looks for a reset; one reopens the gate, and Sol resumes for the runs not yet dispatched. A run already
      dispatched keeps its pair, always.
    Everything is a line of the full log `gate-log.jsonl`, appended before the state changes, with its time and reading: the calls (`call`, one
    per Sol attempt), the probes (`probe`), `closed`, `reopened`, `switched`, `posted`, `post_failed`. The state is the replay of that log, so a
    restart reaches the same gate, the wait included (the wait is counted from the closing time on the log). `gate.json` is the snapshot. The
    public `plan-events.jsonl` carries the same events except the calls, and the runner's totals lines: nothing per attempt or per packet.
    The limit-error text (`coders.quota_error`) is a best-effort match: no real limit response was ever captured. So the gate does not rely on
    it: any run of `blind_after` Codex calls that show no readable reading, failed or not, closes the gate the same way (`blind`)."""

    def __init__(self, work, plan: dict, *, clock=time.time, wait_s: float = GATE_WAIT_S, probe_s: float = PROBE_S,
                 probe_slow_s: float = PROBE_SLOW_S, private=None, sonnet_hard_stop: float = SONNET_HARD_STOP_PERCENT):
        g = plan["gate"]
        self.threshold, self.blind_after, self.plan_sha256 = float(g["percent"]), int(g["blind_after"]), plan["plan_sha256"]
        hs = float(sonnet_hard_stop)
        if not (math.isfinite(hs) and self.threshold < hs <= 100.0):
            raise GateError(f"the Sonnet hard stop {sonnet_hard_stop!r} must be above the threshold {self.threshold} and at most 100")
        self.sonnet_hard_stop, self.sol_limited = hs, False
        self.wait_s, self.probe_s, self.probe_slow_s, self._clock = float(wait_s), float(probe_s), float(probe_slow_s), clock
        self.dir = Path(work) / "quota"
        # The full log (every Sol attempt, the replay's source) is `gate-log.jsonl`, in `private` (the sealed directory) when one is given. The
        # public `plan-events.jsonl` mirrors only the gate's own events and the totals lines: no line per attempt, none per packet.
        self.log = (Path(private) if private is not None else self.dir) / "gate-log.jsonl"
        self.public_log, self.state_path = self.dir / "plan-events.jsonl", self.dir / "gate.json"
        self._lock = threading.RLock()
        self.mode, self.episode, self.closed, self.episodes = "open", 0, None, []
        self.n_calls = self.n_readings = self.n_quota_errors = self.blind_streak = self.n_probes = self.n_post_failed = 0
        self.last_reading = self.max_used_percent = self.episode_last_probe_ts = None
        self.posted: set = set()
        self.seq = 0
        self.dir.mkdir(parents=True, exist_ok=True)
        if self.state_path.is_file():
            old = json.loads(self.state_path.read_text())
            if old.get("plan_sha256") != self.plan_sha256:
                raise GateError(f"{self.state_path} belongs to another plan ({old.get('plan_sha256')} != {self.plan_sha256}): "
                                "use a new work directory for a new plan")
        if self.log.is_file():
            if self.log.read_bytes()[-1:] not in (b"", b"\n"):      # a torn last line: end it, so that the next fact starts on a line of its own
                with self.log.open("a") as fh:
                    fh.write("\n")
            for ln in self.log.read_text().splitlines():
                if not ln.strip():
                    continue
                try:
                    e = json.loads(ln)
                except ValueError:
                    continue            # a torn last line of a killed process: the facts before it stand
                self.seq = max(self.seq, e.get("seq", 0))
                self._apply(e)
        self._write_state()

    # -- reading the state
    @property
    def is_open(self) -> bool:
        return self.mode == "open"

    def has_reading(self) -> bool:
        return self.n_readings > 0

    def sonnet_sol_ok(self) -> bool:
        """May a SONNET-SUBJECT run use Sol now (science, #34, 4 Nov 20:22Z)? Yes while the gate is open. Once it has closed AT THE THRESHOLD (95), yes until
        the newest reading reaches the hard stop (99): a Sonnet subject run never gets Opus + Sonnet, so it keeps Sol while the plan's window lasts, and no
        other run does. No when it closed on a blind streak or a limit error, when Codex has since answered with a limit error, when the readings have
        stopped (a blind streak since), or when there is no reading at all. Derived from the log, so a restart gives the same answer."""
        with self._lock:
            if self.mode == "open":
                return True
            lr = self.last_reading
            return bool((self.closed or {}).get("reason") == "threshold" and not self.sol_limited and self.blind_streak < self.blind_after
                        and lr is not None and lr["used_percent"] < self.sonnet_hard_stop)

    def snapshot(self) -> dict:
        return {"format": FORMAT_GATE, "plan_sha256": self.plan_sha256, "threshold_percent": self.threshold, "blind_after": self.blind_after,
                "wait_s": self.wait_s, "probe_s": self.probe_s, "probe_slow_s": self.probe_slow_s,
                "mode": self.mode, "state": "open" if self.mode == "open" else "closed", "episode": self.episode, "closed": self.closed,
                "episodes": [dict(e) for e in self.episodes], "last_reading": self.last_reading, "max_used_percent": self.max_used_percent,
                "n_calls": self.n_calls, "n_readings": self.n_readings, "n_probes": self.n_probes, "n_quota_errors": self.n_quota_errors,
                "blind_streak": self.blind_streak, "n_post_failed": self.n_post_failed, "posted_episodes": sorted(self.posted),
                "sonnet_hard_stop_percent": self.sonnet_hard_stop, "sonnet_sol_ok": self.sonnet_sol_ok()}

    def unposted(self) -> list[int]:
        with self._lock:
            return [e["episode"] for e in self.episodes if e["episode"] not in self.posted]

    def due(self, now: float) -> dict:
        with self._lock:
            if self.mode == "open":
                return {"probe": False, "switch": False}
            base = self.episode_last_probe_ts if self.episode_last_probe_ts is not None else self.episodes[-1]["closed_ts"]
            interval = self.probe_s if self.mode == "holding" else self.probe_slow_s
            return {"probe": now >= base + interval,
                    "switch": self.mode == "holding" and now >= self.episodes[-1]["closed_ts"] + self.wait_s}

    # -- the state machine: a fold over the log, the same at write time and at replay
    def _write_state(self) -> None:
        _atomic_write(self.state_path, json.dumps(self.snapshot(), indent=1, sort_keys=True) + "\n")

    def _note_reading(self, e: dict) -> None:
        u = e["used_percent"]
        if self.last_reading is None or e["ts"] >= self.last_reading["ts"]:          # the newest by time, whatever order the workers report in
            self.last_reading = {**{k: e.get(k) for k in ("ts", "t", "used_percent", "window_minutes", "resets_at", "resets_at_iso")},
                                 "source": e["event"]}
        if self.max_used_percent is None or u > self.max_used_percent:
            self.max_used_percent = u

    def _mark_hard_stop(self, e: dict, u: float) -> None:
        """The time of the first reading at or above the Sonnet hard stop in the open episode (what the final row counts from)."""
        if u >= self.sonnet_hard_stop and self.mode != "open" and self.episodes:
            self.episodes[-1].setdefault("sonnet_hard_stop_at", e["t"])

    def _close(self, e: dict, reason: str, detail: str) -> None:
        if self.mode != "open":
            return
        self.mode, self.episode = "holding", self.episode + 1
        reading = {k: e.get(k) for k in ("t", "used_percent", "window_minutes", "resets_at", "resets_at_iso")}
        self.closed = {"episode": self.episode, "at": e["t"], "ts": e["ts"], "reason": reason, "detail": detail, "reading": reading}
        self.episodes.append({"episode": self.episode, "closed_at": e["t"], "closed_ts": e["ts"], "reason": reason, "detail": detail,
                              "reading": reading, "probes": 0, "switched_at": None, "reopened_at": None,
                              "reopened_reading": None, "posted_at": None})
        self.episode_last_probe_ts = None

    def _apply(self, e: dict) -> None:
        ev = e.get("event")
        if ev == "call":
            self.n_calls += 1
            if e.get("quota_error"):
                self.n_quota_errors += 1
                self._close(e, "quota_error", str(e["quota_error"])[:200])
            u = e.get("used_percent")
            if u is not None:
                self.blind_streak = 0
                self.n_readings += 1
                self._note_reading(e)
                if u >= self.threshold:
                    self._close(e, "threshold", f"used_percent {u} >= {self.threshold}")
                self._mark_hard_stop(e, u)
                if u < self.sonnet_hard_stop and not e.get("quota_error"):
                    self.sol_limited = False        # a readable answer under the hard stop: Sol is answering
            else:                                   # a call that shows no reading, an answer or a failed call alike (the limit-error text is best effort)
                self.blind_streak += 1
                if self.blind_streak >= self.blind_after:
                    self._close(e, "blind", f"no readable primary.used_percent in {self.blind_after} Codex calls running")
            if e.get("quota_error"):
                self.sol_limited = True             # Codex said the limit is hit: no Sonnet-subject exception until a later answer reads under the hard stop
        elif ev == "probe":
            self.n_probes += 1
            if self.mode != "open":
                self.episode_last_probe_ts = e["ts"]
                self.episodes[-1]["probes"] += 1
            u = e.get("used_percent")
            if u is not None:
                self._note_reading(e)
                self._mark_hard_stop(e, u)
                if u < self.sonnet_hard_stop:
                    self.sol_limited = False
                if self.mode != "open" and u < self.threshold:        # a reset: Sol resumes for the runs not yet dispatched
                    self.episodes[-1].update(reopened_at=e["t"], reopened_reading={k: e.get(k) for k in (
                        "t", "used_percent", "window_minutes", "resets_at", "resets_at_iso")})
                    self.mode, self.closed, self.blind_streak = "open", None, 0
        elif ev == "switched":
            if self.mode == "holding" and e.get("episode") == self.episode:
                self.mode = "switched"
                self.episodes[-1]["switched_at"] = e["t"]
        elif ev == "posted":
            if 1 <= e.get("episode", 0) <= len(self.episodes):
                self.posted.add(e["episode"])
                self.episodes[e["episode"] - 1]["posted_at"] = e["t"]
        elif ev == "post_failed":
            self.n_post_failed += 1

    def _stamp(self, event: str, t, fields: dict) -> dict:
        ts = _epoch(t) if t is not None else self._clock()
        self.seq += 1
        return {"event": event, "seq": self.seq, "ts": ts, "t": _iso(ts), **fields}

    def _append(self, *events: dict) -> None:
        with self.log.open("a") as fh:
            fh.write("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
            fh.flush()
            os.fsync(fh.fileno())
        shown = [e for e in events if e.get("event") != "call"]            # a call is a Sol attempt: it stays in the full log
        if shown:
            with self.public_log.open("a") as fh:
                fh.write("".join(json.dumps(e, sort_keys=True) + "\n" for e in shown))
                fh.flush()

    def _record(self, e: dict) -> dict:
        """Append one fact, apply it, and add the audit lines for what it changed. Under the lock."""
        before = (self.mode, self.episode)
        self._append(e)
        self._apply(e)
        extra = []
        if self.episode != before[1]:
            extra.append(self._stamp("closed", e["ts"], {"episode": self.episode, "reason": self.closed["reason"], "detail": self.closed["detail"],
                                                          "reading": self.closed["reading"]}))
        if before[0] != "open" and self.mode == "open":
            extra.append(self._stamp("reopened", e["ts"], {"episode": self.episode, "reading": self.episodes[-1]["reopened_reading"]}))
        if extra:
            self._append(*extra)
        self._write_state()
        return e

    # -- the facts
    def observe_call(self, *, pid, status, rate_limits=None, quota_error=None, t=None) -> dict:
        """One Codex call (an attempt). `rate_limits`: the call's `detail["ran"]["rate_limits"]`."""
        rd = reading_of(rate_limits) or {}
        with self._lock:
            return self._record(self._stamp("call", t, {              # no packet id: the log is public, and carries quota readings only
                "status": status, "answer": status in ("ok", "contaminated"), "used_percent": rd.get("used_percent"),
                "window_minutes": rd.get("window_minutes"), "resets_at": rd.get("resets_at"), "resets_at_iso": rd.get("resets_at_iso"),
                "limit_id": rd.get("limit_id"), "plan_type": rd.get("plan_type"), "quota_error": quota_error or None}))

    def observe_probe(self, *, status, rate_limits=None, usage=None, error=None, t=None) -> dict:
        """One probe through the real launcher: a reading, never a coder answer. Its tokens are logged here and nowhere else."""
        rd = reading_of(rate_limits) or {}
        with self._lock:
            return self._record(self._stamp("probe", t, {
                "status": status, "used_percent": rd.get("used_percent"), "window_minutes": rd.get("window_minutes"),
                "resets_at": rd.get("resets_at"), "resets_at_iso": rd.get("resets_at_iso"), "limit_id": rd.get("limit_id"),
                "plan_type": rd.get("plan_type"), "usage": usage or {}, "error": (str(error)[:300] if error else None),
                "mode_before": self.mode}))

    def mark_switched(self, *, t=None) -> dict:
        with self._lock:
            if self.mode != "holding":
                raise GateError(f"cannot switch from {self.mode}")
            return self._record(self._stamp("switched", t, {"episode": self.episode, "waited_s": self.wait_s}))

    def mark_posted(self, episode: int, sinks: list, event: dict, *, t=None) -> dict:
        with self._lock:
            return self._record(self._stamp("posted", t, {"episode": episode, "sinks": list(sinks), "post": event}))

    def mark_post_failed(self, episode: int, error, *, t=None) -> dict:
        with self._lock:
            return self._record(self._stamp("post_failed", t, {"episode": episode, "error": str(error)[:300]}))

    def audit(self, event: str, **fields) -> dict:
        """A line for the record that changes nothing (a pass starting or ending, the parameters, a queue-file error)."""
        with self._lock:
            e = self._stamp(event, None, fields)
            self._append(e)
            return e


class ReadingBackend:
    """A Codex backend whose every call is shown to the gate. It has the wrapped backend's coder, model and effort, and calls it unchanged."""

    def __init__(self, inner, gate: QuotaGate, pid: str):
        self.inner, self.gate, self.pid = inner, gate, pid
        self.coder, self.model, self.effort = inner.coder, inner.model, inner.effort

    def call(self, message, schema):
        res = self.inner.call(message, schema)
        d = res.detail if isinstance(res.detail, dict) else {}
        ran = d.get("ran") if isinstance(d.get("ran"), dict) else {}
        self.gate.observe_call(pid=self.pid, status=res.status, rate_limits=ran.get("rate_limits"), quota_error=d.get("quota_error"))
        return res


class SolSlots:
    """At most `capacity` Sol runs at once, and ONE until the gate has seen a first reading (twelve calls started with nothing to read would be
    running blind). `acquire` waits, and returns False if the gate is not open (or leaves `open` while it waits): the caller then follows the
    gate. `force` is for a run that already has its Sol pair (resume) and for a probe: it waits for a slot whatever the gate says."""

    def __init__(self, capacity: int, gate: QuotaGate, poll_s: float = 0.2):
        self.capacity, self.gate, self.poll_s, self.in_flight = int(capacity), gate, poll_s, 0
        self._cond = threading.Condition()

    def acquire(self, force: bool = False) -> bool:
        with self._cond:
            while True:
                if not force and not self.gate.is_open:
                    return False
                cap = self.capacity if (self.gate.has_reading() or not self.gate.is_open) else 1
                if self.in_flight < cap:
                    self.in_flight += 1
                    return True
                self._cond.wait(self.poll_s)

    def release(self) -> None:
        with self._cond:
            self.in_flight -= 1
            self._cond.notify_all()


class OperatorQueue:
    """The runner's OWN queue file for the operator's morning queue, never the campaign's (lane-int2's format, via the lead, 3 Nov): one JSON
    object `{"items": [...]}` rewritten whole by atomic replace. The item `codex_quota_95` has `since_utc`, `held` (one line: what is held), `ask`
    (one exact line: what is needed), `last_seen_utc`, and `resolved_utc` (null while open; set when a reset is seen or the plan ends). A second
    closing opens the same item again."""

    def __init__(self, path):
        self.path = Path(path)

    def _items(self) -> list:
        if not self.path.is_file():
            return []
        d = json.loads(self.path.read_text())
        return list(d.get("items", [])) if isinstance(d, dict) else []

    def _write(self, items: list) -> None:
        _atomic_write(self.path, json.dumps({"items": items}, indent=1, sort_keys=True) + "\n")

    def _item(self, items: list):
        return next((i for i in items if i.get("key") == QUEUE_KEY), None)

    def is_open(self) -> bool:
        it = self._item(self._items())
        return bool(it) and it.get("resolved_utc") is None

    def post(self, event: dict) -> None:
        items = [i for i in self._items() if i.get("key") != QUEUE_KEY]
        items.append({"key": QUEUE_KEY, "since_utc": event["closed_at"], "held": event["held"], "ask": event["ask"],
                      "last_seen_utc": event["closed_at"], "resolved_utc": None})
        self._write(items)

    def touch(self, utc: str, held: str | None = None) -> None:
        items = self._items()
        it = self._item(items)
        if it and it.get("resolved_utc") is None:
            it["last_seen_utc"] = utc
            if held:
                it["held"] = held
            self._write(items)

    def resolve(self, utc: str) -> None:
        items = self._items()
        it = self._item(items)
        if it and it.get("resolved_utc") is None:
            it["last_seen_utc"] = it["resolved_utc"] = utc
            self._write(items)


ASK_LINE = ("Reset or raise the ChatGPT plan's Codex limit (the runner probes the quota and resumes Sol by itself), "
            "or tell science to let the plan run on Opus + Sonnet.")


class GateKeeper:
    """What the gate does with time: posts a closing once, probes, switches, and keeps the operator queue's item current. `tick()` does what is
    due; the runner calls it from a thread, a test calls it with a clock it controls. `sink` is any object with `post(event)` and, optionally,
    `touch(utc, held)`, `resolve(utc)` and `is_open()` (the `OperatorQueue`); a post that fails is logged and retried, never raised. `probe()`
    returns a `CallResult` from the real isolated launcher (a one-line message, no schema)."""

    def __init__(self, gate: QuotaGate, *, probe=None, sink=None, clock=time.time, post_retry_s: float = POST_RETRY_S,
                 touch_s: float = TOUCH_S, out=print):
        self.gate, self.probe, self.sink, self.clock = gate, probe, sink, clock
        self.post_retry_s, self.touch_s, self.out = post_retry_s, touch_s, out
        self.deferred = 0                       # Sonnet subject runs waiting for Sol, set by the runner (for the queue's `held` line)
        self._last_try: dict = {}
        self._last_touch = -math.inf
        self._synced = self._item_open = False

    def event(self, episode: int) -> dict:
        ep = self.gate.episodes[episode - 1]
        r = ep["reading"]
        pct = f"{r['used_percent']}%" if r.get("used_percent") is not None else "no reading"
        return {"kind": "codex_quota_gate_closed", "plan_sha256": self.gate.plan_sha256, "episode": episode, "reason": ep["reason"],
                "detail": ep["detail"], "closed_at": ep["closed_at"], "reading": r, "window_end": r.get("resets_at_iso"),
                "to": ["operator-morning-queue", "science"], "held": self.held_line(ep), "ask": ASK_LINE, "reading_text": pct}

    def held_line(self, ep: dict | None = None) -> str:
        ep = ep or (self.gate.episodes[-1] if self.gate.episodes else None)
        if ep is None:
            return ""
        r = ep["reading"]
        pct = f"{r['used_percent']}% used" if r.get("used_percent") is not None else "no readable reading"
        state = {"holding": f"waiting {self.gate.wait_s / 60:.0f} min for a reset, probing every {self.gate.probe_s / 60:.0f} min",
                 "switched": f"no reset in the wait: Opus + Sonnet for the next dispatches, probing every {self.gate.probe_slow_s / 60:.0f} min",
                 "open": "reset seen"}[self.gate.mode]
        wait = "; some planned runs are waiting for Sol" if self.deferred else ""
        exc = ""
        if self.gate.mode != "open":
            exc = (f"; Sonnet-subject runs still use Sol (Sol + Opus) until {self.gate.sonnet_hard_stop:g}%" if self.gate.sonnet_sol_ok()
                   else "; Sonnet-subject runs are NOT using Sol either (hard stop, a limit error, or no readable reading)")
        return (f"Codex (Sol) coding of the main block: no new Sol dispatch for the other runs since {ep['closed_at']} ({ep['reason']}: {pct}, window ends "
                f"{r.get('resets_at_iso')}); {state}{wait}{exc}")

    def _do_probe(self, now: float) -> None:
        if self.probe is None:
            self.gate.observe_probe(status="unavailable", error="this backend cannot probe", t=now)
            return
        try:
            res = self.probe()
        except Exception as e:      # noqa: BLE001 -- a probe that cannot run is a probe with no reading, never a stop
            self.gate.observe_probe(status="error", error=f"{type(e).__name__}: {e}", t=now)
            return
        d = res.detail if isinstance(res.detail, dict) else {}
        ran = d.get("ran") if isinstance(d.get("ran"), dict) else {}
        self.gate.observe_probe(status=res.status, rate_limits=ran.get("rate_limits"), usage=res.usage, error=d.get("error"), t=now)

    def _try(self, label: str, fn, *a) -> bool:
        try:
            fn(*a)
            return True
        except Exception as e:      # noqa: BLE001 -- the operator queue is best effort, coding never waits on it
            self.gate.audit("queue_error", op=label, error=f"{type(e).__name__}: {e}"[:300])
            return False

    def tick(self, now: float | None = None) -> list[str]:
        now = self.clock() if now is None else now
        g, done = self.gate, []
        if self.sink is not None and not self._synced:       # a restart: is the queue's item still open?
            self._item_open = bool(getattr(self.sink, "is_open", lambda: False)())
            self._synced = True
        for ep in g.unposted():                               # a closing is posted once; a failed post is retried, and nothing waits on it
            if now - self._last_try.get(ep, -math.inf) < self.post_retry_s:
                continue
            self._last_try[ep] = now
            ev = self.event(ep)
            try:
                if self.sink is not None:
                    self.sink.post(ev)
                    self._item_open = True
                g.mark_posted(ep, ["operator-queue"] if self.sink is not None else [], ev, t=now)
                done.append(f"posted:{ep}")
                self._last_touch = now
            except Exception as e:                          # noqa: BLE001
                g.mark_post_failed(ep, f"{type(e).__name__}: {e}", t=now)
                done.append(f"post_failed:{ep}")
        if g.due(now)["probe"]:
            self._do_probe(now)
            done.append("probe")
        if g.due(now)["switch"]:
            g.mark_switched(t=now)
            done.append("switched")
        if self.sink is not None:
            ts = _iso(now)
            if g.mode == "open":
                if self._item_open and self._try("resolve", self.sink.resolve, ts):
                    self._item_open = False
                    done.append("queue_resolved")
            elif self._item_open and now - self._last_touch >= self.touch_s:
                if self._try("touch", self.sink.touch, ts, self.held_line()):
                    self._last_touch = now
        return done

    def refresh(self) -> None:
        """Bring the queue's item up to date now (the runs waiting for Sol, the time last seen), whatever the throttle says."""
        if self.sink is not None and self._item_open and self.gate.mode != "open" and hasattr(self.sink, "touch"):
            self._try("touch", self.sink.touch, _iso(self.clock()), self.held_line())

    def finish(self, why: str = "the plan ended") -> None:
        """The pass is over. The queue's item is resolved if the gate is not open but nothing waits for Sol (the plan ended without it)."""
        if self.sink is not None and self._item_open and not self.deferred and self.gate.mode != "open":
            if self._try("resolve", self.sink.resolve, _iso(self.clock())):
                self._item_open = False
                self.gate.audit("queue_resolved", why=why)


# ----------------------------------------------------------------------------- the per-run pair record

def pair_path(work, pid) -> Path:
    return Path(work) / "answers" / pid / "pair.json"


def read_pair(work, pid) -> dict | None:
    p = pair_path(work, pid)
    if not p.is_file():
        return None
    try:
        rec = json.loads(p.read_text())
    except ValueError as e:
        raise PairError(f"{p} is unreadable: {e}") from e
    if not isinstance(rec, dict) or rec.get("format") != FORMAT_PAIR:
        raise PairError(f"{p} is not a pair record")
    return rec


def guard_pair(rec: dict) -> None:
    """The invariants of a pair record. A subject model never judges its own runs: Sonnet never codes a Sonnet run."""
    pair = rec.get("pair")
    if pair is None:
        if rec.get("status") != "uncoded":
            raise PairError(f"packet {rec.get('packet')}: no pair but status {rec.get('status')!r}")
        return
    if tuple(pair) not in PAIR_NAMES or rec.get("status") != "coded":
        raise PairError(f"packet {rec.get('packet')}: {pair!r} is not a coder pair of the plan")
    if "sonnet" in pair and (rec.get("subject_sonnet") or is_sonnet_subject(rec.get("subject_model"))):
        raise PairError(f"packet {rec.get('packet')}: Opus + Sonnet on a Sonnet subject run (a subject model never judges its own runs)")


def new_pair_record(entry: dict, pair, gate: dict, reason: str, *, at=None) -> dict:
    """The record written BEFORE any call of the run. `pair` is None for a Sonnet subject run met by a closed gate (uncoded)."""
    rec = {"format": FORMAT_PAIR, "packet": entry["packet"], "position": entry["position"], "section": entry["section"],
           "subject_model": entry["model"], "subject_sonnet": bool(entry["subject_sonnet"]),
           "status": "coded" if pair is not None else "uncoded", "pair": list(pair) if pair is not None else None,
           "pair_name": pair_name(pair), "assigned": {"pair": list(pair) if pair is not None else None, "pair_name": pair_name(pair),
                                                      "at": at or _now(), "reason": reason, "gate": {
                                                          "mode": gate["mode"], "episode": gate["episode"],
                                                          "last_reading": gate.get("last_reading"), "closed": gate.get("closed")}},
           "reassignments": [], "notes": [], "uncoded_reason": reason if pair is None else None}
    guard_pair(rec)
    return rec


def write_new_pair(work, rec: dict) -> None:
    guard_pair(rec)
    _create_new(pair_path(work, rec["packet"]), json.dumps(rec, indent=1, sort_keys=True) + "\n")


def replace_pair(work, rec: dict) -> None:
    guard_pair(rec)
    _atomic_write(pair_path(work, rec["packet"]), json.dumps(rec, indent=1, sort_keys=True) + "\n")


def check_pair_record(rec: dict, entry: dict) -> None:
    """A record already on disk (resume) must be this run's: same place in the order, same subject, and obey the rule."""
    if (rec.get("packet"), rec.get("position"), rec.get("subject_model")) != (entry["packet"], entry["position"], entry["model"]):
        raise PairError(f"packet {entry['packet']}: its pair record is for another run (position {rec.get('position')}, "
                        f"subject {rec.get('subject_model')!r})")
    guard_pair(rec)


def sol_quota_failure(work, pid) -> str | None:
    """The limit error of this packet's Sol attempts, when it has no valid Sol answer; else None. Reads only each attempt's recorded
    `quota_error` and whether the final answer is valid (its status): never what an answer says."""
    base = Path(work) / "answers" / pid / "codex"
    fin = base / "final.json"
    if not fin.is_file():
        return None
    try:
        if json.loads(fin.read_text()).get("status") == "valid":
            return None
    except ValueError:
        return None
    for d in sorted(base.glob("attempt-*"), key=lambda p: p.name):
        if not d.name[len("attempt-"):].isdigit():
            continue
        try:
            q = json.loads((d / "meta.json").read_text()).get("quota_error")
        except (OSError, ValueError):
            continue
        if q:
            return str(q)[:200]
    return None


def reassign_if_quota_failed(work, rec: dict, *, at=None) -> tuple[dict, str | None]:
    """The one permitted change of a pair. A run with its Sol pair whose Sol attempts met a limit error and never gave a valid answer goes
    to Opus + Sonnet, with the reason recorded and the original assignment kept. Never for a Sonnet subject run: it keeps its pair (its Sol
    verdict is CANNOT TELL under 21(a)), is annotated, and the caller raises it loudly. Returns (record, "reassigned" |
    "sonnet_subject_not_reassigned" | None)."""
    if tuple(rec.get("pair") or ()) != SOL_PAIR:
        return rec, None
    reason = sol_quota_failure(work, rec["packet"])
    if reason is None:
        return rec, None
    at = at or _now()
    if rec["subject_sonnet"] or is_sonnet_subject(rec.get("subject_model")):
        if any(n.get("event") == "sonnet_subject_sol_quota_failed" for n in rec.get("notes", [])):
            return rec, "sonnet_subject_not_reassigned"
        new = {**rec, "notes": [*rec.get("notes", []), {"event": "sonnet_subject_sol_quota_failed", "at": at, "quota_error": reason,
                                                        "note": "no valid Sol answer; a Sonnet subject run is never given Opus + Sonnet"}]}
        replace_pair(work, new)
        return new, "sonnet_subject_not_reassigned"
    new = {**rec, "pair": list(FALLBACK_PAIR), "pair_name": pair_name(FALLBACK_PAIR),
           "reassignments": [*rec.get("reassignments", []), {"from": list(SOL_PAIR), "to": list(FALLBACK_PAIR), "at": at,
                                                             "reason": "codex_quota_error_no_valid_answer", "quota_error": reason}]}
    replace_pair(work, new)
    return new, "reassigned"


def write_stopped(sealed, plan: dict, counts: dict) -> None:
    """Coding reached the plan's `stop_at`: what was left. The runs with no pair record from here on are uncoded for good."""
    _atomic_write(Path(sealed) / "stopped.json",
                  json.dumps({"format": "icsa-inspection-stopped-v1", "plan_sha256": plan["plan_sha256"], "stop_at": plan["stop_at"], "at": _now(),
                              "counts": counts}, indent=1, sort_keys=True) + "\n")


def write_deferred(sealed, plan: dict, packets: dict) -> None:
    """The Sonnet subject runs a pass left undispatched because Sol was not open: packet -> why. They have no pair record (a later pass, after a
    reset, dispatches them with Sol); until then the report lists them as not coded. Rewritten by every pass. In the sealed directory."""
    _atomic_write(Path(sealed) / "deferred.json",
                  json.dumps({"format": FORMAT_DEFERRED, "plan_sha256": plan["plan_sha256"], "at": _now(), "packets": packets},
                             indent=1, sort_keys=True) + "\n")


# ----------------------------------------------------------------------------- the pair plan, for the report and coverage

class PairPlan:
    """What `report.decisions` needs to give each packet of the plan its own pair: the plan, the sealed directory's pair records and the gate's
    snapshot (`gate_dir`, the public `<work>/quota`)."""

    def __init__(self, plan: dict, sealed, key: dict, gate_dir=None, now: float | None = None):
        self.plan, self.work, self.key = plan, Path(sealed), key
        self.gate_dir = Path(gate_dir) if gate_dir is not None else self.work / "quota"
        self.position = {it["run_key"]: i for i, it in enumerate(plan["order"])}
        # past the plan's coding stop (or after the runner said so), a run with no pair record is uncoded for good, not "not yet dispatched"
        self.stopped = (now if now is not None else time.time()) >= _epoch(plan["stop_at"]) or (self.work / "stopped.json").is_file()

    @classmethod
    def load(cls, plan_path, sealed, key: dict, gate_dir=None, now: float | None = None) -> "PairPlan":
        return cls(load_plan(plan_path), sealed, key, gate_dir, now)

    def classify(self, pid: str, pk: dict) -> dict | None:
        """None: the packet is not in the plan (K, the pilot: the report's own pair). Else {'kind': 'coded' | 'uncoded' | 'not_dispatched', ...}."""
        pos = self.position.get(pk.get("run_key"))
        if pos is None:
            return None
        item = self.plan["order"][pos]
        if pk.get("model") != item["model"]:
            raise PairError(f"packet {pid}: the key says subject model {pk.get('model')!r}, the plan {item['model']!r}")
        rec = read_pair(self.work, pid)
        if rec is None:
            why = self.deferred().get(pid)
            if why:           # a Sonnet subject run left waiting for Sol when the runner's pass ended: not coded, its label stands as it was
                return {"kind": "uncoded", "position": pos, "section": item["section"], "reason": why, "deferred": True}
            if self.stopped:
                return {"kind": "uncoded", "position": pos, "section": item["section"], "deferred": True,
                        "reason": f"coding stopped at {self.plan['stop_at']} before this run was coded: it stays as the instrument left it"}
            return {"kind": "not_dispatched", "position": pos, "section": item["section"]}
        entry = {"packet": pid, "position": pos, "model": item["model"]}
        check_pair_record(rec, entry)
        if rec["pair"] is None:
            return {"kind": "uncoded", "position": pos, "section": item["section"], "reason": rec.get("uncoded_reason"), "record": rec}
        return {"kind": "coded", "position": pos, "section": item["section"], "pair": list(rec["pair"]), "record": rec}

    def deferred(self) -> dict:
        """packet -> why, for the Sonnet subject runs the runner's last pass left waiting for Sol (`write_deferred`)."""
        p = self.work / "deferred.json"
        if not p.is_file():
            return {}
        d = json.loads(p.read_text())
        if d.get("plan_sha256") != self.plan["plan_sha256"]:
            raise GateError(f"{p} belongs to another plan")
        return dict(d.get("packets", {}))

    def gate_snapshot(self) -> dict | None:
        p = self.gate_dir / "gate.json"
        if not p.is_file():
            return None
        snap = json.loads(p.read_text())
        if snap.get("plan_sha256") != self.plan["plan_sha256"]:
            raise GateError(f"{p} belongs to another plan")
        return snap


# ----------------------------------------------------------------------------- which runs are finished: the only thing a pass reads about a run

FINISHED, PENDING, TERMINAL, MISMATCH = "finished", "pending", "terminal", "mismatch"
RUN_FILES = ("transcript.json", "code_cells.json")           # what `packet.build` reads of a run directory
DEFAULT_INPUT_ROOT = "/mnt/volume2/icsa-2027/coding-mirror"  # lane-snap's mirror for the coders: `state.sqlite` directly under it, run dirs below it
FETCH_PREFIX_KEY = "fetch_run_dir_prefix"                   # `meta` key: what `snapshot.fetch` prepended to every `run_dir` in its copy of the store
SCIENCE_MIRROR = "snapshot-mirror"                          # science's alone: this lane never reads under a directory of this name
PULLED_SUFFIX = ".pulled.json"                              # beside a run directory, written by rename after its copy succeeded


class _NoMarker:
    def __repr__(self):
        return "NO_MARKER"


NO_MARKER = _NoMarker()           # "no pulled marker": for tests only (the runner's --no-complete-marker); a partial copy could then pass


def refuse_science_mirror(path) -> None:
    """The input root may never be, or be under, a `snapshot-mirror` directory (science's alone, amendment 29(c)), by its name or through a link."""
    p = Path(path)
    for q in (p.absolute(), p.resolve()):
        if SCIENCE_MIRROR in q.parts:
            raise PlanError(f"{path} is under {SCIENCE_MIRROR}/, which is the science agent's alone: the coders read their own mirror "
                            f"({DEFAULT_INPUT_ROOT})")


def _tree_size(d: Path) -> tuple[int, int]:
    """(files, bytes) of the regular files below a directory, as `snapshot.fetch.measure` counts them for the marker: a link is neither counted nor followed."""
    n = b = 0
    for root, _dirs, files in os.walk(d):
        for f in files:
            st = (Path(root) / f).lstat()
            if stat.S_ISREG(st.st_mode):
                n += 1
                b += st.st_size
    return n, b


def _first_int(d: dict, keys) -> int | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
            return v
    return None


class StoreRunSource:
    """Finished-or-not for each planned run, from the store's status, how its attempt ended, and the run directory's own pull marker, and from
    nothing else (science, #34, 3 Nov 00:18Z: never the record's label). The input is lane-snap's mirror for the coders, `input_root`
    (default `DEFAULT_INPUT_ROOT`): `state.sqlite` directly under it, replaced atomically by rename (so it is opened afresh at the start of each
    pass and never held across one), and the run directories at their recorded paths below it (`strip_prefix` drops a leading part of the recorded path
    first). `snapshot.fetch` prepends its destination to `run_dir` in that copy and says so in `meta` (`FETCH_PREFIX_KEY`): that prefix comes off first, or every
    run would be looked for at <root>/<root>/... and read as having no marker, for good. `check(item)` returns (state, run_dir or why):
    - 'finished': the store says `done`, the done attempt's termination is `report` (the agent ended with its final message), the run directory
      has a MARKER `<run_dir>.pulled.json` beside it (written by rename after that directory's copy succeeded) whose file count and byte count
      equal the directory's own, and the files a packet is built from are there. NO MARKER MEANS NOT FINISHED, whatever the directory holds.
    - 'mismatch': there is a marker and the directory does not match it (or the marker cannot be read): not finished, looked at again on the next
      pass, and counted apart in the pass's totals.
    - 'pending': not ended yet (pending, or re-queued after our own error), not in this snapshot of the store, or no marker yet.
    - 'terminal': ended without finishing (time cap, turn cap, token budget, error, infrastructure exhausted): no packet in the main block, never
      picked up.
    The marker's file count and byte count are read from the keys `files`/`file_count`/`n_files` and `bytes`/`total_bytes`/`size_bytes`
    (the marker's exact field names are lane-snap's). `NO_MARKER` (the runner's `--no-complete-marker`) skips the marker: tests only. An input root
    under a `snapshot-mirror` directory is refused."""

    def __init__(self, input_root=DEFAULT_INPUT_ROOT, *, strip_prefix=None, marker=None, mirror_roots=(), hold_keys_file=None):
        refuse_science_mirror(input_root)
        roots = []
        for m in mirror_roots:
            refuse_science_mirror(m)
            norm = os.path.normpath(os.path.abspath(str(m)))          # one spelling: absolute, no `.`, `..` or trailing slash; the recorded paths are compared in it
            roots.append((norm, os.path.realpath(norm)))
        self.root, self.strip_prefix, self.marker = Path(input_root), strip_prefix, marker
        self.mirror_roots = tuple(roots)
        self.hold_keys_file = Path(hold_keys_file) if hold_keys_file else None
        self._held: frozenset = frozenset()
        self.n_held = 0
        self.store_path = self.root / "state.sqlite"
        self._runs: dict = {}
        self._fetch_prefix = None

    def begin_pass(self) -> None:
        refuse_science_mirror(self.root)
        if not self.store_path.is_file():
            raise PlanError(f"no store snapshot at {self.store_path}")
        db = sqlite3.connect(f"file:{self.store_path}?mode=ro", uri=True, timeout=30)       # opened afresh every pass: the file is replaced by rename
        try:
            runs = dict(db.execute("SELECT run_key, status FROM runs").fetchall())
            done = {r[0]: (r[1], r[2]) for r in db.execute(
                "SELECT run_key, termination, run_dir FROM attempts WHERE state='done' ORDER BY attempt")}
            has_meta = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()
            row = db.execute("SELECT value FROM meta WHERE key=?", (FETCH_PREFIX_KEY,)).fetchone() if has_meta else None
        except sqlite3.Error as e:
            raise PlanError(f"store snapshot {self.store_path}: {type(e).__name__}: {e}") from e
        finally:
            db.close()
        self._runs = {k: (st, *done.get(k, (None, None))) for k, st in runs.items()}
        self._fetch_prefix = row[0] if row else None
        if self.hold_keys_file is not None:         # read afresh every pass; a named file that cannot be read is an error, never "nothing held"
            try:
                text = self.hold_keys_file.read_text()
            except (OSError, ValueError) as e:                  # ValueError: not text (UnicodeDecodeError)
                raise PlanError(f"hold-keys file {self.hold_keys_file}: {type(e).__name__}: {e}") from e
            self._held = frozenset(ln.strip() for ln in text.splitlines() if ln.strip())
            self.n_held = len(self._held & self._runs.keys())

    def run_dir_of(self, run_key: str, recorded: str) -> Path:
        path = str(recorded)
        norm = os.path.normpath(path) if os.path.isabs(path) else None
        for m, real in self.mirror_roots:
            if norm is not None and norm.startswith(m.rstrip("/") + "/"):
                # a merged store (snapshot.bmerge): a run made elsewhere is recorded under ITS mirror, a path on this host as it stands
                return self._inside(run_key, recorded, Path(norm), real)
        if self._fetch_prefix and path.startswith(self._fetch_prefix):
            path = path[len(self._fetch_prefix):]                        # back to the path on the run host, which is where the directory sits below the root
        rel = Path(path).relative_to(self.strip_prefix) if self.strip_prefix else Path(path.lstrip("/"))
        return self._inside(run_key, recorded, self.root / rel, os.path.realpath(self.root))

    @staticmethod
    def _inside(run_key: str, recorded: str, d: Path, real_root: str) -> Path:
        """`d` unchanged, if it stays inside `real_root` once `..` and links are followed and is not under the science agent's mirror; else a PlanError (a
        run is never read from outside its mirror, and a path that climbs out is a store or a mirror that is wrong, so the pass stops)."""
        there, top = os.path.realpath(d), real_root.rstrip("/")
        if there != top and not there.startswith(top + "/"):
            raise PlanError(f"run {run_key}: the recorded directory {recorded} leaves its root {real_root} ('..' or a link): refusing to read it")
        refuse_science_mirror(d)
        return d

    def is_held(self, run_key: str) -> bool:
        return run_key in self._held

    def marker_state(self, d: Path) -> tuple[str, str]:
        """('ok' | 'missing' | 'mismatch', why) for a run directory's pull marker."""
        m = d.with_name(d.name + PULLED_SUFFIX)
        if not m.is_file():
            return "missing", f"no {PULLED_SUFFIX} marker beside the run directory"
        try:
            info = json.loads(m.read_text())
        except (OSError, ValueError):
            return "mismatch", "the pull marker cannot be read"
        files = _first_int(info, ("files", "file_count", "n_files")) if isinstance(info, dict) else None
        size = _first_int(info, ("bytes", "total_bytes", "size_bytes")) if isinstance(info, dict) else None
        if files is None or size is None:
            return "mismatch", "the pull marker holds no file count and byte count"
        if not d.is_dir():
            return "mismatch", "there is a marker and no run directory"
        n, b = _tree_size(d)
        if (n, b) != (files, size):
            return "mismatch", f"the marker says {files} files and {size} bytes, the directory holds {n} and {b}"
        return "ok", ""

    def check(self, item: dict) -> tuple[str, object]:
        rk = item["run_key"]
        if rk in self._held:
            return PENDING, "held: started on two providers, the merge decides which copy counts (science, #34 17:00Z)"
        if rk not in self._runs:
            return PENDING, "not in this snapshot of the store"
        status, termination, recorded = self._runs[rk]
        if status == "done":
            if termination != "report":
                return TERMINAL, f"ended by {termination}"
            if not recorded:
                return PENDING, "no run directory recorded"
            d = self.run_dir_of(rk, recorded)
            if self.marker is not NO_MARKER:
                st, why = self.marker_state(d)
                if st == "missing":
                    return PENDING, why
                if st == "mismatch":
                    return MISMATCH, why
            missing = [f for f in RUN_FILES if not (d / f).is_file()]
            if missing:
                return PENDING, f"the run directory has not arrived complete (missing {missing})"
            return FINISHED, d
        if status == "infra_exhausted":
            return TERMINAL, "infrastructure exhausted"
        return PENDING, f"status {status}"


# ----------------------------------------------------------------------------- sealing

class SealError(RuntimeError):
    """The sealed directory cannot be sealed: the run is refused."""


SEAL_MARKER = ".sealed"


def is_sealed(path) -> bool:
    return (Path(path) / SEAL_MARKER).is_file()


def require_unsealed(path, unseal: bool) -> None:
    """A tool that would read a sealed directory refuses it unless told, explicitly, to unseal (after the main block)."""
    if is_sealed(path) and not unseal:
        raise SealError(f"{path} is sealed (the main block's per-packet answers): --unseal reads it, and under amendment 29(c) only the science agent "
                        "runs snapshots and reads their tables (an instruction, not a lock)")


def seal_dir(path, plan_sha256: str) -> Path:
    """Create (or re-check) the sealed directory: mode 700, owned by us, no link inside, nothing readable by group or others, a marker naming the
    plan. A file that cannot be sealed raises SealError and the run does not start."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except OSError as e:
        raise SealError(f"{path}: cannot set mode 700: {e}") from e

    def check(p: Path, *, tighten: bool) -> None:
        st = p.lstat()
        if stat.S_ISLNK(st.st_mode):
            raise SealError(f"{p} is a link: nothing can be sealed through one")
        if st.st_uid != os.getuid():
            raise SealError(f"{p} is not ours")
        if st.st_mode & 0o077:
            if tighten:
                try:
                    os.chmod(p, st.st_mode & ~0o077)
                except OSError as e:
                    raise SealError(f"{p}: cannot be sealed: {e}") from e
            if p.lstat().st_mode & 0o077:
                raise SealError(f"{p} is still readable by group or others (mode {oct(p.lstat().st_mode & 0o777)}) and cannot be sealed")
    check(path, tighten=False)
    for root, dirs, files in os.walk(path):
        for n in dirs + files:
            check(Path(root) / n, tighten=True)
    marker = path / SEAL_MARKER
    if marker.is_file():
        if json.loads(marker.read_text()).get("plan_sha256") != plan_sha256:
            raise SealError(f"{path} was sealed for another plan: use a new directory for a new plan")
    else:
        _atomic_write(marker, json.dumps({"format": "icsa-inspection-sealed-v1", "plan_sha256": plan_sha256, "created": _now()}) + "\n")
        os.chmod(marker, 0o600)
    if not os.access(path, os.W_OK | os.X_OK):
        raise SealError(f"{path} cannot be written")
    return path


class SealedLog:
    """The per-packet log: lines that name a packet, kept under the sealed directory and nowhere else."""

    def __init__(self, sealed):
        self.path, self._lock = Path(sealed) / "run.log", threading.Lock()

    def __call__(self, line: str) -> None:
        with self._lock, self.path.open("a") as fh:
            fh.write(f"{_now()} {line}\n")


# ----------------------------------------------------------------------------- packets built by the runner, and the report's key

def packet_id_for(plan: dict, run_key: str) -> str:
    """The opaque id of a run's packet: a keyed hash of its run key under a secret from the plan's seed. The same on every pass."""
    from . import packet, queue
    return packet.packet_id(queue.id_secret(plan["seed"]), run_key)


def item_row(item: dict) -> dict:
    """The row `queue.identifiers` wants for a planned run, from its key alone: `<block>__<instance>__<option>__<layout>__<model>__s<seed>`."""
    block, rest = item["run_key"].split("__", 1)
    return {"run_key": item["run_key"], "instance_id": rest.split("__", 1)[0], "model": item["model"], "key": rest}


def identifiers_for(plan: dict, item: dict, run_dir) -> dict:
    """What to sanitise in one run's packet: its run key and directory, its instance and every other scenario name of the plan, every model name."""
    from . import queue
    instances = sorted({i["run_key"].split("__", 2)[1] for i in plan["order"]})
    models = sorted({i["model"] for i in plan["order"]})
    return queue.identifiers({**item_row(item), "run_dir": str(run_dir)}, instance_ids=instances, model_names=models)


def plan_c_rates(plan: dict, cell_size) -> dict:
    """The per-cell rate of set C's hash rule (science, #34, 4 Nov 18:53Z): the planned C size of a cell over the plan's planned SEED-1 runs of that
    cell, at most 1. The projected population is the plan's own (the campaign runs seed 1 first, and its starts by the cut come close to the plan's
    count), never what has finished. A cell with no planned seed-1 run is refused: it would have no rate."""
    if isinstance(cell_size, bool) or not isinstance(cell_size, (int, float)) or cell_size <= 0:
        raise PlanError(f"the cell size must be positive, not {cell_size!r}")
    cells, seed1 = set(), Counter()
    for it in plan["order"]:
        c = (str(it["option"]), str(it["layout"]))
        cells.add(c)
        seed1[c] += it["run_key"].rsplit("__", 1)[-1] == "s1"
    empty = sorted(c for c in cells if not seed1[c])
    if empty:
        raise PlanError(f"no seed-1 run is planned in cell {empty[0][0]} x {empty[0][1]}: it would have no C rate")
    return {c: min(1.0, cell_size / seed1[c]) for c in sorted(cells)}


def build_report_key(sealed, plan: dict, population: list[dict], *, c_main_per_cell: int = 15, seed=None) -> dict:
    """AFTER the main block: the report's key, from the sealed packets and the population (the labels). Sets R and C are assigned here and only
    here, by `queue.assign_sets` over the plan's population. Set C is the order-stable hash rule (science, #34, 4 Nov 18:53Z): a decided run joins it when a
    seeded hash of its run key falls below its cell's rate, `plan_c_rates` of 2 x `c_main_per_cell` per cell (the planned complete + omitting), so membership
    depends on neither which runs finished nor which were coded; the realised sizes are in the strata. A coded run in
    neither set is coded and unused: counted (`coded_unused`). A run of R or C with no coded packet is a refused entry with its reason. Every entry
    carries its sealed directory, so that `report.decisions` reads each packet's answers where they are."""
    from . import prompt, queue, rubric
    sealed = Path(sealed)
    seed = plan["seed"] if seed is None else seed
    rows = [r for r in population if r.get("phase") in PLAN_BLOCKS]
    cell_size = 2 * c_main_per_cell
    rates = plan_c_rates(plan, cell_size)
    sets, strata = queue.assign_sets(rows, seed=seed, c_main_per_cell=c_main_per_cell, c_rates=rates)
    by_run = {r["run_key"]: r for r in rows}
    metas = {f.stem: json.loads(f.read_text()) for f in sorted((sealed / "meta").glob("*.json"))}
    refused_why = {json.loads(f.read_text())["run_key"]: json.loads(f.read_text())["reason"] for f in sorted((sealed / "refused").glob("*.json"))}
    coded = {m["run_key"]: pid for pid, m in metas.items()}
    entries, unused = {}, 0
    for pid, m in sorted(metas.items()):
        rk = m["run_key"]
        s, r = sets.get(rk), by_run.get(rk)
        if s is None or r is None:
            unused += pair_path(sealed, pid).is_file()          # a packet with a pair record, in neither set: coded and unused
            continue
        entries[pid] = {**m, **s, "label": r.get("label"), "decoded_not_delivered": r.get("decoded_not_delivered"),
                        "_work": str(sealed), "_packets_dir": str(sealed / "packets")}
    refused = []
    for rk, s in sorted(sets.items()):
        if rk in coded or rk not in by_run or rk not in {i["run_key"] for i in plan["order"]}:
            continue
        r = by_run[rk]
        refused.append({"run_key": rk, **s, "phase": r["phase"], "instance_id": r.get("instance_id"), "option": r.get("option"),
                        "layout": r.get("layout"), "model": r.get("model"), "seed": r.get("seed"), "label": r.get("label"),
                        "reason": refused_why.get(rk, "no packet was coded for this run in the main block (not finished, terminal, or not picked up)")})
    unlabelled = [{"run_key": r["run_key"], "phase": r["phase"], "option": r.get("option"), "layout": r.get("layout"), "model": r.get("model"),
                   "reason": r.get("unlabelled_reason"), "time_capped": bool(r.get("time_capped")), "set": sets.get(r["run_key"], {}).get("set")}
                  for r in rows if r.get("unlabelled")]
    rub = rubric.info()
    return {"format": queue.FORMAT_KEY, "seed": seed, "rubric": rub, "prompt_sha256": prompt.prompt_sha256(), "c_main_per_cell": c_main_per_cell,
            "c_main_strata": strata, "c_rule": {"kind": "seeded hash of the run key", "cell_size": cell_size,
                                                "rates": {f"{o}|{l}": r for (o, l), r in rates.items()}},
            "packets": entries, "refused": refused, "unlabelled": sorted(unlabelled, key=lambda u: u["run_key"]),
            "coded_unused": unused, "coded_packets": sum(pair_path(sealed, pid).is_file() for pid in metas)}


def merge_keys(base: dict | None, main: dict) -> dict:
    """The gate's key (set K, the pilot: `--key`) and the main block's, one key for the report. Packet ids never collide (both are keyed hashes)."""
    if base is None:
        return main
    clash = set(base["packets"]) & set(main["packets"])
    if clash:
        raise PlanError(f"packet ids in both keys: {sorted(clash)[:3]}")
    if base.get("prompt_sha256") != main.get("prompt_sha256"):
        raise PlanError("the two keys were made under different prompts")
    return {**base, "packets": {**base["packets"], **main["packets"]}, "refused": [*base.get("refused", []), *main["refused"]],
            "unlabelled": [*base.get("unlabelled", []), *main["unlabelled"]],
            "c_main_strata": base.get("c_main_strata") or main["c_main_strata"], "c_rule": main.get("c_rule"), "coded_unused": main["coded_unused"],
            "coded_packets": main["coded_packets"]}


def main_inputs(plan_path, sealed, population_path, work, *, key_path=None, unseal: bool = False, c_main_per_cell: int = 15,
                now: float | None = None):
    """For `report` and `coverage`, AFTER the main block: (key, pair plan, population) from the sealed directory. Refuses a sealed directory
    unless `unseal`."""
    from . import queue
    require_unsealed(sealed, unseal)
    plan = load_plan(plan_path)
    population = queue.read_population(population_path)
    key = build_report_key(sealed, plan, population, c_main_per_cell=c_main_per_cell)
    if key_path:
        key = merge_keys(json.loads(Path(key_path).read_text()), key)
    return key, PairPlan(plan, sealed, key, gate_dir=Path(work) / "quota", now=now), population


# ----------------------------------------------------------------------------- CLI

def _write_json(path, obj) -> None:
    _atomic_write(Path(path), json.dumps(obj, indent=1, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.inspection.plan", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="the seeded order over the PLANNED matrix, written once")
    src = b.add_mutually_exclusive_group(required=True)
    src.add_argument("--campaign-root", help="holds state.sqlite: its runs table's plan columns are read (never a status)")
    src.add_argument("--planned", help="JSONL of plan rows (run_key, block, instance_id, option, layout, model, seed)")
    b.add_argument("--seed", default=str(CODING_SEED), help="the coding order's seed (default: amendment 30(l)'s); the plan records it")
    b.add_argument("--out", required=True)
    b.add_argument("--stop-at", default=DEFAULT_STOP_AT,
                   help="coding stops here, UTC (amendment 29(c): 6 Nov 06:00Z): no new dispatch after it; fixed in the plan file, so a second build "
                        "with another time refuses")
    b.add_argument("--allow-after-results", action="store_true",
                   help="build although the store shows runs past pending (the order should be fixed before the results exist)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "build":
            progress = None
            if a.campaign_root:
                rows, progress = planned_from_store(a.campaign_root)
                past = sum(n for s, n in progress.items() if s != "pending")
                if past and not Path(a.out).exists() and not a.allow_after_results:
                    raise PlanError(f"{past} in-scope run(s) are already past pending in the store: the order must be fixed before the "
                                    "main block's results exist (--allow-after-results to build anyway; it is recorded)")
            else:
                rows = [json.loads(x) for x in Path(a.planned).read_text().splitlines() if x.strip()]
            seed = int(a.seed) if a.seed.lstrip("-").isdigit() else a.seed
            plan = build_plan(rows, seed, stop_at=a.stop_at)
            how = write_plan(plan, a.out)
            if how == "created":
                _write_json(Path(a.out).with_name(Path(a.out).name + ".provenance.json"),
                            {"built_at": _now(), "source": a.campaign_root or a.planned, "store_statuses_in_scope": progress,
                             "plan_sha256": plan["plan_sha256"]})
            print(json.dumps({"plan": how, "plan_sha256": plan["plan_sha256"], "order_sha256": plan["order_sha256"],
                              "n_planned": plan["n_planned"], "sections": plan["sections"], "stop_at": plan["stop_at"]}, sort_keys=True))
    except (PlanError, GateError, OSError, ValueError, KeyError) as e:
        print(f"icsa.inspection.plan: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
