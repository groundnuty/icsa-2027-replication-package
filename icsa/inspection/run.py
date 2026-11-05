"""Resumable runner: both coders over the queue's packets. Reads only the packet directory (never the key).

    python -m icsa.inspection.run --packets <dir> --work <dir> [--coders codex claude]
        [--max-attempts 3] [--claude-workers 4] [--limit N]

The main block's coding plan (amendment 26, `plan.py`): the same coders, each run's second coder chosen when it is dispatched.

    python -m icsa.inspection.run --packets <dir> --work <dir> --plan plan.json --dispatch dispatch.json
        [--codex-workers N] [--claude-workers N] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import coders as cm
from . import isolation, packet, prompt
from . import plan as P

DEFAULT_QUEUE = "inspection_operator_queue.json"       # under <work>/quota/: the runner's OWN queue file, named apart from the campaign's operator_queue.json


def _line(f: dict, extra: str = "") -> str:
    u = f["usage"]
    return (f"{f['packet']} {f['coder']} {f['status']} attempts={f['attempts']} contaminated={f['contaminated_attempts']} "
            f"in={u['input_tokens']} cached={u['cached_input_tokens']} out={u['output_tokens']} "
            f"reason={u['reasoning_tokens']} wall={f['wall_s']:.0f}s cost={f['cost_usd']}{extra}")


def code_one(pid: str, coder: str, backend, packets_dir, work_dir, *, max_attempts: int = 3,
             codex_price_per_mtok: dict | None = None) -> dict | None:
    """One coder on one packet, resumably. None when a final answer for this packet text, model and effort is already on disk; a final
    for another text, model or effort is kept as `final.stale-N.json` and never reused."""
    packets_dir, work_dir = Path(packets_dir), Path(work_dir)
    text = (packets_dir / f"{pid}.txt").read_text()
    fin = work_dir / "answers" / pid / coder / "final.json"
    if fin.exists():
        try:
            old = json.loads(fin.read_text())
        except json.JSONDecodeError:
            old = {}
        if (old.get("message_sha256"), old.get("model"), old.get("effort")) == (
                prompt.message_sha256(text), backend.model, backend.effort):
            return None
        j = 1  # stale: another packet text, model or effort; keep it, never reuse it
        while fin.with_name(f"final.stale-{j}.json").exists():
            j += 1
        fin.rename(fin.with_name(f"final.stale-{j}.json"))
    lines = {int(k): v for k, v in json.loads((packets_dir / f"{pid}.lines.json").read_text()).items()}
    return cm.code_packet(pid, text, lines, backend, work_dir, max_attempts=max_attempts, codex_price_per_mtok=codex_price_per_mtok)


def run_queue(packets_dir, work_dir, coders=("codex", "claude"), backends=None, *, max_attempts: int = 3,
              claude_workers: int = 4, codex_workers: int = 1, limit: int | None = None,
              codex_price_per_mtok: dict | None = None, codex_client: str = "cli", out=print) -> list[dict]:
    if not 1 <= codex_workers <= isolation.MAX_PARALLEL:
        raise SystemExit(f"--codex-workers must be 1..{isolation.MAX_PARALLEL} (this host's memory)")
    packets_dir, work_dir = Path(packets_dir), Path(work_dir)
    queue = json.loads((packets_dir / "queue.json").read_text())
    if queue["prompt_sha256"] != prompt.prompt_sha256():
        raise SystemExit("refusing to run: the prompt changed after the packets were queued "
                         f"({queue['prompt_sha256'][:12]} != {prompt.prompt_sha256()[:12]})")
    backends = backends or cm.default_backends(codex_client, coders)
    pre = {}
    for c in coders:                      # an isolated coder that cannot be set up stops the run before any call
        pf = getattr(backends[c], "preflight", None)
        if pf:
            pre[c] = pf()
    cm.archive_prompt(work_dir)
    if pre:
        (work_dir / "prompt" / "isolation-preflight.json").write_text(json.dumps(pre, indent=1))
    pids = queue["order"][:limit] if limit else queue["order"]
    done: list[dict] = []
    lock = threading.Lock()
    stop = threading.Event()

    def one(pid: str, coder: str) -> None:
        if stop.is_set():
            return
        try:
            f = code_one(pid, coder, backends[coder], packets_dir, work_dir, max_attempts=max_attempts,
                         codex_price_per_mtok=codex_price_per_mtok)
        except isolation.IsolationError:
            stop.set()          # no further call starts; the error ends the run
            raise
        if f is None:
            return
        with lock:
            done.append(f)
            out(_line(f))

    # Codex: `codex_workers` isolated containers at once (1 = one at a time, in queue order); Claude: plain API calls.
    with ThreadPoolExecutor(max_workers=codex_workers) as xex, ThreadPoolExecutor(max_workers=claude_workers) as cex:
        futs = []
        if "codex" in coders:
            futs += [xex.submit(one, pid, "codex") for pid in pids]
        for c in ("claude", "sonnet"):      # plain API calls, one pool
            if c in coders:
                futs += [cex.submit(one, pid, c) for pid in pids]
        for fu in futs:
            fu.result()
    by = {}
    for f in done:
        by.setdefault((f["coder"], f["status"]), 0)
        by[(f["coder"], f["status"])] += 1
    out(f"summary: {len(done)} finished; " + ", ".join(f"{c}/{s}={n}" for (c, s), n in sorted(by.items())))
    return done


def default_builder(item: dict, run_dir, identifiers: dict, pid: str) -> dict:
    """A planned run's packet, straight from its run directory: no label, set, option, model or answer in it or in its metadata."""
    return packet.build(run_dir, identifiers, strict=False)


