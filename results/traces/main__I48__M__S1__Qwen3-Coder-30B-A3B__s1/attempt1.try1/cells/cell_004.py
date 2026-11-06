import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Let's try to load a broader range of data to understand the temporal coverage
start_date = datetime(2016, 6, 1)
end_date = datetime(2016, 8, 31)

# Get all files for the target period
import os
base_dir = "/data/icsa2027_data_20261101T090944Z/s1z"
files = []

for filename in sorted(os.listdir(base_dir)):
    if filename.startswith('sst_') and filename.endswith('.nc'):
        # Extract date from filename
        date_str = filename[4:-3]  # Remove 'sst_' prefix and '.nc' suffix
        try:
            file_date = datetime.strptime(date_str, '%Y%m%d')
            if start_date <= file_date <= end_date:
                files.append((file_date, filename))
        except ValueError:
            continue

print(f"Found {len(files)} files for target period")
files.sort()

# Also check baseline period files
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

baseline_files = []
for filename in sorted(os.listdir(base_dir)):
    if filename.startswith('sst_') and filename.endswith('.nc'):
        # Extract date from filename
        date_str = filename[4:-3]  # Remove 'sst_' prefix and '.nc' suffix
        try:
            file_date = datetime.strptime(date_str, '%Y%m%d')
            if baseline_start <= file_date <= baseline_end:
                baseline_files.append((file_date, filename))
        except ValueError:
            continue

print(f"Found {len(baseline_files)} files for baseline period")

# Test loading one file
if files:
    test_file = files[0][1]
    test_path = os.path.join(base_dir, test_file)
    print(f"Testing with file: {test_file}")
    
    ds = xr.open_dataset(test_path, engine="h5netcdf")
    print(f"Time dimension: {ds.time.values}")
    print(f"SST variable shape: {ds.analysed_sst.shape}")
    print(f"Latitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
    print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")