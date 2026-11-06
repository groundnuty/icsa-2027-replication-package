
import xarray as xr
import numpy as np
import os
import datetime

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Baseline range
base_start = datetime.date(1991, 12, 27)
base_end = datetime.date(2003, 1, 5)

# Build list of baseline dates
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += datetime.timedelta(days=1)
print(f"Baseline dates: {len(base_dates)} days")

# Load the region indices
lat_idx = np.load('lat_idx.npy')
lon_idx = np.load('lon_idx.npy')

# Load baseline data
# We'll load in batches to be efficient
import h5netcdf

# Let's try loading all baseline data for the region
baseline_sst = np.full((len(base_dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float64)

for i, date in enumerate(base_dates):
    fname = f"sst_{date.strftime('%Y%m%d')}.nc"
    path = os.path.join(data_dir, fname)
    try:
        with xr.open_dataset(path, engine='h5netcdf') as ds:
            sst_region = ds['analysed_sst'].isel(time=0, latitude=lat_idx, longitude=lon_idx).values
            baseline_sst[i] = sst_region.astype(np.float64)
    except Exception as e:
        print(f"Error loading {fname}: {e}")
        baseline_sst[i] = np.nan

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"NaN count: {np.isnan(baseline_sst).sum()}")
print(f"Finite count: {np.isfinite(baseline_sst).sum()}")

np.save('baseline_sst.npy', baseline_sst)
np.save('base_dates.npy', np.array([d.toordinal() for d in base_dates]))
print("Saved baseline data")
