"""Assemble the dossier from a config of explicit input paths."""
from __future__ import annotations

import json
import pathlib

from icsa.analysis import adapter
from icsa.analysis.config import load as load_cfg

from . import criteria as C
from . import diagnostics as D
from . import rules as R
from .core import MISSING, PASS, Artifact, overall

KEYS = ("equivalence", "validation_189", "ground_truth_record", "instruments_summary", "scored_rows",
        "run_records", "planted_faults", "pilot_inspections", "live_classes", "fault_cells", "scripted_pipeline", "scripted_timing", "block1_waits", "slot_quarantine")


def build(config_path: str | pathlib.Path) -> str:
    base = pathlib.Path(config_path).parent
    cfg = json.loads(pathlib.Path(config_path).read_text())

    def art(k, jsonl=False):
        v = cfg.get(k)
        return Artifact(None if v is None else (base / v), jsonl)

    eq, val, gt = art("equivalence"), art("validation_189"), art("ground_truth_record")
    ins, scored, recs = art("instruments_summary"), art("scored_rows", True), art("run_records", True)
    live, faults, pipe, timing = art("live_classes"), art("fault_cells"), art("scripted_pipeline"), art("scripted_timing")
    planted, inspections = art("planted_faults"), art("pilot_inspections")
    cal_start = [r.get("started_at") for r in (recs.data or []) if isinstance(r, dict) and r.get("block") == "calibration"] \
        if recs.usable else None
    res = [C.c1_reference(eq, val if val.path else None, gt if gt.path else None),
           C.c2_instruments(ins, cfg.get("instruments_caveat"), art("none_counts")),
           C.c3_labels(ins, scored, planted, inspections, unknown_max=cfg.get("unknown_share_max", C.UNKNOWN_MAX)),
           C.c4_records_and_faults(live, faults, cal_start),
           C.c5_pipeline(pipe), C.c6_timing(timing)]
    lines = ["# Pilot go/no-go dossier", "", f"**Result: {overall(res)}**", "",
             "Hypotheses and expected directions are not stated. Options are treated symmetrically.", "",
             "| # | criterion | status |", "|---|---|---|"]
    lines += [f"| {r.number} | {r.title} | {r.status} |" for r in res]
    for r in res:
        lines += ["", f"## Criterion {r.number}: {r.title}", "", f"**{r.status}**", "", f"Source of the rule: {r.source}"]
        if r.reasons:
            lines += ["", "Reasons:"] + [f"- {x}" for x in r.reasons]
        if r.details:
            lines += [""] + [f"- {x}" if not x.startswith("  ") else f"  - {x.strip()}" for x in r.details]
        lines += ["", "Evidence:"] + [f"- `{e.path}` sha256 `{e.sha256}` {e.note}" for e in r.evidence]
    # diagnostics
    lines += ["", "# Diagnostics (not criteria)", ""]
    if scored.usable:
        rows = [adapter.row_from_dict(d) for d in scored.data]
        pcfg = load_cfg()
        lines += ["| option | runs | finished rate | omitting / complete / unknown | agent F1 (n) | tokens mean / max | wall mean / max s | region SD omission | region SD cov. baseline | region SD cov. target |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for d in D.per_option(rows, pcfg):
            lb = d["labels"]
            f = lambda x: "n/a" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))
            lines.append(f"| {d['option']} | {d['runs']} | {f(d['finished_rate'])} | {lb['omitting']} / {lb['complete']} / {lb['unknown']} | "
                         f"{f(d['agent_f1_mean'])} ({d['agent_f1_n']}) | {f(d['tokens_mean'])} / {f(d['tokens_max'])} | "
                         f"{f(d['wall_mean_s'])} / {f(d['wall_max_s'])} | {f(d['region_sd_omit'])} | "
                         f"{f(d['region_sd_coverage_baseline'])} | {f(d['region_sd_coverage_target'])} |")
        flags = D.render_usage_flags(D.per_option(rows, pcfg))
        lines += ["", *flags] if flags else []
        lines += ["", *D.render_import_errors(D.per_option(rows, pcfg))]
        lines += ["", *D.render_escape_kinds(D.per_option(rows, pcfg))]
        t, note = D.power(rows, pcfg)
        lines += ["", "Power re-estimate from #14's simulation (`secondary.pilot_power`):", ""]
        if t is None:
            lines.append(f"MISSING: {note}")
        else:
            cols = list(t.columns)
            lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
            lines += ["| " + " | ".join(str(round(v, 4)) if isinstance(v, float) else str(v) for v in row) + " |" for row in t.itertuples(index=False)]
    else:
        lines.append(f"MISSING: pilot scored rows ({scored.why_unusable()})")
    # limits actually met: killed cells and peak memory per option
    lines += ["", "# Limits met per option (pilot and calibration runs)", ""]
    if recs.usable:
        lr = D.limits_per_option(recs.data)
        lines += D.render_limits_table(lr) if lr else ["MISSING: no pilot or calibration run records"]
        lines += ["", "Containers per option (CPU seconds and peak memory read from each cgroup before teardown) and ENOSPC:", ""]
        lines += D.render_containers_table(D.containers_per_option(recs.data))
        lines += ["", "Runs ended by the output cap (`max_output_tokens`, a reply cut with no tool call), per model: "
                  + (", ".join(f"{d['model']} {d['output_cap']}/{d['runs']}" for d in D.output_cap_by_model(recs.data)) or "none")]
        bw = art("block1_waits")
        lines += ["", "Block-1 runs that waited for an S2 run to finish (the per-block cap bounds everything in flight): "
                  + (f"{bw.data.get('count', 0)} waits, {bw.data.get('total_s', 0)} s in all (the `block1_waits` value of the campaign store, "
                     "each wait's length is in the event log)" if bw.usable else f"MISSING: not provided ({bw.why_unusable()})")]
        sq = art("slot_quarantine")
        lines += ["", "Slot users quarantined (a sandbox that could not be torn down keeps its slot user held, up to the token lifetime; "
                  "the `slot_quarantine` value of the campaign store, per option): "]
        if sq.usable and isinstance(sq.data, dict) and sq.data:
            lines += ["", "| option | slot users | quarantined now | quarantines in all | slot-hours lost (upper bound) |", "|---|---|---|---|---|"]
            lines += [f"| {o} | {v.get('slots')} | {v.get('quarantined')} | {v.get('quarantines')} | {round(float(v.get('quarantine_slot_hours', 0.0)), 2)} |"
                      for o, v in sorted(sq.data.items())]
        else:
            lines[-1] += f"MISSING: not provided ({sq.why_unusable()})"
        lines += ["", "A run killed for the memory limit or the time cap is the agent's outcome and is not retried; a host out-of-memory kill or a dead "
                  "sandbox is an infrastructure failure (the attempt is discarded and retried) and appears under infra-failed attempts, not here."]
    else:
        lines.append(f"MISSING: run records ({recs.why_unusable()})")
    # rule values
    lines += ["", "# Values the parameter rules produce", ""]
    if recs.usable:
        rv = R.compute(recs.data, C.scripted_wall_at_cap(timing), include_infra_failed=cfg.get("include_infra_failed", False))
        lines += [f"Runs used: {rv.n_runs} {rv.n_by_block}; maxima: tool rounds {rv.max_rounds}, total tokens {rv.max_tokens}, wall {rv.max_wall_s} s.", "",
                  f"- `{{TURN_CAP}}` = {rv.turn_cap}", f"- `{{TOKEN_BUDGET}}` = {rv.token_budget}", f"- `{{TIME_CAP_MIN}}` = {rv.time_cap_min}"]
        if rv.wall_by_backend:
            lines += ["", "Wall time per model backend (analysed pilot and calibration runs; p95 by nearest rank):", "",
                      "| backend | n | max s | p95 s |", "|---|---|---|---|"]
            lines += [f"| {b} | {v['n']}{' (too few to judge)' if v['few'] else ''} | {v['max_s']:.0f} | {v['p95_s']:.0f} |"
                      for b, v in rv.wall_by_backend.items()]
            lines += [""]
        lines += [f"- NOTE: {n}" for n in rv.notes]
        lines += [f"- provisional-cap hit: {c}" for c in rv.cap_hit_cells]
    else:
        lines.append(f"MISSING: run records ({recs.why_unusable()}); no rule value can be computed.")
    return "\n".join(lines) + "\n"
