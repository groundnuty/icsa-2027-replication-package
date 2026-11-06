import os
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import json

# Constants
BASE_DIR = "/data/icsa2027_data_20261101T090944Z/s1z"
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75
TARGET_START = "2021-06-01"
TARGET_END = "2021-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

def get_day_of_year(dt):
    """Map every date to a day of year from 1 to 366.
    1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366.
    Non-leap years have no day 60.
    """
    # Use pandas Timedelta to handle leap years correctly
    # The problem defines day 60 as Feb 29.
    # For non-leap years, the date after Feb 28 is March 1, which is day 61.
    # This is exactly what dt.timetuple().tm_yday provides, but we must be careful.
    # Pandas.dt.dayofyear is 1-indexed and handles this:
    # In 2021 (non-leap), Feb 28 is 59, Mar 1 is 60. Wait.
    # Let's check:
    # 2021-02-28: dayofyear = 59
    # 2021-03-01: dayofyear = 60 (But the prompt says March 1 is 61)
    # Ah, the prompt says: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61".
    # This implies a fixed 366-day calendar where day 60 always corresponds to Feb 29.
    # So for non-leap years, we skip day 60.
    # Let's implement this manually.
    
    # A simple way: 
    # Create a date in a leap year (e.g. 2000) with the same month and day.
    # The day of year of that date in 2000 is the required day of year.
    try:
        leap_date = datetime(2000, dt.month, dt.day)
        return leap_date.timetuple().tm_yday
    except ValueError:
        # This handles Feb 29 in non-leap years (though dt shouldn't be Feb 29)
        return 60

def get_sst_for_range(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    data_list = []
    coords = None
    
    for dt in dates:
        filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            # If a file is missing, we might need to handle it.
            # But the prompt implies the dataset exists.
            print(f"Warning: File {filename} missing.")
            # To keep it simple, we'll use a dataset with NaNs
            if coords is not None:
                ds_nan = xr.Dataset({
                    'analysed_sst': (('time', 'latitude', 'longitude'), np.full((1, coords['lat'].size, coords['lon'].size), np.nan))
                }, coords={'time': [dt], 'latitude': coords['lat'], 'longitude': coords['lon']})
                data_list.append(ds_nan)
            continue
            
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            # Subset to region
            subset = ds.analysed_sst.sel(
                latitude=slice(LAT_MIN, LAT_MAX), 
                longitude=slice(LON_MIN, LON_MAX)
            )
            if coords is None:
                coords = {'lat': subset.latitude, 'lon': subset.longitude}
            data_list.append(subset.to_array().expand_dims('time')) # this is not quite right
            # Correct way to handle single variable:
            # data_list.append(subset)
    
    # Wait, xarray.open_mfdataset would be better, but it might be slow.
    # Let's just open them and concatenate.
    return data_list, coords

# Let's refine the loading.
