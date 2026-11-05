"""The operator queue (#34; the operator via science, 3 Nov 00:00Z): nobody can be woken overnight, so an alarm that needs the operator holds only what it
must, and the ask waits in `<root>/operator_queue.json` for the morning. The campaign process rewrites it beside status.json; the lead posts it to science.

The file: {"as_of", "items": [...], "wake_needed": null | {"since_utc", "key", "message"}} (an interface other agents read: nothing else at the top level). An item is {key, since_utc, held, ask, last_seen_utc, resolved_utc}: the key is stable per cause, so a
repeat adds no line; `since_utc` is when the cause was first seen (kept across rewrites and restarts, because the file is read before it is written);
`held` is one line, exactly what the cause holds; `ask` is one line, what the operator must do; `resolved_utc` is null while the cause stands, and a cause
that clears stays listed with it set. `watching` (kept in the store, not in the file) is a cause not yet old enough for the operator ("down for more than 30 minutes"): first-seen times only.

The causes are read from the structured facts of `progress.build_status`, never from alarm text. `causes_from_status` and `update_queue` are pure."""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

from .config import CampaignConfig

QUEUE_FILE = "operator_queue.json"
PROVIDER_DOWN_S = 30 * 60.0
WAKE_AFTER_S = 30 * 60.0             # all dispatch idle this long, with a cause only the operator can end (operator via science, 3 Nov 01:21Z)          # a provider or a host down for more than this reaches the operator (the runbook's rule)
REOPEN_KEEP_S = 30 * 60.0            # a cause back within this long of clearing is the same episode: it keeps its since_utc
KINDS_UNREADABLE = "operator_queue_unreadable"
META = "operator_queue"
WATCH_META = "operator_queue_watching"


@dataclasses.dataclass(frozen=True)
class Cause:
    key: str
    held: str
    ask: str
    min_age_s: float = 0.0              # the cause reaches the queue once it has stood this long
    since_utc: str | None = None        # when the cause began, if the facts say; else the queue's own first look
    wake_holds_all: bool = False        # the cause stops all dispatch by itself, so runs still in flight (started before it) do not hide it
    wake: str | None = None             # "what is stopped|the one thing needed": set only on a cause that, with ALL dispatch idle for 30 minutes, needs the operator (see wake_needed)


def _iso(t: dt.datetime) -> str:
    return t.isoformat()


