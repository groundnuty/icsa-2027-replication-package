import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
sample_file_remote = f'{root_dir}/sst_19820101.nc'
sample_file_local = '/work/sample_sst.nc'
fs.get(sample_file_remote, sample_file_local)

ds = xr.open_dataset(sample_file_local, engine="h5netcdf")
print(ds)
