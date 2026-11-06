
import fsspec
import xarray as xr
import numpy as np
import datetime

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Define region indices
lat_start, lat_end = 48, 108  # inclusive: 48 to 107
lon_start, lon_end = 353, 413  # inclusive: 353 to 412

# Load target period data
target_start = datetime.date(2021, 6, 1)
target_end = datetime.date(2021, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

print(f"Target period: {target_start} to {target_end}, {len(target_dates)} days")

# Load target SST data
target_sst = np.zeros((len(target_dates), lat_end-lat_start, lon_end-lon_start), dtype=np.float32)
for i, date in enumerate(target_dates):
    path = f'{base}/sst_{date.strftime("%Y%m%d")}.nc'
    with fs.open(path, 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        target_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end, lon_start:lon_end]

print(f"Target SST shape: {target_sst.shape}")
print(f"NaN count: {np.isnan(target_sst).sum()}")

# Identify sea cells: cells with finite SST on every target day
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# Save for later
np.save('/tmp/target_sst.npy', target_sst)
np.save('/tmp/sea_cells.npy', sea_cells)

# Print target dates as ISO strings
print("Target dates:", [d.strftime('%Y-%m-%d') for d in target_dates[:5]], "...")
