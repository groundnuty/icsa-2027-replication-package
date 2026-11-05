"""Progress view: completion per cell, ETA, bytes, tokens, Claude USD, alarms."""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import threading
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import healthgate, manifest
from .config import (CODER_MODEL, SITE_G_MEM_GROWTH_MIN_SPAN_H, SITE_G_MEM_GROWTH_WINDOW_H, SITE_G_MEM_MAX_AGE_S, SITE_G_MEM_NODE_MAX_PCT, SITE_G_MEM_OPW_MAX_PCT,
                     CampaignConfig, group_of, stage_label)
from .endpoints import backend_of, fresh_endpoints, read_endpoints, stale_slots
from .slot_equality import alarms_from_state
from icsa.cutrequest import cut_request_input, harness_caps
from .store import Store, unstarted_streaks

CELL = ("block", "option", "layout", "model")


def _cost(cfg: CampaignConfig, model: str, tin: int, tout: int, cache_write: int = 0, cache_read: int = 0,
          max_call_prompt: int | None = None) -> Decimal | None:
    """Exact cost in USD (Decimal), or None when the model's price is not set.

    `tin` is the whole prompt (uncached + cache write + cache read); the cached parts are priced at their own rates
    and only the remainder at the input rate. A price with a long-prompt tier is applied at the long rates unless the
    caller shows (`max_call_prompt`) that no call exceeded the threshold: the sums stored per attempt cannot show it."""
    p = cfg.prices.get(model)
    if p is None or p.input_per_mtok is None or p.output_per_mtok is None:
        return None
    d = lambda x: Decimal(str(x))  # noqa: E731 - exact decimal prices, no binary float noise
    inp, out, rd, wr = p.input_per_mtok, p.output_per_mtok, p.cache_read_per_mtok, p.cache_write_1h_per_mtok
    if p.long_above_tokens is not None and (max_call_prompt is None or max_call_prompt > p.long_above_tokens):
        if p.long_input_per_mtok is None or p.long_output_per_mtok is None:
            return None                       # a tier is declared but its rates are not: unknown, never the short rates
        inp, out, rd, wr = p.long_input_per_mtok, p.long_output_per_mtok, p.long_cache_read_per_mtok, p.long_cache_write_1h_per_mtok
    rd = d(rd) if rd is not None else Decimal("0.1") * d(inp)
    wr = d(wr) if wr is not None else Decimal(2) * d(inp)
    fresh = tin - cache_write - cache_read
    return (Decimal(fresh) * d(inp) + Decimal(cache_write) * wr + Decimal(cache_read) * rd + Decimal(tout) * d(out)) / Decimal(10**6)


def _usd(cfg: CampaignConfig, model: str, tin: int, tout: int, cache_write: int = 0, cache_read: int = 0) -> float | None:
    c = _cost(cfg, model, tin, tout, cache_write, cache_read)
    return None if c is None else float(c)


def backend_share_by_day(store: Store) -> list[dict[str, Any]]:
    """Finished runs per (model, option, layout) cell, UTC day and backend (site_a, site_b, anthropic).

    A finished run counts once, on its ANALYSED attempt: the latest 'done' attempt of a run whose status is
    'done'. Infra-failed or interrupted attempts of the same run never count. The day is the UTC date of that
    attempt's end; `share` is n over the cell-day's total. Rows are sorted by cell, day, backend."""
    rows = store.q(
        "SELECT r.model, r.option, r.layout, a.slot, a.ended_utc FROM attempts a JOIN runs r USING(run_key)"
        " WHERE r.status='done' AND a.state='done' AND a.ended_utc IS NOT NULL"
        " AND a.id=(SELECT MAX(id) FROM attempts b WHERE b.run_key=a.run_key AND b.state='done')")
    counts: dict[tuple, dict[str, int]] = {}
    for r in rows:
        day = dt.datetime.fromisoformat(r["ended_utc"]).astimezone(dt.timezone.utc).date().isoformat()
        d = counts.setdefault((r["model"], r["option"], r["layout"], day), {})
        b = backend_of(r["slot"])
        d[b] = d.get(b, 0) + 1
    out = []
    for (model, option, layout, day), d in sorted(counts.items()):
        tot = sum(d.values())
        for b in BACKENDS:
            if b in d:
                out.append({"model": model, "option": option, "layout": layout, "day_utc": day, "backend": b,
                            "n": d[b], "share": d[b] / tot, "cell_day_total": tot})
    return out


BACKENDS = ("site_a", "site_b", "anthropic")


def time_cap_by_cell(store: Store) -> list[dict[str, Any]]:
    """Runs stopped by the time cap per (model, option, backend), layouts pooled: n finished runs, n stopped, share.

    Finished = the run is 'done'; its ANALYSED attempt is the latest 'done' attempt, and it is a time-cap stop when that
    attempt's termination is 'time_cap' (Termination.TIME_CAP). Infra-failed and interrupted attempts never count."""
    rows = store.q(
        "SELECT r.model, r.option, a.slot, a.termination FROM attempts a JOIN runs r USING(run_key)"
        " WHERE r.status='done' AND a.state='done'"
        " AND a.id=(SELECT MAX(id) FROM attempts b WHERE b.run_key=a.run_key AND b.state='done')")
    c: dict[tuple, list[int]] = {}
    for r in rows:
        k = (r["model"], r["option"], backend_of(r["slot"]))
        v = c.setdefault(k, [0, 0])
        v[0] += 1
        v[1] += r["termination"] == "time_cap"
    return [{"model": m, "option": o, "backend": b, "n": n, "time_cap_stops": t, "share": t / n}
            for (m, o, b), (n, t) in sorted(c.items())]


def time_cap_alarms(cells: list[dict[str, Any]], cfg: CampaignConfig) -> list[str]:
    """Alarms of the load diagnostic: (1) a cell's time-cap share above cfg.alarm_timecap_share; (2) per model, the site_b
    share more than cfg.alarm_timecap_ratio x the site_a share (pooled over options and layouts). Small denominators are
    named in the text, never silently ignored."""
    out: list[str] = []
    small = cfg.alarm_timecap_small_n
    for x in cells:
        if x["share"] > cfg.alarm_timecap_share:
            note = (f" (small n: {x['n']} < {small} runs, one stop is {1 / x['n']:.0%})" if x["n"] < small else "")
            out.append(f"time-cap share {x['share']:.0%} > {cfg.alarm_timecap_share:.0%} for {x['model']} {x['option']} on "
                       f"{x['backend']}: {x['time_cap_stops']}/{x['n']} runs{note}")
    by: dict[tuple, list[int]] = {}
    for x in cells:
        v = by.setdefault((x["model"], x["backend"]), [0, 0])
        v[0] += x["n"]
        v[1] += x["time_cap_stops"]
    for model in sorted({m for m, _ in by}):
        if (model, "site_b") in by and (model, "site_a") in by:
            (nl, tl), (nh, th) = by[(model, "site_b")], by[(model, "site_a")]
            sl, sh = tl / nl, th / nh
            if sl > cfg.alarm_timecap_ratio * sh:
                notes = []
                if sh == 0:
                    notes.append("site_a has no time-cap stop")
                if min(nl, nh) < small:
                    notes.append(f"small n: site_b {nl}, site_a {nh} (< {small})")
                out.append(f"{model}: site_b time-cap share {sl:.0%} ({tl}/{nl}) is more than {cfg.alarm_timecap_ratio:g}x "
                           f"site_a's {sh:.0%} ({th}/{nh})" + (f" [{'; '.join(notes)}]" if notes else ""))
    return out


def write_backend_share_csv(rows: list[dict[str, Any]], path: Path) -> None:
    import csv
    cols = ["model", "option", "layout", "day_utc", "backend", "n", "share", "cell_day_total"]
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


# --- site_g's memory (science, #34, 23:57Z): an alarm that stops nothing ----------------------------------------------------------------------------------------------
# The reading is the newest `sample` line of the provider monitor's JSONL (tools/provider_mon.py, a copy of site_g's /data/icsa-mon/mon.jsonl on this host). One line is
#   {"kind": "sample", "ts": <epoch s>, "utc": ISO, "node": {"mem_pct", ...}, "opw": {"id": "pid:start_ticks", "rss_mib", "ws_mib", "ws_pct_node", ...}, ...}
# and any number may be null. The limits (science, #34, 02:20Z, so that cache cannot trip them): op_worker's RESIDENT memory as a share of the node (`opw.rss_mib` over the node's
# total > 50) and the node's use (`node.mem_pct`, MemAvailable-based, > 80). The monitor is frozen and does not write the node's total, so it is derived from the same reading,
# `opw.ws_mib` / `opw.ws_pct_node`, never from a constant; any null reads unknown. op_worker's GROWTH is the same resident memory (`opw.rss_mib`, amendment 29(f)); a change of `opw.id` inside the window is a restart (a new process), and the figure restarts there, since a
# restart is not a leak. The functions up to `site_g_memory_report` take plain values (a dict, numbers, epoch seconds), so the monitor's report can call the same judgement.
# Nothing in the scheduler reads what they return.
SITE_G_MEM_FUTURE_S = 120.0       # a reading stamped further ahead than this is unknown: its clock is not ours
SITE_G_MEM_MAX_SAMPLES = 400      # the persisted samples never exceed this, whatever the cadence
SITE_G_MEM_TAIL_BYTES = 65536     # only the end of the file is read, so reading stays as fast at hour 68 as at hour 1
SITE_G_MEM_PCT_FIELDS = ("opw_rss_pct_node", "node_mem_pct")
SITE_G_MEM_FIELDS = {"opw_limit": "opw.rss_mib / (opw.ws_mib / opw.ws_pct_node)", "node_limit": "node.mem_pct", "growth": "opw.rss_mib", "restart": "opw.id"}


def _site_g_num(v: Any, hi: float | None) -> float | None:
    """A finite number in [0, hi]; None (not read) for a bool, null, string, NaN, Infinity, a negative or one above `hi`. json.loads accepts NaN and Infinity, and
    `nan > 50` is False, so a NaN would otherwise pass as a reading below the limit."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) and f >= 0.0 and (hi is None or f <= hi) else None


def site_g_memory_reading(raw: Any) -> tuple[dict | None, str | None]:
    """One monitor `sample` record as plain data: ({"utc": ISO, "t": epoch s, "opw_ws_pct_node", "node_mem_pct", "opw_rss_mib", "opw_ws_mib", "opw_id"}, None), each
    value None when it is not a finite number in range (the id: not a non-empty string); or (None, why) when the record is not a sample or has no readable time. The time is
    `ts` (epoch seconds), else `utc`. A record with neither is not dated from anything else: the seam is wrong then, and the reason names the keys it has."""
    if not isinstance(raw, dict):
        return None, "the newest line is not a JSON object"
    if raw.get("kind", "sample") != "sample":
        return None, f"the newest line is a {raw.get('kind')!r} record, not a sample"
    t = _site_g_num(raw.get("ts"), 4e9)
    if t is None and isinstance(raw.get("utc"), str):
        try:
            u = _utc(raw["utc"])
            t = u.timestamp() if u is not None else None
        except (OverflowError, OSError, ValueError):
            t = None
    if t is None or t <= 0:
        return None, f"the newest sample has no readable ts or utc (its keys: {', '.join(sorted(map(str, raw))) or 'none'})"
    node, opw = raw.get("node"), raw.get("opw")
    node, opw = node if isinstance(node, dict) else {}, opw if isinstance(opw, dict) else {}
    oid = opw.get("id")
    # a share above 100 is not clipped: it is plainly over the limit, and must alarm. A number beyond 1000 is not a percentage.
    ws_pct, ws, rss = _site_g_num(opw.get("ws_pct_node"), 1000.0), _site_g_num(opw.get("ws_mib"), None), _site_g_num(opw.get("rss_mib"), None)
    rss_pct = round(rss * ws_pct / ws, 3) if rss is not None and ws and ws_pct else None      # the node's total is ws / (ws_pct / 100), from this one reading
    return {"utc": dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(), "t": t, "opw_ws_pct_node": ws_pct, "opw_rss_pct_node": rss_pct,
            "node_mem_pct": _site_g_num(node.get("mem_pct"), 1000.0), "opw_rss_mib": _site_g_num(opw.get("rss_mib"), None), "opw_ws_mib": _site_g_num(opw.get("ws_mib"), None),
            "opw_id": oid if isinstance(oid, str) and oid.strip() else None}, None


def judge_site_g_memory(raw: Any, now: float, *, max_age_s: float = SITE_G_MEM_MAX_AGE_S, opw_max_pct: float = SITE_G_MEM_OPW_MAX_PCT,
                    node_max_pct: float = SITE_G_MEM_NODE_MAX_PCT, why: str | None = None) -> dict[str, Any]:
    """The limits, as one pure judgement of one monitor `sample` record at `now` (epoch seconds). `state`: `alarm` (a limit is exceeded; exactly at it is not), `ok` (both
    shares read, fresh, within), or `unknown` (no record, no time, older than `max_age_s`, ahead of `now`, or a share unreadable and no breach seen). A share that is read and
    over its limit alarms even when the other cannot be read: `unknown_fields` then says so. `why` is the caller's reason for passing no record."""
    out: dict[str, Any] = {"state": "unknown", "why": why or "no reading", "reading_utc": None, "age_s": None, "opw_rss_pct_node": None, "opw_ws_pct_node": None, "node_mem_pct": None,
                           "opw_rss_mib": None, "opw_ws_mib": None, "opw_id": None, "opw_over_limit": None, "node_over_limit": None, "unknown_fields": list(SITE_G_MEM_PCT_FIELDS),
                           "limits": {"opw_rss_pct_node": opw_max_pct, "node_mem_pct": node_max_pct}}
    r, bad = site_g_memory_reading(raw) if raw is not None else (None, why)
    if r is None:
        out["why"] = bad or "no reading"
        return out
    age = now - r["t"]
    out.update(reading_utc=r["utc"], age_s=round(age, 1), **{k: r[k] for k in ("opw_rss_pct_node", "opw_ws_pct_node", "node_mem_pct", "opw_rss_mib", "opw_ws_mib", "opw_id")})
    if age > max_age_s:
        out["why"] = f"the newest reading is {age:.0f} s old (more than {max_age_s:g} s): the monitor or the copy of its file has stopped"
        return out
    if age < -SITE_G_MEM_FUTURE_S:
        out["why"] = f"the newest reading is stamped {-age:.0f} s ahead of now: its clock is not ours"
        return out
    out["opw_over_limit"] = None if r["opw_rss_pct_node"] is None else r["opw_rss_pct_node"] > opw_max_pct
    out["node_over_limit"] = None if r["node_mem_pct"] is None else r["node_mem_pct"] > node_max_pct
    out["unknown_fields"] = [k for k in SITE_G_MEM_PCT_FIELDS if r[k] is None]
    if out["opw_over_limit"] or out["node_over_limit"]:
        out["state"], out["why"] = "alarm", None
    elif out["unknown_fields"]:
        out["why"] = "unreadable in the newest reading: " + ", ".join(out["unknown_fields"]) + (f" (the monitor's sample says: {raw['error']})" if isinstance(raw, dict) and raw.get("error") else "")
    else:
        out["state"], out["why"] = "ok", None
    return out


def _site_g_samples(x: Any) -> list[list]:
    """The stored samples as [epoch s, MiB, process id] triples; anything that is not two finite non-negative numbers and a non-empty id string is dropped, so a damaged
    record cannot poison the fit."""
    out = []
    for s in x if isinstance(x, (list, tuple)) else []:
        if isinstance(s, (list, tuple)) and len(s) == 3 and isinstance(s[2], str) and s[2].strip():
            t, y = _site_g_num(s[0], None), _site_g_num(s[1], None)
            if t is not None and y is not None:
                out.append([t, y, s[2]])
    return out


