import xarray as xr
import numpy as np
from datetime import datetime

# Fix the date conversion function
def day_of_year(date_obj):
    """Convert a date to day of year (1-366)"""
    # Handle numpy datetime64 objects
    if isinstance(date_obj, np.datetime64):
        # Convert numpy datetime64 to Python datetime
        dt = date_obj.astype(datetime)
    elif isinstance(date_obj, datetime):
        dt = date_obj
    else:
        # Assume it's a string or other format
        dt = datetime.strptime(str(date_obj), '%Y-%m-%d')
    
    # Handle leap years properly
    if dt.month == 2 and dt.day == 29:
        return 60
    # Create a date for Jan 1 of the same year to calculate DOY
    jan1 = datetime(dt.year, 1, 1)
    return (dt - jan1).days + 1

# Test the fixed function
def test_fixed_date_conversion():
    # Open the dataset
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

    # Define our target period
    target_start = np.datetime64('2008-06-01')
    target_end = np.datetime64('2008-08-31')

    # Get all time indices within our target period
    time_indices = np.where((ds.time >= target_start) & (ds.time <= target_end))[0]

    # Get a few sample times to test
    sample_times = ds.time.isel(time=time_indices[:5]).values
    print("Sample times:", sample_times)
    
    for i, t in enumerate(sample_times):
        print(f"Time {i}: {t}")
        print(f"Type: {type(t)}")
        # Test conversion
        try:
            doy = day_of_year(t)
            print(f"Day of year: {doy}")
        except Exception as e:
            print(f"Error computing DOY: {e}")

test_fixed_date_conversion()