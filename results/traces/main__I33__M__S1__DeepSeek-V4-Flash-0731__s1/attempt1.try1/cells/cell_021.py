
import h5py
import numpy as np
import os
from datetime import datetime, timedelta

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

lat_idx = slice(278, 338)
lon_idx = slice(613, 673)

# Load target data
target_start = datetime(2014, 6, 1)
target_end = datetime(2014, 8, 31)

target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Load all target SST data
target_sst = np.zeros((len(target_dates), 60, 60), dtype=np.float32)
for i, td in enumerate(target_dates):
    date_str = td.strftime('%Y%m%d')
    filepath = f'{data_dir}/sst_{date_str}.nc'
    with h5py.File(filepath, 'r') as f:
        target_sst[i] = f['analysed_sst'][0, lat_idx, lon_idx]

print(f"Target SST shape: {target_sst.shape}")
print(f"Finite values: {np.isfinite(target_sst).sum()} / {target_sst.size}")

# Determine sea cells: finite SST on every day of target period
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} / {60*60}")

# Save target data and sea cells
np.save('output/target_sst.npy', target_sst)
np.save('output/sea_cells.npy', sea_cells)
np.save('output/target_dates.npy', np.array(target_dates, dtype='datetime64[ns]'))
print("Saved target data")