def opw_growth(samples: Any, now: float, *, window_h: float = SITE_G_MEM_GROWTH_WINDOW_H, min_span_h: float = SITE_G_MEM_GROWTH_MIN_SPAN_H, min_n: int = 4) -> dict[str, Any]:
    """op_worker's resident-memory growth (`opw.rss_mib`) in MiB per hour: the least-squares slope of (reading time, MiB) over the samples of the last `window_h` hours
    before `now`, so a few noisy points do not set it (a first-to-last figure would). A sample is [epoch s, MiB, `opw.id`]. When the id changes inside the window op_worker
    restarted, and a restart is not a leak: the fit starts at the first sample of the newest process, `restarts_in_window` counts the changes and `last_restart_utc` is when
    the newest process was first seen. `mib_per_h` is None, never NaN, until at least `min_n` samples of that process cover at least `min_span_h`, and when all their times
    are the same. The window, the span and the count actually used are always reported, so a figure can be read for what it covers."""
    out: dict[str, Any] = {"mib_per_h": None, "field": SITE_G_MEM_FIELDS["growth"], "method": "least_squares", "window_h": window_h, "span_h": 0.0, "n": 0, "min_span_h": min_span_h,
                           "min_n": min_n, "restarts_in_window": 0, "last_restart_utc": None, "why": None}
    pts = sorted((t, y, i) for t, y, i in _site_g_samples(samples) if now - window_h * 3600.0 <= t <= now + SITE_G_MEM_FUTURE_S)
    cut = 0
    for k in range(1, len(pts)):
        if pts[k][2] != pts[k - 1][2]:
            out["restarts_in_window"] += 1
            cut = k
    note = ""
    if cut:
        out["last_restart_utc"] = dt.datetime.fromtimestamp(pts[cut][0], dt.timezone.utc).isoformat()
        note = f"op_worker restarted {out['restarts_in_window']} time(s) in the window, last seen {out['last_restart_utc']}: the figure starts there, a restart is not a leak; "
        pts = pts[cut:]
    out["n"] = len(pts)
    if pts:
        out["span_h"] = round((pts[-1][0] - pts[0][0]) / 3600.0, 4)
    if len(pts) < min_n:
        out["why"] = note + (f"{len(pts)} sample(s) of the newest process" if cut else f"{len(pts)} sample(s) in the last {window_h:g} h") + f", {min_n} needed"
        return out
    if (pts[-1][0] - pts[0][0]) / 3600.0 < min_span_h:
        out["why"] = note + f"the samples cover {out['span_h']:g} h, {min_span_h:g} h needed"
        return out
    tm, ym = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - tm) ** 2 for p in pts)
    if sxx <= 0.0:
        out["why"] = note + "all the samples carry the same time"
        return out
    slope = sum((p[0] - tm) * (p[1] - ym) for p in pts) / sxx * 3600.0
    if not math.isfinite(slope):
        out["why"] = note + "the fit is not a finite number"
        return out
    out["mib_per_h"] = round(slope, 3)
    out["why"] = note.rstrip("; ") or None
    return out


def site_g_memory_points(records: Any) -> list[list]:
    """The growth samples [ts, opw.rss_mib, opw.id] of monitor records (the `sample` lines of a JSONL, in any order); a sample with no resident figure or no process id is no point."""
    out = []
    for r in records if isinstance(records, (list, tuple)) else []:
        rd, _ = site_g_memory_reading(r) if isinstance(r, dict) and r.get("kind", "sample") == "sample" else (None, None)
        if rd is not None and rd["opw_rss_mib"] is not None and rd["opw_id"] is not None:
            out.append([rd["t"], rd["opw_rss_mib"], rd["opw_id"]])
    return out


def judge_site_g_memory_records(records: Any, now: float, *, max_age_s: float = SITE_G_MEM_MAX_AGE_S, opw_max_pct: float = SITE_G_MEM_OPW_MAX_PCT, node_max_pct: float = SITE_G_MEM_NODE_MAX_PCT,
                            window_h: float = SITE_G_MEM_GROWTH_WINDOW_H, min_span_h: float = SITE_G_MEM_GROWTH_MIN_SPAN_H, min_n: int = 4) -> dict[str, Any]:
    """The whole alarm from monitor records (dicts, as read from the JSONL): `judge_site_g_memory` of the newest `sample` and, under `growth`, `opw_growth` of all of them. The
    one definition for the campaign's status and for anything that reports the same alarm (the stability report)."""
    recs = [r for r in records if isinstance(r, dict)] if isinstance(records, (list, tuple)) else []
    dated = [(site_g_memory_reading(r)[0], r) for r in recs if r.get("kind", "sample") == "sample"]
    dated = [(d["t"], r) for d, r in dated if d is not None]
    latest = max(dated, key=lambda x: x[0])[1] if dated else None
    j = judge_site_g_memory(latest, now, max_age_s=max_age_s, opw_max_pct=opw_max_pct, node_max_pct=node_max_pct, why="no sample record")
    j["growth"] = opw_growth(site_g_memory_points(recs), now, window_h=window_h, min_span_h=min_span_h, min_n=min_n)
    return j


def update_site_g_memory(prev: Any, raw: Any, why: str | None, now: float, *, sample_every_s: float, window_h: float = SITE_G_MEM_GROWTH_WINDOW_H,
                     max_age_s: float = SITE_G_MEM_MAX_AGE_S, opw_max_pct: float = SITE_G_MEM_OPW_MAX_PCT, node_max_pct: float = SITE_G_MEM_NODE_MAX_PCT) -> dict[str, Any]:
    """The one record the campaign keeps in the store (meta `site_g_memory`) after a check at `now`: the judgement, the unknown streak (checks in a row that could not say), a
    trimmed copy of the reading (the monitor's own shape, so `judge_site_g_memory` reads it again at status time) and the bounded samples for the growth. A sample is the reading's
    own time, `opw.rss_mib` and `opw.id`; it is kept when it is newer than the last by at least half of `sample_every_s`, or at once when the process id changed, so a line
    read twice counts once and a restart is not missed. Only the last `window_h` hours are kept (at most `SITE_G_MEM_MAX_SAMPLES`), so the record has a constant size however long
    the campaign runs, and a restart of the campaign finds them. A stale or future-dated reading is no sample."""
    j = judge_site_g_memory(raw, now, max_age_s=max_age_s, opw_max_pct=opw_max_pct, node_max_pct=node_max_pct, why=why)
    p = prev if isinstance(prev, dict) else {}
    samples = _site_g_samples(p.get("samples"))
    try:
        streak = max(0, int(p.get("unknown_streak") or 0))
    except (TypeError, ValueError):
        streak = 0
    streak = streak + 1 if j["state"] == "unknown" or j["unknown_fields"] else 0
    r, _ = site_g_memory_reading(raw) if raw is not None else (None, None)
    if r is not None and r["opw_rss_mib"] is not None and r["opw_id"] is not None and -SITE_G_MEM_FUTURE_S <= now - r["t"] <= max_age_s:
        last = samples[-1] if samples else None
        if last is None or (r["t"] > last[0] and (r["opw_id"] != last[2] or r["t"] - last[0] >= sample_every_s / 2.0)):
            samples.append([round(r["t"], 3), r["opw_rss_mib"], r["opw_id"]])
        samples = [s for s in samples if s[0] >= r["t"] - window_h * 3600.0][-SITE_G_MEM_MAX_SAMPLES:]
    return {"checked_utc": dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(), "state": j["state"], "why": j["why"], "unknown_streak": streak,
            "reading": None if r is None else {"kind": "sample", "ts": round(r["t"], 3), "utc": r["utc"], "node": {"mem_pct": r["node_mem_pct"]},
                                               "opw": {"id": r["opw_id"], "rss_mib": r["opw_rss_mib"], "ws_mib": r["opw_ws_mib"], "ws_pct_node": r["opw_ws_pct_node"]}},
            "samples": samples}


