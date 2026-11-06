
import os
import re
import numpy as np
import h5py
from datetime import date, timedelta
import time

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Region indices (same as before)
lat_min_val, lat_max_val = 60.09, 61.29
lon_min_val, lon_max_val = 20.01, 21.21

# Get coordinates from one file
f0 = os.path.join(base_dir, 'sst_20030601.nc')
with h5py.File(f0, 'r') as h5:
    lat = h5['latitude'][:]
    lon = h5['longitude'][:]
lat_idx = np.where((lat >= lat_min_val) & (lat <= lat_max_val))[0]
lon_idx = np.where((lon >= lon_min_val) & (lon <= lon_max_val))[0]

# Build date-to-file mapping
all_dates = {}
for f in os.listdir(base_dir):
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        all_dates[d] = os.path.join(base_dir, f)

# Target dates
target_dates = []
d = date(2003, 6, 1)
while d <= date(2003, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Target dates: {len(target_dates)}, from {target_dates[0]} to {target_dates[-1]}")

# Read target data
start_time = time.time()
target_data = np.zeros((len(target_dates), len(lat_idx), len(lon_idx)), dtype=np.float64)
for i, d in enumerate(target_dates):
    if d in all_dates:
        with h5py.File(all_dates[d], 'r') as h5:
            target_data[i] = h5['analysed_sst'][0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    else:
        print(f"Warning: missing target date {d}")

print(f"Read target data: {time.time()-start_time:.1f}s")
print(f"Target data shape: {target_data.shape}")

# Determine sea cells: cells with finite SST on every day of target period
sea_cells = ~np.isnan(target_data).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# Save
np.save('/tmp/target_data.npy', target_data)
np.save('/tmp/sea_cells.npy', sea_cells)
with open('/tmp/target_dates.txt', 'w') as f:
    for d in target_dates:
        f.write(f"{d.isoformat()}\n")
print("Saved target data")
