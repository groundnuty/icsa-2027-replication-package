import xarray as xr, numpy as np, pickle, json, os
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
li = np.arange(48, 108); lo = np.arange(353, 413)
t = ds.indexes['time']; tdates = np.array(t.date)
def tidx(d): return int(np.searchsorted(tdates, np.datetime64(d)))
b0, b1 = tidx('1991-12-27'), tidx('2003-01-05')
t0, t1 = tidx('2021-06-01'), tidx('2021-08-31')
base = ds['analysed_sst'].isel(time=slice(b0,b1+1), latitude=li, longitude=lo).values.astype(np.float64)
tgt  = ds['analysed_sst'].isel(time=slice(t0,t1+1),  latitude=li, longitude=lo).values.astype(np.float64)
base_dates = tdates[b0:b1+1]; tgt_dates = tdates[t0:t1+1]

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_leap(a):
    s = pd.Series(a.astype('datetime64[ns]'))
    return CUM[s.dt.month.to_numpy()-1] + s.dt.day.to_numpy()
base_doy = doy_leap(base_dates); tgt_doy = doy_leap(tgt_dates)

bl_mask = (base_dates >= np.datetime64('1992-01-01')) & (base_dates <= np.datetime64('2002-12-31'))
bl_idx = np.where(bl_mask)[0]; bl_doy = base_doy[bl_idx]
pools = {}
for d in range(1, 367):
    if d == 60: continue
    ibs = bl_idx[bl_doy == d]
    assert len(ibs) == 11
    pools[d] = np.concatenate([np.arange(ib-5, ib+6) for ib in ibs])

sea = np.isfinite(tgt).all(axis=0)
N = 3600
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    thr = np.full((366, 60, 60), np.nan); clim = np.full((366, 60, 60), np.nan)
    for d, idx in pools.items():
        P2 = base[idx].reshape(len(idx), N)
        thr[d-1] = np.nanquantile(P2, 0.9, method='hazen', axis=0).reshape(60,60)
        clim[d-1] = np.nanmean(P2, axis=0).reshape(60,60)
thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
idx31 = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
thr_s = np.take(thr, idx31, axis=0).mean(axis=1)

Tn = tgt.shape[0]
def cell_mhw_mask(hot):
    T = len(hot)
    runs = []; i = 0
    while i < T:
        if hot[i]:
            j = i
            while j + 1 < T and hot[j+1]: j += 1
            runs.append([i, j]); i = j + 1
        else: i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
        else: merged.append([a, b])
    out = np.zeros(T, bool)
    for a, b in merged: out[a:b+1] = True
    return out, len(merged)

mhw = np.zeros((Tn, 60, 60), bool)
n_ec = np.zeros((60, 60), int)
for i in range(60):
    for j in range(60):
        if not sea[i, j]: continue
        hot = tgt[:, i, j] >= thr_s[tgt_doy - 1, i, j]
        mhw[:, i, j], n_ec[i, j] = cell_mhw_mask(hot)
print('per-cell MHWs:', int(n_ec.sum()), 'cells with >=1:', int((n_ec > 0).sum()))

per_day_cells = mhw.sum(axis=(1, 2))   # cells in MHW per day
active = per_day_cells > 0
events = []
i = 0
while i < Tn:
    if active[i]:
        j = i
        while j + 1 < Tn and active[j+1]: j += 1
        events.append((str(tgt_dates[i]), str(tgt_dates[j]))); i = j + 1
    else: i += 1
d = np.diff(active.astype(np.int8), prepend=0, append=0)
ev2 = [(str(tgt_dates[s]), str(tgt_dates[e])) for s, e in zip(np.where(d==1)[0], np.where(d==-1)[0]-1)]
assert events == ev2
print('regional events:', events)
i_end = int(np.searchsorted(tgt_dates, np.datetime64(events[0][1]))) + 1
print('event span:', i_end, 'days; active days total:', int(active.sum()))
print('min/max cells in MHW on event days:', int(per_day_cells[:i_end].min()), int(per_day_cells[:i_end].max()))
print('per-day cell counts (day 0,1,2 / day 66,67,68):', per_day_cells[:3].tolist(), per_day_cells[66:69].tolist())
# last days inactive?
print('days after event end:', int(active[i_end:].sum()))

# sample threshold values (K) for a mid-region sea cell (lat idx 30 -> 55.06N, lon idx 30 -> 16.66E)
i0, j0 = 30, 30
print('cell(30,30) sea?', bool(sea[i0,j0]))
for dd in (153, 180, 200, 214, 244):
    print(f'  doy {dd}: raw thr {thr[dd-1, i0, j0]:.3f} K, smoothed {thr_s[dd-1, i0, j0]:.3f} K')
# SST range for that cell in target
print('  SST target min/max:', tgt[:, i0, j0].min(), tgt[:, i0, j0].max())

with open('/work/state.pkl','wb') as f:
    pickle.dump({'mhw': mhw, 'tgt_dates': tgt_dates, 'sea': sea, 'events': events, 'active': active,
                 'li': li, 'lo': lo}, f)
print('state saved')
