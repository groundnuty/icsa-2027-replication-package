"""Run the full pre-registered analysis: `python -m icsa.analysis.run --rows rows.jsonl --out DIR`."""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

from icsa.analysis import adapter, audit as audit_mod, config as cfgmod, contrasts as C, exhibits as X, flags as F, infra as I, overhead as OV, secondary as S
from icsa.analysis import strict as STRICT
from icsa.analysis import inspection as INS
from icsa import codestamp

REPO = pathlib.Path(__file__).resolve().parents[2]


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                              cwd=pathlib.Path(__file__).parent).stdout.strip() or None
    except Exception:
        return None


def code_version() -> dict:
    """The analysed code (#14 dry run, F3): from git when the tree is a checkout, else from the snapshot's `.code-stamp.json`
    (icsa/codestamp.py; bin/vmsync and vm2sync copy a tree without .git and stamp it), else unknown. Unknown is None, never "not dirty":
    `bool(git status)` read a failed git as a clean tree with no commit. Whether HEAD is at a tag is known only from git."""
    v = codestamp.version(REPO)
    known = v["commit"] != codestamp.UNKNOWN
    return {"git_commit": v["commit"] if known else None,
            "git_tag_at_head": _git("describe", "--tags", "--exact-match", "HEAD") if v["source"] == "git" else None,
            "git_dirty": bool(v["dirty"]) if known else None,
            "code_version_source": v["source"], "code_version_note": v.get("why")}


def manifest(cfg, n_rows: int, blocks: pd.DataFrame | None = None, acc: "I.InfraAccount | None" = None,
             audit=None, ov: "OV.OverheadTable | None" = None,
             data_error_definitions: str | None = None, inspection: "INS.InspectionInput | None" = None,
             label_sources: dict | None = None, coder_pairs: dict | None = None) -> dict:
    return {"config_sha256": cfg.sha256, **code_version(),
            # amendment 11: H1's primary labels are after inspection; where each primary-scope finished run's label comes from
            "inspection_source": inspection.source if inspection else None, "label_sources": label_sources,
            # amendment 26(j): the runs each coder pair resolved (complete / omitting / unknown), per pair, never pooled
            "coder_pair_counts": coder_pairs,
            "n_rows": n_rows,
            "primary_blocks": cfg["blocks"]["primary"],
            "rows_per_block": [] if blocks is None else blocks.to_dict("records"),
            "infra_export_sha256": acc.sha256 if acc else None,
            "n_exhausted_runs": len(acc.exhausted) if acc else 0,
            "n_unfinished_runs": len(acc.unfinished) if acc else 0,
            "overhead_sha256": ov.sha256 if ov else None,
            "overhead_measured": bool(ov and ov.rows),
            "data_error_definitions": data_error_definitions,   # runs per definition of "agent saw a data-path error" (A tracer, B outside, none = not available)
            "instrument_rates_source": audit.source if audit else "placeholder (preregistered.toml)",
            "python": sys.version.split()[0],
            "numpy": np.__version__, "pandas": pd.__version__}


def mark_pairs(out: pathlib.Path, line: str) -> int:
    """Puts `line` first in every Markdown table in `out`, then a blank line (as snapshot/stamp.py does with its own line, which goes before it). A CSV
    gets nothing: a second line above the columns would break `pd.read_csv` and the snapshot's documented `skiprows=1` read. A table that already
    starts with the line (the same directory written twice) is left as it is."""
    n = 0
    for p in sorted(out.glob("*.md")):
        text = p.read_text()
        if not text.startswith(INS.PAIR_HEADER):
            p.write_text(line + "\n\n" + text)
            n += 1
    return n


