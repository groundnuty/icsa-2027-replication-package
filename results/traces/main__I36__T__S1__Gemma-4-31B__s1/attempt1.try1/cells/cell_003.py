import xarray as xr
import numpy as np
import pandas as pd
import fsspec
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21
target_start = '2003-06-01'
target_end = '2003-08-31'

# Dates for target period
target_dates = pd.date_range(target_start, target_end)

def get_sst_for_dates(dates, lat_bounds, lon_bounds):
    sst_list = []
    lats = None
    lons = None
    for d in dates:
        fname = f"{base_dir}/sst_{d.strftime('%Y%m%d')}.nc"
        with fs.open(fname, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            # Slice to region
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_bounds[0], lat_bounds[1]),
                longitude=slice(lon_bounds[0], lon_bounds[1])
            )
            if lats is None:
                lats = subset.latitude.values
                lons = subset.longitude.values
            sst_list.append(subset.values)
    
    # Stack along time axis
    sst_array = np.stack(sst_list, axis=0)
    return sst_array, lats, lons

sst_target, lats, lons = get_sst_for_dates(target_dates, (lat_min, lat_max), (lon_min, lon_max))
print(f"SST target shape: {sst_target.shape}")
print(f"Lats shape: {lats.shape}, Lons shape: {lons.shape}")

# Identify sea cells: SST finite on every day of the target period
# Finite means not NaN and not Inf
is_sea = np.all(np.isfinite(sst_target), axis=0)
print(f"Sea cells count: {np.sum(is_sea)}")
