import pandas as pd, numpy as np, json, os
# date axis for pooled data
dates_all = pd.DatetimeIndex(np.load('/work/subtime.npy'))
pos = {d:i for i,d in enumerate(dates_all)}
def doy(ts): return pd.Timestamp(2000, ts.month, ts.day).dayofyear
# anchors: baseline dates
anchors = pd.date_range('1992-01-01','2002-12-31')
pools = {d: [] for d in range(1,367) if d!=60}
for b in anchors:
    d = doy(b)
    if d==60: continue
    for k in range(-5,6):
        t = b+pd.Timedelta(days=k)
        pools[d].append(pos[t])
# sanity: no duplicate dates in a pool
for d in pools:
    assert len(set(pools[d]))==len(pools[d])
cells = fin_t.shape
Bv = A[:, :, :]  # all dates
thr = np.full((366,)+cells, np.nan); clim = np.full((366,)+cells, np.nan)
for d in range(1,367):
    if d==60: continue
    P = Bv[pools[d]]  # (n,60,60)
    thr[d-1] = np.nanquantile(P, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(P, axis=0)
thr[59] = (thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(x):
    out = np.zeros_like(x)
    for k in range(-15,16):
        out += np.roll(x, -k, axis=0)  # out[i] += x[(i+k)%366]
    return out/31
thr_s = smooth(thr); clim_s = smooth(clim)
print(np.isnan(thr_s[:,fin_t]).sum(), np.isnan(clim_s[:,fin_t]).sum())
print(thr_s[[0,59,181,365],30,30].round(3), clim_s[[0,59,181,365],30,30].round(3))
print(pools[1][:3], len(pools[1]), len(pools[152]))