import xarray as xr
import numpy as np
import pandas as pd
import fsspec

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region bounds
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45
# Time bounds
baseline_start = "1991-12-27"
baseline_end = "2003-01-05"
target_start = "2004-06-01"
target_end = "2004-08-31"

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    
    # Slicing
    subset = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max)
    )
    
    # Since the baseline and target periods are separated, I'll slice them separately or use a mask.
    # Actually, I can just load the baseline range and target range.
    baseline_ds = subset.sel(time=slice(baseline_start, baseline_end)).load()
    target_ds = subset.sel(time=slice(target_start, target_end)).load()

print(f"Baseline shape: {baseline_ds.analysed_sst.shape}")
print(f"Target shape: {target_ds.analysed_sst.shape}")
print(f"Lat range: {subset.latitude.min().values} to {subset.latitude.max().values}")
print(f"Lon range: {subset.longitude.min().values} to {subset.longitude.max().values}")
