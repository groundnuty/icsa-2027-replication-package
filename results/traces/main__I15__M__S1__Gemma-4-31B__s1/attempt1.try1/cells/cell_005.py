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
    """
    Map every date to a day of year from 1 to 366:
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    standard_doy = dt.timetuple().tm_yday
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and standard_doy >= 60:
        return standard_doy + 1
    return standard_doy

def load_sst_subset(start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start, end)
    
    sst_list = []
    times = []
    
    for dt in date_range:
        fname = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(fname):
            with xr.open_dataset(fname, engine="h5netcdf") as ds:
                subset = ds.analysed_sst.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                # subset is (time:1, lat, lon). We want (lat, lon)
                sst_list.append(subset.values[0])
                times.append(dt)
        else:
            # If a file is missing, we can't just skip it if we want a contiguous time axis.
            # However, the requirement says "SST is finite on every day of the target period" 
            # for sea cells. For baseline, we just pool.
            # To be safe, let's add NaNs if file is missing.
            # We need the shapes from another file.
            pass
            
    if not sst_list:
        return None, None

    # To handle missing files correctly, we should find the shape first
    # or use the first available file to define the coordinates.
    first_file = os.path.join(dataset_dir, f"sst_{date_range[0].strftime('%Y%m%d')}.nc")
    # If first file is missing, find the first existing one.
    if not os.path.exists(first_file):
        for dt in date_range:
            f = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
            if os.path.exists(f):
                first_file = f
                break
    
    with xr.open_dataset(first_file, engine="h5netcdf") as ds:
        lat = ds.latitude.sel(latitude=slice(lat_min, lat_max))
        lon = ds.longitude.sel(longitude=slice(lon_min, lon_max))
        n_lat, n_lon = len(lat), len(lon)

    # Re-process to ensure all dates are present (with NaNs if missing)
    final_sst = []
    final_times = []
    for dt in date_range:
        fname = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(fname):
            with xr.open_dataset(fname, engine="h5netcdf") as ds:
                subset = ds.analysed_sst.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                val = subset.values[0]
                # It's possible the subset shape is different if the file is weird, 
                # but should be consistent.
                final_sst.append(val)
                final_times.append(dt)
        else:
            final_sst.append(np.full((n_lat, n_lon), np.nan))
            final_times.append(dt)

    sst_array = np.stack(final_sst, axis=0).astype(np.float64)
    da = xr.DataArray(
        sst_array,
        coords={'time': final_times, 'latitude': lat, 'longitude': lon},
        dims=['time', 'latitude', 'longitude'],
        name='sst'
    )
    return da

# Baseline windows include 5 days beyond 1992-01-01 and 2002-12-31.
# 1992-01-01 minus 5 days = 1991-12-27
# 2002-12-31 plus 5 days = 2003-01-05
baseline_data = load_sst_subset('1991-12-27', '2003-01-05', lat_min, lat_max, lon_min, lon_max)
target_data = load_sst_subset('2019-06-01', '2019-08-31', lat_min, lat_max, lon_min, lon_max)

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")
