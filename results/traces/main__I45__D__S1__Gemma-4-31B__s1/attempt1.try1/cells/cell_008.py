import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")
print(ds)
