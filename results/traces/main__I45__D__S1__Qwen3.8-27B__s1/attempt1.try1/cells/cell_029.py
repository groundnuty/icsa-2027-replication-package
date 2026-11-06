import numpy as np, os, datetime as dt, json
import xarray as xr

# exact coordinate values from the dataset file (still on disk from first inspection)
src = xr.open_dataset('/work/data/sst_20090601.nc', engine="h5netcdf")
lat_all = src['latitude'].values; lon_all = src['longitude'].values
ls_ = np.where((lat_all >= 63.31 - 1e-9) & (lat_all <= 64.51 + 1e-9))[0]
lo_ = np.where((lon_all >= 21.31 - 1e-9) & (lon_all <= 22.51 + 1e-9))[0]
lat_vals = lat_all[ls_].astype(np.float32)
lon_vals = lon_all[lo_].astype(np.float32)
t0val = src['time'].values[0]
src.close()
print("lat:", lat_vals[0], lat_vals[-1], len(lat_vals), "lon:", lon_vals[0], lon_vals[-1], len(lon_vals), "t0:", t0val)

# time coordinate: midnight of each target day (verified convention from file)
dates = [dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(92)]
time_vals = np.array([d.strftime('%Y-%m-%T') for d in dates], dtype='datetime64[ns]')
assert time_vals[0] == np.datetime64(t0val)

mhw = np.load('/work/mhw.npy')  # (3600, 92)
mhw3d = mhw.T.reshape(92, 60, 60).astype(np.uint8)
print("mhw3d:", mhw3d.shape, mhw3d.dtype, "ones:", int(mhw3d.sum()), "max:", int(mhw3d.max()))

os.makedirs('/work/output', exist_ok=True)
ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw3d)},
    coords={'time': ('time', time_vals), 'lat': ('lat', lat_vals), 'lon': ('lon', lon_vals)},
)
ds.to_netcdf('/work/output/mhw_mask.nc')
print("wrote /work/output/mhw_mask.nc")

# report
events = json.load(open('/work/events.json'))
report = {
    "region": {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": [{"onset": a, "end": b} for a, b in events],
    "complete": True,
    "caveats": ("Region contains 3600 grid cells (lat 63.32-64.50 N, lon 21.32-22.50 E, 0.02 deg grid); "
                "3299 sea cells (finite SST on all 92 target days) were analysed, 301 land cells were excluded and set to 0. "
                "All 4028 baseline-window files (1991-12-27 to 2003-01-05) and 92 target files (2009-06-01 to 2009-08-31) were present; "
                "land cells are NaN on every day, sea cells are finite on every day, so no threshold pool contained NaN. "
                "Threshold = 90th percentile (numpy method='hazen', Hyndman-Fan type 5) of the +/-5-day pool per day of year from baseline 1992-2002; "
                "climatology = pool mean; day-of-year 60 filled by mean of days 59 and 61; both smoothed with a centred 31-day wrapping moving mean. "
                "Per-cell MHW: >=5 consecutive days with SST >= threshold, gaps of 1-2 non-hot days joined. "
                "Two regional events detected: 2009-06-24 to 2009-07-04 and 2009-08-04 to 2009-08-14."),
}
json.dump(report, open('/work/output/report.json','w'), indent=2)
print(json.dumps(report, indent=2)[:1200])