def run_all(rows, out: pathlib.Path, cfg=None, causes: pd.DataFrame | None = None, bootstrap: bool = True,
            fidelity_rows=None, *, infra, overhead, inspection, audit=None, cause_flags: pd.DataFrame | None = None,
            h3_table: pd.DataFrame | None = None) -> dict:
    """`rows`: the campaign's scored runs, each with a block (a row without one is an error).
    `fidelity_rows`: #11's scripted fault-injection runs, which carry no campaign block; given, they
    (and only they) build the fidelity table, otherwise it is built from `rows`.
    `infra` (REQUIRED, keyword): the campaign's infrastructure-failure export (a path, or an
    `infra.InfraAccount`; `InfraAccount.empty()` states that there are no exhausted runs). A missing
    argument is a TypeError and None a ValueError, so an exhausted run cannot vanish silently.
    `overhead` (REQUIRED, keyword): the scripted enforcement overhead (a path of `icsa-enforcement-overhead-v1`, or an
    `overhead.OverheadTable`; `OverheadTable.absent()` states it was not measured, and the wall-time tables then say
    "overhead not measured"). None is a ValueError. It is stated beside wall time, never subtracted.
    `cause_flags` (optional): #17's flags table (`Batch.flags_table()` / `<out>.flags.csv`), for the recovery rate over all runs.
    `audit` (optional): path of the instrument audit's rates file (icsa/analysis/audit.py); without it
    the instrument sensitivity uses the placeholder scenarios and says so.
    `inspection` (REQUIRED, keyword): the coders' decisions and coverage (`inspection.InspectionInput`, from `inspection.load`);
    `InspectionInput.not_run()` states that inspection has not run, so every instrument `unknown` stays unknown and the manifest's
    `label_sources` counts it as not inspected. H1's primary labels are those after inspection (amendment 11, rubric §8)."""
    cfg = cfg or cfgmod.load()
    acc = I.coerce(infra)
    ov = OV.coerce(overhead, cfg)
    ins = INS.coerce(inspection)
    if audit is not None and not isinstance(audit, audit_mod.AuditRates):
        audit = audit_mod.load(audit, cfg)
    out.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    I.check_against_rows(acc, rows)
    raw_rows = rows                                     # before inspection: the Sol-only sensitivity (26(j)) applies its own subset of it
    rows = INS.apply(rows, ins)
    sources = INS.label_source_counts(rows, cfg)
    pairs = INS.pair_counts(rows, cfg)
    _, block_account = adapter.select_rows(rows, cfg)
    ex_kept, ex_account = I.exhausted_scope(acc, cfg)
    block_account = pd.concat([block_account, ex_account], ignore_index=True)
    df = adapter.rows_to_frame(rows, cfg)
    if rows and df.empty and not ex_kept:
        raise ValueError(f"no run is in a primary block {cfg['blocks']['primary']}; "
                         f"rows per block: {block_account.to_dict('records')}")
    X.write_table(block_account, out, "rows_per_block")
    X.write_table(X.out_of_cohort_table(rows, cfg), out, "out_of_cohort_runs")
    X.write_table(I.exhausted_per_cell(acc, df, cfg), out, "exhausted_per_cell")
    X.write_table(I.infra_per_option(acc, cfg), out, "infra_per_option")
    X.write_table(I.unfinished_table(acc), out, "unfinished_runs")
    X.write_table(I.unfinished_per_cell(acc, cfg), out, "unfinished_per_cell")
    X.write_table(X.invalid_rates_table(rows, cfg), out, "invalid_rates")
    if df.empty:     # every primary-scope run exhausted (or no rows): no outcomes to contrast; the account stands
        sd, sb, se = S.exhausted_sensitivity(df, I.exhausted_frame(ex_kept), cfg, bootstrap=bootstrap)
        X.write_table(sd, out, "exhausted_sensitivity_denominators")
        X.write_table(sb, out, "exhausted_sensitivity_bounds_contrasts")
        X.write_table(se, out, "exhausted_sensitivity_bounds_extreme")
        mark_pairs(out, INS.pair_header(rows, cfg, ins))
        m = manifest(cfg, len(rows), block_account, acc, audit, ov, inspection=ins, label_sources=sources, coder_pairs=pairs)
        m["primary_analysis"] = "skipped: no run with outcomes in a primary block"
        (out / "manifest.json").write_text(json.dumps(m, indent=1))
        return m
    tab, pm = C.contrast_tables(df, cfg, bootstrap=bootstrap)
    X.write_table(S.with_null_shares(tab, df, cfg), out, "contrasts")
    X.write_table(S.with_null_shares(S.coverage_bounds_contrasts(df, cfg, bootstrap=bootstrap), df, cfg), out, "coverage_bounds_contrasts")
    X.write_table(S.coverage_null_share(df, cfg), out, "coverage_null_share")
    X.write_table(pm, out, "directions_per_model")
    h4m, h4s = S.h4_directions(tab, pm, df, cfg, bootstrap=bootstrap)          # H4, descriptive (science, #14, 19:11Z)
    X.write_table(h4m, out, "h4_per_model_effects")
    X.write_table(h4s, out, "h4_directions")
    X.write_table(S.denominator_table(df, cfg), out, "denominators")
    for name, t in STRICT.strict_beside(rows, cfg, df=df).items():                                        # amendment 36(d): the strict reading beside the finished share, correctness, omission
        X.write_table(t, out, f"strict_beside_{name}")
    bt, extreme = S.bound_tables(df, cfg, bootstrap=bootstrap)
    X.write_table(bt, out, "bounds_contrasts")
    X.write_table(extreme, out, "bounds_extreme")
    sd, sb, se = S.exhausted_sensitivity(df, I.exhausted_frame(ex_kept), cfg, bootstrap=bootstrap)
    X.write_table(sd, out, "exhausted_sensitivity_denominators")
    X.write_table(sb, out, "exhausted_sensitivity_bounds_contrasts")
    X.write_table(se, out, "exhausted_sensitivity_bounds_extreme")
    X.write_table(S.imputation_sensitivity(df, cfg, bootstrap=bootstrap), out, "imputation_sensitivity")
    for allseeds, name in ((False, "pagination_primary"), (True, "pagination_sensitivity_all_seeds")):
        t, p = S.pagination_cell(df, cfg, all_seeds=allseeds, bootstrap=bootstrap)
        seen = S.pagination_rows(df, cfg, allseeds)         # the same seeds: T's share here is of the runs this contrast uses
        X.write_table(S.with_null_shares(t, seen, cfg), out, name)
        X.write_table(S.with_null_shares(S.pagination_coverage_bounds(df, cfg, all_seeds=allseeds, bootstrap=bootstrap), seen, cfg),
                      out, name + "_coverage_bounds")
    X.write_table(S.instrument_sensitivity(df, cfg, bootstrap=bootstrap, audit=audit), out, "instrument_sensitivity")
    fe, diag = S.mixed_models(df, cfg)
    X.write_table(fe, out, "mixed_fixed_effects")
    X.write_table(diag, out, "mixed_diagnostics")
    X.write_table(S.pooled_model_sensitivity(df, cfg, bootstrap=bootstrap), out, "pooled_model_sensitivity")
    X.write_table(S.routed_share(df, cfg), out, "routed_to_inspection")                                  # amendment 19(a)
    X.write_table(S.instrument_only_sensitivity(rows, cfg, bootstrap=bootstrap), out, "instrument_only_sensitivity")
    X.write_table(S.sol_only_sensitivity(raw_rows, ins, cfg, bootstrap=bootstrap), out, "sol_only_sensitivity")                       # amendment 26(j)
    X.write_table(S.routed_decided_complete(df, cfg), out, "routed_decided_complete")                    # beside it: the instrument's false omissions, by the coders
    X.write_table(S.seed_one_balanced(df, cfg, bootstrap=bootstrap), out, "seed_one_balanced")           # amendment 29(c)
    budget_m, budget_n = S.tracking_budget_sensitivity(df, cfg, bootstrap=bootstrap)                   # 19(b)
    X.write_table(budget_m, out, "tracking_budget_sensitivity")
    X.write_table(budget_n, out, "tracking_budget_excluded")
    X.write_table(S.backend_shares(df, cfg), out, "backend_shares")
    X.write_table(S.slot_shares(df, cfg), out, "slot_shares")
    X.write_table(S.fingerprint_shares(df, cfg), out, "fingerprint_shares")
    X.write_table(S.assignment_by_option(df, cfg), out, "assignment_by_option")
    X.write_table(S.backend_sensitivity(df, cfg, bootstrap=bootstrap), out, "backend_sensitivity")
    X.write_table(S.power_table(cfg), out, "power_simulation")
    X.write_table(S.pilot_power(adapter.pilot_frame(rows, cfg), cfg), out, "power_from_pilot")
    levels = pd.concat([X.level_table(df, cfg, o, B=None if bootstrap else 50) for o in X.LEVEL_OUTCOMES], ignore_index=True)
    X.write_table(levels, out, "levels")
    X.outcome_figure(levels, cfg, out / "fig_outcomes.png")
    cb = X.cause_breakdown(df, cfg, causes)
    X.write_table(cb, out, "cause_breakdown")
    X.cause_figure(cb, out / "fig_causes.png")
    X.write_table(X.cost_table(df, cfg), out, "cost_table")
    X.write_table(X.usage_flagged_table(df, cfg), out, "usage_flagged_runs")                             # science, #34: the flag beside the cost
    X.write_table(S.tokens_flagged_sensitivity(df, cfg, bootstrap=bootstrap), out, "tokens_flagged_sensitivity")
    X.write_table(X.bytes_unknown_table(df, cfg), out, "bytes_unknown")
    X.write_table(OV.wall_time_table(df, cfg, ov), out, "wall_time_with_overhead")
    X.write_table(OV.wall_time_contrasts(df, cfg, ov), out, "wall_time_contrasts_with_overhead")
    X.write_table(F.agent_seen_error_table(df, cfg), out, "agent_seen_errors")
    X.write_table(F.import_error_table(df, cfg), out, "import_errors")
    fa, ft, fp = F.flagged_exclusion_sensitivity(df, cfg, bootstrap=bootstrap)
    X.write_table(fa, out, "flagged_exclusion_account")
    X.write_table(ft, out, "flagged_exclusion_contrasts")
    X.write_table(fp, out, "flagged_exclusion_pagination")
    X.write_table(X.recovered_truncated_listing(df, cfg, cause_flags), out, "recovered_from_truncated_listing")
    fidelity, fidelity_status = X.fidelity_exhibit(X.fault_injection_adapter(rows if fidelity_rows is None else fidelity_rows, cfg), h3_table)
    X.write_table(fidelity, out, "fault_injection_fidelity")
    mark_pairs(out, INS.pair_header(rows, cfg, ins))                    # amendment 26(j): after the last table, so it marks them all
    m = manifest(cfg, len(rows), block_account, acc, audit, ov, F.definitions_used(F.run_status(df, cfg)), inspection=ins,
                 label_sources=sources, coder_pairs=pairs)
    m["fault_injection_fidelity"] = fidelity_status
    m["coverage_sources"] = dict(collections.Counter(str(r.coverage_source) for r in rows))
    (out / "manifest.json").write_text(json.dumps(m, indent=1))
    return m


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", required=True, help="JSONL of ScoredRow (dataclasses.asdict)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--infra", required=True,
                    help="JSON export of the campaign store (python -m icsa.campaign export-infra); "
                         "REQUIRED: exhausted runs are read from it. An explicit empty account is a file with empty lists")
    ap.add_argument("--overhead", required=True,
                    help="JSON of the scripted enforcement overhead (icsa/analysis/overhead.py, written by #12); REQUIRED: "
                         "an explicit 'not measured' is a file with an empty rows list")
    ap.add_argument("--instrument-audit", default=None,
                    help="JSON of the instrument audit's rates per option x layout (icsa/analysis/audit.py); "
                         "without it the instrument sensitivity uses the placeholder scenarios")
    ap.add_argument("--config", default=None)
    ap.add_argument("--causes", default=None, help="CSV with block,run_key,cause (coded causes)")
    ap.add_argument("--cause-flags", default=None,
                    help="CSV of #17's flags table (block,run_key,option,recovered_from_truncated_listing,listing_evidence_incomplete)")
    ap.add_argument("--fidelity-rows", required=True,
                    help="#11's adapter_rows.jsonl, its scripted fault-injection runs (no campaign block needed); REQUIRED: campaign "
                         "rows hold no fault record, so without it H3's table would be empty with no error. An explicit 'not run' is an empty file")
    ap.add_argument("--h3-table", default=None,
                    help="#11's h3_table.csv: joins each cell's verdict onto the fidelity table, and stops if the two disagree")
    ap.add_argument("--inspection-labels", required=True,
                    help="JSONL of the coders' decisions, one record per inspected run: block, run_key, label_after_inspection, route "
                         "(python -m icsa.analysis.inspection --decisions decisions.json --out labels.jsonl). REQUIRED: H1's primary labels "
                         "are after inspection (amendment 11); an explicit 'not run' is an empty file")
    ap.add_argument("--inspection-coverage", default=None,
                    help="JSONL, one record per inspected run, keyed like the labels: block, run_key, both_agree_exactly, "
                         "coverage_baseline, coverage_target")
    a = ap.parse_args()
    causes = pd.read_csv(a.causes) if a.causes else None
    fid = adapter.load_fidelity_rows(a.fidelity_rows)
    rows = adapter.load_jsonl(a.rows)
    ins = INS.load(a.inspection_labels, a.inspection_coverage)
    print(json.dumps(run_all(rows, pathlib.Path(a.out), cfgmod.load(a.config), causes,
                             fidelity_rows=fid, h3_table=pd.read_csv(a.h3_table) if a.h3_table else None,
                             cause_flags=pd.read_csv(a.cause_flags) if a.cause_flags else None, infra=a.infra, overhead=a.overhead,
                             inspection=ins, audit=a.instrument_audit), indent=1))


if __name__ == "__main__":
    main()
