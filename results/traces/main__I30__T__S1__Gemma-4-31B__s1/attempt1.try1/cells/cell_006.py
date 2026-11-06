import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def get_doy(date):
    month = date.month
    day = date.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89
target_start = pd.to_datetime('2010-06-01')
target_end = pd.to_datetime('2010-08-31')
baseline_data_start = pd.to_datetime('1991-12-27')
baseline_data_end = pd.to_datetime('2003-01-05')

def load_sst_range(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords_lat = None
    coords_lon = None
    
    for d in dates:
        file_path = f"{base_path}/sst_{d.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                lat_mask = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
                lon_mask = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                
                if coords_lat is None:
                    coords_lat = ds.latitude.values[lat_mask]
                    coords_lon = ds.longitude.values[lon_mask]
                
                sst_list.append(sst_val)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            if coords_lat is not None:
                sst_list.append(np.full(coords_lat.shape[0] if coords_lat is not None else 60, 
                                        np.nan)) # This is wrong, should be 2D
    
    # To be safe, let's ensure everything is 2D
    # The previous code had a bug in the exception handler.
    return np.array(sst_list, dtype=np.float64), coords_lat, coords_lon

# Let's fix the load_sst_range and run again
def load_sst_range_fixed(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords_lat = None
    coords_lon = None
    
    for d in dates:
        file_path = f"{base_path}/sst_{d.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                lat_mask = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
                lon_mask = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
                sst_val = ds.analysed_sst.values[0, lat_mask, lon_mask]
                if coords_lat is None:
                    coords_lat = ds.latitude.values[lat_mask]
                    coords_lon = ds.longitude.values[lon_mask]
                sst_list.append(sst_val)
        except Exception as e:
            # print(f"Error loading {file_path}: {e}")
            if coords_lat is not None:
                sst_list.append(np.full((len(coords_lat), len(coords_lon)), np.nan))
            else:
                # This happens if the first file fails. We'll use the 60x60 we found earlier.
                sst_list.append(np.full((60, 60), np.nan))

    return np.array(sst_list, dtype=np.float64), coords_lat, coords_lon

print("Loading target data...")
target_sst, lats, lons = load_sst_range_fixed(target_start, target_end)
print(f"target_sst shape: {target_sst.shape}")

print("Loading baseline data...")
baseline_sst, _, _ = load_sst_range_fixed(baseline_data_start, baseline_data_end)
print(f"baseline_sst shape: {baseline_sst.shape}")
