import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z/sst_20210601.nc'
with fs.open(p, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print("---- attrs ----")
    print(dict(ds.attrs))
    for v in ds.variables:
        print(v, ds[v].dtype, dict(ds[v].attrs))
    lat = ds['lat'].values if 'lat' in ds else ds['latitude'].values
    lon = ds['lon'].values if 'lon' in ds else ds['longitude'].values
    print("lat:", lat[:5], "...", lat[-5:], "n=", len(lat))
    print("lon:", lon[:5], "...", lon[-5:], "n=", len(lon))
    print("lat step:", np.diff(lat)[:3], np.diff(lat)[-3:])
    print("lon step:", np.diff(lon)[:3], np.diff(lon)[-3:])
