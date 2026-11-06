import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'

t0=time.time()
with fs.open(f'{base}/sst_20090601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print('open+load hdr s:', time.time()-t0)
    print(ds)
    print('attrs:', dict(ds.attrs))
    for v in ds.variables:
        print(v, ds[v].dims, ds[v].shape, ds[v].dtype, dict(ds[v].attrs))
    lat = ds['lat'].values; lon = ds['lon'].values; tv = ds['time'].values
    print('lat', lat[:3], lat[-3:], lat.dtype)
    print('lon', lon[:3], lon[-3:], lon.dtype)
    print('time', tv[:3], tv[-1:], tv.dtype)
    sst = ds['analysed_sst']
    print('sst attrs', dict(sst.attrs), 'encoding', {k:sst.encoding.get(k) for k in ['_FillValue','dtype','chunksizes','zlib','complevel']})
