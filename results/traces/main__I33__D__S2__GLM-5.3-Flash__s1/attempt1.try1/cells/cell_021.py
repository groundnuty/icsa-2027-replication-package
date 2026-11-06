import numpy as np, h5py, json, os
import xarray as xr
from datetime import date, timedelta

ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values; lat = ds.latitude.values; lon = ds.longitude.values
latm = (lat >= 59.05) & (lat <= 60.25); lonm = (lon >= 21.25) & (lon <= 22.45)
li, oi = np.where(latm)[0], np.where(lonm)[0]
ls, le, os_, oe = li[0], li[-1]+1, oi[0], oi[-1]+1
lat_r = lat[ls:le].astype(np.float64); lon_r = lon[os_:oe].astype(np.float64)

def tidx(s): return int(np.searchsorted(t, np.datetime64(s)))
i_e0, i_e1 = tidx('1991-12-27'), tidx('2003-01-05')+1   # baseline +/- 5-day spillover
i_t0, i_t1 = tidx('2014-06-01'), tidx('2014-08-31')+1
with h5py.File('/work/s2z/sst_s2.nc', 'r') as f:
    ext = np.array(f['analysed_sst'][i_e0:i_e1, ls:le, os_:oe], dtype=np.float64)
    tgt = np.array(f['analysed_sst'][i_t0:i_t1, ls:le, os_:oe], dtype=np.float64)
ext_dates = t[i_e0:i_e1]; tgt_dates = t[i_t0:i_t1]

def doy_of(y, m, d): return (date(2000, m, d) - date(2000, 1, 1)).days + 1  # 1..366 leap-anchored
base_dates = [date(1992,1,1) + timedelta(days=k) for k in range((date(2002,12,31)-date(1992,1,1)).days + 1)]
e0 = date(1991,12,27)
pool = {d: [] for d in range(1, 367)}
for b in base_dates:
    bd = doy_of(b.year, b.month, b.day)
    if bd == 60: continue                      # no pool centred on 29 Feb
    for o in range(-5, 6):
        pool[bd].append((b + timedelta(days=o) - e0).days)

clim_raw = np.full((366, 60, 60), np.nan); thr_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = ext[np.asarray(pool[d])]
    with np.errstate(all='ignore'):
        clim_raw[d-1] = np.nanmean(vals, axis=0)
        thr_raw[d-1]  = np.nanpercentile(vals, 90, axis=0, method='hazen')  # Hazen = MATLAB default
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])   # day 60 = mean of days 59, 61
thr_raw[59]  = 0.5*(thr_raw[58]  + thr_raw[60])

def circ_smooth31(x):
    a = np.concatenate([x[-15:], x, x[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+x.shape[1:]), np.cumsum(a, axis=0)], axis=0)
    j = np.arange(1, 367) + 14
    return (c[j+16] - c[j-15]) / 31.0
clim_sm = circ_smooth31(clim_raw); thr_sm = circ_smooth31(thr_raw)

# --- MHW detection on target period ---
doys = np.array([doy_of(tt.year, tt.month, tt.day) for tt in tgt_dates.astype('datetime64[D]').astype(object)])
assert doys[0] == 153 and doys[-1] == 244
thr_t = thr_sm[doys-1]
hot = np.greater_equal(tgt, thr_t, where=np.isfinite(tgt), out=np.zeros(tgt.shape, dtype=bool))

def runs(m):
    dm = np.diff(np.concatenate([[0], np.asarray(m, int), [0]]))
    return list(zip(np.where(dm == 1)[0], np.where(dm == -1)[0]))

NT = len(tgt_dates)
mask = np.zeros_like(hot)
for i in range(60):
    for j in range(60):
        hot5 = np.zeros(NT, bool)
        for s, e in runs(hot[:, i, j]):
            if e - s >= 5: hot5[s:e] = True
        for s, e in runs(~hot5):                    # join gaps of 1-2 days
            if 0 < s and e < NT and e - s <= 2: hot5[s:e] = True
        mask[:, i, j] = hot5

active = mask.any(axis=(1, 2))
ev = runs(active)
events = [{'onset': str(tgt_dates[s])[:10], 'end': str(tgt_dates[e-1])[:10]} for s, e in ev]

# --- outputs ---
os.makedirs('output', exist_ok=True)
out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mask.astype(np.uint8))},
    coords={'time': ('time', tgt_dates), 'lat': ('lat', lat_r), 'lon': ('lon', lon_r)})
out['lat'].attrs = {'standard_name': 'latitude', 'units': 'degrees_north'}
out['lon'].attrs = {'standard_name': 'longitude', 'units': 'degrees_east'}
out['mhw'].attrs = {'long_name': 'marine heatwave (per-cell) mask', 'flag_values': np.array([0, 1], dtype=np.uint8),
                    'flag_meanings': 'not_in_mhw in_mhw'}
out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf',
              encoding={'mhw': {'dtype': 'uint8', '_FillValue': None},
                        'time': {'units': 'days since 1900-01-01 00:00:00', 'calendar': 'proleptic_gregorian'}})
report = {'region': {'lat_min': 59.05, 'lat_max': 60.25, 'lon_min': 21.25, 'lon_max': 22.45},
          'baseline_analysed': {'start': '1992-01-01', 'end': '2002-12-31'},
          'target_analysed': {'start': '2014-06-01', 'end': '2014-08-31'},
          'events': events, 'complete': True,
          'caveats': 'Climatology and threshold pools use +-5-calendar-day windows around 1992-2002 baseline dates, so values from 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05 also enter the pools. Day-60 (29 Feb) raw values are the mean of days 59 and 61 before smoothing. Land cells (SST not finite on every target day; 310 of 3600) are 0 in mhw.'}
json.dump(report, open('output/report.json', 'w'), indent=2)

print('events:', events)
print('mask cells-days:', int(mask.sum()), '| active days:', int(active.sum()))
print('written:', os.path.getsize('output/mhw_mask.nc'), 'bytes ;', json.dumps(json.load(open('output/report.json')))[:200])