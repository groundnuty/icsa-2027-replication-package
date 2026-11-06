import numpy as np, warnings, time
from datetime import date, timedelta

t0 = time.time()
B = np.load('/work/data/B.npy')      # (4028, 60, 60) f64, 1991-12-27..2003-01-05
T = np.load('/work/data/T.npy')      # (92, 60, 60) f64, 2015-06-01..2015-08-31
tb = np.load('/work/data/tb.npy'); tt = np.load('/work/data/tt.npy')
lat = np.load('/work/data/lat_sel.npy'); lon = np.load('/work/data/lon_sel.npy')
print("loaded", time.time()-t0)

# --- day-of-year helpers (leap-based, 1..366) ---
MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = np.cumsum([0]+MDAYS)
def doy_of(y, m, d):
    return int(CUM[m-1]) + d
def md_of(doy):
    m = int(np.searchsorted(CUM, doy, side='right'))  # CUM[m-1] < doy <= CUM[m]
    # CUM is [0,31,60,91,121,152,182,213,244,274,305,335,366]
    return m+1, doy - CUM[m]
assert doy_of(1992,2,28)==59 and doy_of(1992,2,29)==60 and doy_of(1992,3,1)==61 and doy_of(1992,12,31)==366 and md_of(60)==(2,29)

# --- sea cells ---
sea = np.isfinite(T).all(axis=0)          # (60,60)
nsea = int(sea.sum())
print("sea cells:", nsea, "of", sea.size)
sea_idx = np.flatnonzero(sea.ravel())
Bsea = B[:, sea.ravel().nonzero()[0], sea.ravel().nonzero()[1]]  # (4028, nsea)
Tsea = T[:, sea.ravel().nonzero()[0], sea.ravel().nonzero()[1]]  # (92, nsea)
print("Bsea", Bsea.shape, "Tsea", Tsea.shape)

# sanity: per-cell finite fraction over target for sea cells
print("min target finite frac among sea cells:", np.isfinite(Tsea).all(axis=0).all())

# --- pools & stats per day of year (except 60) ---
d0 = date(1991,12,27)
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
pool_sizes = {}
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        m, dd = md_of(d)
        lo = date(1992, m, dd) - timedelta(days=5)
        hi = date(2002, m, dd) + timedelta(days=5)
        lo_i = (lo - d0).days
        hi_i = (hi - d0).days
        assert 0 <= lo_i < hi_i <= 4027
        pool = Bsea[lo_i:hi_i+1]
        pool_sizes[d] = pool.shape[0]
        # 90th percentile, hazen (type 5), ignoring NaN; then mean ignoring NaN
        thr[d-1] = np.quantile(pool, 0.9, method='hazen', nan_policy='omit', axis=0)
        clim[d-1] = np.nanmean(pool, axis=0)
print("pools done", time.time()-t0)
print("pool size range:", min(pool_sizes.values()), max(pool_sizes.values()))
# check NaN presence in results for days != 60
nanmask = np.isnan(thr)
nanmask[59, :] = False
print("cells with any NaN threshold (d!=60):", int(np.isnan(thr).sum()))
print("cells with any NaN climatology (d!=60):", int(np.isnan(clim).sum()))
np.save('/work/data/thr_raw.npy', thr)
np.save('/work/data/clim_raw.npy', clim)
np.save('/work/data/sea_idx.npy', sea_idx)