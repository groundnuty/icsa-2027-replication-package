"""Diagnostics (not criteria), per option, one loop over a fixed option order: no per-option branches."""
from __future__ import annotations

import numpy as np

from icsa.analysis import adapter, secondary
from icsa.analysis.config import Config
from icsa.records import OmissionLabel, first_request_cut

ORDER = ("T", "D", "M")


def _row(rows, o):
    return [r for r in rows if r.run.option.value == o]


def render_import_errors(per_option_rows: list[dict]) -> list[str]:
    """The pilot's ImportErrors, as runs per option x layout x module. No row at all is said in words."""
    rows = [(d["option"], lay, m, n) for d in per_option_rows for lay, mods in sorted(d.get("import_errors", {}).items())
            for m, n in sorted(mods.items())]
    if not rows:
        return ["ImportErrors the agents saw: none in any run."]
    return ["ImportErrors the agents saw, runs per option x layout x module:", "", "| option | layout | module | runs |", "|---|---|---|---|",
            *(f"| {o} | {lay} | {m} | {n} |" for o, lay, m, n in rows)]


def render_usage_flags(per_option_rows: list[dict]) -> list[str]:
    """The pilot's runs whose usage is flagged (a request was cut): counted in the token figures at their completed requests' tokens, except the ones cut in their
    first request, which have none. Nothing flagged: nothing said."""
    flagged = [d for d in per_option_rows if d.get("usage_incomplete")]
    if not flagged:
        return []
    return ["Runs with usage flagged (a request was cut) are counted in the token figures at their completed requests' tokens, except those cut in their first "
            "request, which have none and are left out: " + "; ".join(f"{d['option']}: {d['usage_incomplete']} run(s), {d.get('first_request_cuts', 0)} cut in its "
                                                                     "first request" for d in flagged) + "."]


def render_escape_kinds(per_option_rows: list[dict]) -> list[str]:
    """The instrument's escapes on the pilot's runs, as counts per option and kind, so an option whose client code forces more of them is
    visible for the instrument-only sensitivity (science, #2, 2 Nov 17:32Z). A kind seen anywhere has a row in every option."""
    kinds = sorted({k for d in per_option_rows for k in d.get("escape_kinds", {})})
    head = "The instrument's escapes on the pilot's runs, counts per option and kind (runs with a trace in brackets):"
    if not kinds:
        return [head, "", "none in any run with a trace: " + ", ".join(f"{d['option']} ({d.get('escape_runs_observed', 0)})" for d in per_option_rows) + "."]
    opts = [d["option"] for d in per_option_rows]
    return [head, "", "| kind | " + " | ".join(f"{d['option']} ({d.get('escape_runs_observed', 0)})" for d in per_option_rows) + " |",
            "|---|" + "---|" * len(opts),
            *(f"| {k} | " + " | ".join(str(d.get("escape_kinds", {}).get(k, 0)) for d in per_option_rows) + " |" for k in kinds)]


