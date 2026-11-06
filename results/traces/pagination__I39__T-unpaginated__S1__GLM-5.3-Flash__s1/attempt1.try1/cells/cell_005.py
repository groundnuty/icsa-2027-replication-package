import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc'
with fs.open(p, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print(ds.attrs)
