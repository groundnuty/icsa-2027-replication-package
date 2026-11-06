import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
sample_file = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    print(ds)
