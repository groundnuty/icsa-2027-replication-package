
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)

# Sea cells: finite SST on every target day
finite_all = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells count:", finite_all.sum(), "out of", finite_all.size)
print("Sea cell shape:", finite_all.shape)
