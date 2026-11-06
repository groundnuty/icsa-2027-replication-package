import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20040615.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print()
    for v in ds.variables:
        print(v, ds[v].dtype, ds[v].shape, ds[v].attrs)
    print("global attrs:", dict(ds.attrs))
    print("lat range:", float(ds.lat.min()), float(ds.lat.max()), "n:", ds.lat.size)
    print("lon range:", float(ds.lon.min()), float(ds.lon.max()), "n:", ds.lon.size)
    ds.close()
