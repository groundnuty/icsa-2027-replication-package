import time, datetime as dt, json
import numpy as np

ext = np.load('/work/chk/ext.npy').astype(np.float64)
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr = np.load('/work/chk/thr.npy')
clim = np.load('/work/chk/clim.npy')

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_b = doy_ext[5:5+4018]

i, j = 30, 30
print("cell (30,30) sea:", sea[i,j])
# target July SST
july = tgt[30:61, i, j]   # Jul 1..31 (doy 183..213)
print("target July SST: min %.2f max %.2f mean %.2f" % (np.nanmin(july), np.nanmax(july), np.nanmean(july)))
# pool for doy 183
d = 183
js = np.where(doy_b == d)[0]
rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
pool = ext[rows, i, j]
pv = pool[np.isfinite(pool)]
print("pool doy183: n=%d min %.2f max %.2f mean %.2f" % (pv.size, pv.min(), pv.max(), pv.mean()))
print("threshold raw doy183 (from thr? recompute):", np.nanquantile(pool, 0.9, method='hazen'))
print("clim doy183:", pv.mean())
print("smoothed thr around doy 183:", thr[180:187, i, j])
# count hot days in target for this cell
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in daterange(dt.date(2012,6,1), dt.date(2012,8,31))])
excess = np.array([tgt[t, i, j] - thr[doy_tgt[t]-1, i, j] for t in range(92)])
print("max excess:", excess.max(), " days with excess>0:", (excess > 0).sum())
print("excess[:10]:", np.round(excess[:10], 2))

# global stats
excess_all = tgt - thr[np.ix_(doy_tgt - 1, np.arange(60), np.arange(60))] if False else None
# build properly
thr_t = thr[doy_tgt - 1]  # (92, 60, 60)
ex_all = tgt - thr_t
mask = sea[None] & np.isfinite(tgt)
print("max excess over region: %.3f" % np.nanmax(ex_all[mask]))
print("fraction cell-days with excess>0: %.4f" % (ex_all[mask] > 0).mean())
print("fraction cell-days with excess>0.5: %.4f" % (ex_all[mask] > 0.5).mean())
print("fraction cell-days with excess>1: %.4f" % (ex_all[mask] > 1.0).mean())
