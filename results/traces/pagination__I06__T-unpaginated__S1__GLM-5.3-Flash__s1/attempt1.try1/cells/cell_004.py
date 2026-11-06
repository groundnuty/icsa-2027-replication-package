import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20120601.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print("---- attrs ----")
    for v in ds.variables:
        print(v, ds[v].dtype, ds[v].shape, dict(ds[v].attrs))
    print("global attrs:", dict(ds.attrs))
    lat = ds['lat'].values; lon = ds['lon'].values
    print("lat range:", lat.min(), lat.max(), "n:", lat.size)
    print("lon range:", lon.min(), lon.max(), "n:", lon.size)
    print("lat:", lat[:10], "...", lat[-5:])
    print("lon:", lon[:10], "...", lon[-5:])
    print("time:", ds['time'].values)
    sst = ds[list(ds.data_vars)[0]] if ds.data_vars else None
    print("data vars:", list(ds.data_vars))
