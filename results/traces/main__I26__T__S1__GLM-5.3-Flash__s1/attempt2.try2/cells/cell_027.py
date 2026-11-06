import numpy as np, json, os, datetime as dt
import xarray as xr

os.makedirs('output', exist_ok=True)
dates = json.load(open('cache/dates.json')); tgt_s = dates['tgt_s']
mhw = np.load('cache/mhw.npy')            # (92,60,60) uint8
sea = np.load('cache/sea.npy')
idx = json.load(open('cache/region_idx.json'))
Y0,Y1,X0,X1 = idx['y0'],idx['y1'],idx['x0'],idx['x1']

# coordinates from the dataset itself
import fsspec, io, h5py
fs = fsspec.filesystem('onedata')
BASE='icsa2027_data_20261101T090944Z/s1z'
b = fs.cat(f'{BASE}/sst_20070601.nc')
f = h5py.File(io.BytesIO(b),'r')
lat = f['latitude'][Y0:Y1+1]
lon = f['longitude'][X0:X1+1]
f.close()
tv = np.array([dt.date(int(s[:4]),int(s[4:6]),int(s[6:8])) for s in tgt_s], dtype='datetime64[ns]')
print('lat', lat[0], '..', lat[-1], lat.dtype, '| lon', lon[0], '..', lon[-1], lon.dtype)
print('time', tv[0], '..', tv[-1], tv.dtype, 'n=', len(tv))

assert mhw.shape == (len(tv), len(lat), len(lon)) and mhw.dtype == np.uint8
assert not mhw[:, ~sea].any()   # land cells all zero

ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': tv, 'lat': lat, 'lon': lon},
    attrs={
        'title': 'Per-cell marine heatwave (MHW) mask, Baltic Sea region',
        'method': 'threshold: 90th percentile (Hazen/Hyndman-Fan type 5) of +-5 calendar-day pools '
                  'over 1992-2002 baseline, fixed 366-day calendar, day 60 filled from days 59/61, '
                  'then circular 31-day centred moving mean; climatology: same construction using the mean; '
                  'hot day: SST >= threshold; per-cell MHW: >=5 consecutive hot days, gaps of 1-2 days joined; '
                  'mask is 1 inside a per-cell MHW',
        'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016)',
        'region': 'lat 57.83-59.03 N, lon 17.41-18.61 E',
        'target_period': '2007-06-01 to 2007-08-31',
    },
)
enc = {'mhw': {'dtype': 'uint8', 'zlib': True}}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print('wrote output/mhw_mask.nc', os.path.getsize('output/mhw_mask.nc'), 'bytes')

# verify round-trip
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m2 = chk['mhw']
print('roundtrip:', m2.dtype, m2.dims, m2.shape, 'sum=', int(m2.values.sum()),
      'equal:', bool((m2.values == mhw).all()))
print('lat/lon/time match:', np.array_equal(chk.lat.values, lat), np.array_equal(chk.lon.values, lon),
      np.array_equal(chk.time.values.astype('datetime64[ns]'), tv))
chk.close()

events = json.load(open('cache/events.json'))
report = {
    'region': {'lat_min': 57.83, 'lat_max': 59.03, 'lon_min': 17.41, 'lon_max': 18.61},
    'baseline_analysed': {'start': '1992-01-01', 'end': '2002-12-31'},
    'target_analysed': {'start': '2007-06-01', 'end': '2007-08-31'},
    'events': events,
    'complete': True,
    'caveats': ('Day-of-year is a fixed 366-day calendar by month/day (1 March = 61 in every year; '
                'non-leap years have no day 60). Each non-60 day-of-year pool holds exactly 121 dates: '
                'the +-5 calendar-day window around each of the 11 baseline years\' dates of that month/day, '
                'including 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. The smoothing wrap uses day 366 = 31 Dec '
                'of the same fixed calendar (days 1-15 adjacent); it does not affect the June-August target comparisons. '
                'Sea cells (3294 of 3600) have finite SST on every target day; other cells are masked 0. '
                'SST stored as float32 was promoted to float64 for all computations.'),
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print('wrote output/report.json', os.path.getsize('output/report.json'), 'bytes')
print(json.dumps(report, indent=2)[:1200])
