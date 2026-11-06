import numpy as np, os, time as _time
t0 = _time.time()
d = np.load("cache/region.npz")
sst_b = d['sst_base']; sst_t = d['sst_tgt']; tb = d['time_base']; tt = d['time_tgt']

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s):
    return CUM[int(s[5:7])-1] + int(s[8:10])
doy_b = np.array([doy(s) for s in tb], dtype=int)
doy_t = np.array([doy(s) for s in tt], dtype=int)
print("target doys:", doy_t.min(), doy_t.max(), "| baseline doy range:", doy_b.min(), doy_b.max(), "| day60 in baseline:", 60 in set(doy_b.tolist()))
# spot checks
import datetime
for s in ["1992-01-01","1992-02-28","1992-02-29","1992-03-01","2002-12-31","2003-01-05","1991-12-27","2022-06-01","2022-08-31"]:
    print(s, "->", doy(s))

is_baseline = (tb >= "1992-01-01") & (tb <= "2002-12-31")
N = len(tb)
pool_idx = []
for d_ in range(1, 367):
    if d_ == 60:
        continue
    mask = np.zeros(N, dtype=bool)
    for i in np.where(is_baseline & (doy_b == d_))[0]:
        mask[max(i-5,0):min(i+5,N-1)+1] = True
    pool_idx.append((d_, np.flatnonzero(mask)))
print("pool sizes:", min(len(x) for _,x in pool_idx), max(len(x) for _,x in pool_idx))

nsea_all = np.isfinite(sst_t).all(axis=0).reshape(-1)
nsea = int(nsea_all.sum())
print("sea cells:", nsea, "of 3600")
S = sst_b.reshape(N, -1)[:, nsea_all]

thr = np.full((366, nsea), np.nan); clim = np.full((366, nsea), np.nan)
arow = np.arange(nsea)
for d_, idx in pool_idx:
    V = S[idx, :].T
    fin = np.isfinite(V)
    n = fin.sum(axis=1)
    valid = n > 0
    W = np.sort(np.where(fin, V, np.inf), axis=1)
    r = 0.9 * n - 0.5
    f = np.clip(np.floor(r).astype(np.int64), 0, np.maximum(n-1, 0))
    c = np.clip(np.ceil(r).astype(np.int64), 0, np.maximum(n-1, 0))
    q = W[arow, f] + (r - f) * (W[arow, c] - W[arow, f])
    q[~valid] = np.nan
    thr[d_, :] = q
    clim[d_, :] = np.where(valid, np.where(fin, V, 0.0).sum(axis=1) / np.where(n>0, n, 1), np.nan)

print("t =", round(_time.time()-t0,1), "s")
bad = np.argwhere(np.isnan(thr).any(axis=0))
print("cells with any empty pool:", len(bad))

# day 60 fill (before smoothing)
thr[60, :] = (thr[59, :] + thr[61, :]) / 2.0
clim[60, :] = (clim[59, :] + clim[61, :]) / 2.0

I = np.mod(np.arange(366)[:, None] - 15 + np.arange(31)[None, :], 366)
def smooth31(X):
    out = np.empty_like(X)
    for a in range(0, X.shape[1], 600):
        out[:, a:a+600] = X[I, a:a+600].mean(axis=1)
    return out
thr_s = smooth31(thr); clim_s = smooth31(clim)
print("smooth done, t =", round(_time.time()-t0,1), "s")

sst_tc = sst_t[:, nsea_all]
hot = sst_tc >= thr_s[doy_t - 1, :]
print("hot fraction:", round(float(hot.mean()),4))

np.savez_compressed("cache/stage1.npz", thr_s=thr_s, clim_s=clim_s, hot=hot,
                    nsea_all=nsea_all, doy_t=doy_t)
print("stage1 saved")