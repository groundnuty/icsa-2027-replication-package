import numpy as np, os, json, time as _time

t0 = _time.time()
d = np.load("cache/region.npz")
sst_b = d['sst_base']          # (4028, 60, 60)
sst_t = d['sst_tgt']           # (92, 60, 60)
tb = d['time_base']            # strings
tt = d['time_tgt']
lat = d['lat']; lon = d['lon']

# day-of-year in leap-year calendar (1 Jan=1 ... 29 Feb=60 ... 31 Dec=366)
import datetime
def doy(s):
    m, dd = int(s[5:7]), int(s[8:10])
    cum = [0,31,59,90,120,151,181,212,243,273,304,334]
    return cum[m-1] + dd
doy_b = np.array([doy(s) for s in tb], dtype=int)   # 1..366
doy_t = np.array([doy(s) for s in tt], dtype=int)
print("target doys:", doy_t.min(), doy_t.max(), "has day60 in target:", 60 in set(doy_t.tolist()))
print("baseline doy range:", doy_b.min(), doy_b.max())

# baseline day indices (1992-01-01 .. 2002-12-31)
is_baseline = (tb >= "1992-01-01") & (tb <= "2002-12-31")
print("n baseline days:", is_baseline.sum())

# pool mask (366, 4028): mask[d, t] True if some baseline date with doy=d within 5 days of t
N = len(tb)
pool_idx = []
for d_ in range(1, 367):
    if d_ == 60:
        continue
    mask = np.zeros(N, dtype=bool)
    base_i = np.where(is_baseline & (doy_b == d_))[0]
    for i in base_i:
        a, b = max(i-5, 0), min(i+5, N-1) + 1
        mask[a:b] = True
    idx = np.flatnonzero(mask)
    pool_idx.append((d_, idx))
print("pools built; sizes sample:", [(d_, len(idx)) for d_, idx in pool_idx[:3]], "...", [(d_, len(idx)) for d_, idx in pool_idx[-2:]])

# sea cells
fin_t = np.isfinite(sst_t)
nsea_all = fin_t.all(axis=0)
sea = np.argwhere(nsea_all)
nsea = len(sea)
print("sea cells:", nsea, "of", nsea_all.size, "non-finite target days total:", (~fin_t).sum())

S = sst_b.reshape(N, -1)[:, nsea_all.reshape(-1)]   # (4028, nsea)
print("S:", S.shape, S.nbytes/1e6, "MB")

# per-day q90 (hazen) and mean over pools, vectorised over cells
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
arow = np.arange(nsea)
for d_, idx in pool_idx:
    V = S[idx, :].T                                   # (nsea, k)
    fin = np.isfinite(V)
    n = fin.sum(axis=1)
    valid = n > 0
    W = np.where(fin, V, np.inf)
    sortedW = np.sort(W, axis=1)
    r = 0.9 * n - 0.5
    f = np.floor(r).astype(np.int64); c = np.ceil(r).astype(np.int64)
    f = np.clip(f, 0, np.maximum(n-1, 0)); c = np.clip(c, 0, np.maximum(n-1, 0))
    xf = sortedW[arow, f]; xc = sortedW[arow, c]
    q = xf + (r - f) * (xc - xf)
    q[~valid] = np.nan
    thr[d_, :] = q
    ss = np.where(fin, V, 0.0).sum(axis=1)
    clim[d_, :] = np.where(valid, ss / np.where(n>0, n, 1), np.nan)

# sanity: pool sizes per day
print("min pool size (over days):", min(len(idx) for _, idx in pool_idx), "max:", max(len(idx) for _, idx in pool_idx))
print("empty pools (no finite value) per day count:", int(np.isnan(thr[:, 0]).sum() + np.isnan(thr[5, :]).sum() and 0))
# cells with empty pool for some day
empty_cells = np.argwhere(np.isnan(thr).any(axis=0))
print("cells with any empty pool:", len(empty_cells), "of", nsea)

# day 60 = mean of 59 and 61 (before smoothing)
thr[60, :] = (thr[59, :] + thr[61, :]) / 2.0
clim[60, :] = (clim[59, :] + clim[61, :]) / 2.0

# 31-day circular moving mean
I = np.mod(np.arange(366)[:, None] - 15 + np.arange(31)[None, :], 366)   # (366, 31)
def smooth31(X):   # X: (366, nsea)
    out = np.empty_like(X)
    step = 600
    for a in range(0, X.shape[1], step):
        out[:, a:a+step] = X[I, a:a+step].mean(axis=1)
    return out
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smoothing done. t =", round(_time.time()-t0,1), "s")

# target comparison
sst_tc = sst_t[:, nsea_all.reshape(-1)]                      # (92, nsea)
hot = sst_tc >= thr_s[doy_t - 1, :]                          # (92, nsea)
print("hot fraction:", hot.mean())
np.save("cache/thr_s.npy", thr_s); np.save("cache/clim_s.npy", clim_s)
np.save("cache/hot.npy", hot)
np.save("cache/sea_cells.npy", sea)
print("saved")