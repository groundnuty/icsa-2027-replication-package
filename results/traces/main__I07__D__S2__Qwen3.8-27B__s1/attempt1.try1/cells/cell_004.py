import xarray as xr, numpy as np, datetime as dt, os, pickle

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
li = np.arange(48, 108); lo = np.arange(353, 413)
t = ds.indexes['time']; tdates = np.array(t.date)

def tidx(d): return int(np.searchsorted(tdates, np.datetime64(d)))

# Load base window 1991-12-27..2003-01-05 and target 2021-06-01..2021-08-31 as float64
b0, b1 = tidx('1991-12-27'), tidx('2003-01-05')
t0, t1 = tidx('2021-06-01'), tidx('2021-08-31')
base = ds['analysed_sst'].isel(time=slice(b0,b1+1), latitude=li, longitude=lo).values.astype(np.float64)
tgt  = ds['analysed_sst'].isel(time=slice(t0,t1+1),  latitude=li, longitude=lo).values.astype(np.float64)
base_dates = tdates[b0:b1+1]
tgt_dates  = tdates[t0:t1+1]
print('base shape', base.shape, 'dates', base_dates[0], base_dates[-1], 'T', len(base_dates))
print('tgt shape', tgt.shape, 'dates', tgt_dates[0], tgt_dates[-1])

# day of year by month/day (leap-year convention; 60 = 29 Feb)
def doy(a):  # a: datetime64 array
    m = a.astype('datetime64[M]').astype(int)*12
    d = (a.astype('datetime64[D]').astype(int) - a.astype('datetime64[M]').astype(int)*0) # placeholder
    # simpler: use pandas
    import pandas as pd
    s = pd.Series(a.astype('datetime64[ns]'))
    return (s.dt.dayofyear).values  # pandas dayofyear is exactly month/day based, leap convention
base_doy = doy(base_dates); tgt_doy = doy(tgt_dates)
print('tgt doy range', tgt_doy.min(), tgt_doy.max(), 'first/last', tgt_doy[0], tgt_doy[-1])
print('base doy has 60:', np.isin(60, base_doy).any())

# baseline dates (1992-01-01..2002-12-31) local indices
bl_mask = (base_dates >= np.datetime64('1992-01-01')) & (base_dates <= np.datetime64('2002-12-31'))
bl_idx = np.where(bl_mask)[0]
bl_doy = base_doy[bl_idx]
print('n baseline dates', len(bl_idx), bl_idx.min(), bl_idx.max())

# pool date-local-indices per day d (1..366, skip 60)
pools = {}
for d in range(1, 367):
    if d == 60: continue
    ibs = bl_idx[bl_doy == d]
    assert len(ibs) == 11, (d, len(ibs))
    idx = np.concatenate([np.arange(ib-5, ib+6) for ib in ibs])
    assert idx.min() >= 0 and idx.max() < len(base_dates)
    pools[d] = idx
sizes = {d: len(v) for d, v in pools.items()}
print('pool size set:', set(sizes.values()))

# check Feb 29 participation: 1996-02-29 local index
i29 = int(np.searchsorted(base_dates, np.datetime64('1996-02-29')))
print('1996-02-29 local idx', i29, base_dates[i29])
participating = [d for d, v in pools.items() if i29 in set(v)]
print('days whose pools include 1996-02-29:', participating)

# sea cells: finite on every target day
sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)

# per-day threshold (hazen 90th pct, NaN ignored) and climatology (mean, NaN ignored)
N = sea.size
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
for d, idx in pools.items():
    P = base[idx]  # (121, 60, 60)
    P2 = P.reshape(121, N)
    thr[d-1] = np.nanquantile(P2, 0.9, method='hazen', axis=0).reshape(60, 60)
    clim[d-1] = np.nanmean(P2, axis=0).reshape(60, 60)
print('thr nan count (excl d60):', np.isnan(thr[1:60]).sum(), np.isnan(thr[60:]).sum())
print('clim nan count:', np.isnan(clim[1:60]).sum(), np.isnan(clim[60:]).sum())

# day 60 = mean of 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

# 31-day wrap-around centred moving mean
off = np.arange(-15, 16)
idx31 = (np.arange(366)[:, None] + off[None, :]) % 366
thr_s = np.take(thr, idx31, axis=0).mean(axis=1)
clim_s = np.take(clim, idx31, axis=0).mean(axis=1)
print('smoothed ok, thr_s[151] finite:', np.isfinite(thr_s[151]).all())

# per-cell MHW detection
def cell_mhw_mask(hot):
    T = len(hot)
    runs = []
    i = 0
    while i < T:
        if hot[i]:
            j = i
            while j + 1 < T and hot[j+1]:
                j += 1
            runs.append([i, j])
            i = j + 1
        else:
            i += 1
    runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = np.zeros(T, dtype=bool)
    for a, b in merged:
        out[a:b+1] = True
    return out, len(merged)

Tn = tgt.shape[0]
mhw = np.zeros((Tn, 60, 60), dtype=bool)
n_events_per_cell = np.zeros(sea.shape, dtype=int)
n_runs_kept = 0
for i in range(60):
    for j in range(60):
        if not sea[i, j]: continue
        sst = tgt[:, i, j]
        th = thr_s[tgt_doy - 1, i, j]
        hot = np.isfinite(sst) & np.isfinite(th) & (sst >= th)
        mask, k = cell_mhw_mask(hot)
        mhw[:, i, j] = mask
        n_events_per_cell[i, j] = k
print('total per-cell MHWs (after merging):', n_events_per_cell.sum())
print('cells with >=1 MHW:', (n_events_per_cell > 0).sum())

# regional events
active = mhw.any(axis=(1, 2))
events = []
i = 0
while i < Tn:
    if active[i]:
        j = i
        while j + 1 < Tn and active[j+1]:
            j += 1
        events.append((tgt_dates[i], tgt_dates[j]))
        i = j + 1
    else:
        i += 1
print('regional events:')
for e in events:
    print(e)
print('active days total:', int(active.sum()))

# persist for the writing step
with open('/work/state.pkl', 'wb') as f:
    pickle.dump({'mhw': mhw, 'tgt_dates': tgt_dates, 'sea': sea, 'events': events,
                 'li': li, 'lo': lo, 'base_dates': base_dates, 'tgt_doy': tgt_doy}, f)
print('saved state')
