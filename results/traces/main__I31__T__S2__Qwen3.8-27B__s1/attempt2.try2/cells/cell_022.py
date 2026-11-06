import numpy as np
from datetime import date, timedelta
z = np.load('/work/stats.npz', allow_pickle=False)
thr, clim = z['thr'], z['clim']
t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
tgt = zz['tgt'].astype(np.float64)
base = zz['base']
b_dates = zz['b_dates']

# 2017-06-01 SST distribution across region
print("2017-06-01 SST: min %.2f max %.2f median %.2f (K)" % (np.nanmin(tgt[0]), np.nanmax(tgt[0]), np.nanmedian(tgt[0])))
print("2017-08-31 SST: min %.2f max %.2f median %.2f (K)" % (np.nanmin(tgt[91]), np.nanmax(tgt[91]), np.nanmedian(tgt[91])))
# whole target period per-cell median
print("target median per cell: min %.2f max %.2f" % (np.nanmin(np.nanmedian(tgt, axis=0)), np.nanmax(np.nanmedian(tgt, axis=0))))

# cell (30,30)
c = 30*60 + 30
print("\ncell (30,30):")
print(" target series (K):", np.round(tgt[:, 30, 30], 1))
print(" smoothed thr for target doys:", np.round(thr[c, 151:243:10], 2))
print(" smoothed clim for target doys:", np.round(clim[c, 151:243:10], 2))

# pool for doy 152 (2017-06-01 is doy 152) at cell (30,30): rebuild pool
doy_to_md = {}
for d in range(1, 367):
    dt = date(2000,1,1) + timedelta(days=d-1)
    doy_to_md[d] = (dt.month, dt.day)
d = 152
m, dd = doy_to_md[d]
b_dates_set = {np.datetime64(b_dates[k], 'D'): k for k in range(len(b_dates))}
wset = set()
for y in range(1992, 2003):
    b = date(y, m, dd)
    for k in range(-5, 6):
        ki = b_dates_set.get(np.datetime64(b + timedelta(days=k), 'D'))
        if ki is not None: wset.add(ki)
mask = np.zeros(len(b_dates), bool); mask[np.fromiter(wset, dtype=np.int64)] = True
vals = base[mask, 30, 30]
fv = vals[~np.isnan(vals)]
print("\npool doy152 cell(30,30): n dates", len(vals), "n finite", len(fv))
print(" pool values:", np.round(fv, 1))
print(" pool min/max:", fv.min(), fv.max())
print(" hazen90:", np.quantile(fv, 0.9, method='hazen'), " mean:", fv.mean())
print(" stored smoothed thr[151] %.3f clim[151] %.3f (smoothed across doys!)" % (thr[c,151], clim[c,151]))
# raw (unsmoothed) values around doy 152
zr = None
print(" raw thr[140:165] (smoothed array):", np.round(thr[c, 140:165], 1))
