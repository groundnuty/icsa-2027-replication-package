import os
import glob
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# --- Configuration ---
dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'
target_start_str = '2019-06-01'
target_end_str = '2019-08-31'

def get_day_of_year(dt):
    """Custom day of year mapping as per requirements."""
    month = dt.month
    day = dt.day
    # Days in months for non-leap year
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    # If it's a leap year and we are after Feb 28, shift by 1
    # But the requirement says 29 Feb = 60 and 1 Mar = 61 regardless of year?
    # No, "Non-leap years have no day 60".
    # Let's re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366."
    # This means we are using a 366-day calendar.
    # In a leap year, Feb 29 is doy 60.
    # In a non-leap year, the day after Feb 28 (59) is Mar 1.
    # If we want Mar 1 to be 61, then non-leap years simply skip 60.
    # So we just need to check if it's a leap year and the date is after Feb 28.
    
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if is_leap and month > 2:
        # For leap years, the standard day of year is correct (Feb 29 is 60)
        # But we need to be careful.
        # Standard day of year:
        # Jan: 1-31
        # Feb: 32-59 (non-leap), 32-60 (leap)
        # Mar: 60 (non-leap), 61 (leap)
        pass
    
    # Simpler: use the standard pandas/datetime dayofyear and adjust
    # standard doy: Feb 29 is 60, Mar 1 is 60 (non-leap) or 61 (leap)
    # We want: Feb 29 = 60, Mar 1 = 61 (always)
    # So if non-leap and doy >= 60, doy = doy + 1
    standard_doy = dt.timetuple().tm_yday
    if not is_leap and standard_doy >= 60:
        return standard_doy + 1
    return standard_doy

# --- Data Loading ---
def load_sst_subset(start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start, end)
    
    sst_list = []
    times = []
    
    for dt in date_range:
        fname = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(fname):
            ds = xr.open_dataset(fname, engine="h5netcdf")
            # Subset the region
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_min, lat_max),
                longitude=slice(lon_min, lon_max)
            )
            sst_list.append(subset.values)
            times.append(dt)
            ds.close()
        else:
            # Handle missing files if necessary
            pass
            
    if not sst_list:
        return None, None
    
    # Create xarray DataArray
    # Note: we need the original coordinates
    ds_sample = xr.open_dataset(os.path.join(dataset_dir, f"sst_{date_range[0].strftime('%Y%m%d')}.nc"), engine="h5netcdf")
    lat = ds_sample.latitude.sel(latitude=slice(lat_min, lat_max))
    lon = ds_sample.longitude.sel(longitude=slice(lon_min, lon_max))
    ds_sample.close()
    
    sst_array = np.stack(sst_list, axis=0)
    da = xr.DataArray(
        sst_array,
        coords={'time': times, 'latitude': lat, 'longitude': lon},
        dims=['time', 'latitude', 'longitude'],
        name='sst'
    )
    return da

# Baseline windows: 1991-12-27 to 2003-01-05
baseline_data = load_sst_subset('1991-12-27', '2003-01-05', lat_min, lat_max, lon_min, lon_max)
# Target period: 2019-06-01 to 2019-08-31
target_data = load_sst_subset('2019-06-01', '2019-08-31', lat_min, lat_max, lon_min, lon_max)

if baseline_data is None or target_data is None:
    print("Error loading data")
    exit(1)

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")
