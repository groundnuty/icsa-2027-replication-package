import numpy as np, h5py, pandas as pd, json, warnings, os

warnings.filterwarnings('ignore')

PATH = '/work/sst_s2.nc'
f = h5py.File(PATH, 'r')
lat = f['latitude'][:].astype(np.float64)
lon = f['longitude'][:].astype(np.float64)
t64 = np.datetime64('1981-01-01T00:00:00') + f['time'][:].astype('timedelta64[s]')
d = f['analysed_sst']

eps = 1e-5
latm = (lat >= 57.57 - eps) & (lat <= 58.77 + eps)
lonm = (lon >= 10.25 - eps) & (lon <= 11.45 + eps)
y0, y1 = np.flatnonzero(latm)[0], np.flatnonzero(latm)[-1]
x0, x1 = np.flatnonzero(lonm)[0], np.flatnonzero(lonm)[-1]
NY, NX = y1 - y0 + 1, x1 - x0 + 1
NC = NY * NX

def doy_fixed(times):
    dti = pd.DatetimeIndex(times.astype('datetime64[D]'))
    md = pd.to_datetime(dict(year=2000, month=dti.month, day=dti.day))
    return md.dt.dayofyear.values.astype(int)

b0 = np.searchsorted(t64, np.datetime64('1991-12-27T00:00:00'))
b1 = np.searchsorted(t64, np.datetime64('2003-01-05T00:00:00'), 'right')
slab = d[b0:b1, y0:y1+1, x0:x1+1].astype(np.float64).reshape(b1 - b0, NC)
cand = t64[b0:b1]

t0 = np.searchsorted(t64, np.datetime64('2016-06-01T00:00:00'))
t1 = np.searchsorted(t64, np.datetime64('2016-08-31T00:00:00'), 'right')
sst_t = d[t0:t1, y0:y1+1, x0:x1+1].astype(np.float64).reshape(t1 - t0, NC)
tgt = t64[t0:t1]
NT = tgt.size
f.close()

sea = np.isfinite(sst_t).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', NC)

cand_D = cand.astype('datetime64[D]')
cand_doy = doy_fixed(cand_D)
base_all = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = doy_fixed(base_all.values.astype('datetime64[D]'))

# sanity: no 29 Feb in candidate window, and base_doy values correct
print('29 Feb in candidates?', bool((cand_D == np.datetime64('1996-02-29')).sum()), '| 2000?',
      bool((cand_D == np.datetime64('2000-02-29')).sum()))
print('base_doy for 1992-01-01, 1992-02-28, 1992-03-01, 2000-12-31:',
      base_doy[0], base_doy[31+27], base_doy[31+28], base_doy[-1])

clim_raw = np.full((366, NC), np.nan)
thr_raw = np.full((366, NC), np.nan)
pool_sizes = []
for dd in range(1, 367):
    if dd == 60:
        continue
    bdates = base_all[base_doy == dd]
    mask = np.zeros(cand.size, dtype=bool)
    for b in bdates:
        mask |= (cand_D >= np.datetime64(b.date()) - np.timedelta64(5, 'D')) & \
                (cand_D <= np.datetime64(b.date()) + np.timedelta64(5, 'D'))
    pool_sizes.append(int(mask.sum()))
    vals = slab[mask]
    clim_raw[dd - 1] = np.nanmean(vals, axis=0)
    thr_raw[dd - 1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
print('pool sizes: min %d max %d unique %s' % (min(pool_sizes), max(pool_sizes),
                                               sorted(set(pool_sizes))[:6]))

for arr in (clim_raw, thr_raw):
    arr[59] = 0.5 * (arr[58] + arr[60])

def circ31(a):
    out = np.zeros_like(a)
    for k in range(-15, 16):
        out += np.roll(a, k, axis=0)
    return out / 31.0

clim_s = circ31(clim_raw)
thr_s = circ31(thr_raw)

tidx = doy_fixed(tgt.astype('datetime64[D]')) - 1
print('target doys:', tidx[:3], '..', tidx[-3:], '(Jun 1 ->', tidx[0]+1, ', Aug 31 ->', tidx[-1]+1, ')')
hot = sst_t >= thr_s[tidx]
print('hot cell-days:', int(hot.sum()), 'of', NT * NC)

hp = np.zeros((NT + 2, NC), dtype=np.int8)
hp[1:-1] = hot.astype(np.int8)
dif = np.diff(hp, axis=0)
starts = np.argwhere(dif == 1)
ends = np.argwhere(dif == -1)
runs = [(int(c), int(s), int(e)) for (s, c), (e, _) in zip(starts, ends)]
runs5 = sorted([(c, s, e) for c, s, e in runs if e - s >= 5])
print('runs total %d, runs >=5: %d' % (len(runs), len(runs5)))

merged = []
for c, s, e in runs5:
    if merged and merged[-1][0] == c and s - merged[-1][2] <= 2:
        merged[-1][2] = max(merged[-1][2], e)
    else:
        merged.append([c, s, e])
print('per-cell MHWs after joining:', len(merged))

mhw = np.zeros((NT, NC), dtype=np.uint8)
for c, s, e in merged:
    mhw[s:e, c] = 1
mhw &= sea.astype(np.uint8)[None, :]
print('mhw cell-days:', int(mhw.sum()))

active = mhw.astype(bool).any(axis=1)
ev = np.diff(np.concatenate([[0], active.astype(np.int8), [0]]))
onsets = np.flatnonzero(ev == 1)
off = np.flatnonzero(ev == -1)
events = [{'onset': str(tgt[a].astype('datetime64[D]')),
           'end': str(tgt[b - 1].astype('datetime64[D]'))} for a, b in zip(onsets, off)]
print('active days:', int(active.sum()), 'of', NT)
print('regional events:', len(events))
for e_ in events:
    print(' ', e_)

import xarray as xr
ds_out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw.reshape(NT, NY, NX).astype(np.uint8))},
    coords={'time': tgt.astype('datetime64[ns]'),
            'lat': lat[y0:y1+1].astype(np.float32),
            'lon': lon[x0:x1+1].astype(np.float32)})
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')

report = {
    'region': {'lat_min': 57.57, 'lat_max': 58.77, 'lon_min': 10.25, 'lon_max': 11.45},
    'baseline_analysed': {'start': '1991-12-27', 'end': '2003-01-05'},
    'target_analysed': {'start': str(tgt[0].astype('datetime64[D]')),
                        'end': str(tgt[-1].astype('datetime64[D]'))},
    'events': events,
    'complete': True,
    'caveats': ('Day-of-year uses fixed leap-year numbering (1 Mar = 61; day 60 only in leap '
                'years). Threshold/climatology pools include the specified 5-day window '
                'extensions beyond the 1992-2002 baseline (1991-12-27..1991-12-31 and '
                '2003-01-01..2003-01-05); day 60 has no pool and is set to the mean of days '
                '59 and 61 before smoothing. Sea cells (finite SST on all 92 target days): '
                '%d of %d region cells; per-cell MHW flags are restricted to sea cells, all '
                'other cells are 0.' % (int(sea.sum()), NC))
}
with open('/work/output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print('files written:', os.listdir('/work/output'))
