
import numpy as np, time, datetime, warnings

S_base = np.load('work/S_base.npy')   # (4028, 60, 60), 1991-12-27 .. 2003-01-05
S_tgt  = np.load('work/S_tgt.npy')    # (92, 60, 60)
N = 3600

mday = [31,29,31,30,31,30,31,31,30,31,30,31]
cdf_prev = np.concatenate([[0], np.cumsum(mday)[:-1]])  # days before month m: cdf_prev[m-1]
def doy_of(dates):
    mo = np.array([d.month for d in dates]); da = np.array([d.day for d in dates])
    return cdf_prev[mo - 1] + da

w_start = datetime.date(1991,12,27)
n_w = S_base.shape[0]
win_dates = [w_start + datetime.timedelta(days=i) for i in range(n_w)]
base_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=i) for i in range(4018)]
assert win_dates[5] == datetime.date(1992,1,1) and win_dates[-1] == datetime.date(2003,1,5)

doy_base = doy_of(base_dates)
# sanity checks on mapping
def chk(d, y, m, day):
    assert doy_base[[x.year==y and x.month==m and x.day==day for x in base_dates].index(True)] == d, (d, y, m, day)
chk(1, 1992, 1, 1); chk(59, 2000, 2, 28); chk(60, 2000, 2, 29); chk(61, 1995, 3, 1); chk(366, 2002, 12, 31)
print("doy mapping OK; doy range:", doy_base.min(), doy_base.max())

cnt, vals = np.unique(doy_base, return_counts=True)
bad = [(int(v), int(c)) for v, c in zip(vals, cnt) if (v == 60 and c != 3) or (v != 60 and c != 11)]
print("doy count anomalies (60 should be 3 leap yrs):", bad)

offs = np.arange(-5, 6)[None, :]
J = np.arange(4018)[:, None]
idx_all = (J + 5 + offs).ravel()
doy_all = np.repeat(doy_base, 11)
assert idx_all.min() >= 0 and idx_all.max() < n_w
psizes = {int(v): int(np.sum(doy_all == v)) for v in vals}
print("pool sizes: d=1:", psizes[1], " d=59:", psizes[59], " d=61:", psizes[61], " d=366:", psizes[366], " d=60:", psizes.get(60,0))
i1 = np.sort(idx_all[doy_all == 1])
print("first 11 pool dates for d=1:", [str(win_dates[i]) for i in i1[:11]])
i59 = np.sort(idx_all[doy_all == 59])
print("d=59 pool year-1996 window dates:", [str(win_dates[i]) for i in i59 if win_dates[i].year == 1996])

t0 = time.time()
thr = np.full((366, N), np.nan)
clim = np.full((366, N), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        X = S_base[idx_all[doy_all == d]].astype(np.float64).reshape(-1, N)  # (121, 3600)
        thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
        clim[d-1] = np.nanmean(X, axis=0)
print("pool loop:", round(time.time()-t0,1), "s")

thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0
print("cells with any NaN thr:", int(np.isnan(thr).any(axis=0).sum()), "of", N)
per_doy_nan = np.isnan(thr).sum(axis=1)
print("doy with NaN cells:", [(i+1, int(v)) for i, v in enumerate(per_doy_nan) if v > 0][:10])
np.save('work/thr_raw.npy', thr)
np.save('work/clim_raw.npy', clim)
print("sample thr cell(0,0) doy 152/182/213 (K):", thr[151,0], thr[181,0], thr[212,0])
print("sample clim cell(0,0) (K):", clim[151,0], clim[181,0], clim[212,0])
# min/max of thr over sea-ish cells in summer
print("thr summer range over all cells: min", np.nanmin(thr[150:245]), "max", np.nanmax(thr[150:245]))
