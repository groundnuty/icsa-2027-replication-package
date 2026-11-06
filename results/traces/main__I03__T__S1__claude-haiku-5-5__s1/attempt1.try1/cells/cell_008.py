import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf')
    print(d)
    print(d.time.values[[0,-1]] if 'time' in d.coords else None, d.sizes)