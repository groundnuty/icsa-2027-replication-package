import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20070601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print('lat range', float(ds.lat.min()), float(ds.lat.max()))
    print('lon range', float(ds.lon.min()), float(ds.lon.max()))
    lat = ds.lat.values; lon = ds.lon.values
    print('lat step', np.diff(lat)[:5], 'n', len(lat))
    print('lon step', np.diff(lon)[:5], 'n', len(lon))
    print('attrs', ds.attrs)
    v = ds[list(ds.data_vars)[0]]
    print(v.name, v.dims, v.dtype, v.attrs)
