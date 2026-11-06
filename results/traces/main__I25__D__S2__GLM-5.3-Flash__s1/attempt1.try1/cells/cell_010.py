import numpy as np, h5py, pandas as pd, json, warnings

warnings.filterwarnings('ignore')

PATH = '/work/sst_s2.nc'
f = h5py.File(PATH, 'r')
lat = f['latitude'][:].astype(np.float64)
lon = f['longitude'][:].astype(np.float64)
t64 = np.datetime64('1981-01-01T00:00:00') + f['time'][:].astype('timedelta64[s]')
d = f['analysed_sst']
src_lat = f['latitude'][:]  # raw float32
src_lon = f['longitude'][:]

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
cand_D = cand.astype('datetime64[D]')
base_all = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = doy_fixed(base_all.values.astype('datetime64[D]'))

# ---- independent percentile: manual Hazen (type 5) on sorted columns
thr_raw = np.full((366, NC), np.nan)
clim_raw = np.full((366, NC), np.nan)
for dd in range(1, 367):
    if dd == 60:
        continue
    bdates = base_all[base_doy == dd]
    mask = np.zeros(cand.size, dtype=bool)
    for b in bdates:
        lo = np.datetime64(b.date()) - np.timedelta64(5, 'D')
        hi = np.datetime64(b.date()) + np.timedelta64(5, 'D')
        mask |= (cand_D >= lo) & (cand_D <= hi)
    vals = slab[mask]
    clim_raw[dd - 1] = np.nanmean(vals, axis=0)
    srt = np.sort(vals, axis=0)                     # NaN last
    n = np.isfinite(vals).sum(axis=0)               # finite count per cell
    h = n * 0.9 - 0.5                               # 0-based virtual index
    lo_i = np.floor(h).astype(int)
    g = h - lo_i
    hi_i = np.minimum(lo_i + 1, n - 1)
    lo_i = np.clip(lo_i, 0, n - 1)
    rows = np.arange(NC)
    v1 = srt[lo_i, rows]
    v2 = srt[hi_i, rows]
    v2 = np.where(np.isfinite(v2), v2, v1)          # guard nan*0 at hi boundary
    thr_raw[dd - 1] = v1 * (1 - g) + v2 * g

for arr in (clim_raw, thr_raw):
    arr[59] = 0.5 * (arr[58] + arr[60])

# ---- independent smoothing: explicit index arithmetic instead of np.roll
idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366  # (366, 31)
thr_s = thr_raw[idx].mean(axis=1)
clim_s = clim_raw[idx].mean(axis=1)

tidx = doy_fixed(tgt.astype('datetime64[D]')) - 1
hot = sst_t >= thr_s[tidx]
print('independent recompute: hot cell-days =', int(hot.sum()))

def runs_and_mhw(hotcol):
    hp = np.concatenate(([0], hotcol.astype(np.int8), [0]))
    dif = np.diff(hp)
    st = np.flatnonzero(dif == 1)
    en = np.flatnonzero(dif == -1)
    runs5 = [(int(s), int(e)) for s, e in zip(st, en) if e - s >= 5]
    merged = []
    for s, e in runs5:
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged

mhw2 = np.zeros((NT, NC), dtype=np.uint8)
nmhw = 0
for c in range(NC):
    for s, e in runs_and_mhw(hot[:, c]):
        mhw2[s:e, c] = 1
        nmhw += 1
mhw2 &= sea.astype(np.uint8)[None, :]
print('independent recompute: per-cell MHWs =', nmhw, '| mhw cell-days =', int(mhw2.sum()))

# ---- compare with written file
import xarray as xr
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
mv = chk['mhw'].values
print('file: dims', dict(chk.sizes), '| mhw dtype', mv.dtype, '| sum', int(mv.sum()))
print('coords match dataset values:',
      np.array_equal(chk['lat'].values, src_lat[y0:y1+1]),
      np.array_equal(chk['lon'].values, src_lon[x0:x1+1]),
      np.array_equal(chk['time'].values.astype('datetime64[D]'), tgt.astype('datetime64[D]')))
same = np.array_equal(mv.reshape(NT, NC), mhw2)
print('BIT-FOR-BIT MATCH (file vs independent recompute):', same)
land = (~np.isfinite(sst_t).any(axis=0)).reshape(NY, NX)
print('land cells all zero in mask:', bool(mv.reshape(NT, NY, NX)[:, land].max(initial=0) == 0))

# ---- active days / events from the file mask
mf = mv.reshape(NT, NC)
active = (mf == 1).any(axis=1)
adates = tgt[active].astype('datetime64[D]')
print('active days (%d):' % active.sum(), str(adates[0]), '..', str(adates[-1]),
      '| consecutive:', bool(np.all(np.diff(adates).astype(int) == 1)))
ev = np.diff(np.concatenate([[0], active.astype(np.int8), [0]]))
ons = np.flatnonzero(ev == 1); offs = np.flatnonzero(ev == -1)
events2 = [{'onset': str(tgt[a].astype('datetime64[D]')),
            'end': str(tgt[b-1].astype('datetime64[D]'))} for a, b in zip(ons, offs)]
perday = mf.sum(axis=1)
print('MHW cells/day during event: min %d max %d' % (perday[active].min(), perday[active].max()))

rep = json.load(open('/work/output/report.json'))
print('report keys ok:', sorted(rep.keys()) == sorted(
    ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']))
print('report events match recompute:', rep['events'] == events2)
print(json.dumps({k: rep[k] for k in ('region', 'baseline_analysed', 'target_analysed', 'events', 'complete')}, indent=1))
