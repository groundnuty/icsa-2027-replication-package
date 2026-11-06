
import xarray as xr
import numpy as np
import os

# List all files
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(f"Total files: {len(files)}")
print(f"First few: {files[:5]}")
print(f"Last few: {files[-5:]}")

# Check date range from filenames
dates = [f.replace('sst_','').replace('.nc','') for f in files]
print(f"First date: {dates[0]}")
print(f"Last date: {dates[-1]}")
