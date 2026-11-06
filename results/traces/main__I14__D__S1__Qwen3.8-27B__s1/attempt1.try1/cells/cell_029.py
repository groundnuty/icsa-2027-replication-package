import numpy as np, time
from datetime import date

t0 = time.time()
thr = np.load('/work/data/thr_raw.npy').copy()
clim = np.load('/work/data/clim_raw.npy').copy()
si = np.load('/work/data/sea_idx.npy')
T = np.load('/work/data/T.npy')
tt = np.load('/work/data/tt.npy')

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
assert not np.isnan(thr).any() and not np.isnan(clim).any()

def circ31(A):
    A2 = np.concatenate([A[-15:], A, A[:15]], axis=0)
    W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)
    return W.mean(axis=2)
def circ31_naive(A, i):
    return np.mean(np.stack([A[(i+k) % 366] for k in range(-15, 16)]), axis=0)

thr_s, clim_s = circ31(thr), circ31(clim)
for i in [0, 1, 5, 14, 15, 16, 58, 59, 60, 100, 200, 350, 364, 365]:
    assert np.allclose(thr_s[i], circ31_naive(thr, i), rtol=0, atol=1e-9), ("thr", i)
    assert np.allclose(clim_s[i], circ31_naive(clim, i), rtol=0, atol=1e-9), ("clim", i)
print("smoothing verified (per-column naive), all 31-window boundaries checked")
print("thr_s range:", thr_s.min(), thr_s.max(), "(K)", " clim_s range:", clim_s.min(), clim_s.max())

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)

tt_dates = [date.fromisoformat(str(np.datetime64(t))[:10]) for t in tt]
doy_t = np.array([doy_of(t.month, t.day) for t in tt_dates])
assert len(np.unique(doy_t)) == 92 and doy_t.min() == 153 and doy_t.max() == 244
nsea = thr.shape[1]
Tsea = T[:, si//60, si%60]
assert (np.isfinite(Tsea)).all()
thr_t = thr_s[doy_t - 1]
hot = Tsea >= thr_t
print("hot days total:", int(hot.sum()), " max per day:", int(hot.max(axis=1).max()), " max per cell:", int(hot.max(axis=0).max()))

def runs_bool(v):
    pad = np.concatenate(([0], v.view(np.int8), [0]))
    idx = np.flatnonzero(np.diff(pad))
    if len(idx) == 0: return []
    p = np.vstack(idx).T
    return [(int(p[j,0]), int(p[j,1])-1) for j in range(p.shape[0])]

# cross-check runs_bool on a random vector vs a trivial loop
rng = np.random.default_rng(1)
for _ in range(20):
    v = rng.integers(0, 2, size=rng.integers(1, 100)).astype(bool)
    # trivial
    exp, s = [], None
    for j, x in enumerate(v):
        if x and s is None: s = j
        if (not x) and s is not None: exp.append((s, j-1)); s = None
    if s is not None: exp.append((s, len(v)-1))
    assert runs_bool(v) == exp
print("runs_bool verified")

mask = np.zeros((92, nsea), dtype=np.uint8)
n_mhw_cells = 0
for c in range(nsea):
    ivs = [(s, e) for s, e in runs_bool(hot[:, c]) if e - s + 1 >= 5]
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
print("cells with >=1 MHW:", n_mhw_cells, " mask days*cells:", int(mask.sum()))
active = mask.any(axis=1)
print("active days:", int(active.sum()), "of 92")

ev = []
s = None
for i, a in enumerate(active):
    if a and s is None: s = i
    if (not a) and s is not None:
        ev.append((s, i-1)); s = None
if s is not None: ev.append((s, 91))
evd = [(tt_dates[a].isoformat(), tt_dates[b].isoformat(), b-a+1) for a, b in ev]
print("events:", evd)
np.save('/work/data/thr_s.npy', thr_s)
np.save('/work/data/clim_s.npy', clim_s)
np.save('/work/data/mask.npy', mask)
print("done", round(time.time()-t0, 1), "s")