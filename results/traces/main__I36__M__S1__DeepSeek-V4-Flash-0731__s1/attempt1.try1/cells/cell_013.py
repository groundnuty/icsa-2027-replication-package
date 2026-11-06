
import os
import re
import numpy as np
import h5py
from datetime import date, timedelta
import time

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Region indices
lat_min_val, lat_max_val = 60.09, 61.29
lon_min_val, lon_max_val = 20.01, 21.21

# Get coordinates from one file
f0 = os.path.join(base_dir, 'sst_20030601.nc')
with h5py.File(f0, 'r') as h5:
    lat = h5['latitude'][:]
    lon = h5['longitude'][:]
lat_idx = np.where((lat >= lat_min_val) & (lat <= lat_max_val))[0]
lon_idx = np.where((lon >= lon_min_val) & (lon <= lon_max_val))[0]
print(f"lat_idx: {lat_idx[0]} to {lat_idx[-1]}, count: {len(lat_idx)}")
print(f"lon_idx: {lon_idx[0]} to {lon_idx[-1]}, count: {len(lon_idx)}")

# Build list of all dates
all_dates = {}
for f in os.listdir(base_dir):
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        all_dates[d] = os.path.join(base_dir, f)

# Baseline window dates
baseline_dates = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    baseline_dates.append(d)
    d += timedelta(days=1)

# Read baseline data using h5py
start_time = time.time()
# Store as a big array: (n_days, 60, 60)
n_days = len(baseline_dates)
baseline_data = np.zeros((n_days, len(lat_idx), len(lon_idx)), dtype=np.float64)

for i, d in enumerate(baseline_dates):
    if d in all_dates:
        with h5py.File(all_dates[d], 'r') as h5:
            baseline_data[i] = h5['analysed_sst'][0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    if (i+1) % 500 == 0:
        elapsed = time.time() - start_time
        print(f"Read {i+1}/{n_days}, elapsed: {elapsed:.1f}s")

print(f"Done reading baseline. Total time: {time.time()-start_time:.1f}s")
print(f"Baseline data shape: {baseline_data.shape}")

# Save to disk
np.save('/tmp/baseline_data.npy', baseline_data)
# Also save the date mapping
with open('/tmp/baseline_dates.txt', 'w') as f:
    for d in baseline_dates:
        f.write(f"{d.isoformat()}\n")
print("Saved baseline data")
