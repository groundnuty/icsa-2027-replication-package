
import xarray as xr
import numpy as np
import datetime

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region indices
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lon_idx = np.where((lon >= 17.71) & (lon <= 18.91))[0]

# Target period: 2019-06-01 to 2019-08-31
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
target_mask = (ds.time.values >= target_start) & (ds.time.values <= target_end)
target_time_idx = np.where(target_mask)[0]
print("Target time indices:", target_time_idx[0], target_time_idx[-1], "count:", len(target_time_idx))

# Baseline: 1992-01-01 to 2002-12-31, plus windows 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (ds.time.values >= baseline_start) & (ds.time.values <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]
print("Baseline time indices:", baseline_time_idx[0], baseline_time_idx[-1], "count:", len(baseline_time_idx))

# Extract region data for target
target_sst = ds.analysed_sst[target_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values
print("Target SST shape:", target_sst.shape)
print("Target time:", ds.time.values[target_time_idx])

# Extract region data for baseline
baseline_sst = ds.analysed_sst[baseline_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values
print("Baseline SST shape:", baseline_sst.shape)
print("Baseline first/last time:", ds.time.values[baseline_time_idx[0]], ds.time.values[baseline_time_idx[-1]])
