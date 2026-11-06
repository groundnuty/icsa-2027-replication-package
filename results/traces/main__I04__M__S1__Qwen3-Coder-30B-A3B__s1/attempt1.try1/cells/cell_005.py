import xarray as xr
import numpy as np
from datetime import datetime

# Let's look at the date range in the dataset by checking a few files
base_path = "/data/icsa2027_data_20261101T090944Z/s1z"

# Get a sample of files to determine date range
import os
files = sorted([f for f in os.listdir(base_path) if f.startswith('sst_') and f.endswith('.nc')])
print(f"Found {len(files)} SST files")
print("Sample files:")
for i, f in enumerate(files[:10]):
    print(f"  {f}")

# Check first and last few files to estimate date range
if len(files) > 0:
    print("\nChecking first and last few files for date ranges:")
    
    # First file
    first_file = files[0]
    first_date = first_file.split('_')[1].replace('.nc', '')
    print(f"First file date: {first_date}")
    
    # Last file  
    last_file = files[-1]
    last_date = last_file.split('_')[1].replace('.nc', '')
    print(f"Last file date: {last_date}")