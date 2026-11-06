import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
sample_file = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_sample = '/work/sample.nc'
fs.get(sample_file, local_sample)

ds = xr.open_dataset(local_sample, engine="h5netcdf")
print(ds)
