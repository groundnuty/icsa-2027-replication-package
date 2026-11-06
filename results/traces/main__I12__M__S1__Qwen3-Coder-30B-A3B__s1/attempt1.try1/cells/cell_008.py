import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Define our region of interest
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75

# Define periods
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
TARGET_START = datetime(2009, 6, 1)
TARGET_END = datetime(2009, 8, 31)

def date_to_doy(date):
    """Convert date to day of year (1-366)"""
    # For the calculation we'll use a non-leap year approach
    # but handle Feb 29 specially
    if date.month == 2 and date.day == 29:
        return 60
    # Use a fixed year (non-leap) for consistency
    jan1 = datetime(2001, 1, 1)  # Non-leap year
    doy = (date - jan1).days + 1
    # For leap years, adjust accordingly
    if date.month > 2:  # After Feb 28
        doy += 1  # Add one day for leap year offset
    return doy

def doy_to_date(doy):
    """Convert day of year to date (assuming non-leap year)"""
    jan1 = datetime(2001, 1, 1)
    date = jan1 + timedelta(days=doy-1)
    return date

# Test the conversion
print("Testing DOY conversions:")
for i in [1, 59, 60, 61, 365, 366]:
    date = doy_to_date(i)
    converted_back = date_to_doy(date)
    print(f"DOY {i}: Date {date.strftime('%m-%d')}, back to DOY: {converted_back}")

# Let's examine a few sample files to understand data structure better
sample_files = [
    "/data/icsa2027_data_20261101T090944Z/s1z/sst_20000101.nc",
    "/data/icsa2027_data_20000228.nc",
    "/data/icsa2027_data_20000301.nc"
]

print("\nChecking sample files...")
for f in sample_files:
    try:
        if os.path.exists(f):
            ds = xr.open_dataset(f, engine="h5netcdf")
            print(f"File {os.path.basename(f)}: Shape {ds['analysed_sst'].shape}")
            ds.close()
        else:
            print(f"File {os.path.basename(f)}: Not found")
    except Exception as e:
        print(f"Error with {os.path.basename(f)}: {e}")