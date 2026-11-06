import numpy as np, time
from datetime import date

t0 = time.time()
thr = np.load('/work/data/thr_raw.npy')     # (366, nsea)
clim = np.load('/work/data/clim_raw.npy')
si = np.load('/work/data/sea_idx.npy')
T = np.load('/work/data/T.npy')
tt = np.load('/work/data/tt.npy')

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)

# 1) day 60 = mean of days 59 and 61 (arrays indexed 58, 59, 60)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("day60 filled:", np.isnan(thr[59]).any(), np.isnan(clim[59]).any())

# 2) circular centred 31-day mean (wrap-around)
def circ31(A):
    A2 = np.concatenate([A[-15:], A, A[:15]], axis=0)   # (396, nsea)
    W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)  # (366, nsea, 31)
    return W.mean(axis=2)
thr_s = circ31(thr)
clim_s = circ31(clim)
# verify against a naive loop for a few entries
def circ31_naive(A, i):
    return np.mean([A[(i+k) % 366] for k in range(-15, 16)])
for i in [0, 5, 58, 59, 60, 200, 364, 365]:
    assert np.allclose(thr_s[i], circ31_naive(thr, i)), i
    assert np.allclose(clim_s[i], circ31_naive(clim, i)), i
print("smoothing verified vs naive loop")
print("thr range:", thr_s.min(), thr_s.max(), " clim range:", clim_s.min(), clim_s.max())

# 3) target: hot days
tt_dates = [date.fromisoformat(str(np.datetime64(t))[:10]) for t in tt]
doy_t = np.array([doy_of(t.month, t.day) for t in tt_dates])
assert len(np.unique(doy_t)) == 92 and doy_t.min() == 153 and doy_t.max() == 244
nsea = thr.shape[1]
Tsea = T[:, si//60, si%60]
thr_t = thr_s[doy_t - 1]                     # (92, nsea)
hot = np.isfinite(Tsea) & (Tsea >= thr_t)    # (92, nsea)
print("hot days total:", int(hot.sum()), "max per day:", int(hot.max(axis=1).max()), "max per cell:", int(hot.max(axis=0).max()))

# 4) per-cell MHW: runs of >=5 consecutive hot days, then join runs separated by <=2 non-hot days
def runs_bool(v):
    """maximal True runs -> list of (start, end) inclusive indices"""
    idx = np.flatnonzero(np.diff(np.concatenate(([0], v.view(np.int8), [0]))))
    pairs = np.vstack(idx).T if len(idx) else np.empty((0,2), int)
    return list(zip(pairs[:,0], pairs[:,1]-1))

mask = np.zeros((92, nsea), dtype=np.uint8)
n_mhw_cells = 0
for c in range(nsea):
    ivs = [(s,e) for s,e in runs_bool(hot[:, c]) if e - s + 1 >= 5]
    if not ivs: continue
    merged = [list(ivs[0])]
    for s, e in ivs[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    for s, e in merged:
        mask[s:e+1, c] = 1
    n_mhw_cells += 1
print("cells with >=1 MHW:", n_mhw_cells, " mask cells*days:", int(mask.sum()))
active = mask.any(axis=1)
print("active days:", int(active.sum()), "of 92")

# 5) regional events
ev = []
s = None
for i, a in enumerate(active):
    if a and s is None: s = i
    if (not a) and s is not None:
        ev.append((s, i-1)); s = None
if s is not None: ev.append((s, 91))
evd = [(tt_dates[a].isoformat(), tt_dates[b].isoformat()) for a, b in ev]
print("events:", evd)
np.save('/work/data/thr_s.npy', thr_s)
np.save('/work/data/clim_s.npy', clim_s)
np.save('/work/data/mask.npy', mask)
print("done", round(time.time()-t0,1), "s")