def read_site_g_memory_file(path: str | Path, max_bytes: int = SITE_G_MEM_TAIL_BYTES) -> tuple[Any, str | None]:
    """The newest `sample` line of the monitor's JSONL (start and stop lines carry no numbers; a line the monitor was still writing does not parse), from the last
    `max_bytes` of the file only. (record, None), or (None, why) when the file is missing or unreadable, empty, or no sample line in its tail parses. A line that parses and
    is a sample but is not what is expected (no time, no fields) is returned as it is and judged there, where the reason names what it has."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            start = max(0, f.tell() - max_bytes)
            f.seek(max(0, start - 1))                # one byte before the tail says whether the tail starts on a line
            data = f.read()
    except OSError as e:
        return None, f"{path} cannot be read: {type(e).__name__}"
    lines = data[1 if start else 0:].decode("utf-8", "replace").split("\n")
    if start and data[:1] != b"\n" and lines:
        lines = lines[1:]                          # the tail starts mid-line: its first piece is not a whole line
    lines = [x for x in lines if x.strip()]
    if not lines:
        return None, f"{path} has no complete line"
    kinds: set[str] = set()
    for ln in reversed(lines):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("kind", "sample") == "sample":
            return d, None
        kinds.add(str(d.get("kind")) if isinstance(d, dict) else type(d).__name__)
    return None, (f"no sample line in the last {len(lines)} of {path} (it has: {', '.join(sorted(kinds))})" if kinds else f"no line in the last {len(lines)} of {path} parses as JSON")


def site_g_memory_report(rec: Any, cfg: CampaignConfig, now: dt.datetime) -> tuple[dict[str, Any], list[str]]:
    """The status block `site_g_memory` and its ALARM lines, from the stored record, judged at the status's own `now` (so a check or a monitor that stopped reads unknown here
    without any other rule). Always the same keys. `state`: off | ok | alarm | unknown. An alarm line for a limit at once; for unknown only after
    `site_g_memory_unknown_alarm_after` checks in a row, or when the check itself has not run. It stops nothing."""
    j = judge_site_g_memory(None, now.timestamp(), why="not checked yet by this campaign")
    growth = opw_growth([], now.timestamp(), window_h=cfg.site_g_memory_growth_window_h, min_span_h=cfg.site_g_memory_growth_min_span_h)
    keys = ("state", "why", "reading_utc", "age_s", "opw_rss_pct_node", "opw_ws_pct_node", "node_mem_pct", "opw_rss_mib", "opw_ws_mib", "opw_id", "opw_over_limit", "node_over_limit", "unknown_fields")
    rep: dict[str, Any] = {**{k: j[k] for k in keys}, "limits": j["limits"], "fields": dict(SITE_G_MEM_FIELDS), "checked_utc": None, "unknown_streak": 0,
                           "unknown_alarm_after": cfg.site_g_memory_unknown_alarm_after, "growth": growth, "source": cfg.site_g_memory_file}
    alarms: list[str] = []
    if not (cfg.site_g_memory_file or cfg.site_g_memory_required):
        rep.update(state="off", why="switched off in this launch's config", unknown_fields=[])
        return rep, alarms
    if rec is None:
        return rep, alarms
    if not isinstance(rec, dict):
        rep["why"] = "the stored record is unreadable"
        alarms.append("site_g's memory record is unreadable: whether op_worker or the node is over its memory limit is unknown; an alarm only, nothing is stopped")
        return rep, alarms
    t = now.timestamp()
    j = judge_site_g_memory(rec.get("reading"), t, max_age_s=cfg.site_g_memory_max_age_s, why=rec.get("why") or "no reading")
    try:
        streak = max(0, int(rec.get("unknown_streak") or 0))
    except (TypeError, ValueError):
        streak = 0
    rep.update({k: j[k] for k in keys}, checked_utc=rec.get("checked_utc"), unknown_streak=streak,
               growth=opw_growth(rec.get("samples"), t, window_h=cfg.site_g_memory_growth_window_h, min_span_h=cfg.site_g_memory_growth_min_span_h))
    lim = j["limits"]
    tail = "; an alarm only, nothing is stopped"
    gone = f" (also unreadable: {', '.join(j['unknown_fields'])})" if j["unknown_fields"] and j["state"] == "alarm" else ""
    if j["opw_over_limit"]:
        alarms.append(f"site_g's op_worker memory (resident) is {j['opw_rss_pct_node']:g}% of the node's, over the {lim['opw_rss_pct_node']:g}% limit "
                      f"(resident {j['opw_rss_mib'] if j['opw_rss_mib'] is not None else 'n/a'} MiB, read {j['reading_utc']}){gone}{tail}")
    if j["node_over_limit"]:
        alarms.append(f"site_g's node memory is {j['node_mem_pct']:g}% in use, over the {lim['node_mem_pct']:g}% limit (read {j['reading_utc']}){gone}{tail}")
    if j["state"] == "unknown" and streak >= cfg.site_g_memory_unknown_alarm_after:
        alarms.append(f"site_g's memory cannot be read ({j['why']}), {streak} checks in a row: whether op_worker or the node is over its memory limit is unknown{tail}")
    ck = _utc(rec.get("checked_utc")) if isinstance(rec.get("checked_utc"), str) else None
    if ck is None:
        alarms.append("site_g's memory record has no readable check time: whether the check is running is unknown" + tail)
    else:
        lag = (now - ck).total_seconds()
        if lag > cfg.site_g_memory_unknown_alarm_after * cfg.site_g_memory_every_s + 60:
            alarms.append(f"site_g's memory was last checked {lag / 60:.0f} min ago: the check is not running (state unknown){tail}")
    return rep, alarms


def _blocked_slots(store: Store) -> set[str]:
    """The slots site_a slot equality took out of dispatch (its recorded state); an unreadable record blocks none here, and its own alarm says so."""
    try:
        raw = store.get_meta("slot_equality")
        return {k for k, v in (json.loads(raw).get("slots") or {}).items() if v.get("blocked")} if raw else set()
    except (ValueError, AttributeError, TypeError):
        return set()


def _concurrency(cfg: CampaignConfig, models: set[str], now: dt.datetime | None = None, blocked: set[str] = frozenset()) -> int | None:
    """Enabled backend capacity (HPC and Claude provider caps once each, site_b per model),
    bounded by the global sandbox cap. None = unknown: open models still have work and endpoints.json cannot be read, so how many
    slots are up is not known (the configured cap would read as healthy)."""
    # the identities dispatch enforces: Claude models share the "anthropic" cap, open models the "site_a" cap
    cap = 0
    open_ms = {m for m in models if m not in cfg.api_models}
    if open_ms:   # the per-slot caps of the up slots, as dispatch derives them; the configured cap if the file is unreadable
        eps = read_endpoints(cfg.endpoints_file)
        if eps is None:
            return None
        eps = [x for x in (fresh_endpoints(eps, now or dt.datetime.now(dt.timezone.utc), cfg.endpoints_max_age_s) or [])
               if str(x.get('slot')) not in blocked]       # a slot equality took out of dispatch adds nothing
        derived = cfg.site_a_cap(eps, open_ms)
        cap = cfg.cap("site_a") if derived is None else derived     # None only when no per-slot caps are configured
    api = [m for m in models if m in cfg.api_models]
    cap += sum(cfg.anthropic_caps[m] for m in api if m in cfg.anthropic_caps)       # Claude caps are per model
    cap += cfg.cap("anthropic") if any(m not in cfg.anthropic_caps for m in api) else 0   # unlisted ones share the fallback
    cap += sum(cfg.site_b_caps.get(m, 0) for m in models if m in cfg.open_models)
    if cfg.max_sandboxes is not None:
        cap = min(cap, cfg.max_sandboxes)
    elif cfg.max_sandboxes_by_block:
        cap = min(cap, max(cfg.max_sandboxes_by_block.values()))      # an upper bound: each group runs at its own cap
    return cap if cap > 0 else None     # nothing can dispatch (every slot down, stale or blocked): no capacity, so no ETA


def _projections(store: Store, cfg: CampaignConfig, cells: dict[tuple, dict[str, Any]],
                 now: dt.datetime) -> tuple[list[dict[str, Any]], list[str]]:
    """Projected finish per priority group from the observed completion rate (#34).

    Per model, the rate is the runs finished in the last `rate_window_h` hours (or since the first finished
    attempt, if that is shorter) divided by that span. A group finishes when every model has finished its
    pending runs in that group and the earlier ones: now + max over models of pending_m / rate_m, and not
    sooner than all pending / total rate. The estimate follows the observed mix, so it moves as the mix does."""
    pend: dict[str, dict[str, int]] = {}
    base_of: dict[str, str] = {}        # seed-first: a stage's label -> its priority group (the deadline groups are groups)
    rank: dict[str, tuple] = {}
    if manifest.SEED_FIRST:
        # amendments 27(b), 29(b): the order is the stages' (each seed: block 1, tier A, tier B), so the projection is per stage and cumulative along them
        tiers = ["main_s1", "main_s2_a", "main_s2_b"]
        for r in store.q("SELECT block, layout, model, seed, COUNT(*) n FROM runs WHERE status='pending' GROUP BY 1,2,3,4"):
            g = group_of(r["block"], r["layout"], r["model"])
            lab = g if g in ("pilot", "pilot1") or g not in tiers else stage_label(g, r["seed"])
            base_of[lab] = g
            rank[lab] = (0, 0, 0) if g == "pilot" else (0, 1, 0) if g == "pilot1" else (1, r["seed"], tiers.index(g)) if g in tiers else (2, 0, 0)
            pend.setdefault(lab, {})[r["model"]] = pend.get(lab, {}).get(r["model"], 0) + r["n"]
    else:
        for (block, _opt, layout, model), c in cells.items():
            if c["pending"]:
                g = group_of(block, layout, model)
                pend.setdefault(g, {})[model] = pend.get(g, {}).get(model, 0) + c["pending"]
    since = now - dt.timedelta(hours=cfg.rate_window_h)
    first = store.q("SELECT MIN(ended_utc) t FROM attempts WHERE state='done'")[0]["t"]
    start = max(since, dt.datetime.fromisoformat(first)) if first else now
    span_h = max((now - start).total_seconds() / 3600, 1e-9)
    done_by_model: dict[str, int] = {}
    for r in store.q("SELECT model, COUNT(*) n FROM attempts a JOIN runs USING(run_key) "
                     "WHERE a.state='done' AND a.ended_utc>=? AND a.ended_utc<=? GROUP BY model",
                     (start.isoformat(), now.isoformat())):
        done_by_model[r["model"]] = r["n"]
    n_done = sum(done_by_model.values())
    enough = n_done >= cfg.min_rate_runs
    rate = {m: n / span_h for m, n in done_by_model.items()}
    total_rate = n_done / span_h
    def _t(x):
        return dt.datetime.fromisoformat(x.replace("Z", "+00:00")) if x else None
    # 2 Nov 03:52Z (operator, via science): block 1's own cut-off (3 Nov 12:00Z) is dropped; every group runs to the hard stop
    hard = _t(cfg.hard_stop_utc or cfg.cutoff_utc)       # cutoff_utc only as the fallback of an unset hard stop (old configs)
    order = [g for g in ["pilot", "pilot1", "main_s1", "main_s2_a", "main_s2_b"] if g in pend] + \
            [g for g in pend if g not in ("pilot", "pilot1", "main_s1", "main_s2_a", "main_s2_b")]
    if manifest.SEED_FIRST:
        order = sorted(pend, key=lambda lab: (rank[lab], lab))
    rows, alarms = [], []
    cum: dict[str, int] = {}
    barrier_h = 0.0          # pilot and calibration are barriers: they run one after the other before any main group
    barrier_ok = True
    for g in order:
        is_barrier = g in ("pilot", "pilot1")
        if is_barrier:
            own = pend[g]
            barrier_ok = barrier_ok and enough and all(rate.get(m, 0.0) > 0 for m in own)
            if barrier_ok:
                barrier_h += max(max(n / rate[m] for m, n in own.items()), sum(own.values()) / total_rate)
            cum_here = dict(own)                    # a barrier group does not pool with the main groups after it
        else:
            cum_here = None
            for m, n in pend[g].items():
                cum[m] = cum.get(m, 0) + n
        row: dict[str, Any] = {"group": g, "pending": sum(pend[g].values()), "pending_cumulative": sum((cum_here if is_barrier else cum).values()),
                               "finish_utc": None, "hours_left": None, "note": None}
        if not enough:
            row["note"] = f"too few completions in the window ({n_done} < {cfg.min_rate_runs})"
        else:
            pool = cum_here if is_barrier else cum
            stuck = [m for m in pool if rate.get(m, 0.0) <= 0]
            if stuck:
                row["note"] = "no completions in the window for " + ", ".join(sorted(stuck))
            elif not barrier_ok:
                row["note"] = "a pilot or calibration group before it cannot be projected"
            else:
                h = barrier_h if is_barrier else barrier_h + max(max(cum[m] / rate[m] for m in cum), sum(cum.values()) / total_rate)
                row["hours_left"] = h
                row["finish_utc"] = (now + dt.timedelta(hours=h)).isoformat()
        cutoff, cutoff_s = hard, cfg.hard_stop_utc or cfg.cutoff_utc
        row["deadline_utc"] = cutoff_s
        if cutoff is not None and base_of.get(g, g) in cfg.deadline_groups:
            if row["finish_utc"] is not None and dt.datetime.fromisoformat(row["finish_utc"]) > cutoff:
                late = (dt.datetime.fromisoformat(row["finish_utc"]) - cutoff).total_seconds() / 3600
                alarms.append(f"{g} will not fit: projected finish {row['finish_utc'][:16]}Z is {late:.1f} h after the "
                              f"deadline {cutoff_s}")
                row["misses_cutoff"] = True
            elif row["finish_utc"] is None and (enough or first is not None):
                # a rate was established once (completions exist) but cannot be projected now: a stall, not a fresh start
                alarms.append(f"{g}: no projection ({row['note']}); cannot confirm it fits before {cutoff_s}")
            if cutoff is not None and now > cutoff and row["pending"]:
                alarms.append(f"{g}: deadline {cutoff_s} has passed with {row['pending']} run(s) still pending")
                row["misses_cutoff"] = True
        rows.append(row)
    return rows, alarms


# the options each priority group runs (BlockSpec.interleave): block 1 = main S1 + pagination, blocks 2 = main S2 (tiers A and B)
GROUP_OPTIONS = {"main_s1": ("T", "T-unpaginated", "D", "M"), "main_s2_a": ("T", "D", "M"), "main_s2_b": ("T", "D", "M")}


def slot_need_by_option(cfg: CampaignConfig) -> dict[str, int]:
    """Per option, the most slot users any block that runs it may need at once: that block's concurrency cap
    (`max_sandboxes_by_block`, else `max_sandboxes`). An option whose blocks have no cap is absent (no alarm: nothing to compare to)."""
    from types import SimpleNamespace
    from .scheduler import Campaign
    as_campaign = SimpleNamespace(cfg=cfg, PILOT_GROUPS=Campaign.PILOT_GROUPS)
    need: dict[str, int] = {}
    for g, opts in GROUP_OPTIONS.items():
        cg = Campaign._cap_group(as_campaign, g)                  # the scheduler's own rule, not a copy of it
        cap = cfg.max_sandboxes_by_block[cg] if cg is not None else cfg.max_sandboxes
        if cap:
            for o in opts:
                need[o] = max(need.get(o, 0), int(cap))
    return need


def slot_user_alarms(lease_dir: Path | None = None, slot_map_path: Path | None = None,
                     need: dict[str, int] | None = None, since: float | None = None) -> tuple[dict | None, list[str]]:
    """Alarms of the Onedata slot users (icsa.harness.slot_lease): too few users per option silently lower the throughput,
    because a run with no free user waits. Alarms on a live waiter, and on any wait logged so far (count, total, longest).
    An unreadable pool is reported as unknown, never as fine; a pool that was never used (no directory) has nothing to say."""
    from icsa.harness import slot_lease as L
    d = Path(lease_dir) if lease_dir is not None else L.LEASE_DIR
    if not d.is_dir():
        return None, []
    try:
        st = L.pool_status(d, Path(slot_map_path) if slot_map_path is not None else L.SLOT_MAP, since=since)
    except Exception as e:  # noqa: BLE001
        return None, [f"Onedata slot users: status unreadable ({type(e).__name__}); whether runs wait for a user is unknown"]
    return st, pool_alarm_lines(st, need)


def pool_alarm_lines(st: dict, need: dict[str, int] | None = None) -> list[str]:
    out = []
    for opt, o in sorted(st.items()):
        if opt.startswith("_"):
            continue
        if o["waiting"]:
            out.append(f"{o['waiting']} run(s) WAIT for a free {opt} slot user ({o['busy']}/{o['slots']} busy): too few users, "
                       "throughput is lowered; create more")
        if o["waits"]:
            out.append(f"{opt}: {o['waits']} run(s) waited for a slot user, {o['wait_s_total']:.0f} s in all, longest "
                       f"{o['wait_s_max']:.0f} s (waits are not in the runs' wall time)")
        if o["quarantined"] or o["quarantines"]:
            out.append(f"{opt}: {o['quarantined']} slot user(s) QUARANTINED now (a sandbox that could not be torn down may still use "
                       f"the token; the slot is held until its teardown is proven), {o['quarantines']} quarantine(s) in all, "
                       f"{o['quarantine_slot_hours']:.1f} slot-hours lost (an upper bound: a holder that died ends it early)")
        if need and opt in need and o["usable"] < need[opt]:
            out.append(f"{opt}: only {o['usable']} of {o['slots']} slot users are usable ({o['quarantined']} quarantined) but a block "
                       f"may run {need[opt]} {opt} runs at once: the runs will wait for a user (throughput lowered)")
    return out


def _since(store: Store) -> float | None:
    """When this campaign first counted quarantines (the lease directory is shared and outlives a campaign): the cumulative
    totals count only events from then on. Current availability stays global (a quarantine of an earlier campaign still holds its slot)."""
    v = store.get_meta("slot_quarantine_since")
    return dt.datetime.fromisoformat(v).timestamp() if v else None


_BILLED = "('done','infra_fail','harness_error','interrupted','running')"   # every attempt that may have called the API
_CODER_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def coder_config_problem(cfg: CampaignConfig) -> str | None:
    """Why the campaign config cannot show the coders' spend (a start refusal, scheduler.open), or None."""
    if not cfg.coder_work_dir:
        return "no coder_work_dir in the campaign config"
    if not (Path(cfg.coder_work_dir) / "answers").is_dir():
        return f"no coders' archive at {Path(cfg.coder_work_dir) / 'answers'}"
    if cfg.coder_packets_dir is None and cfg.coder_expected_packets is None:
        return "neither coder_packets_dir nor coder_expected_packets in the campaign config (the coders' spend to come is unknown)"
    return None


# icsa.inspection.coders (ClaudeBackend.call) answers a failure that brought no message with CallResult(status="error", detail={"error": "<Name>: ..."}),
# and CallResult.usage stays its default `{}`; code_packet writes both into meta.json (the detail is spread into the top level: "error", no "stop_reason").
# These are the failures the API's own response shows to have come before any generation: a 429 (`except anthropic.RateLimitError` writes
# "RateLimitError: ...") and a connection that never carried a reply (`except anthropic.APIConnectionError` writes "APIConnectionError: ...").
# NOT among them, all estimated: "APITimeoutError: ..." (its own label since the coder catches it first: a timed-out call may have been partly billed),
# "APIStatusError <code>: ..." (a streamed error event can come after billing began) and code_packet's catch-all f"{type(e).__name__}: {e}"
# (a crash after the call may have billed).
_PRE_BILLING_ERRORS = ("RateLimitError", "APIConnectionError")


def _coder_failed_before_billing(meta: dict) -> str | None:
    """The error name when meta.json shows an attempt that failed before billing, by the API's own response, else None.

    All three must hold: status "error" with no stop_reason (no message came back); no usage (absent, `{}` as coders.py writes it, or all
    zero); and the top-level `error` text begins with exactly "RateLimitError:" or "APIConnectionError:"."""
    if meta.get("status") != "error" or "stop_reason" in meta:
        return None
    u = meta.get("usage")
    if u is not None and not (isinstance(u, dict) and all(isinstance(v, int) and not isinstance(v, bool) and v == 0 for v in u.values())):
        return None
    err = meta.get("error")
    for name in _PRE_BILLING_ERRORS:
        if isinstance(err, str) and err.startswith(name + ":"):
            return name
    return None


def _coder_usage(meta: dict) -> dict | None:
    """meta.json's usage when it is complete (the four token fields, each a non-negative int) and not all zero; else None.
    A call that answered cannot have used nothing, so an all-zero usage (what coders.py writes when the API's reply carried none) is no usage."""
    u = meta.get("usage")
    if not isinstance(u, dict) or any(not isinstance(u.get(k), int) or isinstance(u.get(k), bool) or u[k] < 0 for k in _CODER_KEYS):
        return None
    return u if any(u[k] for k in _CODER_KEYS) else None


def _coder_packet_bound(cfg: CampaignConfig, packets_dir: str | Path | None, pid: str, models: list[str]) -> Fraction | None:
    """An upper bound on what one call on this packet can cost, at list price, or None when it cannot be computed.

    Output: coders.CLAUDE_MAX_TOKENS (the request's max_tokens, thinking included). Input: the bytes of the exact message the runner sends
    (prompt.message of `<packets_dir>/<pid>.txt`) plus the bytes of the schema the request also carries in output_config, taken as tokens:
    one token per byte, the loosest count any tokenizer allows (a token is never empty). No cache is used, so the plain input rate applies
    (a price with a long-prompt tier is taken at its long rates). Priced at the dearest of `models`. None: no packet directory, no readable
    packet text, or none of the models has a price."""
    if packets_dir is None:
        return None
    from icsa.inspection import answer, prompt
    from icsa.inspection.coders import CLAUDE_MAX_TOKENS
    try:
        text = (Path(packets_dir) / f"{pid}.txt").read_text()
        tokens = len(prompt.message(text).encode()) + len(json.dumps(answer.schema()).encode())
    except (OSError, ValueError):                  # an unreadable packet text is data; a missing module is a bug and is not hidden
        return None
    costs = [_cost(cfg, m, tokens, CLAUDE_MAX_TOKENS) for m in models]
    costs = [Fraction(c) for c in costs if c is not None]
    return max(costs) if costs else None


def coder_spend(cfg: CampaignConfig, work_dir: str | Path | None, packets_dir: str | Path | None = None,
                expected_packets: int | None = None) -> dict[str, Any]:
    """The #76 Claude coder's spend from its archive, and what is still to come.

    Reads `<work_dir>/answers/<packet>/claude/attempt-*/meta.json` (icsa.inspection.coders): every attempt directory counts,
    the renamed stale and interrupted ones included, because each may have been billed. Each attempt is priced by the model its meta.json
    records, never by a default. Returns spent (Decimal-exact Fraction USD or None), packets_done (a packet with a claude final.json),
    remaining (None = unknown), cost_per_packet (the spend of the FINISHED packets, their estimated attempts included, / packets done: an unfinished packet's bounded attempt is in `spent` but never multiplied over the packets to come), `unknown` (reasons the figures cannot be trusted), and what part of
    `spent` is not a measurement: zero_attempts and zero_reasons, estimated_attempts, estimated_usd and estimated_reasons, by_model (priced
    attempts only: spent = sum of by_model + estimated_usd) and notes (the status's log of the above).

    Nothing here is ever zero by default, but one bad attempt must not hold the figure for the whole campaign, so an attempt is:
    - priced: complete usage and a recorded, priced model (the largest of these costs is "the largest seen");
    - ZERO, logged: it failed before billing by the API's own response (_coder_failed_before_billing);
    - ESTIMATED, logged: it has no meta.json (interrupted), an unreadable meta.json, or no readable usage that is no pre-billing failure. It is
      charged at an upper bound: the largest cost seen in the archive, or if larger the packet's bound (_coder_packet_bound). With neither it is unknown;
    - UNKNOWN: a recorded model with no price, or usage with no recorded model, or an estimate with no bound, or a finished packet with no
      archived attempt, or no archive, or an archive that cannot be listed."""
    unknown: list[str] = []
    out: dict[str, Any] = {"spent": None, "packets_done": 0, "remaining": None, "cost_per_packet": None, "unknown": unknown,
                           "zero_attempts": 0, "zero_reasons": {}, "estimated_attempts": 0, "estimated_usd": Fraction(0),
                           "estimated_reasons": {}, "by_model": {}, "finished_spent": None, "notes": []}
    if work_dir is None:
        unknown.append("inspection coders: no archive path given")
        return out
    wd = Path(work_dir)
    answers = wd / "answers"
    if not answers.is_dir():
        unknown.append(f"inspection coders: no archive at {answers} (an unrelated or mistyped directory looks the same as "
                       "one with no usage; create the empty answers/ directory to state that no coder has run yet)")
        return out
    done, no_attempt = 0, 0
    done_ids: set[str] = set()
    priced: dict[str, Fraction] = {}                 # recorded model -> its priced attempts' cost
    by_packet: dict[str, Fraction] = {}              # packet id -> all it has cost (priced and estimated attempts): cost_per_packet reads the finished ones
    largest: Fraction | None = None                  # the largest per-attempt cost seen (priced attempts only, never an estimate)
    zero: dict[str, int] = {}
    to_bound: list[tuple[str, str]] = []             # (packet id, why) for the attempts to charge at an upper bound
    unpriced: set[str] = set()
    no_model = 0
    try:
        packets = sorted(answers.iterdir())
    except OSError as e:
        unknown.append(f"inspection coders: archive {answers} cannot be listed ({type(e).__name__})")
        return out
    for packet in packets:
        cdir = packet / "claude"
        if not cdir.is_dir():
            continue
        n_att = 0
        # Completion first, then the attempts: the runner writes final.json after its last attempt, so a packet seen finished lists every attempt it had. The
        # other way round, a retry that finishes between the listing and the check leaves the listing with the failed attempt (read as zero) and the packet
        # counted finished at that cost. A packet that completes during this read is not done in it (its attempts are in `spent`) and is done in the next.
        complete = (cdir / "final.json").exists()
        try:
            attempts = sorted(cdir.glob("attempt-*"))
        except OSError as e:
            unknown.append(f"inspection coders: {cdir} cannot be listed ({type(e).__name__})")
            return out
        for att in attempts:
            if not att.is_dir():
                continue
            n_att += 1
            try:
                meta = json.loads((att / "meta.json").read_text())
                if not isinstance(meta, dict):
                    raise ValueError("meta.json is not an object")
            except FileNotFoundError:
                to_bound.append((packet.name, "no meta.json (an interrupted attempt)"))
                continue
            except (OSError, ValueError):
                to_bound.append((packet.name, "unreadable meta.json"))
                continue
            failed = _coder_failed_before_billing(meta)
            if failed:
                zero[failed] = zero.get(failed, 0) + 1
                continue
            model = meta.get("model")
            recorded = isinstance(model, str) and model != ""
            if recorded and _cost(cfg, model, 0, 0) is None:
                unpriced.add(model)                    # its list price is unknown, so no bound at it either
                continue
            u = _coder_usage(meta)
            if u is None:
                to_bound.append((packet.name, "no readable usage in meta.json"))
                continue
            if not recorded:
                no_model += 1                          # usage with no model: which price applies is not known, and is not guessed
                continue
            c = Fraction(_cost(cfg, model, u["input_tokens"] + u["cache_creation_input_tokens"] + u["cache_read_input_tokens"],
                               u["output_tokens"], u["cache_creation_input_tokens"], u["cache_read_input_tokens"]))
            priced[model] = priced.get(model, Fraction(0)) + c
            by_packet[packet.name] = by_packet.get(packet.name, Fraction(0)) + c
            largest = c if largest is None or c > largest else largest
        if complete:
            done += 1
            done_ids.add(packet.name)
            if n_att == 0:
                no_attempt += 1                   # a finished packet with no archived attempt: its usage is not on record
    out["packets_done"] = done
    # The upper bound is the largest seen over the WHOLE archive (never the sort order's), or if larger the packet's bound at the dearest model.
    bound_models = sorted({CODER_MODEL, *priced})
    est_usd, est_n, est_why, unbounded = Fraction(0), 0, {}, 0
    packet_bounds: dict[str, Fraction | None] = {}
    for pid, why in to_bound:
        if pid not in packet_bounds:
            packet_bounds[pid] = _coder_packet_bound(cfg, packets_dir, pid, bound_models)
        cands = [x for x in (largest, packet_bounds[pid]) if x is not None]
        if not cands:
            unbounded += 1
            continue
        est_usd += max(cands)
        by_packet[pid] = by_packet.get(pid, Fraction(0)) + max(cands)
        est_n += 1
        est_why[why] = est_why.get(why, 0) + 1
    out.update(zero_attempts=sum(zero.values()), zero_reasons=dict(sorted(zero.items())), estimated_attempts=est_n, estimated_usd=est_usd,
               estimated_reasons=dict(sorted(est_why.items())), by_model=dict(sorted(priced.items())))
    if zero:
        out["notes"].append(f"inspection coders: {sum(zero.values())} attempt(s) counted ZERO: they failed before billing, by the API's own "
                            f"response ({', '.join(f'{k} {v}' for k, v in sorted(zero.items()))})")
    if est_n:
        out["notes"].append(f"inspection coders: {est_n} attempt(s) ESTIMATED at an upper bound, ${float(est_usd):,.2f} in all, counted in the "
                            f"spend ({', '.join(f'{k}: {v}' for k, v in sorted(est_why.items()))})")
    for m in sorted(unpriced):
        unknown.append(f"inspection coders: no price for {m}")
    if no_model:
        unknown.append(f"inspection coders: {no_model} attempt(s) with usage but no recorded model (the price to apply is not guessed)")
    if unbounded:
        unknown.append(f"inspection coders: {unbounded} attempt(s) with no readable usage and no upper bound to charge (no priced attempt in "
                       "the archive to take the largest cost from, and no readable packet text under coder_packets_dir): a call may have been billed")
    if no_attempt:
        unknown.append(f"inspection coders: {no_attempt} finished packet(s) with no archived attempt, so no readable usage (a call may have been billed)")
    if unknown:
        return out
    spent = sum(priced.values(), Fraction(0)) + est_usd
    out["spent"] = spent
    finished = sum((by_packet.get(pid, Fraction(0)) for pid in done_ids), Fraction(0))
    out["finished_spent"] = finished
    if done:
        out["cost_per_packet"] = finished / done          # measured on finished packets only: in-flight attempts are not packets to come
    elif cfg.coder_cost_per_packet_usd is not None:
        out["cost_per_packet"] = Fraction(str(cfg.coder_cost_per_packet_usd))      # an operator-set estimate, used until one is measured
    if packets_dir is not None:
        try:
            order = json.loads((Path(packets_dir) / "queue.json").read_text())["order"]
            if not isinstance(order, list) or not all(isinstance(pid, str) for pid in order):
                raise ValueError("order is not a list of packet ids")
            # packets in this queue with no finished archive entry; a finished packet outside this queue is not one of them
            out["remaining"] = sum(1 for pid in order if pid not in done_ids)
        except (OSError, ValueError, KeyError, TypeError):
            unknown.append(f"inspection coders: queue.json in {packets_dir} unreadable, so the packets still to code are unknown")
    elif expected_packets is not None:
        out["remaining"] = max(0, int(expected_packets) - done)
    else:
        unknown.append("inspection coders: neither a queue nor an expected packet count given")
    if out["remaining"] and out["cost_per_packet"] is None:
        unknown.append("inspection coders: packets remain but no packet is finished and no cost per packet is configured, so the "
                       "cost to come is unknown (set coder_cost_per_packet_usd, or wait for a measurement)")
    return out


# --- Usage that cannot be taken at face value is BOUNDED, never unknown (science, #34, 21:33Z). Unknown stays only where a price cannot be computed. ---------
# An attempt falls in one class, in this order: its usage is incomplete (`usage_complete` 0: a request was abandoned or a reply carried no usage); a token
# count is missing (NULL); cache tokens exceed the prompt; a finished attempt recorded no tokens; or an unfinished one recorded none at all. The first is
# charged what it recorded PLUS the request that was cut. The next three have no usable figure: they are left out of the sums and each is charged the largest
# cost of a complete attempt of the model (the coders' rule for an attempt with no readable usage), or with none seen the ceiling of one attempt, the run's
# token budget at the model's dearest rate. An attempt with NO usage at all (killed, failed, or still running: usage is saved when an attempt ends) is charged
# that ceiling (science, #34, 22:58Z: a bound, not a mean, which is a typical attempt). All of it goes into the spend so far and NEVER into the mean per
# finished run that projects what is left, which stays a mean of measured spend.
_REASON = ("CASE WHEN COALESCE(usage_complete,1)=0 THEN 'incomplete_usage'"
           " WHEN input_tokens IS NULL OR output_tokens IS NULL OR cache_creation_tokens IS NULL OR cache_read_tokens IS NULL THEN 'missing_count'"
           " WHEN COALESCE(cache_creation_tokens,0)+COALESCE(cache_read_tokens,0) > COALESCE(input_tokens,0) THEN 'inconsistent_cache'"
           " WHEN COALESCE(input_tokens,0)=0 AND COALESCE(output_tokens,0)=0 AND state='done' THEN 'no_tokens'"
           " WHEN COALESCE(input_tokens,0)=0 AND COALESCE(output_tokens,0)=0 AND state='running' THEN 'running'"
           " WHEN COALESCE(input_tokens,0)=0 AND COALESCE(output_tokens,0)=0 THEN 'no_usage'"
           " ELSE 'ok' END")
USABLE_REASONS = ("ok", "incomplete_usage", "no_usage", "running")        # the counts of these attempts are priced as recorded (zero for the last two)


def billed_cond(states: str) -> str:
    """The SQL condition (alias `a`) for the attempts that bill: those whose state is in `states` (a SQL tuple), and an attempt marked `unstarted` that carries usage all the
    same. A start whose answer was lost is marked `unstarted` (it uses no attempt: store.infra_attempts, the retries, the seed boundary) and kept as an orphan, but its worker may
    have run and billed: the usage read back from its host when it ended (`_orphan_ended`), or, while that is not read, the mark `usage_complete` 0 (unknown, never zero), count in
    the spend. A plain refusal to start a sandbox has neither and bills nothing. Billing and charging are two questions: this changes only the first."""
    return (f"(a.state IN {states} OR (a.state='unstarted' AND (COALESCE(a.input_tokens,0)>0 OR COALESCE(a.output_tokens,0)>0 OR COALESCE(a.cache_creation_tokens,0)>0"
            " OR COALESCE(a.cache_read_tokens,0)>0 OR COALESCE(a.usage_complete,1)=0)))")
UNUSABLE_REASONS = ("missing_count", "inconsistent_cache", "no_tokens")
FIRST_REQUEST_TOOLS_BYTES = 32_000    # allowance for the tool definitions that travel with every request, added to a first request's prompt


def usage_rows(store: Store, billed: str) -> dict[str, dict[str, Any]]:
    """Per model, over the attempts whose state is in `billed` (a SQL tuple; see billed_cond): `i`, `o`, `cw`, `cr`, the token sums of the attempts whose counts are
    priced as recorded (USABLE_REASONS), and `n`, the attempts per reason. Shared by the spend alarm and the Sonnet gate, so the two read an attempt's
    usage by one rule."""
    out: dict[str, dict[str, Any]] = {}
    for r in store.q("SELECT model, reason, COUNT(*) n, SUM(input_tokens) i, SUM(output_tokens) o, SUM(cache_creation_tokens) cw, SUM(cache_read_tokens) cr"
                     f" FROM (SELECT model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, {_REASON} reason"
                     f" FROM attempts a JOIN runs USING(run_key) WHERE {billed_cond(billed)}) GROUP BY model, reason"):
        m = out.setdefault(r["model"], {"i": 0, "o": 0, "cw": 0, "cr": 0, "n": {}})
        m["n"][r["reason"]] = r["n"]
        if r["reason"] in USABLE_REASONS:
            for k in ("i", "o", "cw", "cr"):
                m[k] += r[k] or 0
    return out


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _cut_request(run_dir: str | None, chars: int) -> tuple[int, int, str] | None:
    """The input of the request that was cut, from the attempt's own record: (tokens, of them the prompt before the last turn, basis), or None when the record
    cannot be read here (no run dir, missing, truncated, or on a host whose directory is not synced). One token per byte, an upper bound, not a count.
    - last turn: its whole input + its output (the assistant message is sent back) + the cap of each of its tool calls' results, `chars` x 4 bytes;
    - first request: no turn completed, so the prompt, the transcript's bytes + an allowance for the tool definitions."""
    if not run_dir:
        return None
    d = Path(run_dir)
    rec = _read_json(d / "run_record.json")
    turns = rec.get("turns") if isinstance(rec, dict) else None
    if not isinstance(turns, list):
        return None
    if turns:
        t = turns[-1]
        try:
            i, o, calls = int(t["input_tokens"]), int(t["output_tokens"]), len(t.get("tool_calls") or [])
        except (KeyError, TypeError, ValueError, AttributeError):
            return None
        return cut_request_input(i, o, calls, chars), i, "last_turn"
    tr = _read_json(d / "transcript.json")
    msgs = tr.get("system_and_messages") if isinstance(tr, dict) else None
    if msgs is None:
        inf = _read_json(d / "infra.json")
        msgs = inf.get("transcript") if isinstance(inf, dict) else None
    if not isinstance(msgs, list) or not msgs:
        return None
    return len(json.dumps(msgs).encode()) + FIRST_REQUEST_TOOLS_BYTES, 0, "first_request"


def _request_usd(cfg: CampaignConfig, m: str, tin: int, prefix: int, tout: int) -> Fraction | None:
    """One request of `tin` prompt tokens, `prefix` of them already cached, and `tout` output tokens, at the dearer of: all the prompt at the full uncached input
    rate (the ruling), or the prefix at the cache-read rate and the rest written to the cache (the 1-hour write costs twice the input rate, so a prompt that is
    mostly new costs more that way). The tier is that of this request's prompt. None when a rate is not set."""
    a = _cost(cfg, m, tin, tout, 0, 0, max_call_prompt=tin)
    b = _cost(cfg, m, tin, tout, tin - prefix, prefix, max_call_prompt=tin)
    return None if a is None or b is None else Fraction(max(a, b))


def _ceiling(cfg: CampaignConfig, m: str, budget: int) -> Fraction | None:
    """One attempt's ceiling (amendment 26(c)): `budget` tokens at the model's dearest rate (uncached input, output, or written to the 1-hour cache). None when no rate is set."""
    rates = [c for c in (_cost(cfg, m, budget, 0, 0, 0, max_call_prompt=budget), _cost(cfg, m, 0, budget),
                         _cost(cfg, m, budget, 0, budget, 0, max_call_prompt=budget)) if c is not None]
    return Fraction(max(rates)) if rates else None


def bounded_usage(store: Store, cfg: CampaignConfig, billed: str, rows: dict[str, dict[str, Any]],
                  attempt_budgets: dict[int, int] | None = None) -> dict[str, dict[str, Any]]:
    """Per model with a priced rate and an attempt to bound: {attempts, usd (Fraction: the dollars charged ON TOP of the recorded counts for an incomplete
    attempt, IN PLACE of them for the rest), by_reason, by_basis}. A model whose price is not set is left out: the caller says so (unknown).
    Everything here is an assumed upper bound, stated in the status: one token per byte; the request cut at the output cap.
    The ceiling of an attempt with no usage at all is the run token budget at the dearest rate: the harness config's budget now, or, for an attempt the store record
    `attempt_bounds` names (attempt_bounds.py), the budget that record gives, the one in force when it ran (science, #34, 4 Nov 00:32Z), basis `budget_record`. `attempt_budgets`
    ({attempt id: budget}) hands in what the caller already read from the record; left out, the record is read here, at every call, never cached."""
    from . import attempt_bounds
    budgets = attempt_bounds.read(store, billed).budgets() if attempt_budgets is None else attempt_budgets
    out: dict[str, dict[str, Any]] = {}
    for m, r in rows.items():
        n = r["n"]
        if not any(n.get(k) for k in ("incomplete_usage", "no_usage", "running", *UNUSABLE_REASONS)) or _cost(cfg, m, 0, 0) is None:
            continue
        o_cap, chars, budget = harness_caps(m)
        seen = store.q(f"SELECT input_tokens i, output_tokens o, cache_creation_tokens cw, cache_read_tokens cr, reason FROM (SELECT input_tokens, output_tokens,"
                       f" cache_creation_tokens, cache_read_tokens, {_REASON} reason FROM attempts a JOIN runs USING(run_key) WHERE {billed_cond(billed)}"
                       " AND model=?) WHERE reason IN ('ok','incomplete_usage')", [m])
        costs = [_cost(cfg, m, x["i"], x["o"], x["cw"], x["cr"], max_call_prompt=x["i"]) for x in seen if x["reason"] == "ok"]
        largest_cost = Fraction(max(costs)) if costs else None
        largest_input = max([x["i"] for x in seen] or [0])
        ceiling = _ceiling(cfg, m, budget)
        usd, by_reason, by_basis, unknown = Fraction(0), {}, {}, []

        def charge(reason: str, basis: str, cost: Fraction, k: int = 1) -> None:
            nonlocal usd
            usd += cost * k
            by_reason[reason] = by_reason.get(reason, 0) + k
            by_basis[basis] = by_basis.get(basis, 0) + k

        for a in store.q(f"SELECT a.id id, a.run_dir, a.input_tokens i, a.output_tokens o, a.cache_creation_tokens cw, a.cache_read_tokens cr FROM attempts a JOIN runs USING(run_key)"
                         f" WHERE {billed_cond(billed)} AND model=? AND COALESCE(a.usage_complete,1)=0", [m]):
            cut = _cut_request(a["run_dir"], chars)
            basis = "last_turn"
            own = budgets.get(a["id"])       # the budget this attempt ran under, from the record `attempt_bounds`, in place of the config's now (None: no record names it)
            if cut is None and not any(a[k] for k in ("i", "o", "cw", "cr")):
                # Amendment 26(c): "With no usage at all, the bound is one attempt's token budget at the dearest rate." An attempt lost to a killed dispatcher or host has no
                # counts and no record to read a request from: nothing is known of what it did, so another attempt's usage says nothing about it (the largest input below
                # bounds a request that was seen to be cut).
                own_ceiling = ceiling if own is None else _ceiling(cfg, m, own)
                if own_ceiling is None:
                    unknown.append(f"{m}: a rate the ceiling of one attempt needs is not set, so an attempt with no usage at all cannot be priced")
                else:
                    charge("incomplete_usage", "budget_ceiling" if own is None else "budget_record", own_ceiling)
                continue
            if cut is None:                  # the record is not here: no request of the model recorded more input than the largest attempt total
                tin, prefix, basis = max(largest_input, (a["i"] or 0) + (a["o"] or 0)) or own or budget, 0, "largest_input"
            else:
                tin, prefix, basis = cut
            c = _request_usd(cfg, m, tin, prefix, o_cap)
            if c is None:
                unknown.append(f"{m}: a rate the cut request needs (a long-prompt tier) is not set, so it cannot be priced")
            else:
                charge("incomplete_usage", basis, c)
        for reason in UNUSABLE_REASONS:       # a count that cannot be read: the largest complete attempt, or the ceiling when none was seen
            k = n.get(reason, 0)
            if k and largest_cost is None and ceiling is None:
                unknown.append(f"{m}: a rate the ceiling of one attempt needs is not set, so {k} attempt(s) with no readable usage cannot be priced")
            elif k:
                charge(reason, "largest_seen" if largest_cost is not None else "budget_ceiling", largest_cost if largest_cost is not None else ceiling, k)
        for reason in ("no_usage", "running"):    # no usage at all: the ceiling of one attempt, always (a bound, not a mean)
            k = n.get(reason, 0)
            if k and ceiling is None:
                unknown.append(f"{m}: a rate the ceiling of one attempt needs is not set, so {k} attempt(s) with no usage recorded cannot be priced")
            elif k:
                charge(reason, "budget_ceiling", ceiling, k)
        if by_reason or unknown:
            out[m] = {"attempts": sum(by_reason.values()), "usd": usd, "by_reason": dict(sorted(by_reason.items())), "by_basis": dict(sorted(by_basis.items())),
                      "unknown": unknown}
    return out


def _gate_bounds_note(sg: dict[str, Any]) -> str:
    """A text-status note for the gate line when an entry of the store record `attempt_bounds` is not used (attempt_bounds.py): never silent. The reasons are in status.json."""
    ign = (sg.get("attempt_bounds") or {}).get("ignored") or []
    return f"; attempt_bounds: {len(ign)} entr{'y' if len(ign) == 1 else 'ies'} ignored ({ign[0]})" if ign else ""


def bounded_for_status(b: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {m: {k: (float(v) if k == "usd" else v) for k, v in x.items() if k != "unknown"} for m, x in sorted(b.items()) if x["attempts"]}


def spend_alarm(store: Store, cfg: CampaignConfig, cells: dict[tuple, dict[str, Any]], *, coder_work_dir=None,
                coder_packets_dir=None, coder_expected_packets=None) -> tuple[dict[str, Any], list[str]]:
    """The $ alarm (#34): fires when the spend so far, or the spend projected at the finish, reaches cfg.spend_alarm_usd,
    and whenever either is unknown (a missing price or token count, no coder archive): unknown is never zero.

    Spend so far = every Claude attempt of every block (calibration, discarded and failed attempts; an interrupted, running or failed
    one with no usage recorded is charged the model's mean recorded spend per finished run; one with incomplete usage is charged what it recorded plus the request
    that was cut, one with a count that cannot be read the largest complete attempt: all upper bounds, counted in the status and the alarm text as BOUNDED,
    apart from the coders': bounded_usage)
    + the inspection coders' usage, each attempt priced by the model it records (an attempt that failed before billing counts zero and one with
    no readable usage counts at an upper bound, both counted in the status and the alarm text: coder_spend). Projected = spend so far + per Claude model (that model's spend / its finished
    runs) x its pending runs + the coders' remaining packets x their measured cost per packet. A model with pending runs
    and no finished run has no observed mean: unknown."""
    limit = Fraction(str(cfg.spend_alarm_usd))
    rows = usage_rows(store, _BILLED)
    # Priced attempt by attempt: an attempt whose whole prompt total is at or under a tier threshold proves every call was. Only the attempts whose counts
    # are usable (see usage_rows); the others are bounded below.
    att_cost: dict[str, Fraction | None] = {}
    for r in store.q("SELECT model, COALESCE(input_tokens,0) i, COALESCE(output_tokens,0) o, COALESCE(cache_creation_tokens,0) cw,"
                     f" COALESCE(cache_read_tokens,0) cr FROM attempts a JOIN runs USING(run_key) WHERE {billed_cond(_BILLED)}"
                     f" AND ({_REASON}) IN {USABLE_REASONS!r}"):
        c = _cost(cfg, r["model"], r["i"], r["o"], r["cw"], r["cr"], max_call_prompt=r["i"])
        c = None if c is None else Fraction(c)
        att_cost[r["model"]] = None if c is None or att_cost.get(r["model"], Fraction(0)) is None else att_cost.get(r["model"], Fraction(0)) + c
    done_runs = {r["model"]: r["n"] for r in store.q("SELECT model, COUNT(*) n FROM runs WHERE status='done' GROUP BY model")}
    bounds = bounded_usage(store, cfg, _BILLED, rows)
    pending: dict[str, int] = {}
    for (_b, _o, _l, m), c in cells.items():
        pending[m] = pending.get(m, 0) + c["pending"]
    # --- spend so far: a model is unknown when its price or any of its token counts cannot be trusted
    # every Claude model the store knows, not only those scheduled now: spend of a model dropped from the configuration is spend
    seen = set(rows) | set(pending) | set(done_runs)
    api = sorted(set(cfg.api_models) | {m for m in seen if m.startswith("claude-")})
    spent: dict[str, Fraction] = {}
    recorded: dict[str, Fraction] = {}
    spent_unknown: list[str] = []
    for m in api:
        r = rows.get(m)
        if _cost(cfg, m, 0, 0) is None:
            if r is not None or pending.get(m):
                spent_unknown.append(f"{m}: price not set")
            continue
        if r is None:
            spent[m] = recorded[m] = Fraction(0)   # priced, and no attempt has been billed
            continue
        if m in bounds and bounds[m]["unknown"]:
            spent_unknown += bounds[m]["unknown"]
            continue
        recorded[m] = att_cost.get(m, Fraction(0))
        spent[m] = recorded[m] + (bounds[m]["usd"] if m in bounds else Fraction(0))
    cs = coder_spend(cfg, coder_work_dir if coder_work_dir is not None else cfg.coder_work_dir,
                     coder_packets_dir if coder_packets_dir is not None else cfg.coder_packets_dir,
                     coder_expected_packets if coder_expected_packets is not None else cfg.coder_expected_packets)
    past = Fraction(str(cfg.past_spend_usd))        # test spend before the campaign: stated, with its source, in cfg
    spent_total = (sum(spent.values(), Fraction(0)) + cs["spent"] + past) if not spent_unknown and cs["spent"] is not None else None
    # --- projection: per model the mean spend per finished run x the runs it still has
    remaining: dict[str, Fraction] = {}
    proj_unknown: list[str] = []
    for m in api:
        n = pending.get(m, 0)
        if not n or m not in spent:
            continue
        if not done_runs.get(m):
            proj_unknown.append(f"{m}: {n} run(s) pending but no finished run to take a mean spend from")
        else:
            remaining[m] = recorded[m] / Fraction(done_runs[m]) * Fraction(n)
    coder_rem = None
    if cs["remaining"] is not None and (cs["cost_per_packet"] is not None or cs["remaining"] == 0):
        coder_rem = (cs["cost_per_packet"] or Fraction(0)) * Fraction(cs["remaining"])
    need = [m for m in api if pending.get(m)]
    projected = None
    if spent_total is not None and coder_rem is not None and all(m in remaining for m in need):
        projected = spent_total + sum(remaining.values(), Fraction(0)) + coder_rem
    unknown_all = sorted(set(spent_unknown + proj_unknown + cs["unknown"]))
    info = {"limit_usd": float(limit), "spent_usd": None if spent_total is None else float(spent_total),
            "projected_usd": None if projected is None else float(projected),
            "spent_by_model": {m: float(v) for m, v in spent.items()},
            "bounded": bounded_for_status(bounds),
            "remaining_by_model": {m: float(v) for m, v in remaining.items()},
            "coders": {"spent_usd": None if cs["spent"] is None else float(cs["spent"]), "packets_done": cs["packets_done"],
                       "packets_remaining": cs["remaining"], "remaining_usd": None if coder_rem is None else float(coder_rem),
                       "finished_spent_usd": None if cs["finished_spent"] is None else float(cs["finished_spent"]),
                       # what part of the coders' spent figure is not a measurement (coder_spend): zero = failed before billing, estimated = an upper bound
                       "zero_attempts": cs["zero_attempts"], "zero_reasons": dict(cs["zero_reasons"]),
                       "estimated_attempts": cs["estimated_attempts"], "estimated_usd": float(cs["estimated_usd"]),
                       "estimated_reasons": dict(cs["estimated_reasons"]),
                       "by_model": {m: float(v) for m, v in cs["by_model"].items()}, "notes": list(cs["notes"])},
            "unknown": unknown_all}
    alarms: list[str] = []
    note = _coder_bound_note(info["coders"]) + _bounded_note(info["bounded"])
    for m, b in info["bounded"].items():       # the bound is charged whatever the count; this many ended attempts without a record is something to look at
        lost = b["by_reason"].get("no_usage", 0)
        if lost > cfg.lost_usage_alarm_after:
            alarms.append(f"USAGE RECORDS LOST: {m}: {lost} attempt(s) ended with no usage recorded (more than {cfg.lost_usage_alarm_after}): something is losing usage "
                          f"records. Each is charged the bound, the run token budget at the dearest rate (${b['usd']:,.2f} for this model's bounded attempts in all), in the "
                          "spend and never in the per-run mean; nothing is stopped")
    if spent_total is not None and spent_total >= limit:
        alarms.append(f"SPEND ALARM: spent ${float(spent_total):,.2f} has reached the ${float(limit):,.0f} limit" + note)
    elif projected is not None and projected >= limit:
        alarms.append(f"SPEND ALARM: projected spend at the finish ${float(projected):,.2f} reaches the ${float(limit):,.0f} limit "
                      f"(spent ${float(spent_total):,.2f} + remaining campaign ${float(sum(remaining.values(), Fraction(0))):,.2f} + coders ${float(coder_rem):,.2f})" + note)
    elif projected is None:
        alarms.append(f"SPEND ALARM: spend or projected spend is UNKNOWN, treated as over the ${float(limit):,.0f} limit: "
                      + "; ".join(unknown_all) + note)
    return info, alarms


def _coder_bound_note(c: dict[str, Any] | None) -> str:
    """Words for a reader of the status: part of the coders' figure is an upper bound or counted zero (empty when none is)."""
    if not c or not (c.get("estimated_attempts") or c.get("zero_attempts")):
        return ""
    parts = []
    if c.get("estimated_attempts"):
        parts.append(f"{c['estimated_attempts']} coder attempt(s) ESTIMATED at an upper bound (${c['estimated_usd']:,.2f} of the spent figure is a bound, not a measurement)")
    if c.get("zero_attempts"):
        parts.append(f"{c['zero_attempts']} coder attempt(s) counted ZERO (failed before billing)")
    return " [" + "; ".join(parts) + "]"


def _bounded_note(b: dict[str, dict[str, Any]] | None) -> str:
    """Words for a reader of the status: the Claude campaign attempts charged at an upper bound, apart from the coders' estimated attempts (empty when none)."""
    if not b:
        return ""
    n, usd = sum(x["attempts"] for x in b.values()), sum(x["usd"] for x in b.values())
    per = "; ".join(f"{m}: " + ", ".join(f"{k} {v}" for k, v in x["by_reason"].items()) + f" = ${x['usd']:,.2f}" for m, x in sorted(b.items()))
    return (f" [{n} Claude campaign attempt(s) BOUNDED at an upper bound, ${usd:,.2f} in all, counted in the spend and not a measurement: a cut request is "
            f"charged at its largest input (one token per byte) and the output cap, an unreadable count at the largest complete attempt, an attempt with no usage "
            f"at the ceiling of one attempt ({per})]")


def _utc(x: str | None) -> dt.datetime | None:
    if not x:
        return None
    try:
        t = dt.datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t


def _held_alarms(store: Store, cfg: CampaignConfig, now: dt.datetime) -> list[str]:
    """A dispatch loop that starts nothing must never wait silently: runs pending, none in flight, and no start for
    `alarm_no_start_s` since this process began looking is an alarm, whatever holds it (the other alarms say why; if none does,
    nothing is dispatchable). After the hard stop nothing starts by design. And a loop that stopped looking is an alarm too."""
    pend = store.q("SELECT COUNT(*) n FROM runs WHERE status='pending'")[0]["n"]
    if not pend:
        return []
    out = []
    try:
        hard = cfg.hard_stop()
    except Exception:  # noqa: BLE001 - an unreadable hard stop is alarmed where it is read; here it only cannot excuse a hold
        hard = None
    past_hard = hard is not None and now >= hard
    running = store.q("SELECT COUNT(*) n FROM attempts WHERE state='running'")[0]["n"]
    refs = [t for t in (_utc(store.q("SELECT MAX(started_utc) t FROM attempts")[0]["t"]), _utc(store.get_meta("dispatch_since"))) if t]
    if not running and refs and not past_hard:
        idle = (now - max(refs)).total_seconds()
        if idle > cfg.alarm_no_start_s:
            out.append(f"NO RUN HAS STARTED for {idle / 60:.0f} min with {pend} run(s) pending and none in flight: dispatch is held; "
                       "the other alarms say why, and if none does, nothing is dispatchable (look at the slots, the slot gate and the caps)")
    alive = _utc(store.get_meta("dispatch_alive"))
    if alive is not None and not past_hard and (now - alive).total_seconds() > cfg.alarm_dispatch_stale_s:
        out.append(f"the campaign's dispatch loop last looked {(now - alive).total_seconds() / 60:.0f} min ago with {pend} run(s) pending: "
                   "the campaign process may have stopped or hung")
    return out


def _failed_precheck_entries(store: Store, cut: dt.datetime) -> dict[str, dict[str, int]]:
    """Science, #34, 21:45Z: a failed pre-run health check before the cut (no sandbox started, no executor ran) counts as the run's first dispatch, so the run
    is in the cohort; how many entered that way, per option: `real_start_after_cut`, and `no_real_start_yet`. A run also deferred before the cut, or really
    started before it, entered by that instead and is not counted."""
    from .errors import PRE_CHECK_FAILED
    by_run: dict[str, list] = {}
    for r in store.q("SELECT r.run_key, r.option, r.deferred_utc, a.started_utc, a.infra_detail FROM attempts a JOIN runs r USING(run_key) "
                     "WHERE a.state != 'unstarted' AND a.started_utc IS NOT NULL"):
        by_run.setdefault(r["run_key"], []).append(r)
    when = lambda ts: dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))  # noqa: E731
    out: dict[str, dict[str, int]] = {}
    for rows in by_run.values():
        rows.sort(key=lambda r: when(r["started_utc"]))
        pre = lambda r: (r["infra_detail"] or "").startswith(PRE_CHECK_FAILED)  # noqa: E731
        if not pre(rows[0]) or when(rows[0]["started_utc"]) >= cut or (rows[0]["deferred_utc"] and when(rows[0]["deferred_utc"]) < cut):
            continue
        real = next((r for r in rows if not pre(r)), None)
        if real is not None and when(real["started_utc"]) < cut:
            continue
        o = out.setdefault(rows[0]["option"], {"real_start_after_cut": 0, "no_real_start_yet": 0})
        o["no_real_start_yet" if real is None else "real_start_after_cut"] += 1
    return dict(sorted(out.items()))


