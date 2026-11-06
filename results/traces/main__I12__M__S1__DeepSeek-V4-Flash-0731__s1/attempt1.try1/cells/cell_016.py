
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# Load target data
target_start = date(2009, 6, 1)
target_end = date(2009, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

n_target = len(target_dates)
n_lat, n_lon = 60, 60

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
lat_start, lon_start = 130, 78

target_data = np.zeros((n_target, n_lat, n_lon), dtype=np.float32)
for i, td in enumerate(target_dates):
    fname = f'sst_{td.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(os.path.join(data_dir, fname), engine='h5netcdf')
    target_data[i] = ds.analysed_sst.values[0, lat_start:lat_start+60, lon_start:lon_start+60]
    ds.close()

print(f"Target data shape: {target_data.shape}")
print(f"NaN count: {np.isnan(target_data).sum()}")

# Identify sea cells: cells with finite SST on every target day
sea_cells = ~np.isnan(target_data).any(axis=0)  # shape (60, 60)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

np.save('/tmp/target_data.npy', target_data)
np.save('/tmp/sea_cells.npy', sea_cells)
print("Saved target data and sea cells")
