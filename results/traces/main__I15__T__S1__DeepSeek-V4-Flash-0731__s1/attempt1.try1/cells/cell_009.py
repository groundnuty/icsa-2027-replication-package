import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')

# Get the time indices we need
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

t_vals = ds.time.values

# Baseline including window extension: 1991-12-27 to 2003-01-05
# Actually, the task says baseline 1992-2002 with windows up to 5 days beyond
# So 1991-12-27 to 2002-12-31 plus 2003-01-01 to 2003-01-05
# But really, we need the windows for ALL day-of-year values.
# The ±5 day window around each baseline date means we need all dates from 
# (1992-01-01 - 5 days) to (2002-12-31 + 5 days) = 1991-12-27 to 2003-01-05

base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')

b_idx = np.where((t_vals >= base_start) & (t_vals <= base_end))[0]
print(f"Baseline extended idx: {b_idx[0]} to {b_idx[-1]}, count: {len(b_idx)}")
print(f"Baseline extended dates: {t_vals[b_idx[0]]} to {t_vals[b_idx[-1]]}")

# Target period
t_start = np.datetime64('2019-06-01')
t_end = np.datetime64('2019-08-31')
t_idx = np.where((t_vals >= t_start) & (t_vals <= t_end))[0]
print(f"Target idx: {t_idx[0]} to {t_idx[-1]}, count: {len(t_idx)}")

# Region indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Lat idx: {lat_idx[0]} to {lat_idx[-1]}, count: {len(lat_idx)}")
print(f"Lon idx: {lon_idx[0]} to {lon_idx[-1]}, count: {len(lon_idx)}")

# Load baseline data for region
baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values
print(f"Baseline SST shape: {baseline_sst.shape}")

# Load target data for region
target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=lat_idx, longitude=lon_idx).values
print(f"Target SST shape: {target_sst.shape}")

# Check units - are these in Kelvin?
print(f"\nBaseline SST range: {np.nanmin(baseline_sst):.2f} to {np.nanmax(baseline_sst):.2f}")
print(f"Target SST range: {np.nanmin(target_sst):.2f} to {np.nanmax(target_sst):.2f}")

# Check for NaN
print(f"Baseline NaN count: {np.isnan(baseline_sst).sum()}")
print(f"Target NaN count: {np.isnan(target_sst).sum()}")
print(f"Baseline total: {baseline_sst.size}")
