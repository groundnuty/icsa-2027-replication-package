"""Break-even number of analyses for M+ (data pre-provisioned at the agent's site at a one-off cost P).

Each analysis costs W when the data is pre-placed and C for a cold run. The break-even is the smallest integer k >= 1
with P + k*W <= k*C, i.e. ceil(P / (C - W)) when C > W, else infinity. Pure functions; no I/O.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

NO_BREAK_EVEN = "no break-even"


def break_even(P: float, C: float, W: float) -> float:
    if not (math.isfinite(P) and math.isfinite(C) and math.isfinite(W)):
        raise ValueError(f"non-finite input: P={P}, C={C}, W={W}")
    if P < 0 or C <= 0 or W <= 0:
        raise ValueError(f"need P >= 0, C > 0, W > 0; got P={P}, C={C}, W={W}")
    if C <= W:
        return math.inf
    k = max(1, math.ceil(P / (C - W)))
    # the quotient can round up across an integer (0.3 / (0.5 - 0.2)): the definition itself decides, with no tolerance
    if k > 1 and P + (k - 1) * W <= (k - 1) * C:
        k -= 1
    return float(k)


def _check(name: str, xs: Sequence[float], *, allow_zero: bool) -> np.ndarray:
    a = np.asarray(xs, dtype=float)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{name}: need a non-empty list of numbers")
    if not np.all(np.isfinite(a)) or (np.any(a < 0) if allow_zero else np.any(a <= 0)):
        raise ValueError(f"{name}: samples must be finite and {'>= 0' if allow_zero else '> 0'}")
    return a


def bootstrap_interval(p_samples, c_samples, w_samples, *, seed: int, n_boot: int = 10000, level: float = 0.95) -> dict:
    p = _check("p_samples", p_samples, allow_zero=True)
    c = _check("c_samples", c_samples, allow_zero=False)
    w = _check("w_samples", w_samples, allow_zero=False)
    if n_boot < 1 or not 0 < level < 1:
        raise ValueError("need n_boot >= 1 and 0 < level < 1")
    rng = np.random.default_rng(seed)
    mp = p[rng.integers(0, p.size, size=(n_boot, p.size))].mean(axis=1)
    mc = c[rng.integers(0, c.size, size=(n_boot, c.size))].mean(axis=1)
    mw = w[rng.integers(0, w.size, size=(n_boot, w.size))].mean(axis=1)
    draws = np.sort(np.array([break_even(a, b, d) for a, b, d in zip(mp, mc, mw)]))   # inf sorts last
    lo = int(math.floor((1 - level) / 2 * (n_boot - 1)))
    hi = int(math.ceil((1 + level) / 2 * (n_boot - 1)))
    return {"point": break_even(float(p.mean()), float(c.mean()), float(w.mean())),
            "low": float(draws[lo]), "high": float(draws[hi]),
            "share_no_break_even": float(np.isinf(draws).mean()),
            "n_boot": n_boot, "seed": seed, "level": level,
            "n_p": int(p.size), "n_c": int(c.size), "n_w": int(w.size),
            "mean_p": float(p.mean()), "mean_c": float(c.mean()), "mean_w": float(w.mean())}


def json_safe(d):
    """Replace inf by the string "no break-even", recursively, so that the result is valid JSON."""
    if isinstance(d, dict):
        return {k: json_safe(v) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [json_safe(v) for v in d]
    if isinstance(d, float) and math.isinf(d):
        return NO_BREAK_EVEN
    return d
