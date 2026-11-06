import os
print("cwd:", os.getcwd())
import numpy as np, xarray as xr, json
from datetime import date, timedelta

mask = np.load('/work/mask.npy')          # (92, 60, 60) uint8
lat_vals = np.load('/work/lat_vals.npy')  # float32 (60,)
lon_vals = np.load('/work/lon_vals.npy')  # float32 (60,)
events = np.load('/work/events.npy')      # (n, 2)

tgt_dates = []
d = date(2021,6,1)
while d <= date(2021,8,31):
    tgt_dates.append(d); d += timedelta(days=1)
times = np.array([np.datetime64(f'{dt}') for dt in tgt_dates], dtype='datetime64[ns]')

out_dir = os.path.join(os.getcwd(), 'output')
os.makedirs(out_dir, exist_ok=True)
if os.path.abspath(out_dir) != '/work/output':
    os.makedirs('/work/output', exist_ok=True)

da = xr.DataArray(
    mask.astype(np.uint8),
    dims=('time', 'lat', 'lon'),
    coords={'time': times, 'lat': lat_vals, 'lon': lon_vals},
    name='mhw',
)
ds_out = da.to_dataset()
ds_out.to_netcdf(os.path.join(out_dir, 'mhw_mask.nc'), engine='h5netcdf')
print("wrote", os.path.join(out_dir, 'mhw_mask.nc'))

report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [
        {"onset": tgt_dates[int(s)].isoformat(), "end": tgt_dates[int(e)].isoformat()}
        for s, e in events
    ],
    "complete": True,
    "caveats": "",
}
with open(os.path.join(out_dir, 'report.json'), 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
# copy to /work/output too if different
if os.path.abspath(out_dir) != '/work/output':
    import shutil
    shutil.copy(os.path.join(out_dir, 'mhw_mask.nc'), '/work/output/mhw_mask.nc')
    shutil.copy(os.path.join(out_dir, 'report.json'), '/work/output/report.json')
    print("also copied to /work/output")
