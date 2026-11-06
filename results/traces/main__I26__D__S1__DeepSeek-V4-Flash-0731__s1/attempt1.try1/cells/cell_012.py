import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select the spatial region
lat_slice = slice(57.83, 59.03)
lon_slice = slice(17.41, 18.61)

# Check what we get
region = ds.sel(latitude=lat_slice, longitude=lon_slice)
print(region.dims)
print(region.analysed_sst.shape)

# Check the time range
times = ds.time.values
print("Time range:", times[0], "to", times[-1])
print("Total time steps:", len(times))
