
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values

# Find indices in region
lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]
print("lat_idx:", lat_idx.min(), lat_idx.max(), "count:", len(lat_idx))
print("lon_idx:", lon_idx.min(), lon_idx.max(), "count:", len(lon_idx))

# Get time indices
time = ds.time.values
print("Time dtype:", time.dtype)
print("First few times:", time[:5])
print("Times around 1991-12-27 to 2003-01-05")
# Find indices for baseline window
import pandas as pd
t = pd.to_datetime(time)
# Baseline 1992-2002 plus extension 1991-12-27 to 2003-01-05
start = pd.Timestamp('1991-12-27')
end = pd.Timestamp('2003-01-05')
mask = (t >= start) & (t <= end)
idx_base = np.where(mask)[0]
print("Baseline idx range:", idx_base.min(), idx_base.max(), "count:", len(idx_base))

# Target period 2009-06-01 to 2009-08-31
t_start = pd.Timestamp('2009-06-01')
t_end = pd.Timestamp('2009-08-31')
mask_t = (t >= t_start) & (t <= t_end)
idx_target = np.where(mask_t)[0]
print("Target idx:", idx_target.min(), idx_target.max(), "count:", len(idx_target))
