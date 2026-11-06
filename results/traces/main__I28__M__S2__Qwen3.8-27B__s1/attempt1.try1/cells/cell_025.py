import numpy as np, pickle
from datetime import date, timedelta

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/mhw_state.pkl","rb") as f: S = pickle.load(f)
sst_pool = D["sst_pool"]; sst_target = D["sst_target"]; sea = D["sea"]
time_pool = D["time_pool"]; time_target = D["time_target"]
mhw_ref = S["mhw_mask"]; events_ref = S["events"]; cell_idx_ref = S["cell_idx"]

CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])

# --- independent sea cells ---
sea2 = np.isfinite(sst_target).all(axis=0)
assert (sea2 == sea).all()
cell_idx = np.flatnonzero(sea)
assert (cell_idx == cell_idx_ref).all()
nc = len(cell_idx)

# --- independent pool matrix: per date t, determine which doys it belongs to ---
N = 4028
M2 = np.zeros((366, N), dtype=bool)
pool_dates = [date(1991,12,27) + timedelta(days=i) for i in range(N)]
# for each pool date t and baseline date b with |t-b|<=5: M2[doy(b), t]=True
base_start = date(1992,1,1); base_end = date(2002,12,31)
for t_i, t in enumerate(pool_dates):
    lo = max(base_start, t - timedelta(days=5))
    hi = min(base_end, t + timedelta(days=5))
    d = lo
    while d <= hi:
        M2[CUM[d.month-1] + d.day, t_i] = True
        d += timedelta(days=1)
M = np.load("/tmp/M.npy")
print("pool matrix identical:", (M2 == M).all())

# --- independent threshold via manual hazen on sorted finite values ---
def hazen_manual(X):  # X (n_sel, nc) with possible NaNs
    out = np.empty(X.shape[1])
    order = np.argsort(X, axis=0)
    Xs = X[order]
    nsel = X.shape[0]
    for c in range(X.shape[1]):
        x = Xs[:, c]
        fin = x[~np.isnan(x)]
        n = len(fin)
        if n == 0:
            out[c] = np.nan; continue
        v = n * 0.9 - 0.5
        if v <= 0: out[c] = fin[0]; continue
        if v >= n - 1: out[c] = fin[n-1]; continue
        i = int(np.floor(v)); f = v - i
        out[c] = fin[i] + f * (fin[i+1] - fin[i])
    return out

thr2 = np.full((366, nc), np.nan); clim2 = np.full((366, nc), np.nan)
pool2 = sst_pool.reshape(N, 3600)[:, cell_idx]
for d in range(1, 367):
    if d == 60: continue
    X = pool2[M2[d-1], :]
    thr2[d-1] = hazen_manual(X)
    clim2[d-1] = np.nanmean(X, axis=0)
thr2[59] = 0.5*(thr2[58] + thr2[60]); clim2[59] = 0.5*(clim2[58] + clim2[60])

with open("/tmp/thr.pkl","rb") as f: T = pickle.load(f)
print("thr identical (allclose):", np.allclose(thr2, T["thr"], equal_nan=True))
print("max abs diff thr:", np.nanmax(np.abs(thr2 - T["thr"])))
print("clim identical:", np.allclose(clim2, T["clim"], equal_nan=True))

def smooth31(a):
    out = np.empty_like(a)
    for d in range(366):
        idx = [(d-1+k) % 366 for k in range(31)]
        out[d] = a[idx].mean(axis=0)
    return out
thr2s = smooth31(thr2)
print("smoothed thr identical:", np.allclose(thr2s, T["thr_s"], equal_nan=True))

# --- independent hot detection & MHW (diff-based runs, fixed-point merge) ---
doy_t = np.array([CUM[dt.month-1] + dt.day for dt in time_target])
sst_c = sst_target.reshape(92, 3600)[:, cell_idx]
hot2 = sst_c >= thr2s[doy_t, :]
print("hot identical:", (hot2 == S["hot"]).all())

def runs2(mask):  # diff based
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1) - 1
    return list(zip(starts, ends))

mhw2 = np.zeros((92, nc), dtype=bool)
for c in range(nc):
    rs = [r for r in runs2(hot2[:, c]) if r[1]-r[0]+1 >= 5]
    # fixed-point pairwise merge
    changed = True
    while changed:
        changed = False
        new = []
        for r in rs:
            if new and r[0] - new[-1][1] - 1 <= 2:
                new[-1] = (new[-1][0], r[1]); changed = True
            else:
                new.append(r)
        rs = new
    for s, e in rs:
        mhw2[s:e+1, c] = True
print("mhw mask identical:", (mhw2 == mhw_ref).all())

active2 = mhw2.any(axis=1)
ar = runs2(active2)
events2 = [(time_target[s].strftime("%Y-%m-%d"), time_target[e].strftime("%Y-%m-%d")) for s, e in ar]
print("events ref:", events_ref)
print("events new:", events2)
print("events identical:", events_ref == events2)
