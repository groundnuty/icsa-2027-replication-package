import numpy as np, datetime, time, warnings

t0 = time.time()
ext = np.load('/work/ext.npy')          # (4028, 3600)
ncells = ext.shape[1]
ext_dates = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    ext_dates.append(d); d += datetime.timedelta(days=1)
d2i = {dt: i for i, dt in enumerate(ext_dates)}

# canonical calendar date for day-of-year d (1..366), mapping by month/day (d=60 -> Feb 29)
canon = {}
for dnum in range(1, 367):
    if dnum <= 59:
        dt = datetime.date(2001,1,1) + datetime.timedelta(days=dnum-1)   # non-leap reference
    elif dnum == 60:
        dt = datetime.date(2004,2,29)
    else:
        dt = datetime.date(2001,3,1) + datetime.timedelta(days=dnum-61)
    canon[dnum] = (dt.month, dt.day)
assert canon[59] == (2,28) and canon[61] == (3,1) and canon[366] == (12,31) and canon[60] == (2,29)
assert canon[1] == (1,1)

thr_raw = np.full((366, ncells), np.nan)
clim_raw = np.full((366, ncells), np.nan)

years = list(range(1992, 2003))
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    for dnum in range(1, 367):
        if dnum == 60:
            continue
        m, dd = canon[dnum]
        idxs = []
        for y in years:
            b = datetime.date(y, m, dd)
            i0 = d2i[b]
            idxs.extend(range(i0-5, i0+6))
        idxs = np.asarray(idxs)
        assert idxs.min() >= 0 and idxs.max() < len(ext_dates)
        pool = ext[idxs]                     # (121, 3600)
        thr_raw[dnum-1] = np.nanquantile(pool, 0.9, axis=0, method="hazen")
        clim_raw[dnum-1] = np.nanmean(pool, axis=0)

# fill day 60
thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])
print("raw computed", time.time()-t0)

# wrap-around centred 31-day moving mean on 366 arrays
def smooth31(arr):
    out = np.zeros_like(arr)
    for k in range(-15, 16):
        out += np.roll(arr, k, axis=0)
    return out / 31.0

thr = smooth31(thr_raw)
clim = smooth31(clim_raw)

np.save('/work/thr.npy', thr)
np.save('/work/clim.npy', clim)

# diagnostics
fin_cells = np.load('/work/sea_mask.npy')
print("thr finite on sea cells:", np.isfinite(thr[:, fin_cells]).all(), " clim finite:", np.isfinite(clim[:, fin_cells]).all())
sub_t = thr[151:244, fin_cells]   # June-Aug (doy 152..243)
print("summer thr K range:", sub_t.min(), sub_t.max(), "mean:", sub_t.mean())
print("summer clim K range:", clim[151:244, fin_cells].min(), clim[151:244, fin_cells].max())
print("sample thr 2016-06-15 (doy 166) sea cells min/max:", thr[165][fin_cells].min(), thr[165][fin_cells].max())
print("sample clim doy 166:", clim[165][fin_cells].min(), clim[165][fin_cells].max())
