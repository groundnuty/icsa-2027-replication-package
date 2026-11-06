import fsspec, xarray as xr, numpy as np, datetime as dt
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20090601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    v = ds['analysed_sst']
    print('var attrs:', v.attrs)
    print('encoding chunks:', v.encoding.get('chunks'))
    lat = ds['latitude'].values.astype(np.float64)
    lon = ds['longitude'].values.astype(np.float64)
    print('lat range', lat.min(), lat.max(), 'n', lat.size)
    print('lon range', lon.min(), lon.max(), 'n', lon.size)
    dlat = np.diff(lat); dlon = np.diff(lon)
    print('dlat uniq', np.unique(np.round(dlat,6))[:5], 'dlon uniq', np.unique(np.round(dlon,6))[:5])

latm = (lat >= 61.57) & (lat <= 62.77)
lonm = (lon >= 20.17) & (lon <= 21.37)
i0, i1 = np.where(latm)[0][[0,-1]]
j0, j1 = np.where(lonm)[0][[0,-1]]
print('lat idx', i0, i1, lat[i0], lat[i1], 'n', i1-i0+1)
print('lon idx', j0, j1, lon[j0], lon[j1], 'n', j1-j0+1)
