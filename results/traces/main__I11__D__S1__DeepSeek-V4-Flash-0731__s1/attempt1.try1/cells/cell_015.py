
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Check a sample of the data
# Take a single time step
sample = ds['analysed_sst'].isel(time=0, latitude=109, longitude=373).load()
print(f"Sample value: {sample.values}")
print(f"Data type: {ds['analysed_sst'].dtype}")

# Check the first few values of the first time step
first_sst = ds['analysed_sst'].isel(time=0).load()
print(f"First time step: min={first_sst.min().values:.2f}, max={first_sst.max().values:.2f}")
print(f"Non-NaN count: {np.count_nonzero(~np.isnan(first_sst.values))}")
