"""Campaign time and cost budget (#34).

Inputs, each with its source:
  * run counts per priority group and model: built from icsa.campaign.config and the manifest, never retyped;
  * endpoint capacity: the throughput benchmark's raw results (bench/results/<date>/*__c*.json): the
    concurrency level that gives the highest aggregate output tokens/s without errors, and the mean seconds
    per model turn at that level. Nothing comes from vendor rate limits or nominal numbers;
  * per-run turns, tokens and tool time: ASSUMPTIONS (low and high scenario) in reports/budget/inputs.json
    until the pilot and calibration records exist; `from_records` replaces them from a campaign store;
  * the #12 concurrency curve: a marked placeholder (`sandbox_cap`) until #12 lands.

Model of the finish time: a group g finishes at the largest of
  (a) for each model m: (its runs in groups <= g) x seconds per run / streams_m,
  (b) all runs in groups <= g x seconds per run / the global stream cap,
because groups are priorities, not barriers (priority_mode = per_model), except pilot and calibration, which
are barriers. Seconds per run = turns x (measured seconds per model turn + tool seconds per turn).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import (ALL_MODELS, CLAUDE_MODELS, MODEL_API_IDS, CampaignConfig, group_of)
from .instances import load_instances
from .manifest import build_manifest

GROUP_ORDER = ["pilot", "pilot1", "main_s1", "main_s2_a", "main_s2_b"]
GROUP_LABEL = {"pilot": "pilot", "pilot1": "calibration", "main_s1": "main S1 + pagination",
               "main_s2_a": "S2 tier A", "main_s2_b": "S2 tier B"}
API_TO_NAME = {v: k for k, v in MODEL_API_IDS.items()}


def run_counts(cfg: CampaignConfig | None = None) -> dict[str, dict[str, int]]:
    """{group: {model reporting name: runs}} from the manifest (instance contents do not matter for counts)."""
    cfg = cfg or CampaignConfig()
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in build_manifest(cfg, load_instances()):
        r = row.run
        out[group_of(row.block, r.layout.value, r.model)][r.model] += 1
    return {g: dict(m) for g, m in out.items()}


# ------------------------------------------------------------------ measurements

def load_measurements(paths: list[str | Path]) -> dict[tuple[str, str], dict[int, dict]]:
    """{(model reporting name, backend): {level: {stats..., started_utc, ended_utc, slots_up, slot}}} from the
    benchmark's raw result files. Stats are recomputed from the raw turns by bench/model_throughput.level_stats."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "model_throughput", Path(__file__).resolve().parents[2] / "bench" / "model_throughput.py")
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    out: dict[tuple[str, str], dict[int, dict]] = {}
    for d in paths:
        for f in sorted(x for x in glob.glob(str(Path(d) / "*__c*.json")) if not x.endswith("__skipped.json")):
            res = json.loads(Path(f).read_text())
            if res.get("warmup") or res["model"] not in API_TO_NAME:
                continue
            st = bench.level_stats(res)
            prefix = res["model"].split("/")[-1]
            up = [s for s in res.get("slots_at_start", []) if s.get("up") and s.get("slot", "").split("-")[0] ==
                  {"site_ab": "qwen", "site_l": "gemma", "site_m": "glm",
                   "site_k": "deepseek", "site_aa": "qwencoder"}.get(API_TO_NAME[res["model"]], "-")]
            st.update(started_utc=res.get("started_utc"), ended_utc=res.get("ended_utc"), slot=res.get("slot"),
                      slots_up=len(up), source=str(f))
            out.setdefault((API_TO_NAME[res["model"]], res["backend"]), {})[res["level"]] = st
    return out


KNEE = 0.90


def clean(st: dict) -> bool:
    """Error-free and not aborted for an endpoint reason. A level cut short by OUR spend cap has no errors and
    counts (its throughput is then a slight under-estimate: the window kept its full length)."""
    stopped_by_cap = str(st.get("abort_reason") or "").startswith("spend cap")
    return st["n_errors"] == 0 and (not st["aborted"] or stopped_by_cap) and st["n_turns"] > 0


