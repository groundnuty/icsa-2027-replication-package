import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20090601.nc','rb') as f:
    ds=xr.open_dataset(f, engine='h5netcdf')
    print(ds['analysed_sst'].attrs)
    lat=ds['latitude'].values; lon=ds['longitude'].values
    print('lat dtype', lat.dtype, 'lon dtype', lon.dtype)
    print('lat step uniques:', np.unique(np.round(np.diff(lat),6))[:5])
    print('lon step uniques:', np.unique(np.round(np.diff(lon),6))[:5])
    # find indices near bounds
    for b,name in [(59.93,'lat_min'),(61.13,'lat_max'),(18.69,'lon_min'),(19.89,'lon_max')]:
        arr = lat if name.startswith('lat') else lon
        i=np.argmin(np.abs(arr-b))
        print(name, b, 'nearest idx', i, 'value', repr(arr[i]), 'diff', arr[i]-b)
    # list all values in range using tolerance
    latmask = (lat>=59.93-1e-4)&(lat<=61.13+1e-4)
    lonmask = (lon>=18.69-1e-4)&(lon<=19.89+1e-4)
    print('lat in range:', lat[latmask])
    print('lon in range:', lon[lonmask])
    sub=ds['analysed_sst'].isel(time=0)[latmask][:,lonmask]
    print('sub shape', sub.shape, 'finite frac', np.isfinite(sub.values).mean())
