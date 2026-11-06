import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Set up filesystem
fs = fsspec.filesystem('onedata')

# Let's find all the files for our target period (2004-06-01 to 2004-08-31)
dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Get all files and filter for the right dates
all_files = fs.ls(dataset_dir)
sst_files_2004 = [f for f in all_files if 'sst_2004' in f]

print(f"Found {len(sst_files_2004)} files for 2004")

# Also check what years we have available for baseline (1992-2002)
baseline_files = [f for f in all_files if any(str(year) in f for year in range(1992, 2003))]
print(f"Found {len(baseline_files)} files for baseline years (1992-2002)")

# Let's look at a few baseline files to make sure they're consistent
if baseline_files:
    print("Sample baseline files:")
    for i, f in enumerate(baseline_files[:3]):
        print(f"  {f}")

# And a few 2004 files
if sst_files_2004:
    print("Sample 2004 files:")
    for i, f in enumerate(sst_files_2004[:3]):
        print(f"  {f}")