def best_level(levels: dict[int, dict], max_level: int | None = None) -> dict | None:
    """The smallest error-free level whose aggregate output tokens/s reaches 90% of the best error-free level's:
    more streams past that point only lengthen every turn (the plateau)."""
    ok = [s for lv, s in sorted(levels.items()) if clean(s) and (max_level is None or lv <= max_level)]
    if not ok:
        return None
    top = max(s["agg_output_tok_s"] for s in ok)
    return next(s for s in ok if s["agg_output_tok_s"] >= KNEE * top)


# ---------------------------------------------------------------------- compute

@dataclasses.dataclass
class Unit:
    """What one model can run at once, and how fast a turn goes there."""
    streams: float = 0.0
    turn_s: float | None = None      # seconds per completed model turn of all its backends together (rates add)
    parts: list[str] = dataclasses.field(default_factory=list)
    missing: str | None = None


def model_unit(model: str, meas: dict, inputs: dict, cfg: CampaignConfig, clip: bool = True, tool_s: float = 0.0) -> Unit:
    """clip=True limits Claude to the configured `anthropic` cap and each site_b backend to its configured cap
    (the finish-time table); clip=False takes the knee of everything measured (the per-model requirement table).
    `tool_s` is the scenario's tool time per turn; it is added to each backend's turn time BEFORE the backends'
    completion rates are summed, so `turn_s` is the seconds a stream spends per turn including tools."""
    u = Unit()
    num = 0.0
    if model in CLAUDE_MODELS:
        lv = best_level(meas.get((model, "claude"), {}), inputs["caps"]["anthropic"] if clip else None)
        if lv is None:
            return Unit(missing=f"no error-free Claude measurement for {model}")
        u.streams, num = float(lv["level"]), lv["level"] / (lv["mean_turn_s"] + tool_s)       # num = turns per second
        u.parts.append(f"claude c={lv['level']} turn {lv['mean_turn_s']:.1f}s ({lv['started_utc'][:16]}Z)")
    else:
        slots_override = inputs.get("hpc_slots_up", {}).get(model)
        hp = best_level(meas.get((model, "hpc"), {}))
        if hp is not None:
            up = slots_override if slots_override is not None else hp["slots_up"]
            n = hp["level"] * up
            u.streams += n
            num += n / (hp["mean_turn_s"] + tool_s)
            u.parts.append(f"hpc {up} slot(s) x c={hp['level']} turn {hp['mean_turn_s']:.1f}s ({hp['started_utc'][:16]}Z)")
        lb = best_level(meas.get((model, "lab"), {}), cfg.site_b_caps.get(model, 0) if clip else None)
        if lb is not None:
            n = lb["level"]
            u.streams += n
            num += n / (lb["mean_turn_s"] + tool_s)
            u.parts.append(f"lab c={lb['level']} turn {lb['mean_turn_s']:.1f}s ({lb['started_utc'][:16]}Z)")
        if not u.streams:
            return Unit(missing=f"no error-free measurement for {model} on any backend")
    u.turn_s = u.streams / num        # backends add their completion rates: the mean turn time is streams / (turns/s)
    return u


CACHE_READ_X, CACHE_WRITE_1H_X = 0.1, 2.0   # of the input price (Anthropic price list; 1 h cache writes)


def claude_cost(turns: float, mean_ctx: float, out_per_turn: float, pin: float, pout: float) -> tuple[float, float]:
    """(with caching, without) USD for one Claude run, from the prompt sizes.

    Context grows roughly linearly, so the final prompt is about 2 x the mean and every token is written to the
    cache once: writes = 2 x mean_ctx; every later call reads the previous prompt: reads = turns x mean_ctx - writes;
    fresh input is negligible. Checked against the measured Sonnet 5.5 session (16 turns, 37.8k mean context):
    writes 72,963 vs the model's 75.6k, reads 531,656 vs 529k, $0.416 measured vs $0.43 modelled."""
    total_in = turns * mean_ctx
    writes = min(2 * mean_ctx, total_in)
    reads = total_in - writes
    out = turns * out_per_turn
    cached = (writes * CACHE_WRITE_1H_X * pin + reads * CACHE_READ_X * pin + out * pout) / 1e6
    plain = (total_in * pin + out * pout) / 1e6
    return cached, plain


