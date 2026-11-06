"""MODEL (not a measurement): recall of the byte-level records under detector v1 and v2, S2, per fault, per option.

T: onedatarestfsspec's OnedataFile, cache_type "readahead", 5 MiB block (fsspec 2026.9.0 ReadAheadCache._fetch, copied
from the image), ONE file object per run (as an agent's xarray keeps the file open); Traefik serves each fetched range.
M: FsLogic rows = the app's offset, size rounded up to whole 4 KiB pages (seen live 22:06Z: [38840395, +255948) -> +258048);
kernel read-ahead NOT modelled (not measured). Reads follow icsa.faults.script.execute: days in sorted order, a HEADER
day reads [0, data_start) once, a FULL day reads its chunk span. Real S2 chunk index, real instances' required days,
the real scenario generator (make_scenario / injection / read_plan).
v1: a day is read iff a served span overlaps its chunk by >= 1 byte. v2: iff one merged served range covers the chunk.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from icsa.faults.observability import applicable_faults
from icsa.faults.scenarios import Condition, Fault, Mode, injection, make_scenario, read_plan
from icsa.faults.units import Required, build_s2_manifest
from icsa.instances import load as IL
from icsa.records import Layout, Option
from icsa.scripted.runner import split_days

B = 5 * 1024 * 1024
PAGE = 4096
SEED = 20261101


class ReadAhead:                       # fsspec ReadAheadCache._fetch, recording what is fetched
    def __init__(self, size):
        self.size, self.start, self.end, self.fetched = size, 0, 0, []

    def read(self, start, end):
        end = min(end, self.size)
        if start >= self.size or start >= end:
            return
        if start >= self.start and end <= self.end:
            return
        elif self.start <= start < self.end:
            start = self.end
        e = min(self.size, end + B)
        self.fetched.append((start, e))
        self.start, self.end = start, e


def reads(plan, man, key):
    out, hdr = [], False
    for day in sorted(plan.touch):
        _, a, b = man.units[day]
        if plan.touch[day] is Mode.HEADER:
            if not hdr:
                out.append((0, man.data_start(key))); hdr = True
        else:
            out.append((a, b))
    return out


def merge(r):
    r = sorted(x for x in r if x[1] > x[0])
    m = []
    for a, b in r:
        if m and a <= m[-1][1]:
            m[-1][1] = max(m[-1][1], b)
        else:
            m.append([a, b])
    return m


def judged(served, A, Bv):
    """(v1, v2) boolean arrays over the days whose chunk spans are A[k], Bv[k]."""
    m = merge(served)
    if not m:
        z = np.zeros(len(A), bool); return z, z.copy()
    st = np.array([x[0] for x in m]); en = np.array([x[1] for x in m])
    i = np.searchsorted(st, Bv, side="left") - 1          # last merged range starting before the chunk's end
    ok = i >= 0
    ii = np.where(ok, i, 0)
    v1 = ok & (en[ii] > A)                               # merged ranges are disjoint: no earlier one can overlap
    v2 = ok & (st[ii] <= A) & (en[ii] >= Bv)
    return v1, v2


def main():
    s2 = Path(sys.argv[1])
    man = build_s2_manifest(s2, "s2z/sst_s2.nc")
    key = man.files[0].key
    size = man.files[0].size
    offs = [man.units[d][1] for d in sorted(man.units)]
    assert all(x < y for x, y in zip(offs, offs[1:])), "chunks not in day order"
    sizes = [man.units[d][2] - man.units[d][1] for d in man.units]
    recs = {r["instance"]["instance_id"]: r for r in IL.load_instances()["instances"]}
    res = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for opt in (Option.T, Option.M):
        faults = applicable_faults(Layout.S2, opt) + [Fault.NONE]
        n_each = math.ceil(60 / (len(faults) - 1))
        for iid, rec in sorted(recs.items()):
            base, tgt = split_days(rec)
            req = Required.from_days(base, tgt)
            days = np.array(sorted(req.days))
            A = np.array([man.units[d][1] for d in days]); Bv = np.array([man.units[d][2] for d in days])
            pos = {int(d): k for k, d in enumerate(days)}
            for f in faults:
                for rep in range(n_each if f is not Fault.NONE else 30):
                    s_ = make_scenario(f, Layout.S2, opt, Condition.COLD, rep, SEED)
                    inj, plan = injection(s_, req), read_plan(s_, req)
                    rr = reads(plan, man, key)
                    if opt is Option.T:
                        ra = ReadAhead(size)
                        for a, b in rr:
                            ra.read(a, b)
                        served = ra.fetched
                    else:
                        served = [(a, min(size, a + -(-(b - a) // PAGE) * PAGE)) for a, b in rr]
                    v1, v2 = judged(served, A, Bv)
                    om = np.array(sorted(pos[d] for d in (inj.unread | inj.header_only)), dtype=int)
                    clean = np.ones(len(days), bool); clean[om] = False
                    for d in inj.unused:
                        clean[pos[d]] = False
                    x = res[opt.value][f.value]
                    x["runs"] += 1
                    x["omitted_days"] += len(om)
                    x["det_v1"] += int((~v1[om]).sum()); x["det_v2"] += int((~v2[om]).sum())
                    x["fm_v1"] += int((clean & ~v1).sum()); x["fm_v2"] += int((clean & ~v2).sum())
                    if len(om):
                        x["runs_with_omission"] += 1
                        if v2[om].all():
                            x["masked_runs_v2"] += 1          # every omitted day served: unobservable by design
                        else:
                            x["obs_omitted_days"] += len(om); x["obs_det_v2"] += int((~v2[om]).sum())
    out = {"chunk_bytes": {"min": min(sizes), "median": int(np.median(sizes)), "max": max(sizes)},
           "instances": len(recs), "seed": SEED, "cells": {}}
    for opt, fs in res.items():
        for f, x in fs.items():
            om = x["omitted_days"]; r = x["runs_with_omission"]
            out["cells"][f"{opt}|{f}"] = {
                "runs": x["runs"], "recall_v1": round(x["det_v1"] / om, 4) if om else None,
                "recall_v2": round(x["det_v2"] / om, 4) if om else None,
                "masked_run_share_v2": round(x["masked_runs_v2"] / r, 4) if r else None,
                "recall_v2_unmasked_runs": round(x["obs_det_v2"] / x["obs_omitted_days"], 4) if x["obs_omitted_days"] else None,
                "false_missing_v1": x["fm_v1"], "false_missing_v2": x["fm_v2"]}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
