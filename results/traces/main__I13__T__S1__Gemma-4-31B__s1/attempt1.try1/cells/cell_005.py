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
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    
    coords = None
    
    for date in dates:
        filename = f"{root_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(filename, "rb") as f:
                with xr.open_dataset(f, engine="h5netcdf") as ds:
                    subset = ds.analysed_sst.sel(
                        latitude=slice(lat_min, lat_max), 
                        longitude=slice(lon_min, lon_max)
                    )
                    # Load the values immediately to avoid "file is closed" error
                    data = subset.values.astype(np.float64)
                    if coords is None:
                        coords = (ds.latitude.values, ds.longitude.values) # Wait, the subset has its own coords
                        # To be precise, get the coords of the subset
                        coords = (subset.latitude.values, subset.longitude.values)
                    
                    # Ensure we handle the time dimension (could be (1, lat, lon) or (lat, lon))
                    if data.ndim == 3:
                        data = data[0]
                    sst_list.append(data)
        except (FileNotFoundError, Exception) as e:
            # If first file fails, we don't have coords yet.
            # We'll handle this by filling with NaNs later.
            sst_list.append(None)
            
    # Find first valid entry to get dimensions
    first_val = next((x for x in sst_list if x is not None), None)
    if first_val is None:
        return None, None, None, dates
    
    lats, lons = coords # This was set when the first successful load happened
    # Actually, I should set coords based on the first_val if coords was not set yet
    # But the loop above already sets it. Let's double check.
    
    # Redefine coords from the first valid slice just in case
    # The coords should be consistent across files.
    # But if the first file was missing, coords would be None until first_val is found.
    # I'll fix the loop to set coords correctly.
    
    # Let's just use a simpler approach:
    # Find the first valid file to get the coords.
    
    final_sst = np.full((len(dates), first_val.shape[0], first_val.shape[1]), np.nan, dtype=np.float64)
    
    for i, val in enumerate(sst_list):
        if val is not None:
            if val.shape == first_val.shape:
                final_sst[i, :, :] = val
            else:
                # Shape mismatch - should not happen for the same region
                pass
                
    # Now we need the coordinates. We should have captured them from the first valid subset.
    # Let's just find the coordinates from any valid slice.
    # Since we can't easily return coords if all are None, I'll return them carefully.
    
    # Let's re-run this more robustly.
    return final_sst, lats, lons, dates

# Re-running with improved logic
fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 56.09, 57.29
lon_min, lon_max = 10.55, 11.75

def load_sst_region_fixed(fs, root_dir, start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    lats, lons = None, None
    
    for date in dates:
        filename = f"{root_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(filename, "rb") as f:
                with xr.open_dataset(f, engine="h5netcdf") as ds:
                    subset = ds.analysed_sst.sel(
                        latitude=slice(lat_min, lat_max), 
                        longitude=slice(lon_min, lon_max)
                    )
                    data = subset.values.astype(np.float64)
                    if lats is None:
                        lats = subset.latitude.values
                        lons = subset.longitude.values
                    if data.ndim == 3:
                        data = data[0]
                    sst_list.append(data)
        except Exception:
            sst_list.append(None)
            
    first_val = next((x for x in sst_list if x is not None), None)
    if first_val is None:
        return None, None, None, dates
    
    final_sst = np.full((len(dates), first_val.shape[0], first_val.shape[1]), np.nan, dtype=np.float64)
    for i, val in enumerate(sst_list):
        if val is not None and val.shape == first_val.shape:
            final_sst[i, :, :] = val
            
    return final_sst, lats, lons, dates

print("Loading baseline...")
baseline_sst, lats, lons, baseline_dates = load_sst_region_fixed(
    fs, root_dir, datetime(1991, 12, 27), datetime(2003, 1, 5), lat_min, lat_max, lon_min, lon_max
)
print("Loading target...")
target_sst, _, _, target_dates = load_sst_region_fixed(
    fs, root_dir, datetime(2021, 6, 1), datetime(2021, 8, 31), lat_min, lat_max, lon_min, lon_max
)
print("Loaded.")
print(f"Baseline shape: {baseline_sst.shape if baseline_sst is not None else 'None'}")
print(f"Target shape: {target_sst.shape if target_sst is not None else 'None'}")
