import xarray as xr
import numpy as np
from datetime import datetime

# First let's test the date conversion logic
def test_date_conversion():
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
            dt = t.astype(datetime)
            print(f"Converted to datetime: {dt}")
            print(f"Month: {dt.month}, Day: {dt.day}")
        except Exception as e:
            print(f"Error converting: {e}")

test_date_conversion()