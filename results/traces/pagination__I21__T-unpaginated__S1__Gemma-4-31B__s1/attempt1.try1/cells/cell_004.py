import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_day_of_year(dt):
    """Map date to day of year from 1 to 366."""
    # Using a simple mapping
    # Jan: 1-31
    # Feb: 32-59 (non-leap) or 32-60 (leap)
    # Mar: 61-91 ...
    # But the prompt says: 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61
    # This is precisely the day-of-year in a leap year.
    # For non-leap years, Feb 28 is 59 and Mar 1 is 61.
    # We can use pd.Timestamp.dayofyear but we must check if it's a leap year.
    # Actually, pd.Timestamp.dayofyear is always 1-366.
    # In a non-leap year, Feb 28 is 59 and Mar 1 is 60? No, pd.Timestamp('2021-03-01').dayofyear is 60.
    # Let's double check:
    # 2021-02-28: 59
    # 2021-03-01: 60 (pd.Timestamp)
    # But the prompt says 1 March = 61.
    # So we need a custom mapping.
    month = dt.month
    day = dt.day
    days_in_months = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # The prompt defines a fixed mapping:
    # 1 Jan = 1
    # 28 Feb = 59
    # 29 Feb = 60
    # 1 Mar = 61
    # This is just the leap-year dayofyear.
    # For any date, we calculate the day of year as if it were a leap year.
    
    # Use a leap year like 2000 to get the mapping
    temp_date = datetime(2000, month, day)
    return temp_date.timetuple().tm_yday

# Parameters
lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23
target_start = pd.to_datetime("2021-06-01")
target_end = pd.to_datetime("2021-08-31")
baseline_start = pd.to_datetime("1992-01-01")
baseline_end = pd.to_datetime("2002-12-31")

# We need SST for baseline windows and target period.
# Baseline windows range from baseline_start - 5 days to baseline_end + 5 days.
data_start = baseline_start - timedelta(days=5)
data_end = baseline_end + timedelta(days=5)
# Also target period.
# Since baseline and target are far apart, we'll load them separately.

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

def load_sst_region(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    valid_dates = []
    
    for d in dates:
        date_str = d.strftime("%Y%m%d")
        file_path = f"{root_dir}/sst_{date_str}.nc"
        try:
            with fs.open(file_path, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Slice the region
                # Using .sel with slice can be slow or imprecise if coords aren't exactly as expected
                # Better use the indices we found earlier or just .sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                # Actually, the prompt says "grid cells with latitude from 57.33 to 58.53 and longitude from 9.03 to 10.23, bounds inclusive."
                region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                # Wait, if the coords are decreasing, slice(lat_min, lat_max) will be empty.
                # Let's check coords.
                if region_ds.latitude.size == 0:
                    region_ds = ds.sel(latitude=slice(lat_max, lat_min), longitude=slice(lon_min, lon_max))
                
                # Extract the variable and convert to float64
                sst_val = region_ds.analysed_sst.values.astype(np.float64)
                # analysed_sst is (time, lat, lon), we only have time=1
                sst_list.append(sst_val[0])
                valid_dates.append(d)
        except Exception as e:
            # print(f"Error loading {file_path}: {e}")
            pass
            
    return np.array(sst_list), np.array(valid_dates), \
           xr.open_dataset(f"{root_dir}/sst_{dates[0].strftime('%Y%m%d')}.nc", engine="h5netcdf", 
                           # We just need the coords
                           drops_variables=['analysed_sst']).sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max)) 
           # Note: the above is a bit buggy, will fix it in the main script.

# Correcting the loading function for a real run
