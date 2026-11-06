
import numpy as np, time, datetime, warnings

S_base = np.load('work/S_base.npy')
N = 3600
mday = [31,29,31,30,31,30,31,31,30,31,30,31]
cdf_prev = np.concatenate([[0], np.cumsum(mday)[:-1]])
def doy_of(dates):
    mo = np.array([d.month for d in dates]); da = np.array([d.day for d in dates])
    return cdf_prev[mo - 1] + da

n_w = S_base.shape[0]
base_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=i) for i in range(4018)]
doy_base = doy_of(base_dates)
counts = np.zeros(367, dtype=int)
for v in doy_base: counts[v] += 1
assert counts[60] == 3 and np.all(counts[np.arange(1,367)!=60] == 11)
print("baseline doyear counts OK")

offs = np.arange(-5, 6)[None, :]
J = np.arange(4018)[:, None]
idx_all = (J + 5 + offs).ravel()
doy_all = np.repeat(doy_base, 11)
assert idx_all.min() >= 0 and idx_all.max() < n_w
win_dates = [datetime.date(1991,12,27) + datetime.timedelta(days=i) for i in range(n_w)]
i1 = np.sort(idx_all[doy_all == 1])
print("d=1 first window:", [str(win_dates[i]) for i in i1[:11]])
i366 = np.sort(idx_all[doy_all == 366])
print("d=366 last window:", [str(win_dates[i]) for i in i366[-11:]])
i61 = np.sort(idx_all[doy_all == 61])
print("d=61 1996 window:", [str(win_dates[i]) for i in i61 if win_dates[i].year == 1996])

t0 = time.time()
thr = np.full((366, N), np.nan)
clim = np.full((366, N), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        X = S_base[idx_all[doy_all == d]].astype(np.float64).reshape(-1, N)
        assert X.shape[0] == 121
        thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
        clim[d-1] = np.nanmean(X, axis=0)
print("pool loop:", round(time.time()-t0,1), "s")

thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0
print("cells with any NaN thr:", int(np.isnan(thr).any(axis=0).sum()), "of", N)
per = np.isnan(thr).sum(axis=1)
print("doys with NaN cells:", [(int(i+1), int(v)) for i, v in enumerate(per) if v > 0][:10])
np.save('work/thr_raw.npy', thr)
np.save('work/clim_raw.npy', clim)
print("sample thr cell0 doy152/213/243 (K):", thr[151,0], thr[212,0], thr[242,0])
print("summer thr min/max over cells:", float(np.nanmin(thr[150:244])), float(np.nanmax(thr[150:244])))