def per_run(scn: dict, inputs: dict, model: str, unit: Unit) -> dict[str, float | None]:
    turns = scn["turns"]
    uncapped = turns * (scn["mean_ctx_tokens"] + scn["out_tokens_per_turn"])
    f = min(1.0, inputs["caps"]["token_budget"] / uncapped)      # the 4M token budget ends a longer run early
    # time, tokens and spend all shrink by f (the run is cut at the token budget; proportional approximation)
    secs = None if unit.turn_s is None else f * turns * unit.turn_s      # unit.turn_s already includes tool time
    usd = usd_plain = None
    if model in CLAUDE_MODELS:
        pin, pout = inputs["prices_usd_per_mtok"][model]
        usd, usd_plain = (f * x for x in claude_cost(turns, scn["mean_ctx_tokens"], scn["out_tokens_per_turn"], pin, pout))
    return {"secs": secs, "usd": usd, "usd_nocache": usd_plain, "tokens": uncapped * f}


BARRIER_GROUPS = ("pilot", "pilot1")      # pilot and calibration are hard barriers (config.barrier_blocks): nothing later starts


def group_cap(cfg: CampaignConfig, group: str, default: float) -> float:
    """The sandbox cap of a priority group: `max_sandboxes_by_block` (the pilot and calibration groups at main_s1's, as the scheduler
    does), else `default` (the single planning cap). Mirrors Campaign._cap_group."""
    by = cfg.max_sandboxes_by_block
    key = group if group in by else ("main_s1" if group in BARRIER_GROUPS and "main_s1" in by else None)
    return float(by[key]) if key is not None else default


def _phase_time(work: dict[str, float], units: dict[str, Unit], glob_cap: float, cfg: CampaignConfig) -> tuple[float, str]:
    """Seconds to clear `work` (seconds of session per model) given each model's streams, the shared `anthropic`
    provider cap (both Claude models draw on it) and the global stream cap. Returns (time, binding limit)."""
    cands = {m: w / units[m].streams for m, w in work.items() if w}
    cands["global stream cap"] = sum(work.values()) / glob_cap
    cands["shared anthropic cap"] = sum(w for m, w in work.items() if m in CLAUDE_MODELS) / cfg.cap("anthropic")
    k = max(cands, key=cands.get)
    return cands[k], k


def compute(inputs: dict, meas: dict, counts: dict[str, dict[str, int]], cfg: CampaignConfig | None = None) -> dict[str, Any]:
    """Finish time of each group. Pilot and calibration run one after the other as barriers; the main groups then
    share the endpoints, so each group's finish adds the barrier time to the time needed for all the main work up
    to it (groups are priorities, not barriers)."""
    cfg = cfg or CampaignConfig()
    glob_cap = float(inputs["sandbox_cap"]["value"])
    res: dict[str, Any] = {"units": {m: dataclasses.asdict(model_unit(m, meas, inputs, cfg)) for m in ALL_MODELS},
                           "scenarios": {}}
    for name, scn in inputs["scenarios"].items():
        units = {m: model_unit(m, meas, inputs, cfg, tool_s=scn["tool_s_per_turn"]) for m in ALL_MODELS}
        rows, base = [], 0.0
        cum: dict[str, float] = defaultdict(float)
        cum_usd, cum_plain, incomplete = 0.0, 0.0, []
        for g in GROUP_ORDER:
            if g not in counts:
                continue
            g_usd, g_plain, g_miss = 0.0, 0.0, []
            g_work: dict[str, float] = defaultdict(float)
            for m, n in counts[g].items():
                pr = per_run(scn, inputs, m, units[m])
                if pr["secs"] is None:
                    g_miss.append(units[m].missing)
                    continue
                g_work[m] += n * pr["secs"]
                if pr["usd"] is not None:
                    g_usd += n * pr["usd"]
                    g_plain += n * pr["usd_nocache"]
            incomplete += [x for x in g_miss if x not in incomplete]
            cum_usd += g_usd
            cum_plain += g_plain
            if g in BARRIER_GROUPS:
                t, binding = _phase_time(g_work, units, group_cap(cfg, g, glob_cap), cfg) if g_work else (0.0, "")
                base += t
                fin = None if incomplete else base
            else:
                for m, w in g_work.items():
                    cum[m] += w
                # the group's own cap applies to the work cleared up to it: later groups with a lower cap read pessimistically
                t, binding = _phase_time(cum, units, group_cap(cfg, g, glob_cap), cfg) if cum else (0.0, "")
                fin = None if incomplete else base + t
            rows.append({"group": g, "label": GROUP_LABEL[g], "runs": sum(counts[g].values()),
                         "finish_h": None if fin is None else fin / 3600, "usd": g_usd, "cum_usd": cum_usd,
                         "usd_nocache": g_plain, "cum_usd_nocache": cum_plain,
                         "binding": None if fin is None else binding})
        res["scenarios"][name] = {"rows": rows, "incomplete": incomplete}
    return res


