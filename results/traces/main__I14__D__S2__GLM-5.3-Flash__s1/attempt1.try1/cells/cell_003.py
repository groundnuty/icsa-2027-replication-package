import xarray as xr, numpy as np, json
from datetime import date

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')

# Region bounds inclusive
i0 = np.where((lat >= 56.13 - 1e-6) & (lat <= 57.33 + 1e-6))[0]
j0 = np.where((lon >= 17.71 - 1e-6) & (lon <= 18.91 + 1e-6))[0]
print('lat idx', i0[0], i0[-1], 'lat vals', lat[i0[0]], lat[i0[-1]], 'n', len(i0))
print('lon idx', j0[0], j0[-1], 'lon vals', lon[j0[0]], lon[j0[-1]], 'n', len(j0))

t = ds['time'].values
dates = t.astype('datetime64[D]').astype('O')  # array of datetime.date
n = len(dates)
print('n time', n, dates[0], dates[-1])

# baseline 1992-2002
bs = date(1992,1,1); be = date(2002,12,31)
bi = np.array([d >= bs and d <= be for d in dates])
print('baseline days', bi.sum(), dates[np.where(bi)[0][0]], dates[np.where(bi)[0][-1]])

# target 2015-06-01..2015-08-31
ts_ = date(2015,6,1); te_ = date(2015,8,31)
ti_mask = np.array([d >= ts_ and d <= te_ for d in dates])
ti = np.where(ti_mask)[0]
print('target days', len(ti), dates[ti[0]], dates[ti[-1]])

# doy mapping (Feb29 -> 60, non-leap has no 60; Dec 31 -> 366)
def doy_of(d):
    if d.month == 2 and d.day == 29:
        return 60
    return (d - date(d.year,1,1)).days + 1

# verify no day 367: check 31 Dec maps to 365 or 366 depending on leap
print('doy 2000-12-31', doy_of(date(2000,12,31)), 'doy 2001-12-31', doy_of(date(2001,12,31)))

b_doy = np.array([doy_of(d) for d in np.array(dates)[bi]])
print('baseline doy range', b_doy.min(), b_doy.max())
print('baseline has doy60?', (b_doy==60).sum())

# slices per doy
start = np.full(366, -1); end = np.full(366, -1)
b_idx = np.where(bi)[0]
bd_sorted = np.sort(b_doy)  # baseline is sorted by date so doy is mostly increasing but wraps not here (single span, 1992-2002 continuous) - doy resets each year
# better: for each doy d, indices where b_doy==d
# since target period only needs doys 152..243, but compute all pools for completeness? Just needed range; compute all 366 pools' slices cheaply.
doy_sets = {}
for d in range(1,367):
    idxs = np.where(b_doy == d)[0] + b_idx[0]  # positions within baseline block -> absolute indices
    doy_sets[d] = idxs
# windows: d from 1..366 -> include doys d-5..d+5 with wrap, excluding 60
# For d=1: baseline dates with doy 1 (Jan1 1992..2002) ±5 days: Dec 27..Jan 6 -> doys 361..366,1..6 (leap years give 366 for Dec31)
# For d=366: doys 361..366,1..5
# General with wrap modulo 366: dd = ((d-1+k) % 366)+1
import sys
sel = {}
for d in range(1,367):
    dd_list = [((d-1+k) % 366)+1 for k in range(-5,6)]
    dd_list = [x for x in dd_list if x != 60]
    allidx = np.concatenate([doy_sets[x] for x in dd_list])
    sel[d] = np.sort(allidx)
print('pool sizes sample:', {d: len(sel[d]) for d in (1,2,59,60,61,152,200,243,366)})
json.dump({str(k): v.tolist() for k,v in sel.items()}, open('/work/doy_pools.json','w'))
np.save('/work/lat.npy', lat); np.save('/work/lon.npy', lon)
np.save('/work/i0.npy', i0); np.save('/work/j0.npy', j0)
np.save('/work/bi.npy', bi); np.save('/work/ti.npy', ti)
# store dates as doy full array
full_doy = np.array([doy_of(d) for d in dates])
np.save('/work/full_doy.npy', full_doy)
print('saved meta')
