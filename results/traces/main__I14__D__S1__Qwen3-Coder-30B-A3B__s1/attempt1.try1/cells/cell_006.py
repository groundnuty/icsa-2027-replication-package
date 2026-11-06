import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os

# First, let's download a couple of files to understand the structure
fs = fsspec.filesystem('onedata')

# Download first few files
for i, remote_path in enumerate(fs.ls('/icsa2027_data_20261101T090944Z/s1z/')[:5]):
    local_path = f'/work/{os.path.basename(remote_path)}'
    fs.get(remote_path, local_path)
    print(f"Downloaded {local_path}")

# Now let's examine the time range by looking at the filenames
filenames = fs.ls('/icsa2027_data_20261101T090944Z/s1z/')
dates = []
for fname in filenames:
    # Extract date from filename sst_YYYYMMDD.nc
    date_str = fname.split('_')[-1].split('.')[0]  # Gets YYYYMMDD part
    dates.append(datetime.strptime(date_str, '%Y%m%d'))

print(f"Date range: {min(dates)} to {max(dates)}")
print(f"Total days: {len(dates)}")

# Let's also check what the region looks like
first_file = '/work/sst_19820101.nc'
ds = xr.open_dataset(first_file, engine='h5netcdf')
print("\nFirst file coordinates:")
print("Latitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
print("Shape:", ds.analysed_sst.shape)
ds.close()