def max_measured_streams(model: str, meas: dict, inputs: dict, cfg: CampaignConfig) -> float:
    """Highest error-free MEASURED concurrency (no degradation judgement): Claude one stream pool; open models
    the sum over backends of slots up x highest error-free level (hpc) + highest error-free level (lab)."""
    def top(key):
        ok = [lv for lv, st in meas.get(key, {}).items() if clean(st)]
        return max(ok, default=0), meas.get(key, {}).get(max(ok, default=0))
    if model in CLAUDE_MODELS:
        return float(top((model, "claude"))[0])
    lh, sh = top((model, "hpc"))
    ll, _ = top((model, "lab"))
    slots = inputs.get("hpc_slots_up", {}).get(model, sh["slots_up"] if sh else 0)
    return float(lh * slots + ll)


def configured_streams(model: str, inputs: dict, cfg: CampaignConfig, claude_share: float) -> float:
    """Concurrency the CONFIGURED caps allow this model. Claude: the shared `anthropic` cap times the model's
    share of the Claude work. Open models: its site_b cap plus an equal share of the shared `site_a` cap."""
    if model in CLAUDE_MODELS:
        if model in cfg.anthropic_caps:           # the per-Claude-model cap (harness.toml, 64 each since 2 Nov 06:22Z): not shared, so no split
            return float(cfg.anthropic_caps[model])
        return cfg.cap("anthropic") * claude_share
    up = inputs.get("hpc_slots_up", {}).get(model)
    slot_cap = cfg.site_a_slot_caps.get(cfg.open_models.get(model, ""))
    if up is not None and slot_cap is not None:   # (0 up slots = 0 site_a streams) the slots up x the per-slot session cap: what dispatch derives (config.site_a_cap)
        return cfg.site_b_caps.get(model, 0) + up * slot_cap
    n_open = len(cfg.open_models)
    return cfg.site_b_caps.get(model, 0) + cfg.cap("site_a") / n_open


