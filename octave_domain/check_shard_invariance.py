"""Rehearsal shards (other column ranges) against the same columns of the production shards: Step_2 values must not depend on the shard.

    python3 check_shard_invariance.py <run dir>      (reads rehearsal/shards/{t8,t1_*} and shards/s*; bit patterns compared)
"""
import json
import sys
from pathlib import Path

import numpy as np

root = Path(sys.argv[1])
ROWS, TD = 449, 15338
prod = [(n, int(a), int(b)) for n, a, b in (ln.split() for ln in (root / "shards" / "shards.txt").read_text().splitlines())]
reh = [(n, int(a), int(b)) for n, a, b in (ln.split() for ln in (root / "rehearsal" / "shards" / "shards_test.txt").read_text().splitlines())]
shape = {"m90": 366, "mclim": 366, "mhw_ts": TD}


_cache = {}


def cols(d, name, nc, n3):
    """Raw bit patterns of the doubles, [t, column, row]; each file is read once, sequentially (the last 2 kept)."""
    key = (str(d), name)
    if key not in _cache:
        if len(_cache) > 6:
            _cache.pop(next(iter(_cache)))
        _cache[key] = np.fromfile(d / name, np.uint64).reshape(n3, nc, ROWS)
    return _cache[key]


res = []
for rn, ra, rb in reh:
    for col in range(ra, rb + 1):
        pn, pa, pb = next(p for p in prod if p[1] <= col <= p[2])
        row = {"rehearsal": rn, "column": col, "production": pn}
        for f, n3 in shape.items():
            r = cols(root / "rehearsal" / "shards" / rn, f"{f}.f64", rb - ra + 1, n3)[:, col - ra, :]
            p = cols(root / "shards" / pn, f"{f}.f64", pb - pa + 1, n3)[:, col - pa, :]
            row[f] = bool(np.array_equal(r, p))
        res.append(row)
bad = [r for r in res if not (r["m90"] and r["mclim"] and r["mhw_ts"])]
print(json.dumps({"columns_compared": len(res), "all_bit_identical": not bad, "differing": bad[:5]}))
sys.exit(1 if bad else 0)