def per_option(rows, cfg: Config, block: str = "pilot") -> list[dict]:
    """rows: ScoredRow list. Pilot block only."""
    rows = [r for r in rows if r.block == block]
    df = adapter.rows_to_frame(rows, cfg, blocks=[block]) if rows else None
    out = []
    for o in ORDER:
        ro = _row(rows, o)
        n = len(ro)
        d = {"option": o, "runs": n}
        d["finished_rate"] = sum(r.finished for r in ro) / n if n else None
        lab = [r for r in ro if r.label is not None]
        d["labels"] = {l.value: sum(r.label is l for r in lab) for l in OmissionLabel}
        f1 = [r.event_f1 for r in ro if r.finished and not r.event_free and r.event_f1 is not None]
        d["agent_f1_mean"] = float(np.mean(f1)) if f1 else None
        d["agent_f1_n"] = len(f1)
        # the H2 rule (science, #34, 21:41Z to 22:58Z), as the analysis: a run cut mid-request counts at its completed requests' tokens; one cut in its FIRST
        # request has none, is left out of the figures and is counted apart
        toks = [r.input_tokens + r.output_tokens for r in ro if not first_request_cut(r)]
        d["usage_incomplete"] = sum(not r.usage_complete for r in ro)
        d["first_request_cuts"] = sum(first_request_cut(r) for r in ro)
        d["tokens_mean"] = float(np.mean(toks)) if toks else None
        d["tokens_max"] = max(toks) if toks else None
        w = [r.wall_time_s for r in ro]
        d["wall_mean_s"] = float(np.mean(w)) if w else None
        d["wall_max_s"] = max(w) if w else None
        by_layout: dict = {}                      # the pilot's ImportErrors: runs per layout and module (science, #2, 10:52Z)
        for r in ro:
            for m in (r.import_errors or {}):
                cell = by_layout.setdefault(r.run.layout.value, {})
                cell[m] = cell.get(m, 0) + 1
        d["import_errors"] = by_layout
        esc = [r.escape_kinds for r in ro if r.escape_kinds is not None]      # the instrument's escapes by kind (science, #2, 17:32Z)
        d["escape_runs_observed"] = len(esc)
        d["escape_kinds"] = {k: sum(e.get(k, 0) for e in esc) for k in sorted({k for e in esc for k in e})}
        for col in ("omit", "coverage_baseline", "coverage_target"):
            d[f"region_sd_{col}"] = _region_sd(df, o, col) if df is not None else None
        out.append(d)
    return out


def _region_sd(df, option, col):
    s = df[(df.option == option)][["region_id", col]].dropna()
    m = s.groupby("region_id")[col].mean()
    return float(m.std(ddof=1)) if len(m) >= 2 else None


def power(rows, cfg: Config, block: str = "pilot"):
    """#14's pilot power re-estimate; (table | None, note)."""
    rs = [r for r in rows if r.block == block]
    if not rs:
        return None, "no pilot scored rows"
    try:
        return secondary.pilot_power(adapter.pilot_frame(rs, cfg), cfg), ""
    except Exception as e:  # reported, never hidden
        return None, f"power re-estimate failed: {type(e).__name__}: {e}"


GIB = 1024 ** 3


def limits_per_option(records: list[dict], blocks=("pilot", "calibration")) -> list[dict]:
    """Per option, from the run records of the pilot and calibration blocks: cells killed (by cause), and each run's peak memory.

    Peak memory is the sandbox's cgroup reading: `memory_peak_bytes` is the high-water mark and includes file cache and tmpfs
    (it reflects the data path as much as the agent's own use); `memory_anon_peak_bytes` is the sampled maximum of anon+shmem
    (1 s period), the better measure of what the agent's code allocated. A run whose sandbox could not be read counts under
    `unread`, never as zero. Both are reported against the agent's allowance (16 GiB by rule) and the container limit."""
    out: dict[str, dict] = {}
    for r in records:
        if r.get("block") not in blocks:
            continue
        o = r["run"]["option"]
        d = out.setdefault(o, {"option": o, "runs": 0, "runs_with_kill": 0, "kills": {}, "peak": [], "anon_peak": [], "unread": 0,
                               "max_bytes": None, "allowance_bytes": None})
        d["runs"] += 1
        ex = r.get("extras") or {}
        ck = ex.get("cell_kills") or {}
        if ck.get("total"):
            d["runs_with_kill"] += 1
        for reason, n in (ck.get("by_reason") or {}).items():
            d["kills"][reason] = d["kills"].get(reason, 0) + n
        mem = ex.get("memory") or {}
        if mem.get("memory_peak_bytes") is None:
            d["unread"] += 1
        else:
            d["peak"].append(mem["memory_peak_bytes"])
        if mem.get("memory_anon_peak_bytes") is not None:
            d["anon_peak"].append(mem["memory_anon_peak_bytes"])
        d["max_bytes"] = mem.get("memory_max_bytes") or d["max_bytes"]
        d["allowance_bytes"] = ((ex.get("sandbox_limits") or {}).get("agent_memory_gib") or 0) * GIB or d["allowance_bytes"]
    return [out[k] for k in sorted(out)]


