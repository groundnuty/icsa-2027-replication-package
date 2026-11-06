import numpy as np, warnings, time
from datetime import date, timedelta

t0 = time.time()
B = np.load('/work/data/B.npy')
T = np.load('/work/data/T.npy')
tb = np.load('/work/data/tb.npy'); tt = np.load('/work/data/tt.npy')
lat = np.load('/work/data/lat_sel.npy'); lon = np.load('/work/data/lon_sel.npy')

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])  # ENDS[i] = end-of-doy of month i+1
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))   # 0-based month index
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)
for d in list(range(1,367)):
    m,dd = md_of(d); assert doy_of(m,dd)==d, (d,m,dd)
assert md_of(59)==(2,28) and md_of(60)==(2,29) and md_of(61)==(3,1) and md_of(366)==(12,31)
print("doy mapping OK (all 366)")

sea = np.isfinite(T).all(axis=0)
nsea = int(sea.sum())
print("sea cells:", nsea, "of", sea.size)
si = np.flatnonzero(sea.ravel())
Bsea = B[:, si//60, si%60]
Tsea = T[:, si//60, si%60]
print("Bsea", Bsea.shape, "Tsea", Tsea.shape)

d0 = date(1991,12,27)
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
pool_sizes = {}
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        m, dd = md_of(d)
        lo = date(1992, m, dd) - timedelta(days=5)
        hi = date(2002, m, dd) + timedelta(days=5)
        lo_i, hi_i = (lo - d0).days, (hi - d0).days
        assert 0 <= lo_i < hi_i <= 4027
        pool = Bsea[lo_i:hi_i+1]
        pool_sizes[d] = pool.shape[0]
        thr[d-1] = np.quantile(pool, 0.9, method='hazen', nan_policy='omit', axis=0)
        clim[d-1] = np.nanmean(pool, axis=0)
print("pools done", round(time.time()-t0,1), "s")
print("pool size min/max:", min(pool_sizes.values()), max(pool_sizes.values()))
print("NaN thr (d!=60):", int(np.isnan(thr[:59,:]).sum() + np.isnan(thr[60:,:]).sum()),
      " NaN clim (d!=60):", int(np.isnan(clim[:59,:]).sum() + np.isnan(clim[60:,:]).sum()))
np.save('/work/data/thr_raw.npy', thr)
np.save('/work/data/clim_raw.npy', clim)
np.save('/work/data/sea_idx.npy', si)
print("saved")