import numpy as np, pandas as pd, json, os

z = np.load("work/data.npz")
base = z["base"].astype(np.float64)           # (4028, 60, 60)
targ = z["targ"].astype(np.float64)           # (92, 60, 60)
base_dates = pd.DatetimeIndex(z["base_dates"].astype(str))
targ_dates = pd.DatetimeIndex(z["targ_dates"].astype(str))
print("base", base.shape, base_dates[0].date(), "->", base_dates[-1].date())
print("targ", targ.shape, targ_dates[0].date(), "->", targ_dates[-1].date())

# ---- day-of-year 1..366 with Feb29 = 60 (month/day based) ----
def doy366(ts):
    m, d = ts.month, ts.day
    k = pd.Timestamp(2001, m, d).dayofyear  # 2001 non-leap: Jan1=1..Dec31=365
    if m == 1 or (m == 2 and d <= 28):
        return k            # 1..59
    if m == 2 and d == 29:
        return 60
    return k + 1            # Mar1=61 .. Dec31=366
# verify mapping
assert doy366(pd.Timestamp(2001,2,28)) == 59 and doy366(pd.Timestamp(2000,2,29)) == 60
assert doy366(pd.Timestamp(2000,3,1)) == 61 and doy366(pd.Timestamp(2001,12,31)) == 366
assert doy366(pd.Timestamp(2000,12,31)) == 366 and doy366(pd.Timestamp(1999,3,1)) == 61

base_doy = np.array([doy366(t) for t in base_dates])
targ_doy = np.array([doy366(t) for t in targ_dates])
print("target doy range:", targ_doy.min(), targ_doy.max())
print("base block doy range:", base_doy.min(), base_doy.max())

# ---- pools per day-of-year: union of +/-5 calendar-day windows around baseline-period anchors ----
bl = pd.date_range("1992-01-01", "2002-12-31", freq="D")
in_block = np.ones(len(base_dates), dtype=bool)  # every pool candidate date must be a read date
pool_idx = {}   # doy -> np.array of positions into base
for d in range(1, 367):
    if d == 60:
        continue
    anchors = bl[[doy366(t) == d for t in bl]]
    assert len(anchors) in (1, 11), (d, len(anchors))
    mask = np.zeros(len(base_dates), dtype=bool)
    for a in anchors:
        w0, w1 = a - pd.Timedelta(days=5), a + pd.Timedelta(days=5)
        mask |= (base_dates >= w0) & (base_dates <= w1)
    idx = np.where(mask)[0]
    assert len(idx) > 0, d
    pool_idx[d] = idx
sizes = np.array([len(pool_idx[d]) for d in range(1, 367) if d != 60])
print("pool sizes: min", sizes.min(), "max", sizes.max(), "| d=1:", len(pool_idx[1]), "d=59:", len(pool_idx[59]),
      "d=61:", len(pool_idx[61]), "d=365:", len(pool_idx[365]), "d=366:", len(pool_idx[366]))
# pool date coverage of read block
used = np.zeros(len(base_dates), bool)
for d, idx in pool_idx.items(): used[idx] = True
print("pool dates used:", used.sum(), "of", len(base_dates), "| first", base_dates[np.where(used)[0][0]].date(),
      "last", base_dates[np.where(used)[0][-1]].date())

# ---- raw threshold (hazen quantile 0.9) and climatology (mean) per cell ----
nth, nlat, nlon = 366, 60, 60
thr = np.full((nth, nlat, nlon), np.nan)
clm = np.full((nth, nlat, nlon), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = base[pool_idx[d]]                       # (n_pool, 60, 60)
    thr[d-1] = np.quantile(vals, 0.90, axis=0, method="hazen")
    clm[d-1] = vals.mean(axis=0)
# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clm[59] = 0.5*(clm[58] + clm[60])
print("raw thr/clm filled for all 366 doys:", np.isfinite(thr).all(), np.isfinite(clm).all())

# ---- circular 31-day (±15) moving mean over 366 days ----
def circ_movmean(a):   # a: (366, nlat, nlon)
    out = np.empty_like(a)
    w = np.arange(-15, 16)
    idx = (np.arange(366)[:, None] + w[None, :]) % 366     # (366, 31) doy indices
    out = a[idx].mean(axis=1)                              # mean over window
    return out
thr_s = circ_movmean(thr)
clm_s = circ_movmean(clm)
print("smoothed thr range:", np.nanmin(thr_s), np.nanmax(thr_s))
print("smoothed clm range:", np.nanmin(clm_s), np.nanmax(clm_s))
# spot check a mid-summer value for a central cell
c = (30, 30)
print("sample cell (30,30): raw thr d=196:", thr[195][c], "smoothed:", thr_s[195][c], "| raw clm d=196:", clm[195][c], "smoothed:", clm_s[195][c])
np.savez_compressed("work/clim.npz", thr_s=thr_s, clm_s=clm_s)
print("saved clim.npz")