def _retries_pending(store: Store, first: dict[str, dt.datetime], cut: dt.datetime) -> list[dict]:
    """Science, #34, 21:14Z: the cohort's runs with a retry pending (started by the cut, not finished, nothing of theirs in flight), per option x layout x
    model: past the hard stop they wait for the operator's word, and are released as one batch, never by option."""
    cells: dict[tuple, int] = {}
    for r in store.q("SELECT r.run_key, r.option, r.layout, r.model FROM runs r WHERE r.status='pending' "
                     "AND EXISTS (SELECT 1 FROM attempts a WHERE a.run_key=r.run_key AND a.state NOT IN ('unstarted','running')) "
                     "AND NOT EXISTS (SELECT 1 FROM attempts a WHERE a.run_key=r.run_key AND a.state='running')"):
        if r["run_key"] in first and first[r["run_key"]] < cut:
            k = (r["option"], r["layout"], r["model"])
            cells[k] = cells.get(k, 0) + 1
    return [{"option": o, "layout": la, "model": m, "runs": n} for (o, la, m), n in sorted(cells.items())]


def _deferred_report(store: Store, cfg: CampaignConfig, cut: dt.datetime) -> dict:
    """Amendment 24, science's #34, 21:14Z: the runs deferred before the cut, by reason apart, and the last one's start and finish against the hard
    stop, so the analysis knows when the cohort is complete: `deferred_complete` says each has its final outcome (a retry pending is not one)."""
    try:
        hard = cfg.hard_stop()
    except ValueError:
        hard = None

    def against(k: str | None, ts: str | None) -> dict | None:
        if ts is None:
            return None
        return {"run_key": k, "utc": ts, "after_hard_stop_s": None if hard is None else round((dt.datetime.fromisoformat(ts) - hard).total_seconds(), 1)}
    why: dict[str, int] = {}
    unfinished = 0
    last_start: tuple[str, str] | None = None
    last_finish: tuple[str, str] | None = None
    for r in store.q("SELECT r.run_key, r.status, r.deferred_utc, r.deferred_why, "
                     "(SELECT MAX(a.started_utc) FROM attempts a WHERE a.run_key=r.run_key AND a.state != 'unstarted') s, "
                     "(SELECT MAX(a.ended_utc) FROM attempts a WHERE a.run_key=r.run_key AND a.state != 'unstarted') e "
                     "FROM runs r WHERE r.deferred_utc IS NOT NULL"):
        if dt.datetime.fromisoformat(r["deferred_utc"]) >= cut:
            continue
        w = r["deferred_why"] or "unknown"
        why[w] = why.get(w, 0) + 1
        final = r["status"] not in ("pending", "harness_error")      # a harness_error is re-queued when the campaign reopens: no final outcome (final pass S3 #3)
        if not final:
            unfinished += 1
        if r["s"] and (last_start is None or r["s"] > last_start[1]):
            last_start = (r["run_key"], r["s"])
        if r["e"] and final and (last_finish is None or r["e"] > last_finish[1]):
            last_finish = (r["run_key"], r["e"])
    return {"deferred_by_reason": dict(sorted(why.items())), "deferred_unfinished": unfinished, "deferred_complete": unfinished == 0,
            "deferred_last_start": against(*last_start) if last_start else None, "deferred_last_finish": against(*last_finish) if last_finish else None}


