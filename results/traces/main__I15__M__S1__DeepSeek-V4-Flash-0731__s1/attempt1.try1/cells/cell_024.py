import numpy as np
from datetime import datetime, timedelta
import json
import os

# Load data
in_mhw = np.load('/tmp/in_mhw.npy')  # (n_sea, n_target)
sea_mask = np.load('/tmp/sea_mask.npy')  # (60, 60)
sea_indices = np.load('/tmp/sea_indices.npy')  # (n_sea, 2)
target_sst = np.load('/tmp/target_sst.npy')  # (92, 60, 60)
lat_idx = np.load('/tmp/lat_idx.npy')
lon_idx = np.load('/tmp/lon_idx.npy')

n_target = in_mhw.shape[1]
n_lat = len(lat_idx)
n_lon = len(lon_idx)

# Create the mhw mask for the full 60x60 grid
mhw_grid = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

# Map sea cell MHW results to the grid
for c, (lat_i, lon_j) in enumerate(sea_indices):
    mhw_grid[:, lat_i, lon_j] = in_mhw[c].astype(np.uint8)

print(f"mhw_grid shape: {mhw_grid.shape}")
print(f"Sum of mhw: {mhw_grid.sum()}")

# Target dates
target_dates = []
d = datetime(2019, 6, 1)
while d <= datetime(2019, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Write mhw_mask.nc
import xarray as xr

# Get coordinate values from the original data
ds_ref = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
region_lats = ds_ref.latitude.values[lat_idx]
region_lons = ds_ref.longitude.values[lon_idx]
ds_ref.close()

# Create the NetCDF file
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_grid)
    },
    coords={
        'time': np.array([np.datetime64(d) for d in target_dates]),
        'lat': region_lats,
        'lon': region_lons,
    }
)

os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Verify the file
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"mhw dtype: {ds_check['mhw'].dtype}")
print(f"mhw dims: {dict(ds_check['mhw'].sizes)}")
print(f"mhw values sum: {ds_check['mhw'].sum().values}")
ds_check.close()

# Write report.json
# Determine events
active = in_mhw.any(axis=0)
events = []
i = 0
while i < n_target:
    if active[i]:
        start = i
        while i < n_target and active[i]:
            i += 1
        end = i - 1
        events.append({
            'onset': target_dates[start].strftime('%Y-%m-%d'),
            'end': target_dates[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

report = {
    'region': {
        'lat_min': 56.13,
        'lat_max': 57.33,
        'lon_min': 17.71,
        'lon_max': 18.91
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2019-06-01',
        'end': '2019-08-31'
    },
    'events': events,
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nWrote output/report.json")
print(json.dumps(report, indent=2))
