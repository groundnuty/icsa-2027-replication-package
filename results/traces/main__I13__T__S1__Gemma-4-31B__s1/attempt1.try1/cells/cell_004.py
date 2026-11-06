import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_doy(date):
    # date is a datetime object
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61...
    # Non-leap years have no day 60.
    doy = date.timetuple().tm_yday
    is_leap = (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0))
    if not is_leap and doy >= 60:
        doy += 1
    return doy

def load_sst_region(fs, root_dir, start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    # start_date and end_date are datetime objects
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    
    # To avoid too many open files and optimize, we can load each file and slice
    for date in dates:
        filename = f"{root_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(filename, "rb") as f:
                with xr.open_dataset(f, engine="h5netcdf") as ds:
                    # Slice the region
                    subset = ds.analysed_sst.sel(
                        latitude=slice(lat_min, lat_max), 
                        longitude=slice(lon_min, lon_max)
                    )
                    sst_list.append(subset)
        except FileNotFoundError:
            # Handle missing files by adding NaNs if necessary
            # But the prompt says "SST is finite on every day of the target period" for sea cells
            # For baseline, we can just ignore missing dates or add NaNs.
            # Let's add a NaN array of the correct shape.
            # We'll get the shape from the first successful load.
            sst_list.append(None)
            
    # Now we need to align these. 
    # Let's find the first non-None to get coords.
    first_val = next((x for x in sst_list if x is not None), None)
    if first_val is None:
        return None
    
    lats = first_val.latitude.values
    lons = first_val.longitude.values
    
    final_sst = np.full((len(dates), len(lats), len(lons)), np.nan, dtype=np.float64)
    
    for i, val in enumerate(sst_list):
        if val is not None:
            # Ensure it matches the shape
            if val.shape == (1, len(lats), len(lons)):
                final_sst[i, :, :] = val.values[0]
            elif val.shape == (len(lats), len(lons)):
                final_sst[i, :, :] = val.values
            else:
                # This might happen if the grid changes slightly, but usually it's constant
                # We'll just skip or handle if needed.
                pass
                
    return final_sst, lats, lons, dates

# Parameters
lat_min, lat_max = 56.09, 57.29
lon_min, lon_max = 10.55, 11.75
target_start = datetime(2021, 6, 1)
target_end = datetime(2021, 8, 31)
baseline_start_bound = datetime(1991, 12, 27)
baseline_end_bound = datetime(2003, 1, 5)

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Load baseline data
print("Loading baseline data...")
baseline_sst, lats, lons, baseline_dates = load_sst_region(
    fs, root_dir, baseline_start_bound, baseline_end_bound, lat_min, lat_max, lon_min, lon_max
)

# Load target data
print("Loading target data...")
target_sst, _, _, target_dates = load_sst_region(
    fs, root_dir, target_start, target_end, lat_min, lat_max, lon_min, lon_max
)

print("Data loaded.")
print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")