def quiet_window_state(store: Store, cfg: CampaignConfig) -> tuple[dict | None, list[str]]:
    """Amendment 29(g): the quiet window of M+'s timed measurements and the registered curve. While it is open, dispatch is paused for all options, the runs in flight
    finish, and only a file at `quiet_window_release_file` naming who and why resumes it (used once). Nothing is stopped. Other lanes run the measurements."""
    try:
        q = json.loads(store.get_meta("quiet_window") or "null")
    except ValueError:
        return {"error": "unreadable record"}, ["quiet window: its record in the campaign state is unreadable; whether dispatch is paused for it is unknown"]
    if not q:
        return None, []
    alarms: list[str] = []
    if q.get("opened_utc") and not q.get("released_by"):
        n = store.q("SELECT COUNT(*) c FROM attempts WHERE state='running'")[0]["c"]

        def held(key: str) -> int:
            try:
                return len(json.loads(store.get_meta(key) or "null") or [])
            except (ValueError, TypeError):
                return 0
        lost, left = held("host_orphans"), held("held_back_slot_users")      # a lost remote run may still read site_g, and so may a sandbox a dead dispatcher left
        alarms.append(f"the quiet window is OPEN since {q['opened_utc']} ({q.get('cause')}): dispatch is PAUSED for all options, {n + lost + left} run(s) still in flight "
                      f"({n} running, {lost} lost to a host and not shown gone, {left} sandbox(es) left by a dead dispatcher) finish; nothing is stopped. "
                      f"It resumes only on a file written now at {cfg.quiet_window_release_file} whose first line names who resumes it and why, used once")
    return q, alarms