def _prepare(plan: dict, sealed: Path, entry: dict, run_dir, builder, log) -> bool:
    """The run's packet, built once and kept in the sealed directory. False (and a sealed `refused` note) when it cannot be built: that is final."""
    pid, item = entry["packet"], entry["item"]
    if (sealed / "packets" / f"{pid}.txt").is_file() and (sealed / "meta" / f"{pid}.json").is_file():
        return True
    try:
        pk = builder(item, run_dir, P.identifiers_for(plan, item, run_dir), pid)
    except packet.PacketError as e:
        P._atomic_write(sealed / "refused" / f"{pid}.json", json.dumps({"run_key": item["run_key"], "reason": str(e)[:500]}) + "\n")
        log(f"{pid} packet refused: {str(e)[:200]}")
        return False
    P._atomic_write(sealed / "packets" / f"{pid}.lines.json", json.dumps({str(k): v for k, v in pk["lines"].items()}))
    P._atomic_write(sealed / "packets" / f"{pid}.txt", pk["text"])
    rest = item["run_key"].split("__", 1)[1].split("__")
    P._atomic_write(sealed / "meta" / f"{pid}.json", json.dumps({
        "run_key": item["run_key"], "phase": item["block"], "position": entry["position"], "instance_id": rest[0], "option": item["option"],
        "layout": item["layout"], "model": item["model"], "seed": int(rest[-1][1:]) if rest[-1][1:].isdigit() else None,
        "packet_sha256": pk["sha256"], "cells": pk["cells"], "cues": pk["cues"], "tokens": pk["tokens"]}, sort_keys=True, default=str) + "\n")
    return True


def _scan_totals(sealed: Path) -> dict:
    """What the sealed directory already holds: runs whose recorded pair has both finals, and the tokens of every final."""
    packets, tok = 0, {}
    for pf in sorted(sealed.glob("answers/*/pair.json")):
        rec = json.loads(pf.read_text())
        if not rec.get("pair"):
            continue
        finals = []
        for coder in rec["pair"]:
            fp = pf.parent / coder / "final.json"
            if fp.is_file():
                finals.append(json.loads(fp.read_text()))
        packets += len(finals) == len(rec["pair"])
        for f in finals:
            t = tok.setdefault(f["coder"], {"input": 0, "output": 0})
            t["input"] += f["usage"]["input_tokens"]
            t["output"] += f["usage"]["output_tokens"]
    return {"packets": packets, "tokens": tok}


def _coded_whole(sealed: Path, pid: str) -> bool:
    """Both coders of the run's recorded pair have a final answer file."""
    rec = P.read_pair(sealed, pid)
    return bool(rec and rec["pair"]) and all((sealed / "answers" / pid / c / "final.json").is_file() for c in rec["pair"])


