"""Per-run masking verdicts, decided BEFORE any run (science, #11, 21:54Z; amendment 12).

Where an option's client serves more than the script asked for, some injected omissions are served
whole anyway and no record can show them. Which ones is a deterministic function of the scenario, the
instance's required set and the static chunk index, so it is computed here, before the run, and sealed into
the claimed plan (matrix.calibration_plan): a masked run is unobservable by design, the rest observable;
recall is computed over the observable runs and units, with the masked share reported beside it.

Inputs only: the scenario's read plan (`scenarios.read_plan`), replayed through `script.execute` with a
recording reader, so the reads are exactly the scripted ones; the manifest (static metadata); and each
client as observed live (`results/faults-live/`, 1 Nov 2026):

- T: onedatarestfsspec's `OnedataFile`, cache_type "readahead", fsspec's default 5 MiB block (its `_open`
  ignores block_size and cache_type), ONE file object per file per run, as an agent keeps it open. The rule
  is fsspec 2026.9.0's `ReadAheadCache._fetch`, copied below. Live: a 15,241 B header read fetched the whole
  S1 file; reading S2 chunk 200 fetched it plus exactly 5 MiB, serving skipped chunk 201 whole.
- D: every touch downloads the whole file.
- M: oneclient's `FsLogic,read` keeps the application's offset and rounds the size up to whole 4 KiB pages
  (live: [38840395, +255948) -> +258048). Kernel read-ahead beyond that was not seen and is not modelled.

No record, parser output or run result is read here. A day counts as served under detector v2's rule
(`records.ranges.covers`): the union of served bytes covers its whole chunk.
"""
from __future__ import annotations

import dataclasses

from icsa.records import Option

from .records.ranges import covers, merge_spans
from .scenarios import Scenario, injection, read_plan
from .script import execute
from .units import Manifest, Required

READAHEAD_BLOCK = 5 * 1024 * 1024     # fsspec AbstractBufferedFile.DEFAULT_BLOCK_SIZE (2026.9.0)
PAGE = 4096
_REST = (Option.T, Option.T_UNPAGINATED)


class _ReadAhead:
    """fsspec 2026.9.0 ReadAheadCache._fetch, recording each fetched range instead of fetching it."""

    def __init__(self, size: int) -> None:
        self.size, self.start, self.end = size, 0, 0
        self.fetched: list[tuple[int, int]] = []

    def read(self, start: int, end: int) -> None:
        if end > self.size:
            end = self.size
        if start >= self.size or start >= end:
            return
        if start >= self.start and end <= self.end:          # cache hit
            return
        if self.start <= start < self.end:                    # partial hit
            start = self.end
        end = min(self.size, end + READAHEAD_BLOCK)
        self.fetched.append((start, end))
        self.start, self.end = start, end


class _Recorder:
    """A ByteReader for script.execute that only records what it is asked."""

    def __init__(self) -> None:
        self.ops: list[tuple] = []

    def read_range(self, file_key: str, start: int, end: int) -> bytes:
        self.ops.append(("range", file_key, start, end))
        return b""

    def download(self, file_key: str) -> bytes:
        self.ops.append(("download", file_key))
        return b""


