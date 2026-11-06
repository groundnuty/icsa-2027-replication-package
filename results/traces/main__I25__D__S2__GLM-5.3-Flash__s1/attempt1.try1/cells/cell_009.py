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
    # pure function of (month, day): leap-year numbering, 29 Feb = 60, 31 Dec = 366
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
base_all = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = doy_fixed(base_all.values.astype('datetime64[D]'))

clim_raw = np.full((366, NC), np.nan)
thr_raw = np.full((366, NC), np.nan)
pool_sizes = set()
for dd in range(1, 367):
    if dd == 60:
        continue
    bdates = base_all[base_doy == dd]
    mask = np.zeros(cand.size, dtype=bool)
    for b in bdates:
        lo = np.datetime64(b.date()) - np.timedelta64(5, 'D')
        hi = np.datetime64(b.date()) + np.timedelta64(5, 'D')
        mask |= (cand_D >= lo) & (cand_D <= hi)
    pool_sizes.add(int(mask.sum()))
    vals = slab[mask]
    clim_raw[dd - 1] = np.nanmean(vals, axis=0)
    thr_raw[dd - 1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
print('pool sizes (all doy except 60):', sorted(pool_sizes))

for arr in (clim_raw, thr_raw):
    arr[59] = 0.5 * (arr[58] + arr[60])

def circ31(a):
    out = np.zeros_like(a)
    for k in range(-15, 16):
        out += np.roll(a, k, axis=0)
    return out / 31.0

clim_s = circ31(clim_raw)
thr_s = circ31(thr_raw)

print('NaN thr at sea cells:', int(np.isnan(thr_s[:, sea]).sum()),
      '| NaN clim at sea cells:', int(np.isnan(clim_s[:, sea]).sum()))
sea_idx = np.flatnonzero(sea)
cidx = int(sea_idx[sea_idx.size // 2])
print('sample sea cell (row %d,col %d): clim Jun1(doy153)=%.3f K, thr Jun1=%.3f K; thr Aug31(doy244)=%.3f K'
      % (cidx // NX, cidx % NX, clim_s[152, cidx], thr_s[152, cidx], thr_s[243, cidx]))

tidx = doy_fixed(tgt.astype('datetime64[D]')) - 1
hot = sst_t >= thr_s[tidx]
print('hot cell-days:', int(hot.sum()), 'of', NT * NC, '(2016 leap: Jun1 doy=%d, Aug31 doy=%d)'
      % (tidx[0] + 1, tidx[-1] + 1))

# ---- per-cell runs: >=5 hot days, join gaps of 1-2 non-hot days (target period only)
def runs_and_mhw(hotcol):
    hp = np.concatenate(([0], hotcol.astype(np.int8), [0]))
    dif = np.diff(hp)
    st = np.flatnonzero(dif == 1)
    en = np.flatnonzero(dif == -1)
    assert st.size == en.size
    runs5 = [(int(s), int(e)) for s, e in zip(st, en) if e - s >= 5]
    merged = []
    for s, e in runs5:
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged

all_runs = [runs_and_mhw(hot[:, c]) for c in range(NC)]
mhw = np.zeros((NT, NC), dtype=np.uint8)
for c, rl in enumerate(all_runs):
    for s, e in rl:
        mhw[s:e, c] = 1
mhw &= sea.astype(np.uint8)[None, :]
print('per-cell MHWs (after joining):', sum(len(rl) for rl in all_runs),
      '| mhw cell-days:', int(mhw.sum()))

# brute-force verification on 25 columns (random 23 + first + last)
rng = np.random.default_rng(0)
check_cols = [int(v) for v in rng.choice(NC, 23, replace=False)] + [0, NC - 1]
ok = True
for c in check_cols:
    hc = hot[:, c]
    i, rr = 0, []
    while i < NT:
        if hc[i]:
            j = i
            while j < NT and hc[j]:
                j += 1
            rr.append((i, j))
            i = j
        else:
            i += 1
    rr5 = [r for r in rr if r[1] - r[0] >= 5]
    mg = []
    for s, e in rr5:
        if mg and s - mg[-1][1] <= 2:
            mg[-1][1] = max(mg[-1][1], e)
        else:
            mg.append([s, e])
    flag = np.zeros(NT, dtype=bool)
    for s, e in mg:
        flag[s:e] = True
    if not np.array_equal(flag, mhw[:, c].astype(bool)):
        ok = False
        print('MISMATCH col', c)
print('brute-force check on %d columns: %s' % (len(check_cols), 'OK' if ok else 'FAILED'))

# ---- regional events
active = mhw.astype(bool).any(axis=1)
ev = np.diff(np.concatenate([[0], active.astype(np.int8), [0]]))
onsets = np.flatnonzero(ev == 1)
offs = np.flatnonzero(ev == -1)
events = [{'onset': str(tgt[a].astype('datetime64[D]')),
           'end': str(tgt[b - 1].astype('datetime64[D]'))} for a, b in zip(onsets, offs)]
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
    'caveats': ('Day-of-year is the fixed leap-year numbering (function of month/day: '
                '29 Feb = 60, 31 Dec = 366; non-leap years have no day 60). Threshold/'
                'climatology pools include the specified 5-day window extensions beyond the '
                '1992-2002 baseline (1991-12-27..1991-12-31, 2003-01-01..2003-01-05); day 60 '
                'has no pool and is set to the mean of days 59 and 61 before smoothing. '
                'Per-cell MHWs and joins were computed only within 2016-06-01..2016-08-31, so '
                'an event ongoing at a period edge is truncated there. Sea cells (finite SST '
                'on all 92 target days): %d of %d region cells (296 land); MHW flags are 0 '
                'outside sea cells.' % (int(sea.sum()), NC))
}
with open('/work/output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print('files written:', os.listdir('/work/output'))
