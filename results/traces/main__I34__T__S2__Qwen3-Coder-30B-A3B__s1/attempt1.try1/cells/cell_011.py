import fsspec
import xarray as xr
import numpy as np
from datetime import datetime

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Let's debug what the time values actually are
print("First few time values:")
for i in range(5):
    val = ds.time[i].values
    print(f"  {i}: {val} (type: {type(val)})")

# Try to understand the datetime conversion better
print("\nTrying to convert manually:")
dt_val = ds.time[0].values
print(f"Value: {dt_val}")
print(f"Type: {type(dt_val)}")

# Check if it's already a datetime object
if hasattr(dt_val, 'timetuple'):
    print("Has timetuple method")
else:
    print("Does not have timetuple method")

# Try converting to datetime
try:
    dt_converted = dt_val.astype(datetime)
    print(f"Converted successfully: {dt_converted}")
except Exception as e:
    print(f"Conversion failed: {e}")
    
# Let's try a different approach
print("\nDirect conversion test:")
test_date = np.datetime64('2000-01-01')
print(f"Test date: {test_date}")
print(f"Test date type: {type(test_date)}")

# Convert to Python datetime
dt_python = test_date.astype(datetime)
print(f"Python datetime: {dt_python}")
print(f"Day of year: {dt_python.timetuple().tm_yday}")