def client_served(option: Option, ops: list[tuple], manifest: Manifest) -> dict[str, list[tuple[int, int]]]:
    """Bytes the option's client gets from the provider for the script's operations, per file."""
    out: dict[str, list[tuple[int, int]]] = {}
    ra: dict[str, _ReadAhead] = {}
    for op in ops:
        key = op[1]
        size = manifest.file(key).size
        if op[0] == "download":
            out.setdefault(key, []).append((0, size))
            continue
        a, b = op[2], op[3]
        if option in _REST:
            ra.setdefault(key, _ReadAhead(size)).read(a, b)
        elif option is Option.M:
            out.setdefault(key, []).append((a, min(size, a + -(-(b - a) // PAGE) * PAGE)))
        else:
            raise ValueError(f"no client model for {option.value} range reads")
    for key, r in ra.items():
        out.setdefault(key, []).extend(r.fetched)
    return out


@dataclasses.dataclass(frozen=True)
class Masking:
    omitted: frozenset[int]           # injected unread + header-only days (what a record could show)
    served_omitted: frozenset[int]    # of those, the days whose whole chunk the client serves anyway

    @property
    def masked(self) -> bool:
        """Every omitted day served whole: the run is unobservable by design."""
        return bool(self.omitted) and self.served_omitted == self.omitted

    def as_dict(self) -> dict:
        return {"masked": self.masked, "omitted": sorted(self.omitted), "served_omitted": sorted(self.served_omitted)}


def masking(s: Scenario, req: Required, manifest: Manifest) -> Masking:
    inj, plan = injection(s, req), read_plan(s, req)
    rec = _Recorder()
    execute(plan, manifest, s.option, rec)
    merged = {k: merge_spans(v) for k, v in client_served(s.option, rec.ops, manifest).items()}
    om = frozenset(inj.unread | inj.header_only)
    served = frozenset(d for d in om
                       if covers(merged.get(manifest.units[d][0], []), manifest.units[d][1], manifest.units[d][2]))
    return Masking(om, served)


# ---- the model's numbers, regenerated through the same code path the plan uses -------------------------------
def summary(manifest: Manifest, required: dict, seed: int, options=(Option.T, Option.M), min_faulted: int = 60) -> dict:
    """Per option x fault (layout of `manifest`): runs, masked-run share, served-unit share, over the instances in
    `required` ({instance id: Required}), with the matrix's replicate counts. Pure: no record, no run."""
    import math

    from .observability import applicable_faults
    from .scenarios import Condition, Fault, make_scenario
    out: dict = {}
    for opt in options:
        faults = applicable_faults(manifest.layout, opt)
        n_each = math.ceil(min_faulted / len(faults))
        for f in faults:
            n = n_masked = n_om = n_served = 0
            for iid in sorted(required):
                for rep in range(n_each):
                    m = masking(make_scenario(f, manifest.layout, opt, Condition.COLD, rep, seed), required[iid], manifest)
                    if not m.omitted:
                        continue
                    n += 1; n_masked += m.masked; n_om += len(m.omitted); n_served += len(m.served_omitted)
            out[f"{opt.value}|{f.value}"] = {"runs_with_omission": n, "masked_run_share": n_masked / n if n else None,
                                             "served_unit_share": n_served / n_om if n_om else None}
    return out


def _required_of(rec: dict) -> Required:
    from icsa.scripted.runner import split_days
    base, tgt = split_days(rec)
    return Required.from_days(base, tgt)


def main(argv=None) -> None:
    """python -m icsa.faults.masking --s2 /mnt/volume2/icsa-2027/s2z/sst_s2.nc --seed 20261101 --out DIR"""
    import argparse
    import gzip
    import hashlib
    import json
    from pathlib import Path

    from icsa.instances import load as IL

    from .units import build_s2_manifest
    ap = argparse.ArgumentParser()
    ap.add_argument("--s2", required=True, type=Path)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    man = build_s2_manifest(a.s2, "s2z/sst_s2.nc")
    recs = {r["instance"]["instance_id"]: r for r in IL.load_instances()["instances"]}
    req = {i: _required_of(r) for i, r in recs.items()}
    cal = [i for i, r in recs.items() if r.get("calibration")]
    h = hashlib.sha256()
    with open(a.s2, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 24), b""):
            h.update(blk)
    a.out.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out / "s2_chunk_index.csv.gz", "wt") as g:
        g.write("day,start,end\n")
        g.writelines(f"{d},{x},{y}\n" for d, (_, x, y) in sorted(man.units.items()))
    res = {"model": "icsa.faults.masking (see its docstring); detector v2 coverage", "seed": a.seed,
           "s2_file": {"bytes": man.files[0].size, "sha256": h.hexdigest()},
           "instances": len(req), "calibration_instance": cal,
           "all_instances": summary(man, req, a.seed),
           "calibration_instance_only": summary(man, {i: req[i] for i in cal}, a.seed) if cal else None}
    (a.out / "masking_summary.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
