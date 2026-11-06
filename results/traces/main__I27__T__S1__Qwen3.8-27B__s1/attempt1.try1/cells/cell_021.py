
import numpy as np, datetime as dt, time, warnings

B = np.concatenate([np.load(f'/tmp/mhw/baseline_part{i}.npy') for i in range(9)], axis=0)
A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
bdates = [dt.date(1991,12,27) + dt.timedelta(days=i) for i in range(B.shape[0])]
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(A.shape[0])]
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(ds):
    return (cum[np.array([d.month for d in ds])-1] + np.array([d.day for d in ds])).astype(np.int64)
bdoy = doy_of(bdates)
sea = np.all(np.isfinite(A), axis=0)

# ---- per-cell thresholds/climatology ----
n_days, ny, nx = B.shape
NC = ny*nx
B2 = B.reshape(n_days, NC)  # (4028, 3600)

# for each doy d (1..366, d!=60): window index blocks
doy_to_base_indices = {}
for d in range(1, 367):
    if d == 60: continue
    idxs = np.where(bdoy == d)[0]
    idxs = idxs[(idxs >= 5) & (idxs <= 4022)]   # only baseline 1992..2002 dates
    if len(idxs) == 0:
        doy_to_base_indices[d] = None
        continue
    blocks = np.concatenate([np.arange(i-5, i+6) for i in idxs])
    doy_to_base_indices[d] = blocks

# sanity: pool sizes
sizes = {d: (v.size if v is not None else 0) for d,v in doy_to_base_indices.items()}
import collections
print("pool size distribution:", collections.Counter(sizes.values()))
# check bounds
for d in (1, 60, 61, 366):
    v = doy_to_base_indices.get(d)
    if v is not None:
        print(d, "n=", v.size, "first dates:", bdates[v[0]], bdates[v[-1]], "min idx", v.min(), "max idx", v.max())
    else:
        print(d, "no pool")

t0=time.time()
thr_raw = np.full((366, NC), np.nan)
clim_raw = np.full((366, NC), np.nan)
all_nan_d = []
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        v = doy_to_base_indices[d]
        pool = B2[v]  # (121, 3600)
        thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(pool, axis=0)
        all_nan_d.append((d, int(np.isfinite(thr_raw[d-1]).sum()==0)))
print("pool+percentile done in", time.time()-t0, "s")
# how many cells have NaN threshold anywhere in Jun-Aug doys (153..243)?
n_nan_summer = np.isfinite(thr_raw[152:243]).all(axis=0)
print("cells with all-finite thresholds for doy 153..243:", n_nan_summer.sum(), "of", NC)
print("cells with NaN threshold in summer range:", (~n_nan_summer).sum())
# also global
bad = ~np.isfinite(thr_raw).all(axis=0)
print("cells with any NaN threshold over 1..365 (excl 60):", bad.sum())
np.save('/tmp/mhw/thr_raw.npy', thr_raw); np.save('/tmp/mhw/clim_raw.npy', clim_raw)
