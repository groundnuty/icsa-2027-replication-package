import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20090601.nc','rb') as f:
    ds=xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print('---- attrs ----')
    print(dict(ds.attrs))
