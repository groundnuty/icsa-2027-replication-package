
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
    n = len(h)
    pad = np.concatenate(([0], h.view(np.int8), [0]))
    d = np.diff(pad)
    starts = np.flatnonzero(d == 1)          # hot-coord start
    ends = np.flatnonzero(d == -1)           # hot-coord exclusive end
    keep = [(int(s), int(e)) for s, e in zip(starts, ends) if e - s >= 5]
    merged = []
    for s, e in keep:
        if merged and s - merged[-1][1] <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    out = np.zeros(n, bool)
    for s, e in merged:
        out[s:e] = True
    return out

mismatch = 0
for c in range(3600):
    if not np.array_equal(cell_mhw_v3(hot[c]), mask[:, c]):
        mismatch += 1
print('mismatches (fixed checker):', mismatch)

# also validate: every mask day either hot or a bridged gap with hot on both sides
import itertools
viol = 0
for c in range(3600):
    m = mask[:, c]
    for t in np.flatnonzero(m & ~hot[c]):
        if not (hot[c, max(0,t-2):t].any() or True):
            pass
        # gap day must be between two hot days (within the merged span)
        left = any(hot[c, k] for k in range(t-2, t))
        right = any(hot[c, k] for k in range(t+1, t+3))
        if not (left and right):
            viol += 1
print('gap-day violations:', viol)

# count how many merged MHWs contain gap days
gapdays = (mask & ~hot).sum()
print('total bridged gap days:', int(gapdays))
