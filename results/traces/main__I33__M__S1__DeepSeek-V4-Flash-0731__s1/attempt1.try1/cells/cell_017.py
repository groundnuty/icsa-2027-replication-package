
import h5py
import numpy as np
import os
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Fixed day-of-year mapping
starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy(month, day):
    return starts[month] + day

# Region indices
lat_idx = slice(278, 338)  # 278-337 inclusive
lon_idx = slice(613, 673)  # 613-672 inclusive

# Data range for baseline
data_start = datetime(1991, 12, 27)
data_end = datetime(2003, 1, 5)

# Build pool membership
doy_pool_dates = defaultdict(set)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

d = baseline_start
while d <= baseline_end:
    d_doy = doy(d.month, d.day)
    if d_doy != 60:
        for delta in range(-5, 6):
            date_in_pool = d + timedelta(days=delta)
            if data_start <= date_in_pool <= data_end:
                doy_pool_dates[d_doy].add(date_in_pool)
    d += timedelta(days=1)

# Build reverse mapping
date_to_doy_pools = defaultdict(list)
for d_doy, dates in doy_pool_dates.items():
    for dt in dates:
        date_to_doy_pools[dt].append(d_doy)

# Load all baseline data and add to pools
pool_values = defaultdict(list)

start_time = time.time()
d = data_start
count = 0
while d <= data_end:
    date_str = d.strftime('%Y%m%d')
    filepath = f'{data_dir}/sst_{date_str}.nc'
    
    with h5py.File(filepath, 'r') as f:
        sst = f['analysed_sst'][0, lat_idx, lon_idx]
    
    for d_doy in date_to_doy_pools.get(d, []):
        pool_values[d_doy].append(sst.copy())
    
    d += timedelta(days=1)
    count += 1

elapsed = time.time() - start_time
print(f"Loaded {count} baseline days in {elapsed:.1f} seconds")

# Save pool values to disk for later use
os.makedirs('output', exist_ok=True)
with open('output/pool_values.pkl', 'wb') as f:
    import pickle
    pickle.dump(dict(pool_values), f)
print("Saved pool values")
