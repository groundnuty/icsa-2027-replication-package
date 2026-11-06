
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Load lat/lon indices
lat_idx = np.load('/tmp/lat_idx.npy')
lon_idx = np.load('/tmp/lon_idx.npy')
n_lat = len(lat_idx)
n_lon = len(lon_idx)

# Load baseline data
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

print(f"Loading {len(baseline_dates)} baseline files...")

# Load in chunks to avoid memory issues
# Let's load all baseline data for the region
baseline_sst = np.zeros((len(baseline_dates), n_lat, n_lon), dtype=np.float64)

for i, d in enumerate(baseline_dates):
    fname = f"sst_{d.strftime('%Y%m%d')}.nc"
    fpath = os.path.join(data_dir, fname)
    ds = xr.open_dataset(fpath, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
    ds.close()
    if (i+1) % 500 == 0:
        print(f"Loaded {i+1}/{len(baseline_dates)} baseline files")

print("All baseline data loaded")
np.save('/tmp/baseline_sst.npy', baseline_sst)
np.save('/tmp/baseline_dates.npy', np.array([d.toordinal() for d in baseline_dates]))

# Verify
print(f"Baseline data shape: {baseline_sst.shape}")
print(f"NaN count: {np.isnan(baseline_sst).sum()}")