def per_model(inputs: dict, meas: dict, counts: dict, cfg: CampaignConfig, start: dt.datetime, cutoff: dt.datetime,
              hard: dt.datetime | None = None) -> dict:
    """Per model and deadline group, under each scenario: session-hours of work (cumulative, pilot and calibration
    included), wall time at the configured caps, the concurrency REQUIRED to finish by the cut-off, and the measured
    concurrency."""
    hard = hard or cutoff
    cutoff = hard or cutoff          # one deadline for every group: the hard stop
    avail_h = (cutoff - start).total_seconds() / 3600
    out: dict[str, Any] = {"avail_h": avail_h, "rows": []}
    for sc, scn in inputs["scenarios"].items():
        units = {m: model_unit(m, meas, inputs, cfg, clip=False, tool_s=scn["tool_s_per_turn"]) for m in ALL_MODELS}
        secs = {m: per_run(scn, inputs, m, units[m])["secs"] for m in ALL_MODELS}
        cum_runs: dict[str, int] = defaultdict(int)
        for g in GROUP_ORDER:
            for m, n in counts.get(g, {}).items():
                cum_runs[m] += n
            if g not in ("main_s1", "main_s2_a", "main_s2_b"):
                continue
            claude_work = {m: cum_runs[m] * secs[m] for m in CLAUDE_MODELS if secs[m] and cum_runs[m]}
            tot_cw = sum(claude_work.values()) or 1.0
            for m in ALL_MODELS:
                if g not in counts or m not in counts[g]:
                    continue
                if secs[m] is None:
                    out["rows"].append({"scenario": sc, "group": g, "model": m, "missing": units[m].missing})
                    continue
                work_h = cum_runs[m] * secs[m] / 3600
                cfg_s = configured_streams(m, inputs, cfg, claude_work.get(m, 0) / tot_cw if m in CLAUDE_MODELS else 0)
                avail = (deadline_for(g, cutoff, hard) - start).total_seconds() / 3600
                req = work_h / avail
                meas_max = max_measured_streams(m, meas, inputs, cfg)
                out["rows"].append({
                    "scenario": sc, "group": g, "model": m, "runs": cum_runs[m], "session_hours": work_h, "window_h": avail,
                    "configured_streams": cfg_s, "wall_h_at_configured": work_h / cfg_s if cfg_s else None,
                    "required_streams": req, "measured_knee": units[m].streams, "measured_max": meas_max,
                    "red_required_gt_measured": req > meas_max, "red_required_gt_configured": req > cfg_s})
    return out


def deadline_for(group: str, soft: dt.datetime, hard: dt.datetime) -> dt.datetime:
    """Every group (pilot, calibration, main S1 + pagination, tiers A and B) by the hard stop: block 1's own cut-off was dropped
    (operator, 2 Nov 03:52Z). `soft` is kept in the signature for callers and is not used."""
    return hard


def latest_starts(res: dict, cutoff: dt.datetime, hard: dt.datetime | None = None) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {}
    for sc, d in res["scenarios"].items():
        out[sc] = {r["group"]: (None if r["finish_h"] is None else
                                (deadline_for(r["group"], cutoff, hard or cutoff) - dt.timedelta(hours=r["finish_h"])).strftime("%Y-%m-%d %H:%MZ")) for r in d["rows"]}
    return out


