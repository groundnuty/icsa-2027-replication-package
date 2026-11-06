import os, json
import numpy as np
import xarray as xr

os.makedirs('output', exist_ok=True)

mask = np.load('/tmp/mask.npy')                 # (92, 60, 60) uint8
lat = np.load('/tmp/lat.npy')[438:498]          # 62.26..63.44
lon = np.load('/tmp/lon.npy')[487:547]          # 18.74..19.92
time_all = np.load('/tmp/time_all.npy')
t = time_all[11109:11201]
assert lat.shape == (60,) and lon.shape == (60,)
assert lat.dtype == np.float32 and lon.dtype == np.float32

ds = xr.Dataset(
    data_vars={'mhw': (('time', 'lat', 'lon'), mask.astype(np.uint8))},
    coords={
        'time': ('time', t),
        'lat': ('lat', lat),
        'lon': ('lon', lon),
    },
)
ds['time'].attrs = {'standard_name': 'time', 'axis': 'T',
                    'units': 'seconds since 1981-01-01', 'calendar': 'proleptic_gregorian'}
ds['lat'].attrs = {'standard_name': 'latitude', 'units': 'degrees_north', 'long_name': 'Latitude'}
ds['lon'].attrs = {'standard_name': 'longitude', 'units': 'degrees_east', 'long_name': 'Longitude'}
ds['mhw'].attrs = {'long_name': 'Marine heatwave mask',
                   'description': '1 where the grid cell is inside a per-cell MHW (>=5 consecutive days with SST >= '
                                  'smoothed 90th-percentile threshold, gaps of 1-2 non-hot days joined), 0 otherwise'}
ds.attrs = {'source_dataset': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
            'region': 'lat 62.25-63.45 N, lon 18.73-19.93 E',
            'target_period': '2012-06-01 to 2012-08-31'}
ds.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": "2012-08-15", "end": "2012-08-19"}],
    "complete": True,
    "caveats": ("Thresholds and climatology per grid cell and day of year: pool = SST values on dates within "
                "+/-5 calendar days of each baseline date (1992-2002), 121 dates per day of year; windows reach "
                "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; day 60 (29 Feb) has no pool of its own and was "
                "set to the mean of days 59 and 61 before smoothing; 90th percentile computed with numpy "
                "method='hazen' ignoring NaN; both arrays smoothed with a 31-day centred moving mean wrapping the "
                "366-day year. MHWs: hot day = SST (K, as stored) >= smoothed threshold; per-cell MHW = run of "
                ">=5 consecutive hot days; MHWs separated by 1-2 non-hot days are joined (gap days included); "
                "no cell in this period had more than one such run, so no joins were triggered. Sea cells = "
                "3308 of 3600 region cells finite on all target days; land/ice cells set to 0.")
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
print("mhw dtype:", chk.mhw.dtype, "sum:", int(chk.mhw.values.sum()))
print("time:", chk.time.values[0], "..", chk.time.values[-1])
print("lat:", chk.lat.values[0], "..", chk.lat.values[-1], " lon:", chk.lon.values[0], "..", chk.lon.values[-1])
print("files:", os.path.abspath('output/mhw_mask.nc'), os.path.abspath('output/report.json'))
