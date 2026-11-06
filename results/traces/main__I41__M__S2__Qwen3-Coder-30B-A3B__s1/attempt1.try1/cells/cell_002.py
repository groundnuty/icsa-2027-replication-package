import xarray as xr
import numpy as np

# Try to open the dataset
try:
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    print("Dataset opened successfully")
    print(ds)
except Exception as e:
    print(f"Error opening dataset: {e}")

# Check what's in the directory
import os
print("\nDirectory structure:")
for root, dirs, files in os.walk('/data/icsa2027_data_20261101T090944Z'):
    level = root.replace('/data/icsa2027_data_20261101T090944Z', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    if files:
        subindent = ' ' * 2 * (level + 1)
        for file in files[:3]:  # Show only first 3 files
            print(f"{subindent}{file}")
        if len(files) > 3:
            print(f"{subindent}... and {len(files)-3} more files")