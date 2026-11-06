import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20090601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print('--- attrs ---')
    for k,v in ds.attrs.items(): print(k, ':', str(v)[:120])
    for c in ds.coords:
        print('coord', c, ds[c].values[:5] if ds[c].size>5 else ds[c].values)
