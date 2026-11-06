import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
sample_file = f'{root_dir}/sst_19820101.nc'

with fs.open(sample_file, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    print(ds)
