
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Read one file to get lat/lon indices
f0 = os.path.join(data_dir, 'sst_20220601.nc')
ds0 = xr.open_dataset(f0, engine='h5netcdf')
lats = ds0.latitude.values
lons = ds0.longitude.values
lat_idx = np.where((lats >= 54.81) & (lats <= 56.01))[0]
lon_idx = np.where((lons >= 19.61) & (lons <= 20.81))[0]
ds0.close()

n_lat = len(lat_idx)
n_lon = len(lon_idx)
print(f"Region: {n_lat}x{n_lon} = {n_lat*n_lon} cells")

# ===== Load target data =====
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

target_sst = np.zeros((len(target_dates), n_lat, n_lon), dtype=np.float64)
for i, d in enumerate(target_dates):
    fname = f"sst_{d.strftime('%Y%m%d')}.nc"
    fpath = os.path.join(data_dir, fname)
    ds = xr.open_dataset(fpath, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
    ds.close()
    if (i+1) % 10 == 0:
        print(f"Loaded {i+1}/{len(target_dates)} target files")

# Sea cells: finite on every target day
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")
print("Target data loaded successfully")

# Save for later use
np.save('/tmp/target_sst.npy', target_sst)
np.save('/tmp/sea_cells.npy', sea_cells)
np.save('/tmp/lat_idx.npy', lat_idx)
np.save('/tmp/lon_idx.npy', lon_idx)