def run_plan(plan_path, work_dir, sealed_dir, source, backends=None, *, builder=None, max_attempts: int = 3, claude_workers: int = 4,
             codex_workers: int = 6, limit: int | None = None, codex_price_per_mtok: dict | None = None, out=print,
             sol_poll_s: float = 0.2, notify_queue=None, sink=None, gate_wait_s: float = P.GATE_WAIT_S, probe_s: float = P.PROBE_S,
             probe_slow_s: float = P.PROBE_SLOW_S, clock=None, post_retry_s: float = P.POST_RETRY_S, touch_s: float = P.TOUCH_S,
             max_packets: int | None = None, totals_every: int = 50, sonnet_hard_stop: float = P.SONNET_HARD_STOP_PERCENT) -> dict:
    """ONE PASS of the main block's coding plan (amendment 26 and the gate of science, #76, 3 Nov 00:02Z; the schedule of #34, 3 Nov 00:18Z).
    `plan.py` has the rule; this is how a pass works.

    The pass walks the fixed order from its first position. For each planned run: a run with a pair record in the sealed directory is finished off
    from it, whatever the gate says now; a run the `source` says is not finished is skipped IN PLACE (counted, picked up on a later pass); a
    terminal one is never picked up; a finished one gets its packet built here (`packet.build`: no label anywhere) and is dispatched. The ONLY
    thing read about a run is finished-or-not (`plan.StoreRunSource`); the pass codes every finished run, whatever it is labelled.

    A run's pair is decided when it is dispatched, from the quota gate alone, and written to `<sealed>/answers/<packet>/pair.json` before any
    call. Gate open: Sol + Opus. Gate holding (it closed at 95, on a limit error or blind): no new dispatch at all, for `gate_wait_s`, while a
    keeper thread posts the closing once (`notify_queue`, the runner's own operator-queue file, or an injected `sink`) and probes the quota
    through the real launcher every `probe_s`; a reading below 95 reopens Sol, with no pair changed. No reset in the wait: the gate switches, the
    next dispatches take Opus + Sonnet, and a Sonnet subject run is DEFERRED, never given Opus + Sonnet: it has no record, waits for Sol, and is
    dispatched with Sol, ahead of the rest, if a probe sees a reset. A run already dispatched keeps its recorded pair always. A pass that starts
    with the gate not open looks first (a probe), because the limit may have been reset since the last one.
    Opus codes every run that has a pair. A Sol call that meets a limit error and never gives a valid answer moves a run that is not a Sonnet
    subject to Opus + Sonnet, reason recorded (`plan.reassign_if_quota_failed`). The Codex coder is always the CLI in its isolation container.

    Sealed: every per-packet file and line is under `sealed_dir` (mode 700; a file that cannot be sealed refuses the run), the gate's full log
    (one line per Sol attempt) included. `out`, the gate's public files (`gate.json`, `plan-events.jsonl`) and the operator queue carry TOTALS only:
    packets coded, tokens, quota readings, a line of them per pass and every `totals_every` coded packets; the gate's own events; and, for the
    runs waiting for Sol, only that "some planned runs are waiting" (the count is sealed). `max_packets` stops new dispatch once that many runs
    have been dispatched in all (a small real smoke run); `limit` caps the new dispatches of one pass. Returns a summary (its lists name
    packets: for the caller, never written outside the sealed directory)."""
    if not 1 <= codex_workers <= isolation.MAX_PARALLEL:
        raise SystemExit(f"--codex-workers must be 1..{isolation.MAX_PARALLEL} (this host's memory)")
    if claude_workers < 1:
        raise SystemExit("--claude-workers must be at least 1")
    work_dir, sealed = Path(work_dir), Path(sealed_dir)
    if work_dir.resolve() == sealed.resolve():
        raise SystemExit("the sealed directory must not be the public work directory")
    plan = P.load_plan(plan_path)
    try:
        P.seal_dir(sealed, plan["plan_sha256"])
    except P.SealError as e:
        raise SystemExit(f"refusing to run: {e}") from e
    for d in ("packets", "meta", "refused", "answers"):
        (sealed / d).mkdir(exist_ok=True, mode=0o700)
    packets_dir = sealed / "packets"
    log = P.SealedLog(sealed)
    builder = builder or default_builder
    backends = backends or cm.default_backends("cli", ("codex", "claude", "sonnet"))
    lacking = [c for c in ("codex", "claude", "sonnet") if c not in backends]
    if lacking:
        raise SystemExit(f"the plan needs the coders codex, claude and sonnet; no backend for {lacking}")
    pre = {}
    for c in ("codex", "claude", "sonnet"):       # an isolated coder that cannot be set up stops the run before any call
        pf = getattr(backends[c], "preflight", None)
        if pf:
            pre[c] = pf()
    work_dir.mkdir(parents=True, exist_ok=True)
    cm.archive_prompt(work_dir)
    if pre:
        (work_dir / "prompt" / "isolation-preflight.json").write_text(json.dumps(pre, indent=1))
    clock = clock or time.time
    stop_epoch = P._epoch(plan["stop_at"])             # fixed in the plan file before any main run (amendment 29(c)); never read from a run
    stopped_by_time = threading.Event()
    capped = threading.Event()

    def past_stop() -> bool:
        return clock() >= stop_epoch
    gate = P.QuotaGate(work_dir, plan, clock=clock, wait_s=gate_wait_s, probe_s=probe_s, probe_slow_s=probe_slow_s, private=sealed,
                       sonnet_hard_stop=sonnet_hard_stop)
    slots = P.SolSlots(codex_workers, gate, sol_poll_s)
    if sink is None:
        notify_queue = notify_queue or work_dir / "quota" / DEFAULT_QUEUE
        sink = P.OperatorQueue(notify_queue)
    can_probe = hasattr(backends["codex"], "probe")

    def probe():
        slots.acquire(force=True)                         # a probe is one container's worth of memory, like a Sol call
        try:
            return backends["codex"].probe(P.PROBE_MESSAGE)
        finally:
            slots.release()
    keeper = P.GateKeeper(gate, probe=probe if can_probe else None, sink=sink, clock=clock, post_retry_s=post_retry_s, touch_s=touch_s, out=out)
    gate.audit("pass_start", wait_s=gate_wait_s, probe_s=probe_s, probe_slow_s=probe_slow_s, codex_workers=codex_workers,
               claude_workers=claude_workers, mode=gate.mode, limit=limit, sonnet_hard_stop=sonnet_hard_stop)
    if not gate.is_open and not past_stop():          # a pass after a closing starts by looking: the operator may have reset the limit since the last one
        keeper._do_probe(clock())
        keeper.tick()
    # -- what is there to do: finished-or-not, from the source alone
    source.begin_pass()
    held_of = getattr(source, "is_held", None)
    counts = Counter()
    resumed: list[dict] = []
    todo: list[dict] = []
    for pos, item in enumerate(plan["order"]):
        pid = P.packet_id_for(plan, item["run_key"])
        entry = {"packet": pid, "position": pos, "section": item["section"], "model": item["model"],
                 "subject_sonnet": P.is_sonnet_subject(item["model"]), "item": item}
        if P.read_pair(sealed, pid) is not None:
            if held_of is not None and held_of(item["run_key"]):
                counts["not_yet_ended"] += 1          # a hold stands over a run being finished off as well; its recorded pair waits with it
                continue
            resumed.append(entry)
            continue
        if (sealed / "refused" / f"{pid}.json").is_file():
            counts["refused"] += 1
            continue
        state, info = source.check(item)
        if state == P.PENDING:
            counts["not_yet_ended"] += 1
        elif state == P.MISMATCH:                 # a copy that does not match its marker: not finished, looked at again, counted in the totals
            counts["marker_mismatch"] += 1
        elif state == P.TERMINAL:
            counts["terminal"] += 1
        else:
            entry["run_dir"] = info
            todo.append(entry)
    if limit:
        todo = todo[:limit]
    done: list[dict] = []
    summary = {"pairs": {}, "deferred_sonnet_subject": [], "reassigned": [], "sonnet_subject_sol_quota_failed": [], "dispatched": 0,
               "not_yet_ended": counts["not_yet_ended"], "terminal": counts["terminal"], "refused": counts["refused"], "resumed": len(resumed),
               "marker_mismatch": counts["marker_mismatch"]}
    lock = threading.Lock()
    stop = threading.Event()
    n_threads = max(codex_workers, claude_workers)
    inflight = threading.BoundedSemaphore(n_threads)
    totals = _scan_totals(sealed)          # what earlier passes coded: the totals lines add this pass's work to it
    since_totals = [0]

    def emit_totals(why: str) -> None:
        """A totals line for the public log. Called with `lock` held, so that the lines come in the order of their counts."""
        lr = gate.snapshot()["last_reading"] or {}
        gate.audit("totals", why=why, packets_coded=totals["packets"], tokens=totals["tokens"], quota_used_percent=lr.get("used_percent"),
                   quota_window_end=lr.get("resets_at_iso"), quota_read_at=lr.get("t"))

    def say(f: dict, rec: dict) -> None:
        with lock:
            done.append(f)
            t = totals["tokens"].setdefault(f["coder"], {"input": 0, "output": 0})
            t["input"] += f["usage"]["input_tokens"]
            t["output"] += f["usage"]["output_tokens"]
        log(_line(f, f" pair={P.pair_name(rec['pair'])}"))           # a line that names a packet goes to the sealed log, nowhere else

    def assign(entry: dict) -> tuple[str, dict | None, bool]:
        """('assigned' | 'deferred' | 'refused' | 'retry' | 'stopped', record, whether a Sol slot is held) for a run with no record: decides its pair now and
        writes it before the run's first call. 'retry': the gate left `open` while the run waited for a slot."""
        if not _prepare(plan, sealed, entry, entry["run_dir"], builder, log):        # the packet first (it takes a moment): the pair is decided just before it is written
            return "refused", None, False
        mode = gate.mode
        held = False
        if mode != "open" and entry["subject_sonnet"] and gate.sonnet_sol_ok():
            # science, #34, 4 Nov 20:22Z: the gate closed at the threshold, and a Sonnet subject run goes on with Sol until the hard stop (it never gets Opus +
            # Sonnet). `force`: a slot, whatever the closed gate says; the exception is asked again once the slot is held, since the readings move meanwhile.
            held = slots.acquire(force=True)
            if stop.is_set() or past_stop():
                slots.release()
                if past_stop():
                    stopped_by_time.set()
                return "stopped", None, False
            if not gate.sonnet_sol_ok():
                slots.release()
                return "deferred", None, False
            snap = gate.snapshot()
            lr = snap["last_reading"] or {}
            rec = P.new_pair_record(entry, P.SOL_PAIR, snap, f"{P.SONNET_EXCEPTION_WHY} ({gate.sonnet_hard_stop:g}%; reading {lr.get('used_percent')}% at {lr.get('t')})")
            P.write_new_pair(sealed, rec)                 # durable BEFORE any call
            return "assigned", rec, held
        if mode == "open":
            held = slots.acquire()
            if stop.is_set() or past_stop():
                if held:
                    slots.release()
                if past_stop():
                    stopped_by_time.set()
                return "stopped", None, False
            if not held:
                return "retry", None, False
            pair, why = P.SOL_PAIR, "gate open"
        elif mode == "switched":
            if past_stop():
                stopped_by_time.set()
                return "stopped", None, False
            if entry["subject_sonnet"]:
                return "deferred", None, False
            pair = P.FALLBACK_PAIR
            c = gate.snapshot()["closed"] or {}
            why = f"gate switched (episode {gate.episode}, {c.get('reason')}): no reset within {gate_wait_s:g} s"
        else:
            return "retry", None, False                   # holding: no new dispatch of any kind
        snap = gate.snapshot()
        rec = P.new_pair_record(entry, pair, snap, why)
        P.write_new_pair(sealed, rec)                     # durable BEFORE any call
        return "assigned", rec, held

    def serve(entry: dict, rec: dict, held: bool) -> None:
        pid = entry["packet"]
        was_whole = _coded_whole(sealed, pid)
        try:
            P.guard_pair(rec)
            opus = cex.submit(code_one, pid, "claude", backends["claude"], packets_dir, sealed, max_attempts=max_attempts,
                              codex_price_per_mtok=codex_price_per_mtok)
            futs = [opus]
            if tuple(rec["pair"]) == P.SOL_PAIR:
                try:
                    f = code_one(pid, "codex", P.ReadingBackend(backends["codex"], gate, pid), packets_dir, sealed,
                                 max_attempts=max_attempts, codex_price_per_mtok=codex_price_per_mtok)
                except BaseException:
                    stop.set()                            # before the slot is released: the dispatcher starts nothing after an error
                    raise
                finally:
                    if held:
                        slots.release()
                        held = False
                if f is not None:
                    say(f, rec)
                rec, what = P.reassign_if_quota_failed(sealed, rec)
                with lock:
                    if what == "reassigned":
                        summary["reassigned"].append(pid)
                    elif what == "sonnet_subject_sol_quota_failed" or what == "sonnet_subject_not_reassigned":
                        summary["sonnet_subject_sol_quota_failed"].append(pid)
                if what:
                    log(f"{pid} codex: Codex limit error and no valid Sol answer: {what}")
            if tuple(rec["pair"]) == P.FALLBACK_PAIR:
                P.guard_pair(rec)
                futs.append(cex.submit(code_one, pid, "sonnet", backends["sonnet"], packets_dir, sealed, max_attempts=max_attempts,
                                       codex_price_per_mtok=codex_price_per_mtok))
            for fu in futs:
                f = fu.result()
                if f is not None:
                    say(f, rec)
            if not was_whole and _coded_whole(sealed, pid):
                with lock:
                    totals["packets"] += 1
                    since_totals[0] += 1
                    if since_totals[0] >= totals_every:
                        since_totals[0] = 0
                        emit_totals("every %d packets coded" % totals_every)
        except BaseException:
            stop.set()
            if held:
                slots.release()
            raise

    stop_keeper = threading.Event()

    def keep() -> None:
        while not stop_keeper.is_set():
            try:
                keeper.tick()
            except Exception as e:                        # noqa: BLE001 -- the keeper never stops the coding
                gate.audit("keeper_error", error=f"{type(e).__name__}: {e}"[:300])
            stop_keeper.wait(sol_poll_s)

    fresh = deque(todo)
    deferred: deque = deque()
    kt = threading.Thread(target=keep, name="gate-keeper", daemon=True)
    kt.start()
    try:
        with ThreadPoolExecutor(max_workers=n_threads) as wex, ThreadPoolExecutor(max_workers=claude_workers) as cex:
            futs = []

            def launch(entry, rec, held):
                summary["dispatched"] += 1
                fu = wex.submit(serve, entry, rec, held)
                fu.add_done_callback(lambda _f: inflight.release())
                futs.append(fu)

            n_resumed_started = 0
            for entry in resumed:                         # dispatched in an earlier pass: the recorded pair stands, whatever the gate says now
                inflight.acquire()
                if stop.is_set() or past_stop():          # after the coding stop nothing new starts, a resumed run included
                    inflight.release()
                    if past_stop():
                        stopped_by_time.set()
                    break
                n_resumed_started += 1
                try:
                    rec = P.read_pair(sealed, entry["packet"])
                    P.check_pair_record(rec, entry)
                    if not (packets_dir / f"{entry['packet']}.txt").is_file():
                        raise P.PairError(f"packet {entry['packet']} has a pair record but no packet text")
                    held = rec["pair"] is not None and tuple(rec["pair"]) == P.SOL_PAIR and slots.acquire(force=True)
                except BaseException:
                    inflight.release()
                    stop.set()
                    raise
                if rec["pair"] is None:
                    inflight.release()
                    continue
                launch(entry, rec, held)

            def pick():
                """('entry', entry, from_deferred) | 'wait' | 'done': the next run to dispatch, by the gate's mode NOW (after a slot is free, so a
                reset that came while the dispatcher waited sends the waiting Sonnet runs first)."""
                keeper.deferred = len(deferred)
                if max_packets is not None and summary["dispatched"] >= max_packets:       # a small real run: enough have been dispatched
                    capped.set()
                    return "done", None, False
                if past_stop():                           # amendment 29(c): no new dispatch after the stop; calls in flight finish
                    stopped_by_time.set()
                    return "done", None, False
                mode = gate.mode
                if mode == "open" and deferred:           # a reset: the Sonnet runs that waited go first, with Sol
                    return "entry", deferred.popleft(), True
                if mode != "open" and gate.sonnet_sol_ok():      # closed at the threshold, under the hard stop: the Sonnet subject runs go on, whatever holds the rest
                    for src, from_def in ((deferred, True), (fresh, False)):
                        for i, cand in enumerate(src):
                            if cand["subject_sonnet"]:
                                del src[i]
                                return "entry", cand, from_def
                if mode == "holding":                     # no new dispatch of any kind while the gate holds
                    return ("wait", None, False) if (fresh or deferred) else ("done", None, False)
                if fresh:
                    return "entry", fresh.popleft(), False
                return "done", None, False

            while not stop.is_set():
                inflight.acquire()
                if stop.is_set():
                    inflight.release()
                    break
                what, entry, from_deferred = pick()
                if what != "entry":
                    inflight.release()
                    if what == "done":
                        break
                    time.sleep(sol_poll_s)
                    continue
                try:
                    outcome, rec, held = assign(entry)
                except BaseException:
                    inflight.release()
                    stop.set()
                    raise
                if outcome == "assigned":
                    launch(entry, rec, held)
                    continue
                inflight.release()
                if outcome == "stopped":
                    (deferred if from_deferred else fresh).appendleft(entry)       # not dispatched: it is counted with what the stop leaves
                    break
                if outcome == "refused":
                    summary["refused"] += 1
                elif outcome == "deferred":
                    deferred.append(entry)
                else:                                     # retry, in its place
                    (deferred if from_deferred else fresh).appendleft(entry)
            for fu in futs:
                fu.result()
    finally:
        stop_keeper.set()
        kt.join()
    keeper.deferred = len(deferred)
    keeper.refresh()
    deferred_why = {e["packet"]: f"waiting for Sol: never given Opus + Sonnet; gate {gate.mode} at the end of the pass" for e in deferred}
    P.write_deferred(sealed, plan, deferred_why)
    summary["deferred_sonnet_subject"] = sorted(deferred_why)
    try:
        keeper.tick()                                     # a closing by the last Sol calls is posted before the pass ends
    except Exception as e:                                # noqa: BLE001
        gate.audit("keeper_error", error=f"{type(e).__name__}: {e}"[:300])
    still_waiting = bool(deferred or fresh or summary["not_yet_ended"] or summary["marker_mismatch"]) and not capped.is_set()
    summary["capped"] = capped.is_set()
    if stopped_by_time.is_set() or (past_stop() and (fresh or deferred)):
        unfinished = sum(1 for e in resumed[n_resumed_started:] if not _coded_whole(sealed, e["packet"]))      # a resumed run whose coders had not all answered
        left = {"finished_uncoded": len(fresh) + len(deferred) + unfinished, "not_yet_ended": summary["not_yet_ended"],
                "ended_unfinished": summary["terminal"], "no_packet": summary["refused"]}
        P.write_stopped(sealed, plan, left)
        gate.audit("coding_stopped", stop_at=plan["stop_at"], **left)
        summary["stopped"] = {"stop_at": plan["stop_at"], **left}
        still_waiting = False
        deferred = deque()                                # nothing waits for Sol any more: the count above says what is left
        keeper.deferred = 0
    if not deferred and not fresh:
        keeper.finish("the pass ended with nothing waiting for Sol")
    for f in sorted((sealed / "answers").glob("*/pair.json")):          # the records on disk are the truth: TOTALS by pair, nothing per run
        rec = json.loads(f.read_text())
        name = P.pair_name(rec["pair"]) or "uncoded"
        summary["pairs"][name] = summary["pairs"].get(name, 0) + 1
    snap = gate.snapshot()
    summary["gate"] = {"mode": snap["mode"], "state": snap["state"], "closed": snap["closed"], "episodes": snap["episodes"],
                       "last_reading": snap["last_reading"], "max_used_percent": snap["max_used_percent"],
                       "unposted_episodes": gate.unposted()}
    summary["still_waiting"] = still_waiting
    gate.audit("pass_end", dispatched=summary["dispatched"], some_waiting_for_sol=bool(deferred), not_yet_ended=summary["not_yet_ended"],
               marker_mismatch=summary["marker_mismatch"], terminal=summary["terminal"], mode=gate.mode, capped=capped.is_set())
    with lock:
        emit_totals("end of the pass")
    tok = {}
    for f in done:
        t = tok.setdefault(f["coder"], {"input": 0, "output": 0})
        t["input"] += f["usage"]["input_tokens"]
        t["output"] += f["usage"]["output_tokens"]
    lr = snap["last_reading"] or {}
    out(f"pass: {summary['dispatched']} dispatched now ({summary['resumed']} finished off from their records), {sum(summary['pairs'].values())} coded in all "
        f"{summary['pairs']}; not yet ended {summary['not_yet_ended']}, copies not matching their marker {summary['marker_mismatch']}, ended unfinished "
        f"{summary['terminal']}, no packet {summary['refused']}; "
        f"{'some planned runs are waiting for Sol; ' if deferred else ''}tokens this pass {tok}; quota reading {lr.get('used_percent')}% (window ends {lr.get('resets_at_iso')}); "
        f"gate {snap['mode']}, {len(snap['episodes'])} closing(s)")
    if summary.get("stopped"):
        st = summary["stopped"]
        out(f"coding stopped at {st['stop_at']} (the plan's fixed time): {st['finished_uncoded']} finished run(s) left uncoded, {st['not_yet_ended']} not "
            f"finished by then, {st['ended_unfinished']} ended unfinished; they stay as the instrument left them")
    if capped.is_set():
        out(f"stopped at --max-packets {max_packets}: {summary['dispatched']} dispatched in all")
    if summary["reassigned"]:
        out("some run(s) were moved to Opus + Sonnet after a Codex limit error with no valid Sol answer")
    if deferred and not summary.get("stopped"):
        out(f"ALARM: the gate is closed ({snap['mode']}) and some planned runs are NOT CODED, waiting for Sol: a run of that kind is never given "
            "Opus + Sonnet. Run another pass after a reset; if the plan ends here they stay as they are.")
    if summary["sonnet_subject_sol_quota_failed"]:
        out("ALARM: some run(s) met the Codex limit with no valid Sol answer and may not take Opus + Sonnet: their Sol result stands as no answer")
    if gate.unposted():
        out(f"ALARM: the gate's closing (episode {gate.unposted()}) is not posted yet: the post failed; it is retried on the next pass")
    return summary


