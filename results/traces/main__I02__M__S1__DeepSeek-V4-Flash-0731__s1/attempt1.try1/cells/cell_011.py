
import numpy as np
import os
import xarray as xr
from datetime import date, timedelta

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def load_region(date_obj):
    """Load the region data for a given date."""
    fname = f'sst_{date_obj.strftime("%Y%m%d")}.nc'
    path = os.path.join(data_dir, fname)
    ds = xr.open_dataset(path, engine='h5netcdf')
    data = ds['analysed_sst'].values[0, 34:94, 213:273].astype(np.float64)
    ds.close()
    return data

# Define all dates
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
target_start = date(2004, 6, 1)
target_end = date(2004, 8, 31)

# Load baseline data
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

# Load target data
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Load all baseline data
print("Loading baseline data...")
baseline_data = np.zeros((len(baseline_dates), 60, 60), dtype=np.float64)
for i, d in enumerate(baseline_dates):
    baseline_data[i] = load_region(d)
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{len(baseline_dates)}")

print(f"Baseline data loaded: {baseline_data.shape}")
print(f"Baseline NaN count: {np.isnan(baseline_data).sum()}")
print(f"Baseline finite count: {np.isfinite(baseline_data).sum()}")

# Load all target data
print("Loading target data...")
target_data = np.zeros((len(target_dates), 60, 60), dtype=np.float64)
for i, d in enumerate(target_dates):
    target_data[i] = load_region(d)
    if (i+1) % 20 == 0:
        print(f"  Loaded {i+1}/{len(target_dates)}")

print(f"Target data loaded: {target_data.shape}")
print(f"Target NaN count: {np.isnan(target_data).sum()}")
print(f"Target finite count: {np.isfinite(target_data).sum()}")
