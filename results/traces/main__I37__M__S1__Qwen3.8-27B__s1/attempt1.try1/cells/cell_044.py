import datetime as dt
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

# explicit pool for doy 183 (1 Jul): baseline dates 1992-07-01..2002-07-01, each +-5 days
i, j = 30, 30
pool_vals, pool_dates = [], []
for y in range(1992, 2003):
    b = dt.date(y, 7, 1)
    for k in range(-5, 6):
        d = b + dt.timedelta(days=k)
        idx = ext_dates.index(d)
        pool_vals.append(ext[idx, i, j])
        pool_dates.append(d)
pv = np.array(pool_vals)
pvf = pv[np.isfinite(pv)]
print("explicit pool n=%d finite=%d hazen90=%.4f mean=%.4f" % (pv.size, pvf.size,
      np.quantile(pvf, 0.9, method='hazen'), pvf.mean()))
# compare with vectorized rows
doy_b = doy_ext[5:5+4018]
js = np.where(doy_b == 183)[0]
rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
pool2 = ext[rows, i, j]
print("vectorized==explicit:", np.array_equal(np.sort(pvf), np.sort(pool2[np.isfinite(pool2)])))

# trajectory at (30,30)
print("\ndoy   rawThr  smThr  smClim")
for d in range(150, 251, 5):
    print(d, f"{thr_raw_v:}").replace("x","") if False else None
# recompute raw thr quickly for display (only needed doys)
thr_raw = {}
for d in list(range(150, 251, 5)):
    if d == 60: continue
    js = np.where(doy_b == d)[0]
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    thr_raw[d] = np.nanquantile(ext[rows, i, j], 0.9, method='hazen')
for d in range(150, 251, 5):
    print(d, round(thr_raw[d], 2), round(thr[d-1, i, j], 2), round(clim[d-1, i, j], 2))

# target daily SST (30,30) June-Aug
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in tgt_dates])
print("\ntarget SST (30,30) vs smoothed thr:")
s = ""
for t in range(92):
    v = tgt[t, i, j]; th = thr[doy_tgt[t]-1, i, j]
    s += f"{v:.1f}/{th:.1f} "
    if (t+1) % 10 == 0:
        print(" ", s); s = ""
if s: print(" ", s)