def render_per_model(pm: dict, start: dt.datetime, cutoff: dt.datetime, hard: dt.datetime, inputs: dict, cfg: CampaignConfig) -> list[str]:
    L = ["", "## Per model: wall time at the configured caps vs the concurrency required", "",
         f"Window: start **{start:%Y-%m-%d %H:%MZ}** (assumed campaign start) to the hard stop **{hard:%Y-%m-%d %H:%MZ}** "
         f"({(hard - start).total_seconds() / 3600:.0f} h) for every group, block 1 included (its own cut-off was dropped, 2 Nov 03:52Z). "
         f"Configured caps: `anthropic` = {cfg.cap('anthropic')} (shared by both Claude models, split by work), `site_a` = {cfg.cap('site_a')} "
         f"(shared by the {len(cfg.open_models)} open models, equal share; a model whose up slots are given in the inputs uses slots x its per-slot session cap {cfg.site_a_slot_caps} instead) plus the per-model site_b caps {cfg.site_b_caps}. "
         "Session-hours are cumulative (pilot + calibration + the block and every block before it). "
         "Seconds per turn are those measured at each model's knee level and are assumed to hold at the configured concurrency "
         "(the knee turn time is at or above the turn time at fewer streams, so wall times at lower caps are, if anything, "
         "over-estimates); where the configured concurrency exceeds what was measured, that is flagged. "
         "Finish-time table: Claude limited to the shared configured `anthropic` cap; open models at measured capacity "
         "(slots up x level on site_a, assuming every slot performs like the one measured, plus site_b to its configured cap); "
         "pilot and calibration run as barriers before main. "
         "**Required** = session-hours / window. 🔴 = required exceeds the measured concurrency (no error) or the configured one.", "",
         "| scenario | block | model | runs (cum.) | session-h | configured streams | wall h at configured | required streams | measured: knee / highest error-free | flag |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in pm["rows"]:
        if "missing" in r:
            L.append(f"| {r['scenario']} | {GROUP_LABEL[r['group']]} | {r['model']} | | | | | | n/a | not measured: {r['missing']} |")
            continue
        flag = ("🔴 required > measured " if r["red_required_gt_measured"] else "") + ("🔴 required > configured" if r["red_required_gt_configured"] else "")
        L.append(f"| {r['scenario']} | {GROUP_LABEL[r['group']]} | {r['model']} | {r['runs']} | {r['session_hours']:.0f} | {r['configured_streams']:.1f} | "
                 f"{r['wall_h_at_configured']:.0f} | {r['required_streams']:.1f} | {r['measured_knee']:g} / {r['measured_max']:g} | {flag or 'ok'} |")
    return L


def claude_spend_table(inputs: dict, counts: dict) -> list[str]:
    L = ["", "## Campaign spend on Claude per block and model (USD, the campaign's own spend; the paper's cost measure stays tokens)", "",
         "With caching is the main column (the harness will send `cache_control`); without caching beside it. Cache model: "
         "writes = 2 x mean context at 2 x the input price (1 h), reads = the rest of the prompt tokens at 0.1 x, checked against "
         "lane-8d's measured Sonnet session (16 turns: $0.416 cached vs $1.228 uncached, 66% less). Rounds and context sizes are "
         "ASSUMPTIONS until the pilot.", "",
         "| scenario | block | " + " | ".join(f"{m} cached / uncached" for m in CLAUDE_MODELS) + " | block total cached / uncached |",
         "|---|---|" + "---|" * (len(CLAUDE_MODELS) + 1)]
    for sc, scn in inputs["scenarios"].items():
        for g in GROUP_ORDER:
            if g not in counts:
                continue
            cs, ps = [], []
            for m in CLAUDE_MODELS:
                pr = per_run(scn, inputs, m, Unit(turn_s=1.0, streams=1.0))
                cs.append(counts[g].get(m, 0) * pr["usd"])
                ps.append(counts[g].get(m, 0) * pr["usd_nocache"])
            L.append(f"| {sc} | {GROUP_LABEL[g]} | " + " | ".join(f"{c:,.0f} / {p:,.0f}" for c, p in zip(cs, ps))
                     + f" | {sum(cs):,.0f} / {sum(ps):,.0f} |")
    return L


def render(inputs: dict, res: dict, counts: dict, meas: dict, cutoff: dt.datetime, hard: dt.datetime | None = None) -> str:
    hard = hard or cutoff
    cutoff = hard                    # block 1 has no cut-off of its own any more (operator, 2 Nov 03:52Z)
    L = ["# Campaign time and cost budget (#34)", "",
         f"Generated by `icsa/campaign/budget.py` on {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%MZ}. "
         "Run counts come from the manifest; capacity and seconds per turn from the throughput benchmark "
         "(measurement times below); **per-run turns, tokens and tool time are ASSUMPTIONS** until the pilot exists; "
         f"the global stream cap is a **PLACEHOLDER for the #12 curve** ({inputs['sandbox_cap']['value']} streams: {inputs['sandbox_cap']['source']}).", "",
         f"Deadline for the latest-start column: **{hard:%Y-%m-%d %H:%MZ}** for every group (the hard stop; block 1's earlier cut-off of 2026-11-03 12:00Z was dropped on 2 Nov 03:52Z by the operator, via the science agent; unfinished runs stay unfinished and are reported).", "",
         "## Finish times and Claude spend (cumulative: a row includes every earlier group)", "",
         "| group | runs | scenario | finish after start (h) | latest start for its deadline | binding limit | campaign Claude USD with caching (group) | with caching (cumulative) | without caching (cumulative) |",
         "|---|---|---|---|---|---|---|---|---|"]
    ls = latest_starts(res, cutoff, hard)
    free = compute({**inputs, "sandbox_cap": {"value": 1e9, "source": "none"}}, meas, counts)   # endpoints only, no global cap
    for sc, d in res["scenarios"].items():
        for r, rf in zip(d["rows"], free["scenarios"][sc]["rows"]):
            fh = "n/a (missing measurement)" if r["finish_h"] is None else \
                f"{r['finish_h']:.1f} (endpoints only: {rf['finish_h']:.1f}; binding {rf['binding']})"
            L.append(f"| {r['label']} | {r['runs']} | {sc} | {fh} | {ls[sc][r['group']] or 'n/a'} | {r['binding'] or 'n/a'} | "
                     f"{r['usd']:.0f} | {r['cum_usd']:.0f} | {r['cum_usd_nocache']:.0f} |")
    L += ["", "## Scenario assumptions (labelled assumptions, not measurements)", "", "| scenario | tool rounds/run | mean context tokens/call | output tokens/call | tool seconds/turn | source |", "|---|---|---|---|---|---|"]
    for sc, s in inputs["scenarios"].items():
        L.append(f"| {sc} | {s['turns']} | {s['mean_ctx_tokens']} | {s['out_tokens_per_turn']} | {s['tool_s_per_turn']} | {s['source']} |")
    L += ["", f"Per-run token ceiling: {inputs['caps']['token_budget']:,} (harness `token_budget`); prices USD/Mtok in,out: "
          + "; ".join(f"{m} {p[0]}/{p[1]}" for m, p in inputs["prices_usd_per_mtok"].items()) + f" ({inputs['prices_source']}). "
          "The harness DOES send `cache_control` (1-hour ephemeral, system block and top-level; adapters.py `CACHE_CONTROL`): a smoke run on 2 Nov showed cache reads on every call after the first, so the 'with caching' column is the one that applies.", "",
          "## Measured capacity per model (from the benchmark)", "", "| model | streams | seconds/turn | measured on |", "|---|---|---|---|"]
    for m, u in res["units"].items():
        L.append(f"| {m} | {u['streams']:g} | {'n/a' if u['turn_s'] is None else f'{u['turn_s']:.1f}'} | {'; '.join(u['parts']) or u['missing']} |")
    L += ["", "## Run counts (manifest)", "", "| group | " + " | ".join(ALL_MODELS) + " |", "|---|" + "---|" * len(ALL_MODELS)]
    for g in GROUP_ORDER:
        if g in counts:
            L.append(f"| {GROUP_LABEL[g]} | " + " | ".join(str(counts[g].get(m, 0)) for m in ALL_MODELS) + " |")
    for sc, d in res["scenarios"].items():
        if d["incomplete"]:
            L += ["", f"**Incomplete ({sc}):** " + "; ".join(d["incomplete"])]
    cfg = CampaignConfig()
    start = dt.datetime.fromisoformat(inputs["campaign_start"]["utc"].replace("Z", "+00:00"))
    L += render_per_model(per_model(inputs, meas, counts, cfg, start, cutoff, hard), start, cutoff, hard, inputs, cfg)
    L += claude_spend_table(inputs, counts)
    L += ["", "## Where the configured caps come from", "", inputs.get("cap_provenance", "")]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inputs", default=str(Path(__file__).resolve().parents[2] / "reports/budget/inputs.json"))
    ap.add_argument("--bench", action="append", required=True, help="benchmark results dir (repeatable)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "reports/budget"))
    ap.add_argument("--hard-stop", help="UTC ISO; overrides inputs.json (the one deadline of every group)")
    ap.add_argument("--config", help="the campaign's launch config: its hard_stop_utc is the deadline, the one setting (overrides inputs.json, not --hard-stop)")
    a = ap.parse_args(argv)
    inputs = json.loads(Path(a.inputs).read_text())
    from_cfg = CampaignConfig.from_json(a.config).hard_stop_utc if a.config else None
    hard = dt.datetime.fromisoformat((a.hard_stop or from_cfg or inputs["hard_stop"]["utc"]).replace("Z", "+00:00"))
    cutoff = hard
    counts, meas = run_counts(), load_measurements(a.bench)
    res = compute(inputs, meas, counts)
    out = Path(a.out)
    (out / "budget.md").write_text(render(inputs, res, counts, meas, cutoff, hard))
    (out / "budget.json").write_text(json.dumps({"result": res, "counts": counts}, indent=1, default=str))
    print(out / "budget.md")


if __name__ == "__main__":
    main()