def _t(x: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


# --- the facts that are not in build_status's own queries ------------------------------------------------------------------
def onedata_health(store: Any) -> dict[str, Any]:
    """The Onedata health check's standing: failing when an attempt failed it (before the run, or after) and no attempt has passed it since. `since_utc`
    is the start of the first failed attempt after the last passing one; a pass is an attempt whose post-run check was ok."""
    ok = store.q("SELECT MAX(id) m FROM attempts WHERE post_health_ok=1 AND COALESCE(infra_kind,'')!='onedata_health'")[0]["m"] or 0
    bad = store.q("SELECT MIN(started_utc) s, MAX(ended_utc) e, COUNT(*) n FROM attempts WHERE infra_kind='onedata_health' AND id>?", (ok,))[0]
    if not bad["n"]:
        return {"failing": False, "failures": 0, "since_utc": None, "last_utc": None, "detail": None}
    last = store.q("SELECT infra_detail d FROM attempts WHERE infra_kind='onedata_health' AND id>? ORDER BY id DESC LIMIT 1", (ok,))[0]["d"]
    return {"failing": True, "failures": bad["n"], "since_utc": bad["s"], "last_utc": bad["e"], "detail": (last or "")[:200]}


def idle_fact(store: Any, cfg: CampaignConfig, now: dt.datetime) -> dict[str, Any]:
    """Whether dispatch has STARTED nothing, as progress._held_alarms judges it but counting only real starts (see below) and reporting runs still in flight apart: runs pending, and
    no start since the later of the last real start and this process's first look. Never after the hard stop (nothing starts then by design). `idle_s` is None when it cannot be told."""
    out: dict[str, Any] = {"pending": 0, "running": 0, "idle_s": None, "since_utc": None}
    out["pending"] = store.q("SELECT COUNT(*) n FROM runs WHERE status='pending'")[0]["n"]
    out["running"] = store.q("SELECT COUNT(*) n FROM attempts WHERE state='running'")[0]["n"]
    try:
        hard = cfg.hard_stop()
    except Exception:  # noqa: BLE001 - an unreadable hard stop is alarmed where it is read
        hard = None
    if not out["pending"] or (hard is not None and now >= hard):
        return out
    from .errors import PRE_CHECK_FAILED
    # A start is an attempt that began real work. Not one refused a sandbox, not one that saw a refused key (a probe, every `key_rejected_pause_s`), not a failed pre-run check:
    # the burn loop of a down provider writes one of those every minute or so, and would keep "the last start" fresh for ever.
    last_start = store.q("SELECT MAX(started_utc) t FROM attempts WHERE state != 'unstarted' AND COALESCE(infra_kind,'') != 'key_rejected' "
                         "AND NOT (COALESCE(infra_kind,'') = 'onedata_health' AND COALESCE(infra_detail,'') LIKE ?)", (PRE_CHECK_FAILED + "%",))[0]["t"]
    refs = []
    for raw in (last_start, store.get_meta("dispatch_since")):
        try:
            if raw:
                refs.append(_t(raw))
        except ValueError:
            pass
    if refs:
        t = max(refs)
        out["idle_s"], out["since_utc"] = (now - t).total_seconds(), _iso(t)
    return out


def wake_needed(st: dict[str, Any], causes: list[Cause], items: list[dict[str, Any]], now: dt.datetime) -> dict[str, str] | None:
    """The one thing this module says about waking the operator (the operator via science, 3 Nov 01:21Z): ALL dispatch idle for over 30 minutes, with no run in flight, AND a
    standing queue item whose cause only the operator can end (a provider that stays down, a refused key with nothing else running, a slot-user stop that the canary gave up on).
    Anything holding one model, one host or one slot is never one, and a stop the canary can still end is not one until it has given up. The campaign only WRITES this; it
    sends nothing. Under 200 characters, no secret: what is stopped, since when, the one thing needed. None when none applies, and it is None again as soon as the cause clears."""
    idle = st.get("dispatch_idle") or {}
    if idle.get("idle_s") is None or idle["idle_s"] <= WAKE_AFTER_S:
        return None
    open_keys = {i["key"] for i in items if i["resolved_utc"] is None}
    for c in causes:
        if c.wake and c.key in open_keys and (c.wake_holds_all or not idle.get("running")):         # a refused key stops one model: only with nothing in flight is it everything
            what, _, needed = c.wake.partition("|")
            msg = f"ALL dispatch stopped since {idle['since_utc'][:16]}Z ({idle['idle_s'] / 60:.0f} min): {what}. Needed: {needed}."
            return {"since_utc": idle["since_utc"], "key": c.key, "message": msg[:199]}
    return None


def key_rejections(store: Any) -> dict[str, dict[str, Any]]:
    """The units held for a refused key (scheduler._hold_key keeps them in meta `key_rejected`): unit -> {model, backend, since_utc, last_utc, count, detail, key_path}.
    An unreadable record is reported under "*", never as no rejection."""
    try:
        d = json.loads(store.get_meta("key_rejected") or "{}")
        if not isinstance(d, dict):
            raise ValueError
        return d
    except ValueError:
        return {"*": {"model": "*", "backend": "?", "since_utc": None, "count": 0, "detail": "the stored record is unreadable", "key_path": "(unknown)"}}


def canary_fact(store: Any) -> dict[str, Any]:
    """The unstarted stop's canary record (scheduler._canary): chain of relatches, and whether the stop is latched for a person. Unreadable: latched for a person."""
    try:
        d = json.loads(store.get_meta("unstarted_canary") or "{}")
        return {"chain": int(d.get("chain", 0)), "person": bool(d.get("person")), "person_utc": d.get("person_utc"), "last_end_epoch": d.get("last_end_epoch")}
    except (ValueError, TypeError, AttributeError):
        return {"chain": 0, "person": True, "person_utc": None, "last_end_epoch": None}


def canary_alarms(c: dict[str, Any], cfg: CampaignConfig) -> list[str]:
    if not c.get("person"):
        return []
    return [f"UNSTARTED STOP LATCHED FOR A PERSON: the stop latched again within {cfg.unstarted_relatch_window_s / 60:g} min of a canary run ending it, {c.get('chain')} times in a row "
            f"(or its record is unreadable): no canary is tried any more; fix the slot users, then write {cfg.unstarted_release_file}"]


def key_alarms(rejected: dict[str, dict[str, Any]], pause_s: float) -> list[str]:
    return [f"KEY REJECTED for {r['model']} on {r['backend']} ({u}): {r['detail']}, {r['count']} time(s) since {r['since_utc']}; no new run of it starts there and no attempt is charged; "
            f"one probe run every {pause_s:g} s ends the hold when the key is accepted; the key file is {r['key_path']}" for u, r in sorted(rejected.items())]


# --- the causes, from the status ------------------------------------------------------------------------------------------
def causes_from_status(st: dict[str, Any], cfg: CampaignConfig) -> tuple[list[Cause], frozenset[str]]:
    """(the causes standing now, key prefixes the status could not see): an item under a blind prefix is left as it is, never resolved, because a fact
    that cannot be read has not cleared."""
    out: list[Cause] = []
    blind: set[str] = set()
    site_g_down = "site_g (the study's only data provider)"
    fs = st.get("site_g_settings")
    if fs is None:
        blind.add("site_g:")
    else:
        why = {"unknown": fs.get("why"), "disk_unknown": (fs.get("disk") or {}).get("why"), "logs_unknown": (fs.get("logs") or {}).get("why")}
        for state, key, what in (("unknown", "site_g:settings_unknown", "its settings hash cannot be read"),
                                 ("disk_unknown", "site_g:disk_unknown", "its log volume's free space cannot be read"),
                                 ("logs_unknown", "site_g:logs_unknown", "the kept-log check cannot run")):
            if fs.get("state") == state:
                out.append(Cause(key, f"ALL dispatch: {site_g_down}: {what} ({why[state] or 'no reason given'})",
                                 "Restore site_g or the ssh path to it from the run VM; dispatch resumes by itself on a good read, nothing to release", PROVIDER_DOWN_S,
                                 wake="site_g cannot be read or reached|bring site_g back (its VM, op_worker or the network)", wake_holds_all=True))
    if fs is not None:                               # site_g's own stops: they clear when site_g or the frozen value is made right, which someone must do
        disk, logs = fs.get("disk") or {}, fs.get("logs") or {}
        for state, key, held, ask in (
                ("mismatch", "site_g:settings_mismatch", f"ALL dispatch: site_g's settings hash {fs.get('hash')} differs from the frozen {fs.get('frozen')}",
                 f"Do not touch site_g; science decides whether site_g is put back or the frozen value in {cfg.site_g_settings_frozen_file} is replaced; dispatch resumes by itself on a match"),
                ("disk_low", "site_g:disk_low", f"ALL dispatch: site_g's log volume is low ({disk.get('why')})",
                 "Free space on site_g's log volume without deleting the logs the study needs (science says what may go); dispatch resumes by itself"),
                ("logs_alarm", "site_g:logs_alarm", f"ALL dispatch: the kept-log check raised its alarm ({logs.get('why')})",
                 "Run the kept-log check by hand (python -m icsa.faults.calibrate logcheck) and read why; science decides; dispatch resumes by itself when it passes")):
            if fs.get("state") == state:
                out.append(Cause(key, held, ask))
    cl = st.get("credential_lifetimes")
    if cl is None:
        blind.add("credential_")                       # the check has not been run (or its file is unreadable): nothing is resolved by that
    else:
        for f in cl["findings"]:
            n, where = f.get("name"), f.get("path") or "in Onezone"
            if f.get("state") in ("unreadable", "error"):
                out.append(Cause(f"credential_lifetime:{n}", f"nothing: no hold; how long {n} lives is not known (read {cl.get('checked_utc')})",
                                 f"Find out how long {n} ({where}) lives and tell the lead: {str(f.get('why'))[:300]}"))
            elif f.get("state") in ("expiring", "expired"):
                out.append(Cause(f"credential_expiring:{n}", f"nothing yet: {n} ends at {f.get('expires_utc')}; from then every run that needs it fails",
                                 f"Renew {n} ({where}) before {f.get('expires_utc')}"))
            elif f.get("state") == "rejected":
                out.append(Cause(f"credential_rejected:{n}", f"{n} is refused when asked (read {cl.get('checked_utc')})", f"Renew or replace {n} ({where})"))
    rc = st.get("read_check") or {}
    if rc.get("state") == "low":
        out.append(Cause("site_g:read_check_low", f"ALL dispatch at the next block: site_g reads at {rc.get('mbit_s')} Mbit/s before {rc.get('group')}, under {rc.get('threshold_mbit_s')}",
                         "Science decides; do not retune site_g; the block starts by itself when a re-check (every 300 s) passes", PROVIDER_DOWN_S))
    if rc.get("state") == "unknown":
        out.append(Cause("site_g:read_check_unknown", f"ALL dispatch at the next block: the read check before {rc.get('group')} cannot run ({rc.get('why')}); it is retried every {int(cfg.read_check_retry_s)} s",
                         "Restore site_g or its read port; the block starts by itself on a passing read", PROVIDER_DOWN_S,
                         wake="site_g's read check cannot run|bring site_g back (its VM, op_worker or the network)", wake_holds_all=True))
    oh = st.get("onedata_health") or {}
    og = st.get("onedata_outages") or {}
    gate_open, gate_unreadable = og.get("open"), og.get("readable") is False
    if oh.get("failing") or gate_open or gate_unreadable:           # a closed gate is an outage even when no attempt shows it (a record restored after a restart, one unreadable, a later run's pass)
        if gate_open or gate_unreadable:
            held = (f"ALL dispatch: the Onedata health gate has been closed since {gate_open['start_utc']}: no run starts on any host; the dispatcher checks every {int(cfg.onedata_pause_s)} s "
                    f"({gate_open.get('checks', 0)} so far) and resumes by itself on the first pass; one infra attempt was used, by the run that found it" if gate_open else
                    "ALL dispatch: the Onedata health gate's record is unreadable, so the gate is treated as closed until a check passes")
            last = (gate_open or {}).get("last_detail") or oh.get("detail")
            since = (gate_open or {}).get("start_utc") if not oh.get("failing") else min((x for x in (oh.get("since_utc"), (gate_open or {}).get("start_utc")) if x), key=_t, default=None)
        else:
            held = f"ALL dispatch: {int(cfg.onedata_pause_s)} s after every failed check ({oh.get('failures')} so far); each failure also uses an infra attempt of the run it was tried on"
            last, since = oh.get("detail"), oh.get("since_utc")
        out.append(Cause("onedata:health_check", held,
                         f"Restore Onezone or site_g's data path so the health check passes (last: {last})", PROVIDER_DOWN_S, since,
                         wake="the Onedata health check fails (a provider is down)|restore Onezone or site_g's data path", wake_holds_all=True))
    ust, can = st.get("unstarted_streaks") or {}, st.get("unstarted_canary") or {}
    for opt, n in sorted(ust.items()):
        if n >= cfg.unstarted_stop_after:
            fix = f"Create or repair the {opt} slot users on Onedata, then have the release file {cfg.unstarted_release_file} written (science's or your word)"
            if can.get("person"):
                ask = (f"LATCHED FOR A PERSON: {can.get('chain')} canary runs started and the stop latched again within {int(cfg.unstarted_relatch_window_s / 60)} min each time, so the cause "
                       f"is not gone and no canary is tried any more. {fix}")
            else:
                ask = f"{fix}; a canary run of {opt} is tried every {int(cfg.unstarted_canary_every_s / 60)} min and ends the stop by itself when it starts a sandbox"
            out.append(Cause("unstarted_stop", f"ALL dispatch, all options (only the canary run goes): {n} runs of option {'(unreadable count)' if opt == '*' else opt} in a row could not start a sandbox", ask,
                             wake=(f"sandboxes cannot start and the canary gave up|fix the {opt} slot users on Onedata, then release the stop" if can.get("person") else None),
                             wake_holds_all=True))
            break
    for unit, r in sorted((st.get("key_rejected") or {}).items()):
        out.append(Cause(f"key_rejected:{unit}", f"{r['model']} on {r['backend']} only ({unit}): no new run starts there and no attempt is charged; one probe run every "
                                                  f"{int(cfg.key_rejected_pause_s)} s; the model's other backends and the other models go on",
                         f"Renew or replace the key in {r['key_path']} (refused: {r['detail']}, {r['count']} time(s)); the hold ends by itself when a probe run is accepted",
                         0.0, r.get("since_utc"), wake="a model API key is refused and nothing else can run|renew the key file the queue names"))
    he, rel = st.get("harness_errors") or {}, cfg.harness_error_release_file
    if he.get("all_stop") or he.get("unreadable"):
        a_ = he.get("all_stop") or {}
        out.append(Cause("harness_error_stop", f"ALL dispatch, all options and models (runs in flight finish): {a_.get('why') or 'the stored record is unreadable'}",
                         f"Have the campaign process stopped and restarted with the fix (the runs go back to pending), THEN the word ALL written on a line of {rel}; not before the restart",
                         0.0, a_.get("utc")))
    for m, s_ in sorted((he.get("stopped_models") or {}).items()):
        out.append(Cause(f"harness_error_stop:{m}", f"{m} only (runs in flight finish; the other models go on): {s_.get('why')}",
                         f"Have the campaign process stopped and restarted with the fix for {m}, THEN the name {m} written on a line of {rel}; not before the restart", 0.0, s_.get("utc")))
    if st.get("hard_stop_stopped"):
        out.append(Cause("hard_stop", "ALL new dispatch (runs in flight finish; only runs deferred by their cap before the cohort cut still start)",
                         f"Say whether dispatch may go on past the hard stop {st.get('hard_stop_utc')}: the release file {cfg.hard_stop_release_file} is written once, after this moment",
                         0.0, st.get("hard_stop_utc")))
    su = st.get("slot_users")
    if su is None:
        blind.add("slot_users:")
    else:
        from .progress import slot_need_by_option
        need = slot_need_by_option(cfg)
        for opt, o in sorted(su.items()):
            if opt.startswith("_"):
                continue
            if o["usable"] == 0 or (o["waiting"] > 0 and o["usable"] < need.get(opt, 0)):
                out.append(Cause(f"slot_users:{opt}", f"runs of option {opt} wait for a slot user ({o['usable']} of {o['slots']} usable, {o['waiting']} waiting, {o['quarantined']} quarantined)",
                                 f"Create more {opt} slot users on Onedata, or repair the quarantined ones", PROVIDER_DOWN_S))
    se = st.get("slot_equality")
    if se is None:
        blind.add("site_a_slot_differs:")
    else:
        for slot, s in sorted((se.get("slots") or {}).items()):
            if (s.get("verdict") == "different" and s.get("blocked", True)) or s.get("run_blocked"):      # a "different" slot still in dispatch (amendment 41: the peer rule alarms only) needs no restart
                out.append(Cause(f"site_a_slot_differs:{slot}", f"slot {slot} ({s.get('model')}) only: out of dispatch until its job changes; the model's other slots and site_b go on",
                                 f"Have slot {slot}'s site_a job restarted with the registered {s.get('model')} checkpoint (llm-hpc-routing); do not force the slot back"))
    for model, v in sorted((st.get("served_settings_stopped") or {}).items()):
        if model != "*":
            out.append(Cause(f"served_settings:{model}", f"all dispatch of {model}: its server reported settings other than requested ({'; '.join(v.get('reasons', []))[:160]})",
                             f"Science decides; a site_a job change may be needed for {model}; then it is listed in {cfg.served_release_file}"))
    ws = st.get("open_endpoint_windows") or []
    model_open = {w["model"] for w in ws if not w.get("parent")}
    for w in sorted(ws, key=lambda w: w["model"]):
        if w["down_s"] <= cfg.alarm_endpoint_down_s or w.get("parent") in model_open:
            continue                                    # under the threshold, or covered by its model's own window
        m, par = w["model"], w.get("parent")
        if not par:
            claude = m in cfg.api_models
            out.append(Cause(f"model_down:{m}", f"all dispatch of {m}: no usable endpoint ({w.get('reason') or 'down'})",
                             "Check the Anthropic API and its key" if claude else f"Ask llm-hpc-routing for {m}'s site_a jobs and check site_b",
                             cfg.alarm_endpoint_down_s, w["down_since"]))
        elif m.startswith("site_b:"):
            out.append(Cause(f"site_b_down:{par}", f"the site_b backend of {par} only; its site_a slots go on",
                             f"Check site_b's status and the lk key for {par}", cfg.alarm_endpoint_down_s, w["down_since"]))
        else:
            out.append(Cause(f"site_a_slot_down:{m}", f"slot {m} ({par}) only; the model's other slots and site_b go on",
                             f"Ask llm-hpc-routing for slot {m}'s site_a job (endpoints.json says it is down, or its requests fail)", cfg.alarm_endpoint_down_s, w["down_since"]))
    rh = st.get("run_hosts")
    hs = rh.get("state") if rh else None
    if getattr(cfg, "hosts", None):
        if hs is None:
            blind.add("host_down:")
        else:
            gone = set(hs.get("down") or {}) | {h for h, p in (hs.get("probes") or {}).items() if not p.get("ok")}
            for h in sorted(gone):
                models = sorted(m for m, hh in cfg.model_host.items() if hh == h)
                out.append(Cause(f"host_down:{h}", f"dispatch of the models on {h} ({', '.join(models)}); the other host goes on; runs lost with it stay counted in flight until it shows them gone",
                                 f"Bring run VM {h} back (power, network, ssh from the dispatcher); its lost runs are re-run on return", PROVIDER_DOWN_S))
    sp = st.get("spend_alarm") or {}
    lim, spent, proj = sp.get("limit_usd"), sp.get("spent_usd"), sp.get("projected_usd")
    if lim is not None and ((spent is not None and spent >= lim) or (proj is not None and proj >= lim)):
        usd = lambda x: "unknown" if x is None else f"{x:,.0f}"       # noqa: E731
        out.append(Cause("spend", "nothing: the campaign goes on (only Sonnet main runs wait, at the Sonnet gate)",
                         f"Say whether the Claude spend can go on: spent {usd(spent)} USD, projected {usd(proj)} USD, alarm at {usd(lim)} USD"))
    sg = st.get("sonnet_gate") or {}
    if sg.get("held") and sg.get("state") == "hold_over":           # a projection over the gate is the operator's spend; an unknown one (a missing price or coder figure) is the lead's
        out.append(Cause("sonnet_gate", "Sonnet main runs only; Haiku and the open models go on",
                         f"Decide whether Sonnet may go on (projected Claude total {sg.get('projected_usd')} USD, gate {sg.get('max_usd')} USD); the release file {sg.get('release_file')} is written after the decision"))
    return out, frozenset(blind)


# --- the queue ------------------------------------------------------------------------------------------------------------
def update_queue(prev: dict[str, Any], causes: list[Cause], now: dt.datetime, blind: frozenset[str] = frozenset()) -> dict[str, Any]:
    """The queue after this look: a standing cause is an open item (one per key, since kept), one that stood long enough is promoted from `watching`, one
    that cleared is marked resolved and stays listed, and a cause under a blind prefix keeps whatever state it had."""
    n = _iso(now)
    items = {i["key"]: dict(i) for i in prev.get("items", [])}
    watching = dict(prev.get("watching", {}))
    standing = {c.key for c in causes}
    for c in causes:
        it = items.get(c.key)
        first = c.since_utc or watching.get(c.key) or n
        if it is not None and it["resolved_utc"] is None:                       # an open item: refreshed, its since only ever earlier
            it.update(held=c.held, ask=c.ask, last_seen_utc=n, since_utc=min(it["since_utc"], first, key=_t))
        elif (now - _t(first)).total_seconds() >= c.min_age_s:
            keep = it is not None and (now - _t(it["resolved_utc"])).total_seconds() <= REOPEN_KEEP_S
            items[c.key] = {"key": c.key, "since_utc": min(it["since_utc"], first, key=_t) if keep else first, "held": c.held, "ask": c.ask,
                            "last_seen_utc": n, "resolved_utc": None}
            watching.pop(c.key, None)
        else:
            watching[c.key] = first                                             # not old enough yet: only the first look is kept
    for k in [k for k in watching if k not in standing and not any(k.startswith(p) for p in blind)]:
        del watching[k]                                                         # cleared before it reached the operator
    for k, it in items.items():
        if k not in standing and it["resolved_utc"] is None and not any(k.startswith(p) for p in blind):
            it["resolved_utc"] = n
    return {"as_of": n, "items": sorted(items.values(), key=lambda i: (i["resolved_utc"] is not None, i["since_utc"], i["key"])), "watching": watching}


def _valid(d: Any) -> bool:
    return (isinstance(d, dict) and isinstance(d.get("items"), list) and isinstance(d.get("watching", {}), dict)
            and all(isinstance(i, dict) and {"key", "since_utc", "held", "ask", "last_seen_utc", "resolved_utc"} <= set(i) for i in d["items"]))


def load_queue(path: Path, now: dt.datetime) -> tuple[dict[str, Any], str | None]:
    """(the queue on disk, None), or (an empty one, where the unreadable file was kept). A file that cannot be read as a queue is renamed with a suffix, never
    overwritten; if it cannot even be renamed this raises, and nothing is written."""
    try:
        text = path.read_text()
    except FileNotFoundError:
        return {"items": [], "watching": {}}, None
    try:
        d = json.loads(text)
        if _valid(d):
            return d, None
    except ValueError:
        pass
    aside = path.with_name(f"{path.name}.unreadable-{now.strftime('%Y%m%dT%H%M%SZ')}")
    os.replace(path, aside)
    return {"items": [], "watching": {}}, str(aside)


def write_queue(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "w") as f:
        f.write(json.dumps(data, indent=1))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def run_cycle(store: Any, cfg: CampaignConfig, st: dict[str, Any], root: Path, now: dt.datetime) -> None:
    """One look, by the campaign process only (the read-only `status` command never writes it): read the file, apply the status, write it back. A failure is
    an event, an alarm in the next status (`queue_alarms`) and a line on stderr, and the campaign goes on."""
    path = Path(root) / QUEUE_FILE
    n = _iso(now)
    try:
        prev, aside = load_queue(path, now)
        try:                                                  # causes not yet old enough are kept in the store, so the file is exactly as_of, items and wake_needed
            prev["watching"] = dict(json.loads(store.get_meta(WATCH_META) or "{}"))
        except (ValueError, TypeError):
            prev["watching"] = {}
        from . import credlife
        st = {**st, "credential_lifetimes": credlife.read(root)}       # written by `python -m icsa.campaign.credlife`; not a status fact
        causes, blind = causes_from_status(st, cfg)
        if aside:
            store.event(n, KINDS_UNREADABLE, None, f"the queue file was unreadable and is kept at {aside}: the items it held may be lost")
            causes.append(Cause("operator_queue:file_unreadable", "nothing: the queue file itself",
                                f"Read the kept-aside file {aside}: the open items and since times it held are not in the new file"))
        data = update_queue(prev, causes, now, blind)
        data["wake_needed"] = wake_needed(st, causes, data["items"], now)         # only written here; the lead sends the wake
        store.put_meta(WATCH_META, json.dumps(data.pop("watching")), n)
        write_queue(path, data)
        store.put_meta(META, json.dumps({"ok": True, "as_of": n}), n)
    except Exception as e:  # noqa: BLE001 - the queue must never stop the campaign; it says so
        print(f"operator queue not written: {type(e).__name__}: {e}", file=sys.stderr)
        try:
            store.put_meta(META, json.dumps({"ok": False, "as_of": n, "why": f"{type(e).__name__}: {e}"[:300]}), n)
        except Exception:  # noqa: BLE001
            pass


def queue_alarms(store: Any) -> list[str]:
    out = []
    try:
        m = json.loads(store.get_meta(META) or "null")
    except ValueError:
        m = {"ok": False, "why": "unreadable record"}
    if m and not m.get("ok"):
        out.append(f"the operator queue file was not written at {m.get('as_of')} ({m.get('why')}): what waits for the operator may be missing")
    bad = store.q("SELECT COUNT(*) n, MAX(id) last FROM events WHERE kind=?", (KINDS_UNREADABLE,))[0]
    if bad["n"]:
        last = store.q("SELECT detail FROM events WHERE id=?", (bad["last"],))[0]["detail"]
        out.append(f"the operator queue file was unreadable {bad['n']} time(s) and kept aside, never overwritten (latest: {last})")
    return out
