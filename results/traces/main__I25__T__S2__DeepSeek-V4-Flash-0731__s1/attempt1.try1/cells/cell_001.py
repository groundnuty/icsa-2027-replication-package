
import fsspec
fs = fsspec.filesystem('onedata')
# Let's explore the dataset
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    import xarray as xr
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print(ds.variables)
