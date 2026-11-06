
import re
src = open("/work/compute.py").read()
old = """idx = {s: i for i, s in enumerate(base_days)}
import collections
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    idxs = set()
    for i, dv in enumerate(doyB):
        if dv == d:
            for k in range(-5, 6):
                idxs.add(i + k)
    pools[d] = np.sort(np.array(sorted(idxs), dtype=np.int64))"""
new = """idx = {s: i for i, s in enumerate(base_days)}
import collections
is_baseline = np.array([(s >= "1992-01-01") and (s <= "2002-12-31") for s in base_days])
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    idxs = set()
    for i, dv in enumerate(doyB):
        if dv == d and is_baseline[i]:
            for k in range(-5, 6):
                idxs.add(i + k)
    pools[d] = np.sort(np.array(sorted(idxs), dtype=np.int64))
    assert pools[d].min() >= 0 and pools[d].max() < nB, (d, pools[d].min(), pools[d].max())"""
assert old in src
src = src.replace(old, new)
open("/work/compute.py","w").write(src)
print("patched")
