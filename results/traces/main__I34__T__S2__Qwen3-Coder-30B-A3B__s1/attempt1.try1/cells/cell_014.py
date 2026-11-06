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

# Correct approach to convert numpy datetime64 to Python datetime
def correct_doy_conversion(dt64):
    """Convert numpy datetime64 to day of year correctly"""
    # Method 1: Use pandas for conversion (if available)
    try:
        import pandas as pd
        pd_dt = pd.Timestamp(dt64)
        doy = pd_dt.dayofyear
        # Adjust for leap year special case
        if pd_dt.month > 2 and pd_dt.is_leap_year:
            doy -= 1
        return doy
    except:
        pass
    
    # Method 2: Manual conversion
    # Extract year, month, day manually from datetime64
    year = int(str(dt64)[:4])
    month = int(str(dt64)[5:7])
    day = int(str(dt64)[8:10])
    
    # Create Python datetime
    py_dt = datetime(year, month, day)
    doy = py_dt.timetuple().tm_yday
    
    # Adjust for leap year if needed
    if month > 2 and ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)):
        # Leap year and after Feb 29
        if doy > 60:
            doy -= 1
            
    return doy

# Test the corrected approach
test_date = np.datetime64('2000-02-29')  # A leap year date
doy = correct_doy_conversion(test_date)
print(f"Test date {test_date} -> DOY: {doy}")

test_date2 = np.datetime64('2001-02-28')  # A non-leap year date
doy2 = correct_doy_conversion(test_date2)
print(f"Test date {test_date2} -> DOY: {doy2}")

# Test with actual data
print("\nTesting with actual baseline data...")
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
baseline_time_indices = np.where((ds.time >= baseline_start) & (ds.time <= baseline_end))[0]
ds_baseline = ds.isel(time=baseline_time_indices[:5])  # Just first 5 for testing

for i in range(len(ds_baseline.time)):
    val = ds_baseline.time[i].values
    doy = correct_doy_conversion(val)
    print(f"  {i}: {val} -> DOY: {doy}")