def run_passes(plan_path, work_dir, sealed_dir, source, backends=None, *, passes: int = 1, pass_interval_s: float = 60.0, **kw) -> list[dict]:
    """Passes until nothing is waiting (every run coded, refused or terminal, none deferred) or `passes` is reached, `pass_interval_s` apart: the
    runs that were not finished are looked at again each time, in the same fixed order."""
    out_ = []
    for i in range(max(1, passes)):
        s = run_plan(plan_path, work_dir, sealed_dir, source, backends, **kw)
        out_.append(s)
        if not s["still_waiting"] or i == passes - 1:
            break
        time.sleep(pass_interval_s)
    return out_


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", help="the queue's packet directory (not with --plan)")
    ap.add_argument("--work", required=True, help="the work directory (with --plan: the PUBLIC one: the gate's files and totals only)")
    ap.add_argument("--coders", nargs="+", default=["codex", "claude"], choices=["codex", "claude", "sonnet"])
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--claude-workers", type=int, default=4)
    ap.add_argument("--codex-workers", type=int, default=None,
                    help=f"isolated Codex containers at once (1..{isolation.MAX_PARALLEL}); default 1, and 6 with --plan (56 MiB per coder measured, the 16 GiB floor)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--codex-client", choices=["cli", "api"], default="cli",
                    help="the Codex coder through its CLI in the isolation container, or through the OpenAI API (science, #76, 18:42Z)")
    ap.add_argument("--plan", help="the main block's coding plan (plan.py): each run's second coder is chosen when it is dispatched")
    ap.add_argument("--sealed", help="with --plan: where everything per packet goes (created mode 700); the report needs --unseal to read it")
    ap.add_argument("--input-root", default=P.DEFAULT_INPUT_ROOT,
                    help="with --plan: the coders' mirror of the campaign: state.sqlite directly under it (re-opened every pass) and the run directories at their "
                         "recorded paths below it, each with its <dir>.pulled.json marker beside it. Never under a snapshot-mirror directory (science's alone)")
    ap.add_argument("--mirror-root", action="append", default=[],
                    help="with --plan: another mirror's root, named (repeatable), for a merged store whose B runs are recorded under their own mirror "
                         "(`snapshot.bmerge stores`): a recorded path under it is read as it stands. A path under no named root is looked for below the input root, "
                         "as before. Never under a snapshot-mirror directory")
    ap.add_argument("--hold-keys", help="with --plan: a file of run keys, one per line, read afresh every pass: a held run is not picked up (a run started on "
                                        "two providers waits for the merge to say which copy counts); a named file that cannot be read stops the run")
    ap.add_argument("--run-prefix", help="with --plan: the recorded run directories' common prefix on the run host, to strip before looking below the input root "
                                         "(default: the whole recorded path, below the root)")
    ap.add_argument("--no-complete-marker", action="store_true",
                    help="with --plan: do not require each run directory's <dir>.pulled.json marker (its file count and bytes must match the directory). "
                         "For tests only: a partial copy could pass")
    ap.add_argument("--max-packets", type=int, help="with --plan: stop dispatching once this many runs have been dispatched in all (a small real smoke run)")
    ap.add_argument("--passes", type=int, default=1, help="with --plan: passes over the fixed order (runs not finished are skipped in place and looked at again)")
    ap.add_argument("--pass-interval-s", type=float, default=300.0)
    ap.add_argument("--notify-queue", help=f"with --plan: the runner's own operator-queue file, rewritten whole by atomic replace (default "
                                           f"<work>/quota/{DEFAULT_QUEUE}); never the campaign's operator_queue.json")
    ap.add_argument("--gate-wait-s", type=float, default=P.GATE_WAIT_S, help="with --plan: wait this long for a Codex reset before Opus + Sonnet")
    ap.add_argument("--probe-s", type=float, default=P.PROBE_S, help="with --plan: probe the quota this often while the gate holds")
    ap.add_argument("--probe-slow-s", type=float, default=P.PROBE_SLOW_S, help="with --plan: probe this often after the switch")
    ap.add_argument("--sonnet-hard-stop", type=float, default=P.SONNET_HARD_STOP_PERCENT,
                    help="with --plan: a Sonnet-subject run keeps using Sol past the gate's 95% until the newest reading reaches this (science, #34, 4 Nov 20:22Z)")
    a = ap.parse_args(argv)
    if a.plan:
        if not a.sealed:
            ap.error("--plan needs --sealed")
        if a.codex_client != "cli" or a.coders != ["codex", "claude"]:
            ap.error("the plan mode takes neither --coders nor --codex-client: Sol is the Codex CLI, with Opus, and Sonnet for the fallback "
                     "(no Codex API, amendment 26)")
        try:
            source = P.StoreRunSource(a.input_root, strip_prefix=a.run_prefix, marker=P.NO_MARKER if a.no_complete_marker else None,
                                   mirror_roots=a.mirror_root, hold_keys_file=a.hold_keys)
        except P.PlanError as e:
            ap.error(str(e))
        run_passes(a.plan, a.work, a.sealed, source, passes=a.passes, pass_interval_s=a.pass_interval_s, max_attempts=a.max_attempts,
                   claude_workers=a.claude_workers, codex_workers=a.codex_workers or 6, limit=a.limit, notify_queue=a.notify_queue,
                   gate_wait_s=a.gate_wait_s, probe_s=a.probe_s, probe_slow_s=a.probe_slow_s, max_packets=a.max_packets,
                   sonnet_hard_stop=a.sonnet_hard_stop)
        return
    if a.sealed or a.max_packets or a.no_complete_marker or a.run_prefix or a.mirror_root or a.hold_keys:
        ap.error("--sealed, --max-packets, --run-prefix, --mirror-root, --hold-keys and --no-complete-marker belong to --plan")
    if not a.packets:
        ap.error("--packets is required (without --plan)")
    run_queue(a.packets, a.work, a.coders, max_attempts=a.max_attempts, claude_workers=a.claude_workers,
              codex_workers=a.codex_workers or 1, limit=a.limit, codex_client=a.codex_client)


if __name__ == "__main__":
    main()
