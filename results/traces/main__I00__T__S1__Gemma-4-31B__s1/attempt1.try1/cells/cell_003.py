import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
sample_file = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat_min, lat_max = 54.13, 55.33
    lon_min, lon_max = 14.67, 15.87
    subset = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    print(f"Subset shape: {subset.analysed_sst.shape}")
    print(f"Latitude values: {subset.latitude.values}")
    print(f"Longitude values: {subset.longitude.values}")
