import numpy as np
import xarray as xr
import json, os

z = np.load('/work/intermediate.npz')
M = z['M'].reshape(92, 60, 60).astype(np.uint8)
lat = z['lat']   # float32, from dataset
lon = z['lon']   # float32, from dataset
t_tgt = z['t_tgt']

os.makedirs('/work/output', exist_ok=True)

ds_out = xr.Dataset(
    data_vars={'mhw': (('time', 'latitude', 'longitude'), M)},
    coords={
        'time': t_tgt.astype('datetime64[ns]'),
        'latitude': ('latitude', lat),
        'longitude': ('longitude', lon),
    },
)
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print("wrote mhw_mask.nc")

report = {
    "region": {"lat_min": 54.81, "lat_max": 56.01, "lon_min": 19.61, "lon_max": 20.81},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2022-06-01", "end": "2022-08-31"},
    "events": [
        {"onset": "2022-06-08", "end": "2022-06-18"},
        {"onset": "2022-06-22", "end": "2022-07-14"},
        {"onset": "2022-07-20", "end": "2022-07-24"},
        {"onset": "2022-08-10", "end": "2022-08-31"},
    ],
    "complete": True,
    "caveats": ("311 of 3600 grid cells in the region are not sea cells (SST not finite on every target day) "
                "and are set to 0 in the mask. The last event ends on the final target day (2022-08-31). "
                "Thresholds/climatology pools use 11-day windows (baseline dates +/-5 calendar days), "
                "hazen 90th percentile, day-of-year 60 averaged from days 59/61, then 31-day circular smoothing."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("wrote report.json")
print(json.dumps(report, indent=2))
