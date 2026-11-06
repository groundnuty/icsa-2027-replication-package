
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load only needed slices
# Extended baseline: indices 3647 to 7674 (inclusive)
# Target: indices 12935 to 13026 (inclusive)
# Region: lat 260-319, lon 485-544

base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()

print("Baseline data shape:", base_data.shape)
print("Target data shape:", target_data.shape)
print("Baseline times:", base_data.time.values[0], "to", base_data.time.values[-1])
print("Target times:", target_data.time.values[0], "to", target_data.time.values[-1])
