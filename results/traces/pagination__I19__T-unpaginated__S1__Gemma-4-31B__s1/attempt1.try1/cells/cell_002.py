import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
