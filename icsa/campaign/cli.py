"""python -m icsa.campaign {run,status,manifest,export-infra} [--stub PLAN.json] [--config C.json]

    python -m icsa.campaign level-down --config LAUNCH.json --root CAMPAIGN_ROOT --who NAME (--why "TEXT" | --reason "TEXT")
        one level lower for every cap together (the restart command calls this, with --reason); on top of what the campaign state holds, while the dispatcher is down or up (it
        re-reads the state every dispatch round; the write is one transaction, so there is no second writer racing it). --reason is idempotent: the same reason twice takes one step.
        Prints one JSON line. Exit 0: the step is recorded (lowered, or "already": true for a reason taken before) and was read back from the state; 3: the level was already at the
        ladder's lowest, nothing changed; 1: bad call, no state, unreadable state, or the step could not be read back.
    python -m icsa.campaign level --config LAUNCH.json --root CAMPAIGN_ROOT
        the level in force, its steps with who, why and UTC, and the last probes (read-only).
    python -m icsa.campaign caps-set --config LAUNCH.json --root CAMPAIGN_ROOT --who NAME --source "TEXT" [--site_b MODEL=N ...] [--site_a-slot KEY=N ...]
        amendment 41(b): endpoint concurrency changes while the dispatcher runs, with its time and source. Writes an override of the launch file's site_b_caps (per model) and
        site_a_slot_caps (per endpoint key, sessions one slot holds) into the campaign state, merged with any override already there (a key not named keeps its value), and an
        event; the dispatcher re-reads it every dispatch round and at start. --who and --source are required (who set it; who said so, and where). Prints one JSON line with the
        effective caps. Exit 0: written and its own event read back; 1: a bad call (an argument argparse refuses once the command word is read, no --who or --source, nothing to set, a model that is not an open model, a key that
        is not an endpoint key, a value that is not a whole number >= 0), no campaign state, or a record that could not be read back. Nothing is written on a bad call.
    python -m icsa.campaign caps-set --show ...   (or: caps ...)
        the launch caps, the override and the effective caps (read-only).
    python -m icsa.campaign price-attempt --config LAUNCH.json --root CAMPAIGN_ROOT --attempt-id N --token-budget N --who NAME --source "TEXT"
        science, #34, 4 Nov 00:32Z: an attempt killed before its outcome was recorded (no usage at all) is charged amendment 26(c)'s bound, the run token budget at the dearest rate,
        and that budget is the one in force when it RAN, not the harness config's now. Writes the budget for that attempt (its attempts.id; the one `--show` or the status names)
        into the campaign state (meta `attempt_bounds`, merged with the entries already there: another attempt's keeps its own), with who set it and the source, and an
        `attempt_bound_set` event, in one transaction; the spend alarm and the Sonnet gate read it at every evaluation, with no restart (attempt_bounds.py). It applies to a billed attempt
        with usage_complete 0 of a Claude model of the launch file. Write it BEFORE the gate decides for a seed: a decision is kept for the seed in progress and does not change
        with a later record (the next seed's decision, and the spend alarm, follow it). Prints one JSON line. Exit 0: written and read back from the state; 1: a bad call (no
        --who, --source, --attempt-id or --token-budget, an attempt that does not exist, does not bill, has complete usage or is of another model, a budget that is not a whole number
        above 0), no campaign state, or a record that could not be read back. Nothing is written on a bad call.
    python -m icsa.campaign price-attempt --show ...
        the records in the state: which apply (with the attempt's run, model and state) and which are ignored, and why (read-only).
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import signal
import sys
import threading
import uuid
from pathlib import Path

from icsa import paths

from . import boverride
from . import endpoint_caps as EC
from . import gatewatch
from . import manifest as manifest_mod
from .config import CampaignConfig
from .instances import load_instances
from .manifest import build_manifest
from . import operator_queue
from .progress import record_slot_quarantine, render, write_status
from .store import PinMismatch, Store
from .scheduler import Campaign, CampaignLocked, utc_now


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.campaign")
    ap.add_argument("cmd", choices=["run", "status", "manifest", "export-infra", "level", "level-down", "opw-restart", "caps", "caps-set", "price-attempt"])
    ap.add_argument("--who", help="level-down: who asks (a name; recorded with the step)")
    ap.add_argument("--why", help="level-down: why (recorded with the step)")
    ap.add_argument("--source", help="caps-set: who stated the figure, and where (recorded with the change)")
    ap.add_argument("--site_b", action="append", metavar="MODEL=N", help="caps-set: the site_b concurrency cap of an open model (repeatable)")
    ap.add_argument("--site_a-slot", action="append", metavar="KEY=N", help="caps-set: the sessions one site_a slot of an endpoint key holds (repeatable)")
    ap.add_argument("--show", action="store_true", help="caps-set: print the launch caps, the override and the effective caps, and write nothing; price-attempt: print the records and which apply")
    ap.add_argument("--attempt-id", help="price-attempt: the attempt's id (attempts.id), a whole number above 0")
    ap.add_argument("--token-budget", help="price-attempt: the run token budget the attempt ran under, a whole number of tokens above 0")
    ap.add_argument("--config")
    ap.add_argument("--root", help="campaign dir (default ICSA_DATA/runs/campaign)")
    ap.add_argument("--stub", metavar="PLAN.json", help="use the stub executor and health check")
    ap.add_argument("--seed-first", action="store_true", help="with --stub: order and pause as a real launch (seed-first, the seed boundary, the quiet window); same as ICSA_TEST_SEED_FIRST=1")
    ap.add_argument("--executor", default="icsa.harness.run:execute_run",
                    help="module:function of the #8 entry point (default once #8 lands)")
    ap.add_argument("--health", default="icsa.harness.health:health_check",
                    help="module:function of the #10 health check")
    ap.add_argument("--out", help="export-infra: the JSON file for the analysis's --infra input")
    ap.add_argument("--past-pilot", action="store_true",
                    help="go: run past the pilot (needs the science agent's go decision)")
    ap.add_argument("--sandbox-image", help="tag or id of the real sandbox image; resolved once and pinned in the campaign state")
    ap.add_argument("--repin-image", action="store_true",
                    help="operator decision: accept a different image id than the one pinned in this campaign's state")
    og = ap.add_argument_group("opw-restart", "restart op_worker on site_g or site_f (science, #34, 3 Nov ruling); never run by the campaign itself")
    og.add_argument("--host", default="site_g", choices=["site_g", "site_f"])
    og.add_argument("--action", default="restart", choices=["restart", "baseline", "accept"],
                    help="restart (default); baseline = record the accepted pod identity at the freeze; accept = an operator's word after an abort or a hand restart")
    og.add_argument("--reason", help="opw-restart: why (amendment 30(c)): " + gatewatch.TRIGGER.replace("%", "%%") + "; never a slow read. level-down: why, and the step's key: the same reason twice takes one step only (what the restart command passes)")
    og.add_argument("--restart-cmd", help="the command that restarts op_worker on --host (the operator's forced command), as one shell-quoted string")
    og.add_argument("--restart-log", help="default $ICSA_SITE_G_RESTART_LOG or /mnt/volume2/icsa-2027/site_g_restart_log.jsonl")
    og.add_argument("--timed-block-file", default="/mnt/volume2/icsa-2027/TIMED_BLOCK")
    og.add_argument("--override-timed", help="the exact timed block named in the file, when cutting it is intended")
    og.add_argument("--force-reason", help="restart although amendment 30(c)'s condition does not hold: why; needs --science-ok or --departure; all recorded in the log and the event")
    og.add_argument("--science-ok", help="the URL of the science agent's comment that agrees to the forced restart")
    og.add_argument("--departure", help="the lead's departure (science did not answer within 15 minutes and every live probe is failing): the probes' state, recorded")
    og.add_argument("--level-down-cmd", help="lane-mh2's command that sets dispatch one level lower; run before the restart ends; a reason is appended")
    og.add_argument("--gate-ssh", action="append", metavar="LABEL=SSH-ARGV", help="another run host whose gate logs are read, read-only, by this ssh command (repeatable)")
    og.add_argument("--work-root", help="the sandboxes' directory on this host (default the sandbox config's)")
    og.add_argument("--warm-passes", type=int, default=3)
    og.add_argument("--plateau-interval-s", type=float, default=30.0)
    og.add_argument("--up-timeout-s", type=float, default=600.0)
    seen = argparse.Namespace()       # argparse fills it as it goes, so a refusal after the command word was read still knows the command (abbreviated options, values named like a command, all of it argparse's own)
    try:
        a = ap.parse_args(argv, namespace=seen)
    except SystemExit as e:
        if e.code == 2 and getattr(seen, "cmd", None) in ("caps", "caps-set", "price-attempt"):
            return 1                  # caps-set's (and price-attempt's) contract: a bad call is exit 1 (argparse has already printed its usage error to stderr); no other command's code changes. A refusal before the command word is read (an option with no value ahead of it) stays argparse's 2
        raise

    if a.cmd == "opw-restart":     # before any manifest is built: it needs the store (events) and the log, and nothing of the campaign's code
        from . import opwcmd
        root0 = Path(a.root) if a.root else paths.RUNS / "campaign"
        if not (root0 / "state.sqlite").exists():
            print(f"opw-restart: no campaign state at {root0 / 'state.sqlite'}: its events have nowhere to go", file=sys.stderr)
            return 1
        st0 = Store(root0 / "state.sqlite")
        try:
            return opwcmd.main(a, st0)
        finally:
            st0.close()

    if a.cmd == "run" and not a.stub and a.config:        # a real launch's config sits outside the hashed tree: editing it later must not change the dispatcher's hash
        from icsa import codestamp
        tree = Path(__file__).resolve().parents[2]
        hit = codestamp.hashed_root_of(a.config, tree)
        if hit:
            print(f"the launch config {a.config} sits inside {hit}/, which the code hash covers ({', '.join(codestamp.ROOTS)}): editing it would change this "
                  "dispatcher's hash and hold the other host. Keep it outside the tree", file=sys.stderr)
            return 4
    if a.stub:       # a stub run is no study's: it keeps the registered order, so the seed boundary and the quiet window (amendments 27 and 29) never pause a development run,
        # unless the run asks for seed-first: --seed-first, or ICSA_TEST_SEED_FIRST set to anything but empty or 0 (the switch the test suite honours). Then it orders and pauses as a real launch.
        manifest_mod.SEED_FIRST = bool(a.seed_first or os.environ.get("ICSA_TEST_SEED_FIRST", "0") not in ("", "0"))
    try:
        cfg, b_provider = boverride.load_config(a.config)       # no `b_provider` block in the launch file: exactly CampaignConfig.from_json(a.config), and nothing below changes
    except boverride.BOverrideError as e:
        print(e, file=sys.stderr)
        return boverride.EXIT_REFUSED
    if a.cmd in ("level", "level-down"):
        return level_command(a, cfg)
    if a.cmd in ("caps", "caps-set"):
        return caps_command(a, cfg)
    if a.cmd == "price-attempt":
        return price_attempt_command(a, cfg)
    if b_provider is not None:       # a B dispatcher reads its own provider: site_g's constants are replaced before anything of the run path is used (boverride.py)
        try:
            boverride.install(b_provider, cfg)          # the same block again is a no-op: a B process has it installed at its start already (ICSA_B_PROVIDER)
        except boverride.BOverrideError as e:
            print(e, file=sys.stderr)
            return boverride.EXIT_REFUSED
        if a.cmd == "run" and not a.stub:
            if boverride.env_block() != b_provider:     # the children of this dispatcher read site_g unless this interpreter started with the override: its venv has the .pth AND ICSA_B_PROVIDER names this launch's block
                print(f"{boverride.BLOCK}: this process was not started with the override of its own block ({boverride.ENV} unset or naming another block, or no {boverride.PTH_NAME} in "
                      "this venv: run `python -m icsa.campaign.boverride write-pth` with this venv's python): its probes and checks would read site_g. See docs/b_launch.md", file=sys.stderr)
                return boverride.EXIT_REFUSED
            problems = boverride.precheck(b_provider, cfg)         # the provider is the one the block names (Onezone's registered domain, the space's supporter), and every Python command of the launch reads it too
            if problems:
                print(f"{boverride.BLOCK}: the provider is not the one the launch names: " + "; ".join(problems), file=sys.stderr)
                return boverride.EXIT_REFUSED
    elif boverride.installed():      # ICSA_B_PROVIDER is set but this launch file has no block: its rows would be site_g's whole manifest read from another provider's constants
        print(f"{boverride.ENV} installs a B provider in this process, but the launch file has no {boverride.BLOCK} block", file=sys.stderr)
        return boverride.EXIT_REFUSED
    cfg.past_pilot = cfg.past_pilot or a.past_pilot
    cfg.sandbox_image = a.sandbox_image or cfg.sandbox_image
    cfg.repin_image = cfg.repin_image or a.repin_image
    if a.stub:
        instances = load_instances()          # the fixture set, for the stub only
    else:
        from icsa.instances.load import load_all_instances   # the real frozen 50-instance manifest (#5)
        instances = load_all_instances()
    rows = build_manifest(cfg, instances)
    if b_provider is not None:       # this dispatcher's store holds the runs of its plan only, each as the manifest has it (run key, seed, seq, order)
        try:
            rows = boverride.filter_rows(rows, b_provider.plan_file)
        except boverride.BOverrideError as e:
            print(e, file=sys.stderr)
            return boverride.EXIT_REFUSED
    root = Path(a.root) if a.root else paths.RUNS / "campaign"

    if a.cmd == "manifest":
        print(json.dumps({"rows": len(rows)}))
        for r in rows:
            print(r.seq, r.run_key)
        return 0

    if a.cmd == "status":  # read-only: no lock, no executor, no manifest sync, no recovery
        db = root / "state.sqlite"
        if not db.exists():
            print(f"no campaign state at {db}", file=sys.stderr)
            return 1
        store = Store(db)
        try:
            rec, _ = EC.check(store.get_meta(EC.META), cfg.open_models)       # the caps in force, not the launch file's (amendment 41(b)); a record that does not validate is not applied
            if rec:
                cfg.site_b_caps, cfg.site_a_slot_caps = EC.effective(cfg.site_b_caps, cfg.site_a_slot_caps, rec)
            print(render(write_status(store, cfg, utc_now(), root / "status.json")))
        finally:
            store.close()
        return 0

    if a.cmd == "export-infra":  # read-only, like status
        from .export import write_infra_export
        db = root / "state.sqlite"
        if not db.exists() or not a.out:
            print(f"needs campaign state at {db} and --out", file=sys.stderr)
            return 1
        store = Store(db)
        try:
            d = write_infra_export(store, instances, Path(a.out))
        finally:
            store.close()
        print(json.dumps({k: len(v) for k, v in d.items() if isinstance(v, list)}))
        return 0

    if a.stub:
        from .stub import make_stub_executor, stub_health_check
        plan = json.loads(Path(a.stub).read_text())
        ex, hc = make_stub_executor(plan), stub_health_check
        cfg.read_check_required = cfg.site_g_settings_required = cfg.hard_stop_required = cfg.coder_spend_required = cfg.launch_times_required = cfg.live_check_required = cfg.site_g_memory_required = False       # a stub touches no site_g, and its timing is no study's; the event log says these are off
    else:
        ex, hc = (_load(a.executor), _load(a.health))

    from .hosts import HostRouter, multi_host
    if multi_host(cfg):                       # two run hosts: a remote model's runs execute on its host (hosts.py)
        ex = HostRouter(ex)
    try:
        camp = Campaign(cfg, rows, ex, hc, root=root)
        camp.open()
    except CampaignLocked as e:
        print(e, file=sys.stderr)
        return 2
    except PinMismatch as e:
        print(e, file=sys.stderr)
        return 3
    try:
        from icsa.sandbox import earlyoom
        earlyoom.name_this_driver()              # the host's earlyoom ignores this name: it must never pick the campaign process
        earlyoom.require_driver_exempt()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: camp.stop.set())
        done = threading.Event()
        record_slot_quarantine(camp.store, utc_now())      # sets the start of this campaign's quarantine count NOW (kept on a resume)

        def report():
            while not done.wait(30):
                record_slot_quarantine(camp.store, utc_now())
                now = utc_now()
                operator_queue.run_cycle(camp.store, cfg, write_status(camp.store, cfg, now, root / "status.json"), root, now)     # what waits for the operator, beside status.json
        threading.Thread(target=report, daemon=True).start()
        camp.run()
        done.set()
        record_slot_quarantine(camp.store, utc_now())
        now = utc_now()
        st = write_status(camp.store, cfg, now, root / "status.json")
        operator_queue.run_cycle(camp.store, cfg, st, root, now)
        print(render(st))
        return 0
    finally:
        camp.close()


def level_command(a, cfg: CampaignConfig) -> int:
    """`level-down` and `level`: the level setting from a shell. Exit 0 (changed, already taken, or read), 3 (already at the ladder's lowest), 1 (a bad call, no readable state, or a step
    that could not be read back: exit 0 only once the step is durably recorded)."""
    from . import livecheck as LC
    root = Path(a.root) if a.root else paths.RUNS / "campaign"
    db = root / "state.sqlite"
    if not db.exists():
        print(f"no campaign state at {db}", file=sys.stderr)
        return 1
    problems = LC.ladder_problems(cfg)
    if problems:
        print("level: " + "; ".join(problems), file=sys.stderr)
        return 1
    reason = (a.reason or "").strip()
    if reason and (a.why or "").strip() and (a.why or "").strip() != reason:
        print("level-down: --why and --reason differ: give one", file=sys.stderr)
        return 1
    who, why = (a.who or ("opw-restart" if reason else "")).strip(), reason or (a.why or "").strip()
    if a.cmd == "level-down" and not (who and why):
        print("level-down needs --who and --why (or --reason): every change of the level is recorded with both", file=sys.stderr)
        return 1
    now = utc_now().isoformat()
    store = Store(db)
    try:
        if a.cmd == "level":
            block, alarms = LC.status_block(store.get_meta(LC.META), cfg, utc_now().timestamp())
            print(json.dumps({"level": block, "alarms": alarms}, indent=1))
            return 0
        box: dict = {}

        def go(raw):
            st = LC.LiveState.from_json(raw)
            box["already"] = next((c for c in st.changes if reason and c.get("reason") == reason), None)
            if box["already"] is not None:                       # the same reason has its step: nothing more
                box["lowered"], box["st"] = False, st
                return None, [], None
            box["lowered"], events = LC.lower_one(st, cfg, "command", who, why, now)
            if box["lowered"] and reason:
                st.changes[-1]["reason"] = reason
            box["st"] = st
            return (st.to_json() if box["lowered"] else None), events, None
        store.update_meta(LC.META, go, now)
        st = box["st"]
        if box["lowered"] or box["already"] is not None:        # read it back from the state, as another process will: the step is there, or the exit is not 0
            back = LC.LiveState.from_json(store.get_meta(LC.META))
            want = box["already"] if box["already"] is not None else st.changes[-1]
            if not any(c["utc"] == want["utc"] and c["steps"] == want["steps"] and c.get("who") == want["who"] for c in back.changes):
                print("level-down: the step was not found in the campaign state after it was written", file=sys.stderr)
                return 1
    except ValueError as e:
        print(f"level-down: the campaign state cannot be changed: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps({"lowered": box["lowered"], "already": box["already"] is not None, "steps": st.steps, "max_steps": LC.max_steps(cfg.level_ladder),
                      "caps": LC._caps_in_force(cfg, st.steps), "who": who, "why": why, "utc": (box["already"] or {}).get("utc", now)}))
    return 0 if (box["lowered"] or box["already"] is not None) else 3


def caps_command(a, cfg: CampaignConfig) -> int:
    """`caps-set` and `caps`/`caps-set --show` (amendment 41(b)): the endpoint caps from a shell. The override is validated against the launch config's open models before anything is
    written, merged with the one already in the state in ONE transaction (the dispatcher re-reads it every round), and read back from the state: exit 0 only once it is there."""
    root = Path(a.root) if a.root else paths.RUNS / "campaign"
    db = root / "state.sqlite"
    if not db.exists():
        print(f"no campaign state at {db}", file=sys.stderr)
        return 1
    launch = (dict(cfg.site_b_caps), dict(cfg.site_a_slot_caps))
    show = a.cmd == "caps" or a.show
    if show and (a.site_b or a.site_a_slot):
        print("caps-set: --show reads only: give it no --site_b or --site_a-slot", file=sys.stderr)
        return 1
    if not show:
        who, source = (a.who or "").strip(), (a.source or "").strip()
        if not (who and source):
            print("caps-set needs --who and --source: every change of an endpoint cap is recorded with who set it and who stated the figure, and where", file=sys.stderr)
            return 1
        try:
            ll, hs = EC.parse_pairs(a.site_b, "--site_b"), EC.parse_pairs(a.site_a_slot, "--site_a-slot")
        except ValueError as e:
            print(f"caps-set: {e}", file=sys.stderr)
            return 1
        if not (ll or hs):
            print("caps-set: nothing to set: give --site_b MODEL=N or --site_a-slot KEY=N", file=sys.stderr)
            return 1
        bad = EC.problems_in(ll, hs, cfg.open_models)
        if bad:
            print("caps-set: " + "; ".join(bad), file=sys.stderr)
            return 1
    store = Store(db)
    try:
        if show:
            rec, bad = EC.check(store.get_meta(EC.META), cfg.open_models)
            eff = EC.effective(*launch, rec)
            print(json.dumps({"launch": {"site_b": launch[0], "site_a_slot": launch[1]}, "override": rec, "override_problems": bad,
                              "effective": {"site_b": eff[0], "site_a_slot": eff[1]}}, indent=1))
            return 0
        now = utc_now().isoformat()
        box: dict = {}

        def go(raw):
            cur, bad_cur = EC.check(raw, cfg.open_models)            # an override that cannot be read is replaced (the event says so), so that a bad one never blocks the fix
            before = EC.effective(*launch, cur)
            new = {"site_b": {**(cur or {}).get("site_b", {}), **ll}, "site_a_slot": {**(cur or {}).get("site_a_slot", {}), **hs},
                   "set_utc": now, "source": source, "who": who}
            after = EC.effective(*launch, new)
            box["new"], box["eff"] = new, after
            moved = EC.diff(before, after)
            note = f" (the record that was there did not validate and is replaced: {'; '.join(bad_cur)})" if bad_cur else ""
            box["token"] = uuid.uuid4().hex                                     # what the read-back looks for: this call's own event
            ev = ("endpoint_caps_set", None, f"{who} set: " + ("; ".join(moved) if moved else "no value changed") + f"; source: {source}; set_utc: {now}{note}; token: {box['token']}")
            return json.dumps(new, sort_keys=True), [ev], None
        store.update_meta(EC.META, go, now)
        back, bad = EC.check(store.get_meta(EC.META), cfg.open_models)     # read it back, as the dispatcher will
        # this call's own event was written in the same transaction as its record, so its presence proves the write; the record itself may meanwhile have been merged over by another caps-set
        # (whose time is no proof of the order it committed in), or hold another writer's value for a key this call set
        wrote = bool(box.get("token")) and store.q("SELECT 1 FROM events WHERE kind='endpoint_caps_set' AND detail LIKE ?", (f"%; token: {box['token']}",))
        if back is None or bad or not wrote:
            print("caps-set: the override was not found in the campaign state as written: " + "; ".join(bad), file=sys.stderr)
            return 1
        box["eff"] = EC.effective(*launch, back)                           # what is in force now, from the state
    except ValueError as e:
        print(f"caps-set: the campaign state cannot be changed: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps({"set": True, "override": back, "effective": {"site_b": box["eff"][0], "site_a_slot": box["eff"][1]}, "who": who, "source": source, "utc": now}))
    return 0


def _whole_number(text: str | None, digits: int) -> int | None:
    """`text` as a whole number above 0 written in plain digits (no sign, point, exponent, underscore or space), at most `digits` of them; None otherwise."""
    if text is None or not (text.isascii() and text.isdigit()) or len(text) > digits or int(text) <= 0 or text != str(int(text)):
        return None
    return int(text)


def price_attempt_command(a, cfg: CampaignConfig) -> int:
    """`price-attempt` and `price-attempt --show` (science, #34, 4 Nov 00:32Z): the budget an attempt ran under, from a shell. Validated before anything is written, merged with the
    record already in the state in ONE transaction with its event, and read back from the state: exit 0 only once it is there and would be applied."""
    from . import attempt_bounds as AB
    from .gate import BILLED
    root = Path(a.root) if a.root else paths.RUNS / "campaign"
    db = root / "state.sqlite"
    if not db.exists():
        print(f"no campaign state at {db}", file=sys.stderr)
        return 1
    if a.show and (a.attempt_id is not None or a.token_budget is not None):
        print("price-attempt: --show reads only: give it no --attempt-id or --token-budget", file=sys.stderr)
        return 1
    if not a.show:
        who, source = (a.who or "").strip(), (a.source or "").strip()
        if not (who and source):
            print("price-attempt needs --who and --source: every budget is recorded with who set it and who stated it, and where", file=sys.stderr)
            return 1
        attempt_id, budget = _whole_number(a.attempt_id, 18), _whole_number(a.token_budget, 18)
        if attempt_id is None or budget is None:
            print(f"price-attempt: --attempt-id (the attempts.id) and --token-budget (tokens) are each a whole number above 0, in plain digits: got {a.attempt_id!r} and {a.token_budget!r}", file=sys.stderr)
            return 1
    store = Store(db)
    try:
        if a.show:
            b = AB.read(store, BILLED)
            print(json.dumps({"present": b.present, "in_force": {str(i): e for i, e in sorted(b.entries.items())}, "ignored": b.ignored}, indent=1))
            return 0
        info, why = AB.attempt_problems(store, BILLED, attempt_id)
        if info is None:
            print(f"price-attempt: {why}", file=sys.stderr)
            return 1
        if info["model"] not in cfg.api_models:
            print(f"price-attempt: attempt {attempt_id} is of {info['model']}, which is not a Claude model of this launch file ({', '.join(cfg.api_models) or 'none'}): only those are priced", file=sys.stderr)
            return 1
        now = utc_now().isoformat()
        box: dict = {}

        def go(raw):
            again, late = AB.attempt_problems(store, BILLED, attempt_id)       # inside the write: an orphan's usage may have been read back since the check above
            if again is None:
                box["refused"] = late
                return None, [], None                            # nothing is written: no record, no event
            cur, bad_cur = AB.parse(raw)                         # a record that cannot be read is replaced (the event says so), so that a bad one never blocks the fix
            note = f" (the record that was there did not validate and is replaced: {bad_cur})" if cur is None else ""
            new = {**(cur or {}), str(attempt_id): {"token_budget": budget, "who": who, "source": source, "set_utc": now}}
            box["token"] = uuid.uuid4().hex                      # what the read-back looks for: this call's own event
            before = (cur or {}).get(str(attempt_id))
            ev = ("attempt_bound_set", info["model"], f"{who} set attempt {attempt_id} ({info['run_key']}, {info['state']}): token budget {budget}"
                  + (f" (was {before.get('token_budget') if isinstance(before, dict) else before!r})" if before is not None else "")
                  + f"; source: {source}; set_utc: {now}{note}; token: {box['token']}")
            return json.dumps(new, sort_keys=True), [ev], None
        store.update_meta(AB.META, go, now)
        if box.get("refused"):
            print(f"price-attempt: {box['refused']}", file=sys.stderr)
            return 1
        back = AB.read(store, BILLED)                              # read it back, as the spend alarm and the gate will
        # this call's own event was written in the same transaction as its record, so its presence proves the write; the entry may meanwhile have been replaced by another call
        wrote = bool(box.get("token")) and store.q("SELECT 1 FROM events WHERE kind='attempt_bound_set' AND detail LIKE ?", (f"%; token: {box['token']}",))
        if not wrote or attempt_id not in back.entries:
            print("price-attempt: the record was not found in the campaign state as written, or would not be applied: " + "; ".join(back.ignored), file=sys.stderr)
            return 1
    except ValueError as e:
        print(f"price-attempt: the campaign state cannot be changed: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps({"set": True, "attempt_id": attempt_id, "run_key": info["run_key"], "model": info["model"], "token_budget": back.entries[attempt_id]["token_budget"],
                      "who": who, "source": source, "utc": now, "in_force": {str(i): e for i, e in sorted(back.entries.items())}, "ignored": back.ignored}))
    return 0


def _load(spec: str):
    mod, fn = spec.split(":")
    return getattr(importlib.import_module(mod), fn)


if __name__ == "__main__":
    sys.exit(main())
