
import sys, numpy as np
sys.path.insert(0,'/work/mhw')
sea = np.load('/work/mhw/sea.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
doy_tgt = np.load('/work/mhw/doy_tgt.npy')
mask = np.load('/work/mhw/mask.npy')
import common
ext, tgt, done = common.load_state()
S = tgt.astype(np.float64)
hot = (S.T >= thr_s[:, doy_tgt]); hot[~sea, :] = False

def cell_mhw_v3(h):
    # independent: find runs by diff, filter len>=5, merge gaps<=2
    n = len(h)
    pad = np.concatenate(([0], h.view(np.int8), [0]))
    d = np.diff(pad)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1) + 1   # exclusive
    keep = [(s, e) for s, e in zip(starts, ends) if e - s >= 5]
    merged = []
    for s, e in keep:
        if merged and s - merged[-1][1] <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    out = np.zeros(n, bool)
    for s, e in merged:
        out[s:e] = True
    return out, merged

mismatch = 0
first = None
for c in range(3600):
    m3, runs = cell_mhw_v3(hot[c])
    if not np.array_equal(m3, mask[:, c]):
        mismatch += 1
        if first is None:
            first = (c, np.flatnonzero(mask[:, c]), np.flatnonzero(m3), runs, np.flatnonzero(hot[c]))
print('mismatches:', mismatch)
if first:
    c, a, b, runs, hz = first
    print('cell', c)
    print('orig idx:', a)
    print('v3  idx :', b)
    print('v3 runs :', runs)
    print('hot idx :', hz)
