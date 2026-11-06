import numpy as np, time
from datetime import date, timedelta
T0 = time.time()

z = np.load('/work/read_done.npz', allow_pickle=False)
base = z['base']; tgt = z['tgt']
lat_vals = z['lat_vals']; lon_vals = z['lon_vals']
b_dates = z['b_dates']; t_dates = z['t_dates']
nB, La, Lo = base.shape
C = La * Lo

def smooth31(a):
    a = np.asarray(a, dtype=np.float64)
    A = np.concatenate([a, a, a])
    cs = np.cumsum(np.concatenate([[0.0], A]))
    return (cs[382:748] - cs[351:717]) / 31.0

doy_to_md = np.zeros((367, 2), dtype=int)
for d in range(1, 367):
    dt = date(2000, 1, 1) + timedelta(days=d - 1)
    doy_to_md[d] = (dt.month, dt.day)
date_to_bidx = {np.datetime64(b_dates[k], 'D'): k for k in range(nB)}
years = list(range(1992, 2003))

thr  = np.full((C, 366), np.nan)
clim = np.full((C, 366), np.nan)
sizes = set()
for d in range(1, 367):
    if d == 60:
        continue
    m, dd = doy_to_md[d]
    wset = set()
    for y in years:
        b = date(y, m, dd)
        for k in range(-5, 6):
            ki = date_to_bidx.get(np.datetime64(b + timedelta(days=k), 'D'))
            if ki is not None:
                wset.add(ki)
    mask = np.zeros(nB, bool); mask[np.fromiter(wset, dtype=np.int64)] = True
    X = base[mask].reshape(len(wset), C).T.astype(np.float64)      # (C, nwin)
    thr[:, d - 1] = np.nanquantile(X, 0.9, axis=1, method='hazen')
    nn = ~np.isnan(X)
    cnt = nn.sum(axis=1)
    clim[:, d - 1] = np.where(cnt > 0, np.where(nn, X, 0.0).sum(axis=1) / np.maximum(cnt, 1), np.nan)
    sizes.add(len(wset))
    if d % 60 == 0:
        print("doy", d, "pool dates", len(wset), "t=", round(time.time()-T0, 1), flush=True)
print("pool sizes:", sizes)

# day 60 (index 59) = mean of days 59 and 61 (indices 58, 60)
thr[:, 59] = np.mean(thr[:, [58, 60]], axis=1)
clim[:, 59] = np.mean(clim[:, [58, 60]], axis=1)
print("any NaN left in thr pre-smooth:", int(np.isnan(thr).sum()), "clim:", int(np.isnan(clim).sum()))

thr  = np.array([smooth31(thr[c])  for c in range(C)])
clim = np.array([smooth31(clim[c]) for c in range(C)])
print("thr range:", np.nanmin(thr), np.nanmax(thr), " clim range:", np.nanmin(clim), np.nanmax(clim))
print("cells with all-finite thr:", int((~np.isnan(thr).any(axis=1)).sum()), "of", C)

np.savez('/work/stats.npz', thr=thr, clim=clim,
         lat_vals=lat_vals, lon_vals=lon_vals, b_dates=b_dates, t_dates=t_dates)
print("stats saved, elapsed:", round(time.time()-T0, 1))
