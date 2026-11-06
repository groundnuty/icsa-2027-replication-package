import xarray as xr, numpy as np, datetime as dt, os, pickle
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
li = np.arange(48, 108); lo = np.arange(353, 413)
t = ds.indexes['time']; tdates = np.array(t.date)

def tidx(d): return int(np.searchsorted(tdates, np.datetime64(d)))

b0, b1 = tidx('1991-12-27'), tidx('2003-01-05')
t0, t1 = tidx('2021-06-01'), tidx('2021-08-31')
base = ds['analysed_sst'].isel(time=slice(b0,b1+1), latitude=li, longitude=lo).values.astype(np.float64)
tgt  = ds['analysed_sst'].isel(time=slice(t0,t1+1),  latitude=li, longitude=lo).values.astype(np.float64)
base_dates = tdates[b0:b1+1]
tgt_dates  = tdates[t0:t1+1]

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335], dtype=np.int64)
def doy_leap(a):
    s = pd.Series(a.astype('datetime64[ns]'))
    return (CUM[s.dt.month - 1].to_numpy() + s.dt.day.to_numpy()).astype(np.int64).to_numpy()

base_doy = doy_leap(base_dates); tgt_doy = doy_leap(tgt_dates)
print('tgt doy range', tgt_doy.min(), tgt_doy.max())
# sanity checks of the mapping
for d, exp in [('1992-02-29',60), ('1992-03-01',61), ('2001-12-31',366), ('2021-08-31',243), ('1992-01-01',1), ('2002-02-28',59)]:
    got = doy_leap(np.array([np.datetime64(d)]))
    print(d, got[0], 'expect', exp, 'OK' if got[0]==exp else 'MISMATCH')

bl_mask = (base_dates >= np.datetime64('1992-01-01')) & (base_dates <= np.datetime64('2002-12-31'))
bl_idx = np.where(bl_mask)[0]
bl_doy = base_doy[bl_idx]
print('n baseline dates', len(bl_idx), 'min/max local', bl_idx.min(), bl_idx.max())

pools = {}
for d in range(1, 367):
    if d == 60: continue
    ibs = bl_idx[bl_doy == d]
    assert len(ibs) == 11, (d, len(ibs))
    idx = np.concatenate([np.arange(ib-5, ib+6) for ib in ibs])
    assert idx.min() >= 0 and idx.max() < len(base_dates)
    assert len(np.unique(idx)) == len(idx)  # disjoint windows
    pools[d] = idx
print('pool sizes:', set(len(v) for v in pools.values()), 'days covered:', len(pools))

# Feb 29 participation check
i29 = int(np.searchsorted(base_dates, np.datetime64('1996-02-29')))
assert base_dates[i29] == np.datetime64('1996-02-29')
participating = [d for d, v in pools.items() if i29 in set(v)]
print('days whose pools include 1996-02-29:', participating)

sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)

N = 3600
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
for d, idx in pools.items():
    P2 = base[idx].reshape(len(idx), N)
    thr[d-1] = np.nanquantile(P2, 0.9, method='hazen', axis=0).reshape(60, 60)
    clim[d-1] = np.nanmean(P2, axis=0).reshape(60, 60)
print('thr nan (excl d60):', int(np.isnan(thr[1:60]).sum()) + int(np.isnan(thr[60:]).sum()),
      'clim nan:', int(np.isnan(clim[1:60]).sum()) + int(np.isnan(clim[60:]).sum()))

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

off = np.arange(-15, 16)
idx31 = (np.arange(366)[:, None] + off[None, :]) % 366
thr_s = np.take(thr, idx31, axis=0).mean(axis=1)
clim_s = np.take(clim, idx31, axis=0).mean(axis=1)
print('smooth done; thr_s finite in target doys:', bool(np.isfinite(thr_s[tgt_doy-1]).all()))

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
n_ec = np.zeros((60, 60), dtype=int)
for i in range(60):
    for j in range(60):
        if not sea[i, j]: continue
        hot = tgt[:, i, j] >= thr_s[tgt_doy - 1, i, j]
        mhw[:, i, j], n_ec[i, j] = cell_mhw_mask(hot)
print('per-cell MHWs total:', int(n_ec.sum()), 'cells with MHW:', int((n_ec > 0).sum()))

active = mhw.any(axis=(1, 2))
events = []
i = 0
while i < Tn:
    if active[i]:
        j = i
        while j + 1 < Tn and active[j+1]:
            j += 1
        events.append((str(tgt_dates[i]), str(tgt_dates[j])))
        i = j + 1
    else:
        i += 1
print('regional events:')
for e in events: print(e)
print('active days:', int(active.sum()), 'of', Tn)
print('per-day active count min/max:', active.sum(axis=1).min(), active.sum(axis=1).max())

with open('/work/state.pkl', 'wb') as f:
    pickle.dump({'mhw': mhw, 'tgt_dates': tgt_dates, 'sea': sea, 'events': events,
                 'thr_s': thr_s, 'clim_s': clim_s}, f)
print('saved')
