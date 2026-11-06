import numpy as np, time as _time, os, json
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
    if d_ == 60: continue
    mask = np.zeros(N, dtype=bool)
    for i in np.where(is_baseline & (doy_b == d_))[0]:
        mask[max(i-5,0):min(i+5,N-1)+1] = True
    pool_idx.append((d_, np.flatnonzero(mask)))

nsea_all = np.isfinite(sst_t).all(axis=0).reshape(-1)
nsea = int(nsea_all.sum())
S = sst_b.reshape(N, -1)[:, nsea_all]

thr = np.full((366, nsea), np.nan); clim = np.full((366, nsea), np.nan)
arow = np.arange(nsea)
for d_, idx in pool_idx:
    V = S[idx, :].T
    fin = np.isfinite(V); n = fin.sum(axis=1); valid = n > 0
    W = np.sort(np.where(fin, V, np.inf), axis=1)
    r = 0.9*n - 0.5
    f = np.clip(np.floor(r).astype(np.int64), 0, np.maximum(n-1,0))
    c = np.clip(np.ceil(r).astype(np.int64), 0, np.maximum(n-1,0))
    q = W[arow,f] + (r-f)*(W[arow,c]-W[arow,f]); q[~valid] = np.nan
    thr[d_-1,:] = q
    clim[d_-1,:] = np.where(valid, np.where(fin, V, 0.0).sum(axis=1)/np.where(n>0,n,1), np.nan)
thr[59,:] = (thr[58,:]+thr[60,:])/2.0
clim[59,:] = (clim[58,:]+clim[60,:])/2.0

I = np.mod(np.arange(366)[:,None] - 15 + np.arange(31)[None,:], 366)
def smooth31(X):
    out = np.empty_like(X)
    for a in range(0, X.shape[1], 600):
        out[:, a:a+600] = X[I, a:a+600].mean(axis=1)
    return out
thr_s = smooth31(thr); clim_s = smooth31(clim)
print("thresholds/clim done, t =", round(_time.time()-t0,1))

# ---------- per-cell MHWs over target ----------
sst_tc = sst_t.reshape(92, -1)[:, nsea_all]
hot = sst_tc >= thr_s[doy_t - 1, :]            # (92, nsea)
NT = 92

mhw = np.zeros((NT, nsea), dtype=np.uint8)
def runs_of(x):
    # x: bool (NT,) ; returns list of (start, end) inclusive of consecutive True
    x = np.asarray(x, dtype=bool)
    d = np.diff(x.view(np.int8))
    starts = list(np.flatnonzero(d == 1)) + ([0] if x[0] else [])
    ends   = list(np.flatnonzero(d == -1) - 1) + ([len(x)-1] if x[-1] else [])
    return list(zip(starts, ends))

n_merged = 0
for ci in range(nsea):
    cand = [r for r in runs_of(hot[:, ci]) if r[1] - r[0] + 1 >= 5]
    merged = []
    for s, e in cand:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e); n_merged += 1
        else:
            merged.append((s, e))
    for s, e in merged:
        mhw[s:e+1, ci] = 1

active = mhw.any(axis=1)
events = runs_of(active)
print("events:", [(str(tt[s])[:10], str(tt[e])[:10], e-s+1) for s, e in events])
print("mhw cells with >=1 MHW day:", int((mhw.sum(0) > 0).sum()), "/", nsea)
print("t =", round(_time.time()-t0,1))

np.savez_compressed("cache/stage1.npz", thr_s=thr_s, clim_s=clim_s, hot=hot, mhw=mhw,
                    nsea_all=nsea_all, events=np.array(events).reshape(-1, 2) if events else np.zeros((0,2), int))
print("saved")