"""The instrument audit's rates, as the sensitivity analysis takes them (#14; written by #35).

The audit (about 100 agent runs per option, code inspection; parameters.md "Instrument audit") needs
agent runs, so its rates are RESULTS of the study. They enter only the sensitivity analysis of the
contrasts, after the audit, and never the primary analysis. Until a file is given, the sensitivity
rows use the placeholder scenarios of `preregistered.toml`, and every output row says which it used
(`rates_source`).

File format `icsa-instrument-audit-v1` (JSON), one entry per option x layout, every main option and
layout exactly once:

    {"format": "icsa-instrument-audit-v1",
     "rates": [{"option": "T", "layout": "S1",
                "false_complete": 0.04,          # P(label complete | truly omitting), re-weighted to the population
                "false_omission": 0.01,          # P(label omitting | truly complete)
                "false_complete_ci": [0.02, 0.08],   # optional 95% interval; all-or-none across entries
                "false_omission_ci": [0.00, 0.03]}, ...]}

Scenarios made from it: `audit_point` (the point rates) and, when every entry has intervals,
`audit_ci_low` / `audit_ci_high` (both rates at their interval's low / high end).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib

from icsa.analysis.config import Config

FORMAT = "icsa-instrument-audit-v1"
Rates = dict[tuple[str, str], tuple[float, float]]   # (option, layout) -> (false_complete, false_omission)


@dataclasses.dataclass(frozen=True)
class AuditRates:
    scenarios: dict[str, Rates]
    sha256: str
    path: str

    @property
    def source(self) -> str:
        return f"audit:{pathlib.Path(self.path).name}@{self.sha256[:12]}"


def _check(name: str, v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.0 <= v <= 1.0:
        raise ValueError(f"instrument audit: {name} must be a number in [0, 1], got {v!r}")
    return float(v)


def parse(d: dict, cfg: Config, sha: str, path: str) -> AuditRates:
    if not isinstance(d, dict) or d.get("format") != FORMAT or not isinstance(d.get("rates"), list):
        raise ValueError(f"instrument audit: format must be {FORMAT!r} with a 'rates' list")
    point: Rates = {}
    lo: Rates = {}
    hi: Rates = {}
    have_ci = []
    for e in d["rates"]:
        key = (e.get("option"), e.get("layout"))
        if key in point:
            raise ValueError(f"instrument audit: {key} appears twice")
        fc, fo = _check("false_complete", e.get("false_complete")), _check("false_omission", e.get("false_omission"))
        if fc + fo >= 1:
            raise ValueError(f"instrument audit: {key}: false_complete + false_omission must be < 1")
        point[key] = (fc, fo)
        ci = [e.get("false_complete_ci"), e.get("false_omission_ci")]
        have_ci.append(all(c is not None for c in ci))
        if all(c is not None for c in ci):
            (fcl, fch), (fol, foh) = ci
            for n, l, v, h in (("false_complete", fcl, fc, fch), ("false_omission", fol, fo, foh)):
                _check(n + "_ci", l), _check(n + "_ci", h)
                if not l <= v <= h:
                    raise ValueError(f"instrument audit: {key}: {n} {v} is outside its interval [{l}, {h}]")
            lo[key], hi[key] = (fcl, fol), (fch, foh)
    need = {(o, l) for o in cfg.options for l in cfg.layouts}
    if set(point) != need:
        raise ValueError(f"instrument audit: needs exactly the option x layout cells {sorted(need)}; "
                         f"missing {sorted(need - set(point))}, unexpected {sorted(set(point) - need, key=str)}")
    if any(have_ci) and not all(have_ci):
        raise ValueError("instrument audit: intervals must be given for every entry or for none")
    sc = {"audit_point": point}
    if lo:
        sc.update(audit_ci_low=lo, audit_ci_high=hi)
    return AuditRates(sc, sha, path)


def load(path: str | pathlib.Path, cfg: Config) -> AuditRates:
    raw = pathlib.Path(path).read_bytes()
    return parse(json.loads(raw), cfg, hashlib.sha256(raw).hexdigest(), str(path))
