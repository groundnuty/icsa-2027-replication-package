import numpy as np, xarray as xr, json, os, datetime as d2

mhw = np.load('/work/mhw.npy')          # (92, 60, 60) uint8
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
L0, L1, O0, O1 = 545, 604, 721, 780
lat = ds.latitude.values[L0:L1+1]       # float32, 64.4 .. 65.58
lon = ds.longitude.values[O0:O1+1]      # float32, 23.42 .. 24.599998
time = ds.time.values[13665:13757]      # 2019-06-01 .. 2019-08-31
assert mhw.shape == (len(time), len(lat), len(lon)) and mhw.dtype == np.uint8

os.makedirs('/work/output', exist_ok=True)
out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw.astype(np.uint8))},
    coords={'time': time, 'lat': lat, 'lon': lon},
    attrs={
        'title': 'Per-cell marine heatwave mask, Baltic Sea region (64.39-65.59N, 23.41-24.61E), 2019-06-01..2019-08-31',
        'source_dataset': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
        'method': 'threshold: per-cell day-of-year 90th percentile (Hyndman-Fan type 5 / MATLAB quantile default) of +-5-day pools over baseline 1992-2002, day 60 filled from days 59/61, smoothed with circular centred 31-day moving mean; hot: SST >= threshold; per-cell MHW: >=5 consecutive hot days, gaps of 1-2 days joined; mhw=1 inside per-cell MHW, 0 otherwise (land 0)',
    },
)
enc = {'mhw': {'dtype': 'uint8', 'zlib': True}}
out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print('wrote mhw_mask.nc', os.path.getsize('/work/output/mhw_mask.nc'), 'bytes')

report = {
    "region": {"lat_min": 64.39, "lat_max": 65.59, "lon_min": 23.41, "lon_max": 24.61},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
    "events": [
        {"onset": "2019-06-06", "end": "2019-06-22"},
        {"onset": "2019-07-20", "end": "2019-07-29"},
    ],
    "complete": True,
    "caveats": ("Baseline years 1992-2002; +-5-day pool windows at the period edges extend to 1991-12-27 and 2003-01-05, "
                "which are the first/last baseline days whose SST values entered the thresholds/climatology (reported above). "
                "Source SST is stored as float32 kelvin (no scale/offset) and was cast to float64 for all computations. "
                "Sea cells = 3311 of 3600 (finite SST on all 92 target days); land cells are 0 in the mask. "
                "2019 is a non-leap year, so day-of-year 60 (filled from days 59/61 before smoothing) is not used by the target period. "
                "Per-cell MHWs: runs of >=5 consecutive hot days (SST >= threshold, kelvin as stored), gaps of 1-2 non-hot days joined; "
                "regional events: maximal runs of days with at least one region sea cell inside a per-cell MHW."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print('wrote report.json', os.path.getsize('/work/output/report.json'), 'bytes')

# verify both files by re-reading
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print('mask file:', dict(chk.sizes), chk['mhw'].dtype, chk['mhw'].dims)
print('time:', str(chk.time.values[0])[:10], '..', str(chk.time.values[-1])[:10])
print('lat:', float(chk.lat[0]), '..', float(chk.lat[-1]), '| lon:', float(chk.lon[0]), '..', float(chk.lon[-1]))
print('mhw values:', np.unique(chk['mhw'].values), '| sum:', int(chk['mhw'].values.sum()))
print('matches in-memory mask:', bool((chk['mhw'].values == mhw).all()))
with open('/work/output/report.json') as f:
    r = json.load(f)
print('report keys:', sorted(r.keys()))
print('events:', r['events'], '| complete:', r['complete'])
