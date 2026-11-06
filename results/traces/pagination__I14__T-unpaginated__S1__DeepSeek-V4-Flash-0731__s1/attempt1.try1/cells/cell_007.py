
import fsspec
import numpy as np
import xarray as xr
from datetime import date, timedelta
import os

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Define region indices (from earlier exploration)
lat_start, lat_end = 132, 191  # inclusive
lon_start, lon_end = 436, 495  # inclusive

# Target period
target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)
n_target = len(target_dates)

# First, read all target data to identify sea cells
target_sst = np.zeros((n_target, 60, 60), dtype=np.float64)
for i, td in enumerate(target_dates):
    fname = f"sst_{td.strftime('%Y%m%d')}.nc"
    fpath = f"{base_dir}/{fname}"
    f = fs.open(fpath, "rb")
    ds = xr.open_dataset(f, engine="h5netcdf")
    target_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1].astype(np.float64)
    ds.close()
    f.close()

print(f"Target SST loaded, shape: {target_sst.shape}")

# Sea cells: finite on every target day
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_mask.sum()}/{sea_mask.size}")
print(f"Land cells: {sea_mask.size - sea_mask.sum()}")

# Save for later
np.save('target_sst.npy', target_sst)
np.save('sea_mask.npy', sea_mask)
