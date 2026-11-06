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

# Test exactly what happens with the first few time values
print("Checking first few time values in baseline data...")
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
baseline_time_indices = np.where((ds.time >= baseline_start) & (ds.time <= baseline_end))[0]
ds_baseline = ds.isel(time=baseline_time_indices[:5])  # Just first 5 for testing

print("First 5 time values:")
for i in range(len(ds_baseline.time)):
    val = ds_baseline.time[i].values
    print(f"  {i}: {val} (type: {type(val)})")
    
    # Try to process it
    try:
        if hasattr(val, 'astype'):
            py_dt = val.astype(datetime)
            print(f"    Converted to: {py_dt}")
            doy = py_dt.timetuple().tm_yday
            print(f"    DOY: {doy}")
        else:
            print(f"    No astype method")
    except Exception as e:
        print(f"    Error: {e}")