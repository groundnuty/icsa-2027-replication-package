import numpy as np, pandas as pd, json, os, pickle

z = np.load("work/data.npz")
base = z["base"].astype(np.float64)
targ = z["targ"].astype(np.float64)
base_dates = pd.DatetimeIndex(z["base_dates"].astype(str))
targ_dates = pd.DatetimeIndex(z["targ_dates"].astype(str))

def doy366(ts):
    m, d = ts.month, ts.day
    if m == 2 and d == 29:
        return 60
    k = pd.Timestamp(2001, m, d).day_of_year
    if m <= 2:
        return k
    return k + 1
assert doy366(pd.Timestamp(2001,2,28)) == 59
assert doy366(pd.Timestamp(2000,2,29)) == 60
assert doy366(pd.Timestamp(2000,3,1)) == 61
assert doy366(pd.Timestamp(2001,12,31)) == 366
assert doy366(pd.Timestamp(2000,12,31)) == 366
assert doy366(pd.Timestamp(1999,3,1)) == 61
assert doy366(pd.Timestamp(1992,1,1)) == 1
assert doy366(pd.Timestamp(1996,2,28)) == 59
assert doy366(pd.Timestamp(2003,1,5)) == 5
assert doy366(pd.Timestamp(1991,12,27)) == 362
print("doy mapping OK")

base_doy = np.array([doy366(t) for t in base_dates])
targ_doy = np.array([doy366(t) for t in targ_dates])
print("target doy range:", targ_doy.min(), "-", targ_doy.max())

# ---- pools: union of +/-5 CALENDAR-day windows around baseline anchors, per doy ----
bl = pd.date_range("1992-01-01", "2002-12-31", freq="D")
bl_doy = np.array([doy366(t) for t in bl])
pool_idx = {}
for d in range(1, 367):
    if d == 60:
        continue
    anchors = bl[bl_doy == d]
    assert len(anchors) == 11, (d, len(anchors))
    mask = np.zeros(len(base_dates), dtype=bool)
    for a in anchors:
        mask |= (base_dates >= a - pd.Timedelta(days=5)) & (base_dates <= a + pd.Timedelta(days=5))
    idx = np.where(mask)[0]
    assert len(idx) > 0, d
    pool_idx[d] = idx
sizes = np.array([len(pool_idx[d]) for d in range(1, 367) if d != 60])
print("pool sizes: min", sizes.min(), "max", sizes.max())
for probe in (1, 15, 28, 32, 55, 59, 61, 120, 196, 240, 275, 306, 334, 365, 366):
    pd_dates = base_dates[pool_idx[probe]]
    print("  d=%3d pool size %3d  from %s to %s" % (probe, len(pool_idx[probe]),
          pd_dates.min().date(), pd_dates.max().date()))
used = np.zeros(len(base_dates), bool)
for d, idx in pool_idx.items(): used[idx] = True
w = np.where(used)[0]
print("pool dates used:", used.sum(), "of", len(base_dates), "| first", base_dates[w[0]].date(), "last", base_dates[w[-1]].date())
with open("work/pool_idx.pkl", "wb") as fh: pickle.dump(pool_idx, fh)

nth, nlat, nlon = 366, 60, 60
thr = np.full((nth, nlat, nlon), np.nan)
clm = np.full((nth, nlat, nlon), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = base[pool_idx[d]]
    thr[d-1] = np.quantile(vals, 0.90, axis=0, method="hazen")
    clm[d-1] = vals.mean(axis=0)
thr[59] = 0.5*(thr[58] + thr[60])
clm[59] = 0.5*(clm[58] + clm[60])
print("raw thr/clm finite everywhere:", np.isfinite(thr).all(), np.isfinite(clm).all())
print("thr sample [0,30,30]:", thr[0,30,30], " [195,30,30]:", thr[195,30,30], " [365,30,30]:", thr[365,30,30])
print("clm sample [195,30,30]:", clm[195,30,30])

w = np.arange(-15, 16)
idxm = (np.arange(366)[:, None] + w[None, :]) % 366
thr_s = thr[idxm].mean(axis=1)
clm_s = clm[idxm].mean(axis=1)
print("smoothed thr range:", thr_s.min(), thr_s.max())
print("smoothed clm range:", clm_s.min(), clm_s.max())
print("sample cell (30,30) d=196: raw thr", round(thr[195,30,30],4), "smoothed", round(thr_s[195,30,30],4),
      "| raw clm", round(clm[195,30,30],4), "smoothed", round(clm_s[195,30,30],4))
np.savez_compressed("work/clim.npz", thr_s=thr_s, clm_s=clm_s, targ_doy=targ_doy)
print("saved clim.npz")