def backend_hold_state(store: Store) -> tuple[dict, dict, dict, list[str]]:
    """Science, #34, 3 Nov 02:45Z (amendment 29(b)): the models with no usable backend (kept by the scheduler), those of them HELD at the seed boundary because it has lasted
    `no_backend_hold_s`, and, per held model and seed, how many runs of a later seed started ahead of its unstarted earlier one (`seed_crossings`). A standing alarm per held model."""
    def meta(key: str) -> Any:
        raw = store.get_meta(key)
        if raw is None:         # never written (the scheduler writes it when a model first loses its backend): nothing lost, not an unreadable record
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            return {"error": "unreadable record"}
    lost, counts = meta("backend_lost"), meta("seed_crossing_counts")
    alarms: list[str] = []
    if not isinstance(lost, dict) or "error" in lost:
        lost = {}
        alarms.append("the record of models without a usable backend is unreadable; whether a model is held at the seed boundary is unknown")
    if not isinstance(counts, dict) or "error" in counts:
        counts = {}
    held = {m: r for m, r in lost.items() if isinstance(r, dict) and r.get("held_utc")}
    for m, r in sorted(held.items()):
        n = sum(int(v) for v in (counts.get(m) or {}).values())
        alarms.append(f"model {m} has had no usable backend since {r.get('since_utc')} ({r.get('why')}): it counts as HELD at the seed boundary, so later seeds start ahead of its "
                      f"unstarted seed-1 runs ({n} run(s) so far, per seed in seed_crossings); when it returns its seed-1 runs go first")
    return held, lost, counts, alarms


def cohort_cut_report(store: Store, cfg: CampaignConfig) -> dict | None:
    """Science, #34, 17:22Z: at the cohort cut, the runs started by then by option per model and stage (block, seed) beside those planned, and per
    option the instances (model, seed, layout, instance) whose run of that option started by the cut but whose M run did not. None: no cut."""
    try:
        cut = cfg.cohort_cut()
    except ValueError as e:
        return {"error": f"the cohort cut cannot be read: {e}"}
    if cut is None:
        return None
    # a run's first start or its deferral sets its cohort, whenever its retries came (science, #34, 21:33Z; amendment 24), a deferred run not yet started too
    first = {k: dt.datetime.fromisoformat(v.replace("Z", "+00:00")) for k, v in store.counted_starts().items()}
    planned: dict[tuple, int] = {}
    started: dict[tuple, int] = {}
    by_unit: dict[tuple, set[str]] = {}
    for r in store.q("SELECT run_key, model, block, seed, option, layout, instance_id FROM runs"):
        k = (r["model"], r["block"], r["seed"], r["option"])
        planned[k] = planned.get(k, 0) + 1
        if r["run_key"] in first and first[r["run_key"]] < cut:
            started[k] = started.get(k, 0) + 1
            by_unit.setdefault((r["model"], r["seed"], r["layout"], r["instance_id"]), set()).add(r["option"])
    missing: dict[tuple, int] = {}
    for (m, sd, _lay, _iid), opts in by_unit.items():
        if "M" not in opts:
            for o in opts:
                missing[(m, sd, o)] = missing.get((m, sd, o), 0) + 1
    waiting = store.q("SELECT run_key, deferred_utc FROM runs r WHERE status='pending' AND deferred_utc IS NOT NULL "
                      "AND NOT EXISTS (SELECT 1 FROM attempts a WHERE a.run_key=r.run_key AND a.state != 'unstarted')")
    return {"cut_utc": cut.isoformat(), **_deferred_report(store, cfg, cut), "entered_by_failed_precheck": _failed_precheck_entries(store, cut), "retries_pending": (rp := _retries_pending(store, first, cut)),
            "retries_pending_total": sum(x["runs"] for x in rp),
            "deferred_not_started": sum(1 for r in waiting if dt.datetime.fromisoformat(r["deferred_utc"]) < cut),   # amendment 24: in cohort, and they still start
            "started": [{"model": m, "block": b, "seed": sd, "option": o, "started": started.get((m, b, sd, o), 0), "planned": n}
                        for (m, b, sd, o), n in sorted(planned.items())],
            "instances_missing_m": [{"model": m, "seed": sd, "option": o, "instances": n} for (m, sd, o), n in sorted(missing.items())],
            "instances_missing_m_by_option": {o: sum(n for (_, _, o2), n in missing.items() if o2 == o) for o in sorted({k[2] for k in missing})}}


