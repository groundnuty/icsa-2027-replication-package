
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

# Region indices
lat_inds = slice(192, 252)  # 60 cells
lon_inds = slice(2, 62)     # 60 cells

# Baseline with extended windows (1991-12-27 to 2003-01-05)
# And target period 2021-06-01 to 2021-08-31
# Read just what we need

# Baseline data
baseline_ds = ds.analysed_sst.isel(time=slice(3647, 7675), latitude=lat_inds, longitude=lon_inds)
print("Loading baseline data...")
baseline_data = baseline_ds.load()
print("Baseline loaded:", baseline_data.shape)
print(baseline_data.time.values[0], baseline_data.time.values[-1])

# Target data
target_ds = ds.analysed_sst.isel(time=slice(14396, 14488), latitude=lat_inds, longitude=lon_inds)
print("Loading target data...")
target_data = target_ds.load()
print("Target loaded:", target_data.shape)
print(target_data.time.values[0], target_data.time.values[-1])

# Save to files for later use
baseline_data.to_netcdf('baseline_data.nc')
target_data.to_netcdf('target_data.nc')
print("Saved.")
