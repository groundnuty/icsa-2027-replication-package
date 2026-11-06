
import numpy as np, time, datetime, pickle

S_base = np.load('work/S_base.npy')   # (4028, 60, 60) float32, 1991-12-27 .. 2003-01-05
S_tgt  = np.load('work/S_tgt.npy')    # (92, 60, 60) float32, 2017-06-01 .. 2017-08-31
lat = np.load('work/lat.npy'); lon = np.load('work/lon.npy')
print(S_base.shape, S_tgt.shape, lat.shape, lon.shape)

# day-of-year by month/day, leap-year mapping (Jan1=1, Feb28=59, Feb29=60, Mar1=61, Dec31=366)
cdf = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def doy_of(dates):
    return cdf[np.array([d.month for d in dates]) - 1] + np.array([d.day for d in dates])

w_start = datetime.date(1991,12,27)
n_base_window = S_base.shape[0]
win_dates = [w_start + datetime.timedelta(days=i) for i in range(n_base_window)]
assert win_dates[-1] == datetime.date(2003,1,5), win_dates[-1]

base_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=i) for i in range(4018)]
assert base_dates[-1] == datetime.date(2002,12,31)
# baseline dates are at window offset 5 .. 4022
assert win_dates[5] == datetime.date(1992,1,1)

doy_base = doy_of(base_dates)   # (4018,)
# pool indices per day-of-year: for each baseline j and k in -5..5 -> window index j+5+k
offs = np.arange(-5, 6)[None, :]
J = np.arange(4018)[:, None]
idx_all = (J + 5 + offs).ravel()          # 44198 indices into S_base time
doy_all = np.repeat(doy_base, 11)         # matching doyears
# verify each (j,k) window index is in range
assert idx_all.min() >= 0 and idx_all.max() < n_base_window
print("doy range in baseline:", doy_base.min(), doy_base.max())
# sanity: number of baseline dates per doyear should be 11 for all d except 60 (0)
cnt, vals = np.unique(doy_base, return_counts=True)
bad = [(int(v), int(c)) for v, c in zip(vals, cnt) if (v == 60 and c != 0) or (v != 60 and c != 11)]
print("doy counts anomalies:", bad[:10])
# pool sizes per doyear
psizes = {int(v): int(np.sum(doy_all == v)) for v in vals}
print("pool size min/max (d!=60):", min(v for k,v in psizes.items() if k!=60), max(v for k,v in psizes.items() if k!=60))
print("d=59 pool:", psizes.get(59), " d=61 pool:", psizes.get(61), " d=60 pool:", psizes.get(60, 0))

# check a specific window: d=1 -> 1991-12-27 .. 1992-01-06 for year 1992
i1 = np.sort(idx_all[doy_all == 1])
print("first 11 pool dates for d=1:", [str(win_dates[i]) for i in i1[:11]])

t0=time.time()
N = 60*60
thr = np.full((366, N), np.nan)
clim = np.full((366, N), np.nan)
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        X = S_base[idx_all[doy_all == d]].astype(np.float64)   # (121, 3600)
        thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
        clim[d-1] = np.nanmean(X, axis=0)
print("pool loop:", time.time()-t0, "s")

# day 60 = mean of days 59 and 61
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# NaN statistics (mostly land)
nan_thr = np.isnan(thr).any(axis=0).sum()
print("cells with any NaN threshold:", int(nan_thr), "of", N)
# per-doy NaN count
per_doy_nan = np.isnan(thr).sum(axis=1)
print("doy with >0 NaN cells:", [(i+1, int(v)) for i, v in enumerate(per_doy_nan) if v > 0][:10])

np.save('work/thr_raw.npy', thr)
np.save('work/clim_raw.npy', clim)
print("sample thr (K) cell(0,0) doy 152,182,213 (Jun1,Jun30,Jul31):", thr[151,0], thr[181,0], thr[212,0])
print("sample clim cell(0,0):", clim[151,0], clim[181,0], clim[212,0])