def render_limits_table(rows: list[dict]) -> list[str]:
    f = lambda xs: "n/a" if not xs else f"{max(xs) / GIB:.2f} / {sum(xs) / len(xs) / GIB:.2f}"   # noqa: E731
    lines = ["| option | runs | runs with a killed cell | kills by cause | peak memory max / mean GiB (cgroup, includes file cache) | anon+shmem peak max / mean GiB (sampled) | runs unread | container limit GiB | agent allowance GiB |",
             "|---|---|---|---|---|---|---|---|---|"]
    for d in rows:
        kills = ", ".join(f"{k} {v}" for k, v in sorted(d["kills"].items())) or "none"
        lim = "n/a" if not d["max_bytes"] else f"{d['max_bytes'] / GIB:.2f}"
        al = "n/a" if not d["allowance_bytes"] else f"{d['allowance_bytes'] / GIB:g}"
        lines.append(f"| {d['option']} | {d['runs']} | {d['runs_with_kill']} | {kills} | {f(d['peak'])} | {f(d['anon_peak'])} | {d['unread']} | {lim} | {al} |")
    return lines


def containers_per_option(records: list[dict], blocks=("pilot", "calibration")) -> list[dict]:
    """Per option and container role (agent, gate, sidecar): CPU seconds and peak memory over the pilot and calibration runs, from the
    cgroup readings in each record (`extras.containers`, science ruling 1 Nov). A reading that was not possible is counted as `unread`,
    never as zero. ENOSPC is reported per option as runs and cells (a lower bound: an error the agent's code caught is not seen)."""
    out: dict[tuple, dict] = {}
    enospc: dict[str, dict] = {}
    for r in records:
        if r.get("block") not in blocks:
            continue
        o = r["run"]["option"]
        ex = r.get("extras") or {}
        e = enospc.setdefault(o, {"runs": 0, "with_enospc": 0, "cells": 0})
        e["runs"] += 1
        n = (ex.get("enospc") or {}).get("count") or 0
        e["with_enospc"] += 1 if n else 0
        e["cells"] += n
        for role, st in (ex.get("containers") or {}).items():
            if not isinstance(st, dict):
                continue
            d = out.setdefault((o, role), {"option": o, "role": role, "runs": 0, "cpu": [], "peak": [], "unread": 0})
            d["runs"] += 1
            if st.get("cpu_s") is None or st.get("peak_bytes") is None:
                d["unread"] += 1
            if st.get("cpu_s") is not None:
                d["cpu"].append(st["cpu_s"])
            if st.get("peak_bytes") is not None:
                d["peak"].append(st["peak_bytes"])
    return [dict(v, enospc=enospc[v["option"]]) for _, v in sorted(out.items())] or \
           [{"option": o, "role": None, "runs": 0, "cpu": [], "peak": [], "unread": 0, "enospc": e} for o, e in sorted(enospc.items())]


def render_containers_table(rows: list[dict]) -> list[str]:
    f = lambda xs, k: "n/a" if not xs else f"{max(xs) / k:.2f} / {sum(xs) / len(xs) / k:.2f}"   # noqa: E731
    lines = ["| option | container | runs | CPU s max / mean | peak memory GiB max / mean (cgroup, includes cache) | runs with an unread value | runs with ENOSPC / cells (lower bound) |",
             "|---|---|---|---|---|---|---|"]
    for d in rows:
        e = d["enospc"]
        lines.append(f"| {d['option']} | {d['role'] or 'n/a'} | {d['runs']} | {f(d['cpu'], 1)} | {f(d['peak'], GIB)} | {d['unread']} | {e['with_enospc']} / {e['cells']} |")
    return lines


def output_cap_by_model(records: list[dict], blocks=("pilot", "calibration")) -> list[dict]:
    """Runs ended by the output cap (a reply cut at max_output_tokens with no tool call), per model: {model, runs, output_cap}."""
    out: dict[str, dict] = {}
    for r in records:
        if r.get("block") not in blocks:
            continue
        m = r["run"]["model"]
        d = out.setdefault(m, {"model": m, "runs": 0, "output_cap": 0})
        d["runs"] += 1
        d["output_cap"] += 1 if r.get("termination") == "output_cap" else 0
    return [out[k] for k in sorted(out)]
