import numpy as np, time as _time, os
t0 = _time.time()
d = np.load("cache/region.npz")
sst_b = d['sst_base']; sst_t = d['sst_tgt']; tb = d['time_base']; tt = d['time_tgt']
lat = d['lat']; lon = d['lon']

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s):
    return CUM[int(s[5:7])-1] + int(s[8:10])
doy_b = np.array([doy(s) for s in tb], dtype=int)
doy_t = np.array([doy(s) for s in tt], dtype=int)
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

nsea_all = np.isfinite(sst_t).all(axis=0).reshape(-1)
nsea = int(nsea_all.sum())
S = sst_b.reshape(N, -1)[:, nsea_all]
print("S finite frac:", np.isfinite(S).mean())

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
    thr[d_-1, :] = q
    clim[d_-1, :] = np.where(valid, np.where(fin, V, 0.0).sum(axis=1) / np.where(n>0, n, 1), np.nan)

thr[59, :] = (thr[58, :] + thr[60, :]) / 2.0
clim[59, :] = (clim[58, :] + clim[60, :]) / 2.0

I = np.mod(np.arange(366)[:, None] - 15 + np.arange(31)[None, :], 366)
def smooth31(X):
    out = np.empty_like(X)
    for a in range(0, X.shape[1], 600):
        out[:, a:a+600] = X[I, a:a+600].mean(axis=1)
    return out
thr_s = smooth31(thr); clim_s = smooth31(clim)

# spot check smoothing: hand-compute one value
cell = 0
hh = (np.arange(366) - 15) % 366  # for day 0: -15..+15 mod 366
check = thr[(np.arange(366) - 15) % 366, cell].mean()
assert np.isclose(thr_s[0, cell], check) and np.isclose(thr_s[20, cell], thr[(np.arange(20-15,20+16))%366, cell].mean())
print("smoothing spot-check OK; t =", round(_time.time()-t0,1), "s")

sst_tc = sst_t.reshape(92, -1)[:, nsea_all]
hot = sst_tc >= thr_s[doy_t - 1, :]
print("hot fraction:", round(float(hot.mean()),4))
print("thr sample (K) cell0, Jun1/Aug31:", thr_s[152,0], thr_s[243,0])

np.savez_compressed("cache/stage1.npz", thr_s=thr_s, clim_s=clim_s, hot=hot,
                    nsea_all=nsea_all, doy_t=doy_t, lat=lat, lon=lon, time_tgt=tt)
print("stage1 saved")