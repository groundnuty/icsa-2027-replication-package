import numpy as np, pickle
from datetime import date, timedelta

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/mhw2_state.pkl","rb") as f: S = pickle.load(f)
sst_pool = D["sst_pool"]; sst_target = D["sst_target"]; sea = D["sea"]
time_pool = D["time_pool"]; time_target = D["time_target"]
mhw_ref = S["mhw_mask"]; events_ref = S["events"]; cell_idx = S["cell_idx"]
nc = len(cell_idx)
assert (cell_idx == np.flatnonzero(sea)).all()

CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
N = 4028
M2 = np.zeros((366, N), dtype=bool)
pool_dates = [date(1991,12,27) + timedelta(days=i) for i in range(N)]
base_start = date(1992,1,1); base_end = date(2002,12,31)
for t_i, t in enumerate(pool_dates):
    lo = max(base_start, t - timedelta(days=5))
    hi = min(base_end, t + timedelta(days=5))
    d = lo
    while d <= hi:
        dd = CUM[d.month-1] + d.day
        if dd != 60:
            M2[dd-1, t_i] = True
        d += timedelta(days=1)
M = np.load("/tmp/M.npy")
print("pool matrix identical:", bool((M2 == M).all()))

def hazen_manual(X):
    out = np.empty(X.shape[1])
    Xs = np.sort(X, axis=0)
    for c in range(X.shape[1]):
        fin = Xs[:, c]; fin = fin[~np.isnan(fin)]
        n = len(fin)
        if n == 0: out[c] = np.nan; continue
        v = n*0.9 - 0.5
        if v <= 0: out[c] = fin[0]; continue
        if v >= n-1: out[c] = fin[n-1]; continue
        i = int(np.floor(v)); f = v - i
        out[c] = fin[i] + f*(fin[i+1]-fin[i])
    return out

with open("/tmp/thr2.pkl","rb") as f: T = pickle.load(f)
pool2 = sst_pool.reshape(N, 3600)[:, cell_idx]
thr2 = np.full((366, nc), np.nan); clim2 = np.full((366, nc), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = pool2[M2[d-1], :]
    thr2[d-1] = hazen_manual(X)
    clim2[d-1] = np.nanmean(X, axis=0)
thr2[59] = 0.5*(thr2[58] + thr2[60]); clim2[59] = 0.5*(clim2[58] + clim2[60])
print("thr identical:", bool(np.allclose(thr2, T["thr"], equal_nan=True)), "maxdiff:", float(np.nanmax(np.abs(thr2 - T["thr"]))))
print("clim identical:", bool(np.allclose(clim2, T["clim"], equal_nan=True)))

def smooth31(a):
    out = np.empty_like(a)
    for d in range(366):
        idx = [(d-1+k) % 366 for k in range(31)]
        out[d] = a[idx].mean(axis=0)
    return out
thr2s = smooth31(thr2)
print("smoothed thr identical:", bool(np.allclose(thr2s, T["thr_s"], equal_nan=True)))

doy_t = np.array([CUM[dt.month-1] + dt.day for dt in time_target])
sst_c = sst_target.reshape(92, 3600)[:, cell_idx]
hot2 = sst_c >= thr2s[doy_t, :]
print("hot identical:", bool((hot2 == S["hot"]).all()))

def runs2(mask):
    dd = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1) - 1))

mhw2 = np.zeros((92, nc), dtype=bool)
for c in range(nc):
    rs = [r for r in runs2(hot2[:, c]) if r[1]-r[0]+1 >= 5]
    changed = True
    while changed:
        changed = False; new = []
        for r in rs:
            if new and r[0] - new[-1][1] - 1 <= 2:
                new[-1] = (new[-1][0], r[1]); changed = True
            else:
                new.append(r)
        rs = new
    for s, e in rs:
        mhw2[s:e+1, c] = True
print("mhw mask identical:", bool((mhw2 == mhw_ref).all()))

active2 = mhw2.any(axis=1)
ar = runs2(active2)
events2 = [(time_target[s].strftime("%Y-%m-%d"), time_target[e].strftime("%Y-%m-%d")) for s, e in ar]
print("events ref:", events_ref)
print("events new:", events2)
print("events identical:", events_ref == events2)

# check the cell with 2 MHWs: gap must be >= 3 non-hot days
cnt2 = [c for c in range(nc) if mhw_ref.sum(axis=0)[c] > 0]
for c in cnt2:
    r5 = [r for r in runs2(S["hot"][:, c]) if r[1]-r[0]+1 >= 5]
    if len(r5) == 2:
        gap = r5[1][0] - r5[0][1] - 1
        print("cell w/ 2 MHWs: flat", c, "runs", r5, "gap", gap)
