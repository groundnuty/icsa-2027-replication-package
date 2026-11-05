"""Runs where the agent saw a data-path error of any origin (#14; science's ruling on #7).

ONE concept in every option: the agent saw an error on the data path, whoever made it. Two definitions, in order:

- **A (preferred):** `ScoredRow.agent_saw_data_error`, the tracer's flag (#9), the same rule in every option.
- **B (otherwise), from outside the agent:** T, T-unpaginated, D: a 5xx or reset that reached the client, gate
  or upstream; M: a FUSE error naming an errno returned to the application.
  Errors the agent's own request causes are not errors seen: the gate's client-origin errors, and the FUSE errnos the
  sidecar log summary marks as caused by the agent (`fuse_caused_by_agent`: ENOENT, EROFS, ...). The summary counts
  EACCES and EPERM as NOT agent-caused (they can mean an expired token), so they flag.
- A wins over B when both exist. A run with neither is **not available**, never 0 and never clear.

A run is *flagged* (excluded from the sensitivity), *clear*, or *not available* (kept in the sensitivity; the
account counts them). Every table says which definition each run used. The per-origin counts (gate, upstream,
sidecar, agent-caused) are descriptive only and never drive the exclusion; they exist for
definition B runs only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from icsa.analysis import contrasts as C, secondary as S
from icsa.analysis.config import Config

LABEL = "excluding_flagged_runs"
NA = "not available"


def _tri(v) -> bool | None:
    if v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)):
        return None
    return bool(v)


def classify_run(saw_data_error, sources) -> dict:
    """status ('flagged' | 'clear' | 'not available'), definition ('A' | 'B' | 'none') and the descriptive counts.

    B: gate options: gate or upstream 5xx / resets (client-origin errors do not count); M: FUSE errors the sidecar
    log marks as not caused by the agent (#61; EACCES and EPERM count, as an expired token looks the same)."""
    a = _tri(saw_data_error)
    src = sources if isinstance(sources, dict) else None
    desc = {"n_gate": 0, "n_upstream": 0, "n_sidecar": 0, "n_agent_caused": 0}
    seen_b = False
    if src:
        if "gate_5xx" in src:
            seen_b = True
            desc["n_gate"] = int(src["gate_5xx"]) + int(src["gate_resets"])
            desc["n_upstream"] = int(src["upstream_5xx"]) + int(src["upstream_resets"])
            desc["n_agent_caused"] += int(src.get("client_request_errors", 0))
        if "fuse_not_caused_by_agent" in src:
            seen_b = True
            desc["n_sidecar"] = int(src["fuse_not_caused_by_agent"])
            desc["n_agent_caused"] += int(src.get("fuse_caused_by_agent", 0))
    b_flag = desc["n_gate"] + desc["n_upstream"] + desc["n_sidecar"] > 0
    if a is not None:
        status, definition = ("flagged" if a else "clear"), "A"
        desc = desc if seen_b else dict.fromkeys(desc, 0)          # the splits are descriptive and come from B only
    elif seen_b:
        status, definition = ("flagged" if b_flag else "clear"), "B"
    else:
        status, definition = NA, "none"
    return {"status": status, "definition": definition, **desc}


def run_status(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    recs = [classify_run(a, s) for a, s in zip(df["saw_data_error"], df["data_error_sources"])]
    return pd.DataFrame(recs, index=df.index, columns=["status", "definition", "n_gate", "n_upstream", "n_sidecar",
                                                       "n_agent_caused"])


def definitions_used(st: pd.DataFrame) -> str:
    c = st["definition"].value_counts()
    return ";".join(f"{k}:{int(c.get(k, 0))}" for k in ("A", "B", "none"))


def agent_seen_error_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per option: runs flagged / clear / not available (count and share), runs per definition, and the
    descriptive error counts per origin (definition B runs; they do not drive the exclusion)."""
    st = run_status(df, cfg)
    rows = []
    for opt in [o for o in cfg.options + [cfg["pagination"]["option"]] if (df.option == o).any()]:
        m = (df.option == opt).to_numpy()
        s, n = st[m], int(m.sum())
        row = {"option": opt, "runs": n}
        for lab, key in (("flagged", "flagged"), ("clear", "clear"), ("not_available", NA)):
            k = int((s["status"] == key).sum())
            row[f"{lab}_runs"], row[f"{lab}_share"] = k, k / n
        for d in ("A", "B", "none"):
            row[f"definition_{d}_runs"] = int((s["definition"] == d).sum())
        for c in ("n_gate", "n_upstream", "n_sidecar", "n_agent_caused"):
            row[c.replace("n_", "errors_")] = int(s[c].sum())
            row[c.replace("n_", "runs_with_")] = int((s[c] > 0).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def import_error_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per option x layout x module: the runs whose agent saw that ImportError, and how many tool outputs ended in it. Every cell
    has a row for every module seen anywhere, so a package that lands on one option shows as a zero on the others; with none
    seen, each cell says so in a `(none)` row. Beside the other agent-visible errors, and no input to any exclusion."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    seen = [v for v in d["import_errors"] if isinstance(v, dict)]
    modules = sorted({m for v in seen for m in v}) or ["(none)"]
    rows = []
    for (opt, layout), g in d.groupby(["option", "layout"], sort=True):
        vals = [v for v in g["import_errors"] if isinstance(v, dict)]
        for m in modules:
            rows.append({"option": opt, "layout": layout, "module": m, "runs": len(g), "runs_observed": len(vals),
                         "runs_with": sum(m in v for v in vals), "errors": sum(v.get(m, 0) for v in vals)})
    return pd.DataFrame(rows, columns=["option", "layout", "module", "runs", "runs_observed", "runs_with", "errors"])


def flagged_exclusion_sensitivity(df: pd.DataFrame, cfg: Config, bootstrap: bool = True):
    """(account per option, contrasts without the flagged runs, the pagination cell without them; the
    all-runs effect beside each, `definitions_used` on every row).

    Same code, same Holm families, the pre-registered contrasts; only the flagged runs are removed."""
    st = run_status(df, cfg)
    keep = df[(st["status"] != "flagged").to_numpy()]
    used = definitions_used(st)
    acct = agent_seen_error_table(df, cfg)[["option", "runs", "flagged_runs", "not_available_runs",
                                            "definition_A_runs", "definition_B_runs"]].rename(
        columns={"runs": "runs_all", "not_available_runs": "not_available_runs_kept"})
    acct["runs_analysed"] = acct["runs_all"] - acct["flagged_runs"]
    full, _ = C.contrast_tables(df, cfg, bootstrap=bootstrap)
    tab, _ = C.contrast_tables(keep, cfg, bootstrap=bootstrap)
    key = ["outcome", "layout", "contrast"]
    tab = tab.merge(full[key + ["effect", "p_holm"]].rename(columns={"effect": "effect_all_runs", "p_holm": "p_holm_all_runs"}),
                    on=key, how="left")
    pg = []
    for all_seeds in (False, True):
        full_p, _ = S.pagination_cell(df, cfg, all_seeds=all_seeds, bootstrap=bootstrap)
        sens_p, _ = S.pagination_cell(keep, cfg, all_seeds=all_seeds, bootstrap=bootstrap)
        pg.append(sens_p.merge(full_p[["T_seeds", "outcome", "effect"]].rename(columns={"effect": "effect_all_runs"}),
                               on=["T_seeds", "outcome"], how="left"))
    pag = pd.concat(pg, ignore_index=True)
    for t in (acct, tab, pag):
        t.insert(0, "definitions_used", used)
        t.insert(0, "sensitivity", LABEL)
    return acct, tab, pag
