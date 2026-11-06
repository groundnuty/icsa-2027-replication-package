
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
print(region.analysed_sst.shape)
print(region.time.values[0], region.time.values[-1])

# Target period
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
print("Target shape:", target.analysed_sst.shape)
print(target.time.values[0], target.time.values[-1])

# Baseline
baseline = region.sel(time=slice('1992-01-01', '2002-12-31'))
print("Baseline shape:", baseline.analysed_sst.shape)