def _start_by_option(store: Store) -> list[dict]:
    """Science, #34, 15:39Z: start times by option per stage (block, seed) and model, from each run's first started attempt, so any
    time-ordering by option that a host's option cap or its skip-ahead causes is visible."""
    first: dict[tuple, list[str]] = {}
    for r in store.q("SELECT r.model, r.block, r.seed, r.option, MIN(a.started_utc) s, r.deferred_utc d FROM attempts a JOIN runs r USING(run_key) "
                     "WHERE a.state != 'unstarted' AND a.started_utc IS NOT NULL GROUP BY a.run_key"):
        s = r["s"] if not r["d"] or r["s"] <= r["d"] else r["d"]          # amendment 24: a deferred run counts as started at its deferral
        first.setdefault((r["model"], r["block"], r["seed"], r["option"]), []).append(s)
    out = []
    for (m, b, sd, o), ts in sorted(first.items()):
        ts.sort()
        out.append({"model": m, "block": b, "seed": sd, "option": o, "n": len(ts), "first_utc": ts[0], "median_utc": ts[len(ts) // 2], "last_utc": ts[-1]})
    return out


def exhausted_by_option(store: Store, model: str | None = None) -> dict[str, dict[str, Any]]:
    """Per option (of one model, if given), the runs that ended infra-exhausted beside its done-or-exhausted ones (a run still pending or lost to a harness bug
    is neither). They are never scored and never imputed; this is where an option-dependent loss would show."""
    out: dict[str, dict[str, Any]] = {}
    for r in store.q("SELECT option, SUM(status='infra_exhausted') ex, SUM(status IN ('done','infra_exhausted')) fin FROM runs"
                     " WHERE (? IS NULL OR model=?) GROUP BY option", (model, model)):
        ex, fin = r["ex"] or 0, r["fin"] or 0
        out[r["option"]] = {"exhausted": ex, "finished_or_exhausted": fin, "rate": ex / fin if fin else 0.0}
    return out


def exhausted_by_model(store: Store) -> dict[str, dict[str, dict[str, Any]]]:
    """`exhausted_by_option` within each model (science, #34, 19:22Z: exhausted runs could cluster in one model's runs of one option)."""
    return {r["model"]: exhausted_by_option(store, r["model"]) for r in store.q("SELECT DISTINCT model FROM runs ORDER BY model")}


def _concentrated(by_option: dict[str, dict[str, Any]], cfg: CampaignConfig) -> dict[str, tuple[int, int, float]]:
    """option -> (the other options' exhausted, done-or-exhausted, rate) for each option at or over both thresholds."""
    tot_ex = sum(v["exhausted"] for v in by_option.values())
    tot_fin = sum(v["finished_or_exhausted"] for v in by_option.values())
    out = {}
    for o, v in sorted(by_option.items()):
        if v["exhausted"] < cfg.alarm_exhausted_min:
            continue
        o_ex, o_fin = tot_ex - v["exhausted"], tot_fin - v["finished_or_exhausted"]
        o_rate = o_ex / o_fin if o_fin else 0.0
        if o_ex and v["rate"] < cfg.alarm_exhausted_ratio * o_rate:
            continue
        out[o] = (o_ex, o_fin, o_rate)
    return out


def exhausted_alarms(by_option: dict[str, dict[str, Any]], cells: dict[tuple, dict[str, Any]], cfg: CampaignConfig,
                     by_model: dict[str, dict[str, dict[str, Any]]] | None = None) -> list[str]:
    """INFRA_EXHAUSTED CONCENTRATED in one option (science, #34, 2 Nov 18:35Z; thresholds and per model confirmed 19:22Z): the option has at least
    `alarm_exhausted_min` exhausted runs and its rate is at least `alarm_exhausted_ratio` times the pooled rate of the other options, or the other options
    have no exhausted run (whatever their number of runs). Computed pooled over the models and within each model: a pooled alarm names the models where
    the option is concentrated too; a concentration within a model that the pooled figures do not show is an alarm of its own. An alarm only: it stops
    nothing."""
    pooled = _concentrated(by_option, cfg)
    within = {m: _concentrated(bo, cfg) for m, bo in sorted((by_model or {}).items())}
    rule = f"(alarm at {cfg.alarm_exhausted_ratio:g}x and {cfg.alarm_exhausted_min} runs); never scored, never imputed: an option-dependent loss"
    alarms: list[str] = []
    for o in sorted({*pooled, *(o for c in within.values() for o in c)}):
        models = [m for m, c in within.items() if o in c]
        if o in pooled:
            v, (o_ex, o_fin, o_rate) = by_option[o], pooled[o]
            missing = ", ".join(f"{k[0]}/{k[2]}/{k[3]} {c['infra_exhausted']}" for k, c in sorted(cells.items()) if k[1] == o and c["infra_exhausted"])
            alarms.append(f"INFRA_EXHAUSTED CONCENTRATED in option {o}: {v['exhausted']} of {v['finished_or_exhausted']} done-or-exhausted runs ({v['rate']:.1%}) "
                          f"against {o_ex} of {o_fin} ({o_rate:.1%}) in the other options {rule}"
                          f"{'; within model ' + ', '.join(models) + ' too' if models else ''}. Missing by block/layout/model: {missing}")
            continue
        for m in models:
            v, (o_ex, o_fin, o_rate) = by_model[m][o], within[m][o]
            missing = ", ".join(f"{k[0]}/{k[2]} {c['infra_exhausted']}" for k, c in sorted(cells.items())
                                if k[1] == o and k[3] == m and c["infra_exhausted"])
            alarms.append(f"INFRA_EXHAUSTED CONCENTRATED in option {o} within model {m}: {v['exhausted']} of {v['finished_or_exhausted']} done-or-exhausted runs "
                          f"({v['rate']:.1%}) against {o_ex} of {o_fin} ({o_rate:.1%}) in {m}'s other options {rule} (not concentrated pooled over the models). "
                          f"Missing by block/layout: {missing}")
    return alarms


def opw_restarts(store: Store, cfg: CampaignConfig) -> dict:
    """The op_worker restarts so far (the restart log's windows) and the attempts they cost, per option x layout x model."""
    from icsa import opwrestart
    out: dict = {"log": cfg.site_g_restart_log, "restarts": [], "lost_by_cell": opwrestart.lost_by_cell(store)}
    if cfg.site_g_restart_log:
        try:
            out["restarts"] = opwrestart.windows(opwrestart.read_log(cfg.site_g_restart_log))
        except ValueError as e:
            out["unreadable"] = str(e)
    return out


def build_status(store: Store, cfg: CampaignConfig, now: dt.datetime, *, lease_dir: Path | None = None,
                 slot_map_path: Path | None = None, coder_work_dir: Path | None = None, coder_packets_dir: Path | None = None,
                 coder_expected_packets: int | None = None) -> dict[str, Any]:
    cells: dict[tuple, dict[str, Any]] = {}
    for r in store.q("SELECT block,option,layout,model,status,COUNT(*) n FROM runs GROUP BY 1,2,3,4,5"):
        c = cells.setdefault(tuple(r[k] for k in CELL), dict(
            total=0, done=0, pending=0, infra_exhausted=0, harness_error=0,
            attempts=0, infra_attempts=0))
        c["total"] += r["n"]
        c[r["status"]] += r["n"]
    for r in store.q(
            "SELECT block,option,layout,model,"
            " SUM(a.state IN ('done','infra_fail','harness_error')) fin,"
            " SUM(a.state='infra_fail') inf FROM attempts a JOIN runs USING(run_key) GROUP BY 1,2,3,4"):
        c = cells[tuple(r[k] for k in CELL)]
        c["attempts"], c["infra_attempts"] = r["fin"] or 0, r["inf"] or 0

    # Backend balance per cell: the share of runs (by their latest finished attempt) that ran on each backend.
    counts_b: dict[tuple, dict[str, int]] = {}
    counts_s: dict[tuple, dict[str, int]] = {}      # slot shares (the slot of each run's latest attempt)
    counts_f: dict[tuple, dict[str, int]] = {}      # system_fingerprint shares (as the slot gate knew it)
    for r in store.q(
            "SELECT block,option,layout,model,slot,slot_identity,COUNT(*) n FROM attempts a JOIN runs USING(run_key)"
            " WHERE a.id=(SELECT MAX(id) FROM attempts b WHERE b.run_key=a.run_key AND"
            " b.state IN ('done','infra_fail','harness_error')) GROUP BY 1,2,3,4,5,6"):  # one per run: its latest
        key = tuple(r[k] for k in CELL)
        d = counts_b.setdefault(key, {})
        b = backend_of(r["slot"])
        d[b] = d.get(b, 0) + r["n"]
        sl = counts_s.setdefault(key, {})
        sk = r["slot"] or "(none)"
        sl[sk] = sl.get(sk, 0) + r["n"]
        try:        # the fingerprint the slot gate knew when the attempt began (site_a slots only; site_b and Anthropic: "n/a"; a site_a attempt that kept none: "unrecorded", never "n/a")
            fp = (json.loads(r["slot_identity"]).get("fingerprint") or "unknown") if r["slot_identity"] else ("unrecorded" if b == "site_a" else "n/a")
        except (ValueError, AttributeError):
            fp = "unknown"
        cf = counts_f.setdefault(key, {})
        cf[fp] = cf.get(fp, 0) + r["n"]
    for key, c in cells.items():
        c["unfinished"] = c["total"] - c["done"]   # pending, infra-exhausted or harness error: never imputed
        tot_b = sum(counts_b.get(key, {}).values())
        c["backend_share"] = {b: n / tot_b for b, n in sorted(counts_b.get(key, {}).items())}
        c["slot_share"] = {b: n / tot_b for b, n in sorted(counts_s.get(key, {}).items())}
        c["fingerprint_share"] = {b: n / tot_b for b, n in sorted(counts_f.get(key, {}).items())}
    alarms: list[str] = []
    for key, c in cells.items():
        c["infra_rate"] = c["infra_attempts"] / c["attempts"] if c["attempts"] else 0.0
        if c["infra_rate"] > cfg.alarm_infra_rate:
            alarms.append(f"infra-failure rate {c['infra_rate']:.0%} > {cfg.alarm_infra_rate:.0%} in cell "
                          + "/".join(map(str, key)))
    windows = []
    open_ws = store.q("SELECT * FROM endpoint_windows WHERE up_utc IS NULL")
    # rows saved before the model column existed have none: an site_b unit is named after its model
    unit_model = {r["unit"]: r["model"] or (r["unit"][len("site_b:"):] if r["unit"].startswith("site_b:") else None)
                  for r in store.q("SELECT unit, model FROM unit_health")}
    parent_of = {w["model"]: w["parent"] for w in open_ws if w["parent"]}
    model_open = {w["model"] for w in open_ws if w["model"] not in unit_model and w["model"] not in parent_of}
    for w in open_ws:
        down_s = (now - dt.datetime.fromisoformat(w["down_utc"])).total_seconds()
        windows.append({"model": w["model"], "down_since": w["down_utc"], "down_s": down_s,
                        "reason": w["reason"], "parent": w["parent"]})     # a unit's window names its model; a model's has none (the operator queue reads it)
        # a unit (slot, site_b) whose model window is open too would alarm twice: the model alarm covers it
        if down_s > cfg.alarm_endpoint_down_s and (parent_of.get(w["model"]) or unit_model.get(w["model"])) not in model_open:
            alarms.append(f"endpoint for {w['model']} down {down_s / 60:.0f} min"
                          f"{' (' + w['reason'] + ')' if w['reason'] else ''} "
                          f"(> {cfg.alarm_endpoint_down_s / 60:.0f} min)")

    if cfg.open_models:
        eps = read_endpoints(cfg.endpoints_file)
        if eps is None:     # alarmed whatever the freshness rule: dispatch holds every site_a slot meanwhile
            alarms.append(f"endpoints file {cfg.endpoints_file} unreadable: slot availability is unknown; no site_a slot is dispatched")
        elif cfg.endpoints_max_age_s is not None:
            for sl in stale_slots(eps, now, cfg.endpoints_max_age_s):
                alarms.append(f"endpoints.json: slot {sl} claims up but its checked_utc is absent or older than "
                              f"{cfg.endpoints_max_age_s:.0f} s: treated as DOWN (not a dispatch candidate, counted 0)")
    projections, proj_alarms = _projections(store, cfg, cells, now)
    alarms += proj_alarms
    tcc = time_cap_by_cell(store)
    alarms += time_cap_alarms(tcc, cfg)

    spend, spend_alarms = spend_alarm(store, cfg, cells, coder_work_dir=coder_work_dir, coder_packets_dir=coder_packets_dir,
                                      coder_expected_packets=coder_expected_packets)
    alarms += spend_alarms
    tot = store.q(
        "SELECT COALESCE(SUM(input_tokens),0) i, COALESCE(SUM(output_tokens),0) o,"
        " COALESCE(SUM(bytes_into_context),0) b, SUM(bytes_moved) m, COUNT(bytes_moved) m_known, COUNT(*) m_all,"
        " COALESCE(AVG(CASE WHEN state='done' THEN wall_s END),0) w FROM attempts "
        "WHERE state IN ('done','infra_fail','harness_error','interrupted')")[0]  # interrupted: billed usage
    usd: dict[str, float | None] = {}
    for r in store.q("SELECT model, COALESCE(input_tokens,0) i, COALESCE(output_tokens,0) o, COALESCE(cache_creation_tokens,0) cw,"
                     " COALESCE(cache_read_tokens,0) cr FROM attempts JOIN runs USING(run_key)"
                     " WHERE state IN ('done','infra_fail','harness_error','interrupted')"):
        if r["model"] in cfg.api_models:
            c = _cost(cfg, r["model"], r["i"], r["o"], r["cw"], r["cr"], max_call_prompt=r["i"])   # attempt by attempt, as the alarm
            prev = usd.get(r["model"], 0.0)
            usd[r["model"]] = None if c is None or prev is None else prev + float(c)
    known = [v for v in usd.values() if v is not None]
    remaining = sum(c["pending"] for c in cells.values())
    # capacity of the backends that still have pending runs only (finished models free no sandbox for the rest)
    conc = _concurrency(cfg, {m for (_, _, _, m), c in cells.items() if c["pending"]}, now, _blocked_slots(store))
    eta_s = remaining * tot["w"] / conc if tot["w"] and conc else None      # unknown capacity: no ETA
    counts = {s: sum(c[s] for c in cells.values())
              for s in ("total", "done", "pending", "infra_exhausted", "harness_error")}
    per_option: dict[str, dict[str, int]] = {}
    for r in store.q(
            "SELECT option, COUNT(*) att, SUM(a.state='infra_fail') inf, SUM(a.state='harness_error') he FROM attempts a "
            "JOIN runs USING(run_key) WHERE a.state IN ('done','infra_fail','harness_error') GROUP BY option"):
        per_option[r["option"]] = {"attempts": r["att"], "infra_failures": r["inf"] or 0, "harness_errors": r["he"] or 0}
    for r in store.q("SELECT option, COUNT(*) n FROM runs WHERE status='infra_exhausted' GROUP BY option"):
        per_option.setdefault(r["option"], {"attempts": 0, "infra_failures": 0, "harness_errors": 0})["exhausted_runs"] = r["n"]
    slot_users, slot_alarms = slot_user_alarms(lease_dir, slot_map_path, slot_need_by_option(cfg), _since(store))
    alarms += slot_alarms
    se_raw = store.get_meta("slot_equality")
    try:
        slot_equality = json.loads(se_raw) if se_raw else None
        alarms += alarms_from_state(slot_equality)
    except (ValueError, KeyError, TypeError):
        slot_equality = None
        alarms.append("site_a slot equality: the recorded state is unreadable, so whether slots match is unknown")
    hm = store.get_meta("host_memory")
    host_memory = json.loads(hm) if hm else {"enabled": bool(cfg.host_mem_pause_below_gib), "paused": False, "readable": None,
                                             "note": "no reading recorded yet"}
    if host_memory.get("paused"):
        alarms.append(f"dispatch is PAUSED by the host-memory watchdog: available {host_memory.get('available_gib')} GiB < "
                      f"{host_memory.get('pause_below_gib'):g} GiB (resumes at {host_memory.get('resume_at_gib'):g} GiB; nothing is killed)")
    if host_memory.get("enabled") and host_memory.get("readable") is False:
        alarms.append("host memory could not be read: the watchdog neither pauses nor resumes (state unknown)")
    onedata_outages = healthgate.fact(store.get_meta(healthgate.META))      # science, #34, 3 Nov 03:27Z: every outage with its start, its end and how it ended
    alarms += healthgate.alarms(onedata_outages, cfg.onedata_pause_s)
    try:
        ld = json.loads(store.get_meta("local_disk") or "null")
    except ValueError:
        ld = {"held": True, "free_gib": None, "floor_gib": None}
    if ld and ld.get("held"):
        alarms.append(f"this run host's disk is {'UNREADABLE' if ld.get('free_gib') is None else 'LOW: ' + str(ld['free_gib']) + ' GiB free'} against a "
                      f"floor of {ld.get('floor_gib')} GiB: nothing new starts on it (runs in flight go on)")
    try:
        back = json.loads(store.get_meta("held_back_slot_users") or "[]")
    except ValueError:
        back = ["unreadable"]
    if back:
        alarms.append(f"{len(back)} slot user(s) held back on this host, a dead run's sandbox not shown gone (a mount that could not be released, or its record could not be collected, so its disks are kept): counted as in flight, "
                      f"retried each minute; look at the host: {back}")
    if store.get_meta("held_back_unknown"):      # set by a sweep that raised, cleared only by one that read the pool: stands until then
        alarms.append(f"the sweep for a dead run's leftover sandboxes could not read this host's slot pool ({store.get_meta('held_back_unknown')}): whether any slot user is "
                      "held back is UNKNOWN, and only the ones last known stuck are counted as in flight. Dispatch goes on, as the lease itself gives a key whose dead holder's "
                      "sandbox is not shown gone to nobody; retried each minute, look at the host if this lasts")
    try:
        pr = json.loads(store.get_meta("process_reservations") or "{}")
    except ValueError:
        pr = {"unreadable": {"?": "the record of the reservations is unreadable"}}
    if pr.get("unreadable"):                     # a lock that cannot be read counts as held (icsa/harness/reservation.py): its sandboxes stay counted and its keys stay out of the pool
        alarms.append(f"process reservation lock(s) UNREADABLE, counted as held until they can be read: {pr['unreadable']}. Fault calibration's or the validation set's sandboxes "
                      "stay counted in every cap and their slot keys stay out of the pool; look at the reservation directory")
    hosts = start_by_option = None
    if getattr(cfg, "hosts", None):          # two run hosts (hosts.py): each host's holds, downs and lost runs still counted
        try:
            hosts = json.loads(store.get_meta("hosts") or "null")
        except ValueError:
            hosts = None
        if hosts is None:
            alarms.append("run hosts: no host state recorded yet, or it is unreadable: whether the remote host takes runs is unknown")
        else:
            for h, why in sorted((hosts.get("down") or {}).items()):
                alarms.append(f"run host {h} is DOWN ({why}): its models' dispatch is paused, the other host goes on")
            for h, why in sorted((hosts.get("holds") or {}).items()):
                if h not in (hosts.get("down") or {}):
                    alarms.append(f"run host {h} takes no new runs: {why}")
            open_on = {h for m, h in (getattr(cfg, "model_host", None) or {}).items() if m in (cfg.open_models or {})}
            for h, pr in sorted((hosts.get("probes") or {}).items()):
                if pr.get("unreaped"):
                    alarms.append(f"run host {h}: {pr['unreaped']} worker(s) died and their sandboxes are not shown gone yet: counted as in flight, a reaper retries; "
                                  "if this lasts, a mount could not be released or a record could not be collected (its disks are kept): look at the host")
                if h in open_on and pr.get("ok") and pr.get("endpoints_readable") is False:
                    alarms.append(f"run host {h}: its endpoints.json is unreadable: its models' site_a slots are unknown, none is dispatched "
                                  "(site_b only, where it has caps)")
                pool = pr.get("pool")
                if pool is None or "_error" in pool:
                    alarms.append(f"run host {h}: its slot-user pool is unreadable ({(pool or {}).get('_error', 'not reported')}): whether its runs wait "
                                  "for a user, or hold quarantined ones, is unknown")
                else:
                    alarms += [f"run host {h}: {x}" for x in pool_alarm_lines(pool)]
            try:
                mb = json.loads(store.get_meta("m_backlog") or "null")
            except ValueError:
                mb = {"state": "unknown"}
            if mb and mb.get("state") == "growing":
                alarms.append(f"M BACKLOG GROWING: {mb.get('now')} M run(s) wait for a slot user ({mb.get('by_host')}), more than at the start of the "
                              f"last {mb.get('window_s', cfg.alarm_m_backlog_window_s):g} s and never fewer in between: M falls behind the other options")
            elif mb and mb.get("state") == "unknown":
                alarms.append(f"M backlog UNKNOWN: a host's slot-user pool could not be read ({mb.get('by_host')})")
            if hosts.get("orphans"):
                alarms.append(f"{len(hosts['orphans'])} run(s) lost with their host are still counted as in flight until it shows them gone: "
                              + ", ".join(hosts["orphans"][:5]))
        start_by_option = _start_by_option(store)
        hosts = {"plan": json.loads(store.get_meta("host_plan") or "null"), "assignment": store.get_meta("host_assignment"), "state": hosts,
                 "attempts_by_host": {r["h"] or "?": r["n"] for r in store.q("SELECT exec_host h, COUNT(*) n FROM attempts GROUP BY exec_host")}}
    from . import gate as _gate
    sg = _gate.evaluate(store, cfg, latch=False)       # read-only: only the scheduler decides
    after = sg.get("hold_after_seed")                       # the gate holds the seeds after this one (0: every seed, before pricing)
    held_runs = store.q("SELECT COUNT(*) c FROM runs WHERE model=? AND status='pending' AND block NOT IN ('pilot','calibration') AND seed > ?",
                        (cfg.gate_model, after if after is not None else 1 << 30))[0]["c"] if cfg.gate_model else 0
    if sg["state"] == "hold_unpriced" and held_runs:       # only worth an alarm while Sonnet main runs actually wait
        alarms.append(f"Sonnet main runs wait for pricing: {sg['priced_runs']}")
    elif sg["held"] and held_runs:
        sip = sg.get("seed_in_progress")
        alarms.append(f"Sonnet main runs HELD: the seeds after seed {after} (the highest authorised; seed {sip} is in progress"
                      f"{' and held' if sip is not None and after is not None and sip > after else ': it goes on'}): projected Claude total "
                      f"{'unknown' if sg['projected_usd'] is None else '%.0f USD (limit %.0f)' % (sg['projected_usd'], sg['max_usd'])}; "
                      f"Haiku and the open models continue; release by writing the file {sg['release_file']} now: one older than this decision does not count")
    try:
        rc = json.loads(store.get_meta("read_check") or "null")
    except ValueError:
        rc = {"state": "unknown", "why": "unreadable record", "group": "?"}
    if rc and rc["state"] == "low":
        alarms.append(f"site_g read check LOW before {rc.get('group')}: {rc['why']}; the block does not start (op_worker rss {rc.get('op_worker_rss_mb')} MB)")
    elif rc and rc["state"] == "unknown":
        alarms.append(f"site_g read check UNKNOWN before {rc.get('group')}: {rc['why']}; dispatch is HELD")
    hard = cohort = None
    try:
        hard, cohort = cfg.hard_stop(), cfg.cohort_cut()
    except ValueError as e:
        alarms.append(f"the hard stop or the cohort cut cannot be read ({e}): when dispatch stops is unknown")
    ccr = cohort_cut_report(store, cfg)
    if hard is not None and now >= hard and not store.get_meta("hard_stop_released"):
        alarms.append(f"the hard stop {hard.isoformat()} has passed: dispatch is STOPPED and runs in flight finish; {sum(c['unfinished'] for c in cells.values())} run(s) "
                      f"unfinished, listed by cell; it resumes only on the operator's word, a file written now at {cfg.hard_stop_release_file}, used once")
        if ccr and ccr.get("retries_pending"):      # every one, so the operator releases them as one batch, never by option (science, #34, 21:14Z)
            alarms.append(f"{ccr['retries_pending_total']} cohort run(s) have a retry pending past the hard stop, released as ONE batch by that word, never by option: "
                          + ", ".join(f"{x['option']}/{x['layout']}/{x['model']} {x['runs']}" for x in ccr["retries_pending"]))
        if ccr and ccr.get("deferred_not_started"):  # amendment 24: not stopped
            alarms.append(f"{ccr['deferred_not_started']} run(s) deferred by their cap or disk before the cohort cut are still to start: they go as their bound allows, "
                          "past the hard stop, and the cohort is not complete until they finish")
    quiet, quiet_alarms = quiet_window_state(store, cfg)
    alarms += quiet_alarms
    held_models, no_backend, seed_crossings, held_alarms = backend_hold_state(store)
    alarms += held_alarms
    out_of_cohort = None
    if cohort is not None:
        starts = store.counted_starts()           # by its first start or deferral, not by the attempt that finished it (science, #34, 21:33Z)
        out_of_cohort = sum(1 for r in store.q("SELECT DISTINCT run_key FROM attempts WHERE state='done'")
                            if r["run_key"] in starts and dt.datetime.fromisoformat(starts[r["run_key"]].replace("Z", "+00:00")) >= cohort)
    try:
        fincore = json.loads(store.get_meta("fincore") or "null")
    except ValueError:
        fincore = {"state": "unknown", "why": "unreadable record"}
    if fincore and fincore.get("state") == "low":
        alarms.append(f"site_g's page cache: the study file's warm share is {fincore.get('last')}, against {fincore.get('reference')} at first, {fincore.get('low_streak')} readings in a row; "
                      "dispatch goes on, so look at whether to force a read check")
    elif fincore and fincore.get("state") == "unknown":
        alarms.append(f"site_g's page cache cannot be read ({fincore.get('why')}); dispatch goes on")
    try:        # site_g's memory (science, #34, 23:57Z): an alarm that stops nothing; a failure to judge it is itself unknown and said, never a crash of the status thread
        try:
            fm_rec = json.loads(store.get_meta("site_g_memory") or "null")
        except ValueError:
            fm_rec = "unreadable"
        site_g_memory, fm_alarms = site_g_memory_report(fm_rec, cfg, now)
    except Exception as e:  # noqa: BLE001
        site_g_memory, fm_alarms = site_g_memory_report(None, cfg, now)[0], [f"site_g's memory could not be judged ({type(e).__name__}): whether op_worker or the node is over its memory "
                                                                     "limit is unknown; an alarm only, nothing is stopped"]
        site_g_memory.update(state="unknown", why=f"the status could not judge it ({type(e).__name__})")
    alarms += fm_alarms
    ust = unstarted_streaks(store, cfg.unstarted_stop_after)
    ust_said = ", ".join("the count is unreadable" if o == "*" else f"{o}: {n}" for o, n in sorted(ust.items()))
    if any(n >= cfg.unstarted_stop_after for n in ust.values()):
        alarms.append(f"runs in a row that could not start a sandbox ({ust_said}), every user of the option in quarantine, none in the slot map, or a start refused "
                      f"before any container (each attempt's detail says which); dispatch of ALL options is STOPPED (they used no attempt); resume by writing {cfg.unstarted_release_file} now: it ends this stop only, and one older than the stop does not count")
    elif ust:
        alarms.append(f"runs in a row that could not start a sandbox ({ust_said}); they used no attempt, dispatch of all options "
                      f"stops when one option reaches {cfg.unstarted_stop_after}")
    from . import harness_stop as HS
    he = HS.status(store, cfg, now)
    alarms += HS.alarms(he, cfg)
    exh = exhausted_by_option(store)
    alarms += exhausted_alarms(exh, cells, cfg, exhausted_by_model(store))
    try:
        served_stop = json.loads(store.get_meta("served_settings") or "{}")
    except ValueError:
        served_stop = {}
        alarms.append("the served-settings record is unreadable: whether the servers ran the frozen settings is unknown")
    for m, v in sorted(served_stop.items()):
        alarms.append(f"SERVER SETTINGS DIFFER for {m} (run {v.get('run_key')}): " + "; ".join(v.get("reasons", [])) + "; dispatch of this model is STOPPED")
    unrep = store.q("SELECT DISTINCT model FROM events WHERE kind='served_settings_unreported'")
    for r in unrep:
        alarms.append(f"{r['model']}: the server reported no model id in a run, so the served model is unverified")
    for r in store.q("SELECT model, COUNT(*) n, MAX(id) last FROM events WHERE kind='site_b_fingerprint_changed' GROUP BY model ORDER BY model"):
        last = store.q("SELECT detail FROM events WHERE id=?", (r["last"],))[0]["detail"]
        alarms.append(f"{r['model']}: site_b's system_fingerprint CHANGED during the campaign ({r['n']} time(s); latest: {last}); "
                      "recorded per run, dispatch continues")
    alarms += _held_alarms(store, cfg, now)
    from . import operator_queue
    alarms += operator_queue.queue_alarms(store)
    key_rejected = operator_queue.key_rejections(store)
    alarms += operator_queue.key_alarms(key_rejected, cfg.key_rejected_pause_s)
    alarms += operator_queue.canary_alarms(operator_queue.canary_fact(store), cfg)
    if store.q("SELECT 1 FROM events WHERE kind='site_b_fingerprint_record_unreadable' LIMIT 1"):
        alarms.append("the stored record of site_b builds was unreadable: a build change before that point may be unrecorded")
    site_g_raw = store.get_meta("site_g_settings")
    site_g_settings: dict | None = None
    if site_g_raw:
        try:
            site_g_settings = json.loads(site_g_raw)
            age = (now - dt.datetime.fromisoformat(site_g_settings["checked_utc"])).total_seconds()
            if site_g_settings["state"] == "mismatch":
                alarms.append(f"site_g's SETTINGS CHANGED: hash {site_g_settings['hash']} differs from the frozen {site_g_settings['frozen']}; dispatch is STOPPED")
            elif site_g_settings["state"] == "unplanned":
                alarms.append(f"op_worker RESTARTED WITHOUT THE LOG ({site_g_settings['why']}); dispatch is STOPPED until an operator accepts it (opw-restart accept)")
            elif site_g_settings["state"] == "restart":
                alarms.append(f"an op_worker restart is under way or aborted ({site_g_settings['why']}); dispatch is HELD")
            elif site_g_settings["state"] == "unknown":
                alarms.append(f"site_g's settings hash is UNKNOWN ({site_g_settings['why']}); dispatch is HELD")
            elif site_g_settings["state"] != "off" and age > 3 * cfg.site_g_settings_every_s + 60:
                alarms.append(f"site_g's settings were last checked {age / 60:.0f} min ago: the check is not running (state unknown)")
        except (ValueError, KeyError, TypeError):
            site_g_settings = None
            alarms.append("site_g's settings record is unreadable: whether site_g is unchanged is unknown")
        try:
            fd = json.loads(store.get_meta("site_g_disk") or "null")
        except ValueError:
            fd = {"state": "unknown", "why": "unreadable record"}
        if fd and fd["state"] == "low":
            alarms.append(f"site_g's log volume is LOW: {fd['why']}; dispatch is STOPPED")
        elif fd and fd["state"] == "unknown":
            alarms.append(f"site_g's log volume free space is UNKNOWN ({fd['why']}); dispatch is HELD")
        try:
            lc = json.loads(store.get_meta("site_g_logcheck") or "null")
        except ValueError:
            lc = {"state": "unknown", "why": "unreadable record"}
        if lc and lc["state"] == "alarm":
            alarms.append(f"the kept-log check raised its ALARM ({lc['why']}); dispatch is STOPPED")
        elif lc and lc["state"] == "unknown":
            alarms.append(f"the kept-log check is UNKNOWN ({lc['why']}); dispatch is HELD")
    elif cfg.site_g_settings_required or cfg.site_g_settings_cmd:
        alarms.append("site_g's settings have never been checked by this campaign: dispatch has not started or the check is off")
    from . import livecheck as _lc
    live_check, live_alarms = _lc.status_block(store.get_meta(_lc.META), cfg, now.timestamp())      # amendment 25(e): the level in force, the probes, the alarms
    alarms += live_alarms
    bw = store.get_meta("block1_waits")
    from .export import container_deaths, host_pressure_kills
    from icsa.sandbox.infradeath import CAUSES
    pressure = [x for x in host_pressure_kills(store) if x["earlyoom"] or x["earlyoom_unattributed"] or x["host_oom"]]
    deaths = [x for x in container_deaths(store) if any(x[c] for c in CAUSES)]
    return {
        "host_pressure_kills": pressure, "container_deaths": deaths, "quiet_window": quiet, "held_models": held_models, "no_backend": no_backend, "seed_crossings": seed_crossings, "snapshot_utc": cfg.snapshot_utc, "quiet_window_utc": cfg.quiet_window_utc,
        "sonnet_gate": sg, "site_g_settings": site_g_settings, "read_check": rc, "served_settings_stopped": served_stop,
        "block1_waits_for_s2": json.loads(bw) if bw else {"count": 0, "total_s": 0.0},
        "host_memory": host_memory, "run_hosts": hosts, "start_by_option": start_by_option, "cohort_cut_report": ccr, "slot_users": slot_users, "slot_equality": slot_equality,
        "as_of": now.isoformat(), "counts": counts,
        "interrupted_attempts": store.q("SELECT COUNT(*) c FROM attempts WHERE state='interrupted'")[0]["c"],
        "eta_s": eta_s, "eta_note": "estimate: remaining runs x mean wall time / total provider caps",
        "input_tokens": tot["i"], "output_tokens": tot["o"],
        "bytes_into_context": tot["b"], "bytes_moved_between_sites": tot["m"],      # None when no attempt measured it: unknown, not zero
        "bytes_moved_coverage": {"attempts_with_a_measurement": tot["m_known"], "attempts": tot["m_all"]},
        "claude_usd": {"per_model": usd, "total": sum(known) if known and len(known) == len(usd) else None,
                       "note": "None = price not set in config (placeholder)"},
        "unfinished_by_cell": {"/".join(map(str, k)): c["unfinished"] for k, c in sorted(cells.items())
                               if c["unfinished"]},
        "spend_alarm": spend,
        "live_check": live_check,
        "fincore": fincore, "site_g_memory": site_g_memory, "cohort_cut_utc": cohort.isoformat() if cohort else None, "out_of_cohort_runs": out_of_cohort, "projections": projections, "cutoff_utc": cfg.cutoff_utc, "hard_stop_utc": cfg.hard_stop_utc,
        "harness_errors": he,
        "infra_exhausted_by_option": exh, "op_worker_restarts": opw_restarts(store, cfg),
        "unstarted_streaks": ust, "unstarted_canary": operator_queue.canary_fact(store), "dispatch_idle": operator_queue.idle_fact(store, cfg, now), "onedata_health": operator_queue.onedata_health(store), "onedata_outages": onedata_outages, "key_rejected": key_rejected,        # structured facts the operator queue reads
        "hard_stop_stopped": bool(hard is not None and now >= hard and not store.get_meta("hard_stop_released")),
        "per_option": per_option, "open_endpoint_windows": windows, "alarms": alarms,
        "backend_share_by_day": backend_share_by_day(store), "time_cap_by_cell": tcc,
        "cells": [dict(zip(CELL, k), **v) for k, v in sorted(cells.items())],
    }


def _spend_line(sp: dict[str, Any] | None) -> str:
    if not sp:
        return "spend alarm: no figures"
    f = lambda x: "UNKNOWN" if x is None else f"${x:,.2f}"  # noqa: E731
    return (f"spend (campaign + inspection coders) {f(sp['spent_usd'])}, projected at the finish {f(sp['projected_usd'])}, "
            f"limit ${sp['limit_usd']:,.0f}" + _coder_bound_note(sp.get("coders")) + _bounded_note(sp.get("bounded")))


def render(st: dict[str, Any]) -> str:
    c = st["counts"]
    eta = f"{st['eta_s'] / 3600:.1f} h" if st["eta_s"] is not None else "n/a"
    usd = st["claude_usd"]["total"]
    lines = [f"campaign as of {st['as_of']}",
             f"runs {c['done']}/{c['total']} done, {c['pending']} pending, "
             f"{c['infra_exhausted']} infra-exhausted, {c['harness_error']} harness errors; "
             f"{st['interrupted_attempts']} interrupted attempts",
             f"ETA {eta} ({st['eta_note']})",
             f"tokens in/out {st['input_tokens']}/{st['output_tokens']}; bytes into context "
             f"{st['bytes_into_context']}; bytes moved between sites "
             f"{'unknown' if st['bytes_moved_between_sites'] is None else st['bytes_moved_between_sites']}"
             f" ({st['bytes_moved_coverage']['attempts_with_a_measurement']} of {st['bytes_moved_coverage']['attempts']} attempts measured); "
             f"Claude USD {'n/a (price placeholder)' if usd is None else f'{usd:.2f}'}",
             *([f"Sonnet gate: {st['sonnet_gate']['state']}"
                + (f", projected Claude total {st['sonnet_gate']['projected_usd']:.0f} USD (limit {st['sonnet_gate']['max_usd']:.0f})"
                   if st['sonnet_gate']['projected_usd'] is not None else ", projected Claude total unknown")
                + (", Sonnet HELD" + (f" (seeds after {st['sonnet_gate']['hold_after_seed']})" if st['sonnet_gate'].get('hold_after_seed') else "")
                   if st['sonnet_gate']['held'] else "")
                + _gate_bounds_note(st['sonnet_gate'])] if st.get("sonnet_gate", {}).get("state", "off") != "off" else []),
             _spend_line(st.get("spend_alarm")),
             "", f"{'block':11} {'option':14} {'lay':3} {'model':22} {'done':>9} {'exh':>4} {'infra%':>7} {'unf':>5}  backends"]
    for x in st["cells"]:
        lines.append(f"{x['block']:11} {x['option']:14} {x['layout']:3} {x['model']:22} "
                     f"{x['done']:>4}/{x['total']:<4} {x['infra_exhausted']:>4} {x['infra_rate']:>7.0%} {x['unfinished']:>5}  "
                     + " ".join(f"{b}={v:.0%}" for b, v in x["backend_share"].items()))
    for p in st.get("projections", []):
        fin = f"{p['finish_utc'][:16]}Z (+{p['hours_left']:.1f} h)" if p["finish_utc"] else f"n/a ({p['note']})"
        lines.append(f"projected finish {p['group']}: {p['pending']} pending, {p['pending_cumulative']} cumulative: {fin}"
                     + (f"  [deadline {p['deadline_utc']}]" if p.get("deadline_utc") else ""))
    by_day = st.get("backend_share_by_day", [])
    if by_day:
        days = sorted({r["day_utc"] for r in by_day})
        lines += ["", "backend share of finished runs per cell and UTC day (analysed attempt):"]
        cd: dict[tuple, list[str]] = {}
        for r in by_day:
            if r["day_utc"] in days:
                cd.setdefault((r["day_utc"], r["model"], r["option"], r["layout"]), []).append(f"{r['backend']} {r['n']} ({r['share']:.0%})")
        lines += [f"  {d} {m} {o} {l}: " + ", ".join(v) for (d, m, o, l), v in sorted(cd.items())]
    if st.get("time_cap_by_cell"):
        lines += ["", "time-cap stops per model, option and backend (analysed attempt; a load diagnostic, the cap is unchanged):"]
        lines += [f"  {x['model']} {x['option']} {x['backend']}: {x['time_cap_stops']}/{x['n']} ({x['share']:.0%})"
                  for x in st["time_cap_by_cell"] if x["time_cap_stops"]] or ["  none"]
    hm = st.get("host_memory") or {}
    if hm.get("enabled"):
        lines += ["", "host memory watchdog: " + (f"PAUSED, available {hm.get('available_gib')} GiB" if hm.get("paused") else
                  f"running, available {hm.get('available_gib')} GiB" if hm.get("readable") else "state unknown (no reading)")
                  + (f" (pause below {hm['pause_below_gib']:g} GiB, resume at {hm['resume_at_gib']:g} GiB; "
                     f"{hm.get('pauses_this_process', 0)} pauses, {hm.get('paused_s_this_process', 0)} s paused in the current process)"
                     if "pause_below_gib" in hm else "")]
    lc = st.get("live_check") or {}
    if lc.get("ladder") is not None:
        eff = ", ".join(f"{g} {c['effective']}" + (f" (configured {c['configured']})" if c["effective"] != c["configured"] else "")
                        for g, c in sorted((lc.get("caps") or {}).items()) if c["configured"] is not None)
        last = "; ".join(f"{s} {x['kind']}" + (f" {x['ratio']:.2f}x" if x.get("ratio") is not None else "") + f" at {x['utc']}" for s, x in sorted((lc.get("last") or {}).items()))
        ch = "; ".join(f"{c['direction']} to step {c['steps']} at {c['utc']} by {c['who']}: {c['why']}" for c in (lc.get("changes") or [])[-3:])
        lines += ["", f"level in force: {lc['steps']} of {lc['max_steps']} step(s) below the configured caps; caps in force: {eff or 'none configured'}; changes: {ch or 'none'}",
                  f"live check (amendment 25(e)): last probes: {last or 'none yet'}; {lc['probes']} probes, {lc['skips']} skipped"]
    bw = st.get("block1_waits_for_s2") or {}
    if bw.get("count"):
        lines += ["", f"block-1 runs that waited for an S2 run to finish (S2 cap bounds everything in flight): {bw['count']} waits, {bw['total_s']} s in all"]
    lines += ["", "kills under host memory pressure (retried as infrastructure; they fall on the largest process, so a difference by option shows here):"]
    lines += [f"  {x['block']} {x['option']} {x['layout']} {x['model']}: {x['earlyoom']} earlyoom, {x['earlyoom_unattributed']} earlyoom nobody saw, {x['host_oom']} kernel, of {x['attempts']} attempts"
              for x in st.get("host_pressure_kills", [])] or ["  none"]
    lines += ["", "gate and sidecar deaths by cause (host_pressure, component_defect and undetermined are retried as infrastructure; own_limit_agent, the sidecar at its own memory limit, is the agent's outcome):"]
    lines += [f"  {x['block']} {x['option']} {x['layout']} {x['model']}: {x['host_pressure']} host_pressure, {x['component_defect']} component_defect, {x['undetermined']} undetermined, "
              f"{x['own_limit_agent']} own_limit_agent, of {x['attempts']} attempts" for x in st.get("container_deaths", [])] or ["  none"]
    he = st.get("harness_errors") or {}
    if he.get("all_time_by_kind"):
        lines += ["", f"harness errors (a bug of ours, not an outcome; the run is pending again after the fix; {he['stop_after']} of one kind on a model stop that model, one kind on {he['models_stop_after']} models stop all dispatch): "
                  + "; ".join(f"{k} {n} ({', '.join(f'{o} {m[k]}' for o, m in he['all_time_by_option'].items() if k in m)})" for k, n in he["all_time_by_kind"].items())]
    fm = st.get("site_g_memory") or {}
    if fm.get("state") not in (None, "off"):
        g = fm.get("growth") or {}
        n = lambda x, f: "n/a" if x is None else f.format(x)  # noqa: E731
        lines += [f"site_g memory ({fm['state']}; an alarm only, nothing is stopped): op_worker resident {n(fm.get('opw_rss_pct_node'), '{:g}')}% of the node, node "
                  f"{n(fm.get('node_mem_pct'), '{:g}')}% in use; op_worker resident {n(fm.get('opw_rss_mib'), '{:,.0f}')} MiB, growth "
                  + (f"{g['mib_per_h']:+,.1f} MiB/h" if g.get("mib_per_h") is not None else "n/a") + f" over the last {g.get('window_h', 0):g} h ({g.get('n', 0)} samples covering {g.get('span_h', 0):g} h)"
                  + (f"; {fm['why']}" if fm.get("why") else "") + (f"; {g['why']}" if g.get("why") and g.get("restarts_in_window") else "")]
    lines += ["", "per option: " + json.dumps(st["per_option"], sort_keys=True)]
    lines += ["ALARM: " + a for a in st["alarms"]] or ["no alarms"]
    return "\n".join(lines)


def write_status(store: Store, cfg: CampaignConfig, now: dt.datetime, path: Path) -> dict[str, Any]:
    st = build_status(store, cfg, now)
    write_backend_share_csv(st["backend_share_by_day"], path.with_name("backend_share_by_day.csv"))
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(st, indent=1))
    os.replace(tmp, path)
    return st


def record_slot_quarantine(store: Store, now: dt.datetime, lease_dir: Path | None = None, slot_map_path: Path | None = None) -> dict | None:
    """Copy the quarantine counts per option into the store (meta `slot_quarantine`), for the dossier. Called by the campaign
    process only (the read-only `status` command never writes). The durable record is the lease directory's quarantines.jsonl."""
    if store.get_meta("slot_quarantine_since") is None:
        store.put_meta("slot_quarantine_since", now.isoformat(), now.isoformat())      # set once: the start of this campaign's count
    st, _ = slot_user_alarms(lease_dir, slot_map_path, since=_since(store))
    if st is None:
        return None
    val = {opt: {k: o[k] for k in ("slots", "quarantined", "quarantines", "quarantine_slot_hours")} for opt, o in sorted(st.items())}
    store.put_meta("slot_quarantine", json.dumps(val), now.isoformat())
    return val
