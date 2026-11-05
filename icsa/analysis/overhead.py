"""Wall time reported with the scripted enforcement overhead beside it (#14; measured by #12).

Option contrasts on wall time are **as measured**. The enforcement overhead (what the gate, or M's
sidecar mount, adds on its own) is stated beside them and **never subtracted**. Tokens, correctness
and bytes are not touched.

`run_all(..., overhead=...)` is REQUIRED (keyword, no default; None is an error), like `infra`:
`OverheadTable.absent()` states that no overhead was measured; the report then says
"overhead not measured" and shows no number (never zero). A cell the table lacks is "not measured" too.

File format `icsa-enforcement-overhead-v1` (JSON), written by #12's quiet-window measurement, one entry
per option x layout it measured (an empty `rows` list is the explicit "not measured"):

    {"format": "icsa-enforcement-overhead-v1",
     "rows": [{"option": "T", "layout": "S1",
               "overhead_s": 1.8,        # median wall time WITH the enforcement minus WITHOUT it, seconds
               "k": 5,                   # repeats per arm in the quiet window (>= [overhead].min_k)
               "baseline": "no gate",    # what the control arm was: "no gate" | "unsandboxed mount"
               "lo": 1.1, "hi": 2.6},    # optional interval of overhead_s (both or neither)
              ...]}

Options with a gate (T, T-unpaginated, D) are measured gate vs no gate; M, sidecar mount vs an unsandboxed mount.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

from icsa.analysis.config import Config

FORMAT = "icsa-enforcement-overhead-v1"
BASELINES = ("no gate", "unsandboxed mount")
NOT_MEASURED = "overhead not measured"


@dataclasses.dataclass(frozen=True)
class OverheadTable:
    rows: tuple[dict, ...] = ()
    sha256: str | None = None

    @classmethod
    def absent(cls) -> "OverheadTable":
        """The explicit statement that the overhead was not measured."""
        return cls()

    def get(self, option: str, layout: str) -> dict | None:
        return next((r for r in self.rows if r["option"] == option and r["layout"] == layout), None)


def parse(d: dict, cfg: Config, sha: str | None = None) -> OverheadTable:
    if not isinstance(d, dict) or d.get("format") != FORMAT:
        raise ValueError(f"overhead: format must be {FORMAT!r}")
    if not isinstance(d.get("rows"), list):
        raise ValueError("overhead: list 'rows' is missing (write an empty list for 'not measured')")
    seen, out = set(), []
    known = set(cfg.options + [cfg["pagination"]["option"]])
    for e in d["rows"]:
        for f in ("option", "layout", "overhead_s", "k", "baseline"):
            if f not in e:
                raise ValueError(f"overhead: entry {e!r} lacks {f!r}")
        if e["option"] not in known or e["layout"] not in cfg.layouts:
            raise ValueError(f"overhead: unknown option/layout {e['option']!r}/{e['layout']!r}")
        if (e["option"], e["layout"]) in seen:
            raise ValueError(f"overhead: {e['option']}/{e['layout']} listed twice")
        seen.add((e["option"], e["layout"]))
        if not isinstance(e["k"], int) or isinstance(e["k"], bool) or e["k"] < int(cfg["overhead"]["min_k"]):
            raise ValueError(f"overhead: {e['option']}/{e['layout']} has k={e['k']!r}, below the minimum "
                             f"{cfg['overhead']['min_k']}")
        if e["baseline"] not in BASELINES:
            raise ValueError(f"overhead: baseline {e['baseline']!r} must be one of {BASELINES}")
        want = "unsandboxed mount" if e["option"] in cfg["overhead"]["sidecar_options"] else "no gate"
        if e["baseline"] != want:
            raise ValueError(f"overhead: {e['option']} is measured against {want!r}, not {e['baseline']!r}")
        if not isinstance(e["overhead_s"], (int, float)) or isinstance(e["overhead_s"], bool) or not np.isfinite(e["overhead_s"]):
            raise ValueError(f"overhead: overhead_s of {e['option']}/{e['layout']} must be a finite number")
        if ("lo" in e) != ("hi" in e):
            raise ValueError(f"overhead: {e['option']}/{e['layout']} needs both lo and hi, or neither")
        out.append(dict(e))
    return OverheadTable(tuple(out), sha)


def load(path: str | pathlib.Path, cfg: Config) -> OverheadTable:
    raw = pathlib.Path(path).read_bytes()
    return parse(json.loads(raw), cfg, hashlib.sha256(raw).hexdigest())


def coerce(x, cfg: Config) -> OverheadTable:
    if x is None:
        raise ValueError("overhead is required: pass a file, or OverheadTable.absent() to state it was not measured")
    if isinstance(x, OverheadTable):
        return x
    return load(x, cfg)


def wall_time_table(df: pd.DataFrame, cfg: Config, ov: OverheadTable) -> pd.DataFrame:
    """Per option x layout: measured wall time (median and mean over runs), overhead beside it.

    `overhead_status` is 'measured' or the text 'overhead not measured' (NaN number, never 0)."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    rows = []
    for (opt, lay), g in d.groupby(["option", "layout"], sort=True):
        r = ov.get(opt, lay)
        rows.append({"option": opt, "layout": lay, "runs": len(g),
                     "wall_time_s_median": g["wall_time_s"].median(), "wall_time_s_mean": g["wall_time_s"].mean(),
                     "overhead_s": np.nan if r is None else float(r["overhead_s"]),
                     "overhead_lo": np.nan if r is None or "lo" not in r else float(r["lo"]),
                     "overhead_hi": np.nan if r is None or "hi" not in r else float(r["hi"]),
                     "overhead_k": np.nan if r is None else r["k"],
                     "overhead_baseline": "" if r is None else r["baseline"],
                     "overhead_status": NOT_MEASURED if r is None else "measured"})
    return pd.DataFrame(rows)


def wall_time_contrasts(df: pd.DataFrame, cfg: Config, ov: OverheadTable) -> pd.DataFrame:
    """The pre-registered option contrasts on median wall time, AS MEASURED (a minus b), with each arm's
    overhead beside them. Descriptive: no test, no adjustment by the overhead."""
    t = wall_time_table(df, cfg, ov).set_index(["option", "layout"])
    rows = []
    for lay in cfg.layouts:
        for a, b in cfg.contrasts:
            if (a, lay) not in t.index or (b, lay) not in t.index:
                continue
            ta, tb = t.loc[(a, lay)], t.loc[(b, lay)]
            rows.append({"layout": lay, "contrast": f"{a}-{b}",
                         "wall_time_s_median_a": ta["wall_time_s_median"], "wall_time_s_median_b": tb["wall_time_s_median"],
                         "difference_as_measured_s": ta["wall_time_s_median"] - tb["wall_time_s_median"],
                         "overhead_s_a": ta["overhead_s"], "overhead_s_b": tb["overhead_s"],
                         "overhead_status_a": ta["overhead_status"], "overhead_status_b": tb["overhead_status"]})
    return pd.DataFrame(rows)
