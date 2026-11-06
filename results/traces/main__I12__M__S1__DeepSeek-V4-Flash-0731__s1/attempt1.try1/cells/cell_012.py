
# Let's first load baseline data and save it to a numpy file for reuse
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, time

# Region indices
lat_start, lat_end = 130, 190
lon_start, lon_end = 78, 138
n_lat, n_lon = 60, 60

# Baseline dates: 1991-12-27 to 2003-01-05
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)

print(f"Loading {len(base_dates)} baseline files...")

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Load all baseline data
baseline_data = np.zeros((len(base_dates), n_lat, n_lon), dtype=np.float32)
t0 = time.time()
for i, bd in enumerate(base_dates):
    fname = f'sst_{bd.strftime("%Y%m%d")}.nc'
    fpath = os.path.join(data_dir, fname)
    ds = xr.open_dataset(fpath, engine='h5netcdf')
    baseline_data[i] = ds.analysed_sst.values[0, lat_start:lat_end, lon_start:lon_end]
    ds.close()
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{len(base_dates)} in {time.time()-t0:.1f}s")

print(f"Baseline data loaded in {time.time()-t0:.1f}s")
print(f"Shape: {baseline_data.shape}")
print(f"NaN count: {np.isnan(baseline_data).sum()}")

# Save for reuse
np.save('/tmp/baseline_data.npy', baseline_data)
print("Saved baseline data")
