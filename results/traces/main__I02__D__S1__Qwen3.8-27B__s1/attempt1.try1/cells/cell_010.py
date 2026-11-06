import numpy as np, datetime as dt, time

t_start = time.time()
S_base = np.load('/work/S_base.npy')   # (4028, 60, 60)
S_tgt  = np.load('/work/S_tgt.npy')    # (92, 60, 60)
cr = np.load('/work/coords.npz')
lat, lon = cr['lat'], cr['lon']
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
tgt_dates  = [dt.date.fromisoformat(str(d)) for d in cr['target_dates'].astype('datetime64[D]').astype(object)]
nd, nlat, nlon = S_base.shape
NC = nlat*nlon
print("shapes ok", S_base.shape, S_tgt.shape, lat[0], lat[-1], lon[0], lon[-1])

# day-of-year mapping (1..366, Feb29=60)
def doy(d):
    cum = [0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]:
        cum.append(cum[-1]+L)
    return cum[d.month-1] + d.day
assert doy(dt.date(2000,2,28))==59 and doy(dt.date(2000,2,29))==60 and doy(dt.date(2000,3,1))==61
assert doy(dt.date(2001,3,1))==60 and doy(dt.date(2001,12,31))==366 and doy(dt.date(2001,1,1))==1

base_doy = np.array([doy(d) for d in base_dates])
tgt_doy  = np.array([doy(d) for d in tgt_dates])
print("base doy range", base_doy.min(), base_doy.max(), " tgt doy range", tgt_doy.min(), tgt_doy.max())

# 1. sea cells: finite on every target day
finite_tgt = np.isfinite(S_tgt)
sea = finite_tgt.all(axis=0) & np.isfinite(S_tgt).all(axis=0)
sea_cells = np.where(finite_tgt.all(axis=0))[0]
print("sea cells:", sea_cells.size, "of", NC)

# 2. pools: for each d != 60, union over baseline dates b (1992..2002) with doy(d) of [b-5, b+5]
# build date->index map for base_dates
date_to_idx = {d: i for i, d in enumerate(base_dates)}
baseline_span = [dt.date(1992,1,1), dt.date(2002,12,31)]
# candidate b dates: all dates in 1992..2002 (present in base_dates)
b_idx_by_doy = {}
for i, d in enumerate(base_dates):
    if baseline_span[0] <= d <= baseline_span[1]:
        b_idx_by_doy.setdefault(base_doy[i], []).append(i)
for d in list(b_idx_by_doy):
    assert len(b_idx_by_doy[d]) == 11, (d, len(b_idx_by_doy[d]))
print("doy groups: 365 groups (60 has 3):", 60 in b_idx_by_doy, len(b_idx_by_doy.get(60,[])))

pool_mask = np.zeros((366, nd), dtype=bool)
pool_sizes = []
for d in range(1, 367):
    if d == 60:
        continue
    for bi in b_idx_by_doy[d]:
        b = base_dates[bi]
        for k in range(-5, 6):
            j = date_to_idx.get(b + dt.timedelta(days=k))
            assert j is not None, (d, b, k)
            pool_mask[d, j] = True
    pool_sizes.append(pool_mask[d].sum())
ps = np.array(pool_sizes)
print("pool size min/max:", ps.min(), ps.max(), "(expect 121 for most)")

# per-cell threshold (hazen quantile) and climatology (nanmean), pool by pool
thr = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    m = pool_mask[d]
    X = S_base[m].reshape(-1, NC)  # (n, NC)
    thr[d] = np.nanquantile(X, 0.9, method='hazen', axis=0)
    clim[d] = np.nanmean(X, axis=0)
print("pools done", time.time()-t_start)

# day 60 = mean of 59 and 61
thr[60] = 0.5*(thr[59]+thr[61])
clim[60] = 0.5*(clim[59]+clim[61])

# smooth: 366-array, centred 31-day moving mean with wrap
def smooth31(x):
    padded = np.tile(x, 3)[15:15+366]
    w = np.lib.stride_tricks.sliding_window_view(padded, 31)
    return w.mean(axis=1)
thr_s = smooth31(thr)
clim_s = smooth31(clim)
# sanity: smoothing of a constant
assert np.allclose(smooth31(np.arange(366, dtype=float) % 2 == 0), None if False else smooth31(np.zeros(366)))
print("smoothed ok; thr_s finite:", np.isfinite(thr_s).all())

np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)
np.save('/work/sea_cells.npy', sea_cells)
np.save('/work/tgt_doy.npy', tgt_doy)
print("ALL ANALYSIS CORE DONE", time.time()-t_start)
