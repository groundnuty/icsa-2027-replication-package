import numpy as np, pickle
from numpy.lib.stride_tricks import sliding_window_view

M = np.load("/tmp/M.npy")
with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
sst_pool = D["sst_pool"]; sea = D["sea"]

cell_idx = np.flatnonzero(sea)          # proper flat indices
assert cell_idx.dtype == np.int64 and cell_idx.min() >= 0 and cell_idx.max() < 3600
nc = len(cell_idx)
print("nc:", nc, "first/last:", cell_idx[:3], cell_idx[-3:])

N = 4028
pool2 = sst_pool.reshape(N, 3600)[:, cell_idx]   # (N, nc)
print("pool2:", pool2.shape)
# spot check: column for flat idx 0 -> (0,0); flat idx 3599 -> (59,59)
i, j = divmod(int(cell_idx[0]), 60)
print("col0 cell:", i, j, "lat/lon:", D["lat"][i], D["lon"][j])
i, j = divmod(int(cell_idx[-1]), 60)
print("last col cell:", i, j, "lat/lon:", D["lat"][i], D["lon"][j])

thr = np.full((366, nc), np.nan)
clim = np.full((366, nc), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = pool2[M[d-1], :]
    thr[d-1] = np.nanquantile(X, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(X, axis=0)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("nan thr:", bool(np.isnan(thr).any()), "nan clim:", bool(np.isnan(clim).any()))
print("thr < clim anywhere?", bool((thr < clim).any()))

def smooth31_wrap(a):
    b = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return sliding_window_view(b, 31, axis=0).mean(axis=-1)

thr_s = smooth31_wrap(thr)
clim_s = smooth31_wrap(clim)
print("thr_s nan:", bool(np.isnan(thr_s).any()))
print("thr_s day153 median C:", float(np.median(thr_s[152]))-273.15, " clim C:", float(np.median(clim_s[152]))-273.15)
print("thr_s day244 median C:", float(np.median(thr_s[243]))-273.15)
print("thr_s range C:", float(thr_s.min())-273.15, float(thr_s.max())-273.15)

with open("/tmp/thr2.pkl","wb") as f:
    pickle.dump({"thr": thr, "clim": clim, "thr_s": thr_s, "clim_s": clim_s, "cell_idx": cell_idx}, f)
print("saved /tmp/thr2.pkl")
