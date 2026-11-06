import datetime as dt
import numpy as np

ext = np.load('/work/chk/ext.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr = np.load('/work/chk/thr.npy')

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])

i, j = 30, 30
print("year: mean SST (1 Jul-31 Aug), finite count")
for y in range(1992, 2003):
    dates = daterange(dt.date(y, 7, 1), dt.date(y, 8, 31))
    idxs = [ext_dates.index(d) for d in dates]
    vals = ext[idxs, i, j]
    v = vals[np.isfinite(vals)]
    print(y, f"{v.mean():.2f}  n={v.size}")

print("\nsmoothed thr doy 183..245 step 10 at (30,30):")
for d in range(183, 246, 10):
    print(d, round(float(thr[d-1, i, j]), 2))

# per test year: mean excess over sea cells, and per-month finite fraction
for y0 in (1992, 1997, 2000, 2002):
    dates = daterange(dt.date(y0, 6, 1), dt.date(y0, 8, 31))
    idxs = [ext_dates.index(d) for d in dates]
    doys = np.array([doy_ext[k] for k in idxs])
    sst = ext[idxs]
    th = thr[doys - 1]
    valid = sea[None] & np.isfinite(sst)
    ex = sst - th
    print(f"year {y0}: finite frac {valid.mean():.3f}, mean excess {np.nanmean(np.where(valid, ex, np.nan)):+.3f}, "
          f"median excess {np.nanmedian(np.where(valid, ex, np.nan)):+.3f}, hot frac {(np.where(valid, ex, -1e9) >= 0).mean():.4f}")
