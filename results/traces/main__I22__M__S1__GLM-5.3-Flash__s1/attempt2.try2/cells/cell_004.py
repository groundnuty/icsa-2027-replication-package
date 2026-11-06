import h5py, numpy as np
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc'
with h5py.File(p, 'r') as f:
    print(list(f.keys()))
    ds = f['analysed_sst']
    print('shape', ds.shape, 'dtype', ds.dtype, 'chunks', ds.chunks, 'compression', ds.compression)
    lat = f['latitude'][:]
    lon = f['longitude'][:]
print('lat', lat[:3], lat[-3:], 'step', np.diff(lat)[:3], np.diff(lat)[-3:])
print('lon', lon[:3], lon[-3:], 'step', np.diff(lon)[:3])
print('lat monotonic inc:', np.all(np.diff(lat) > 0), 'lon:', np.all(np.diff(lon) > 0))
latmin, latmax, lonmin, lonmax = 57.41, 58.61, 18.69, 19.89
ilat = np.where((lat >= latmin - 1e-6) & (lat <= latmax + 1e-6))[0]
ilon = np.where((lon >= lonmin - 1e-6) & (lon <= lonmax + 1e-6))[0]
print('lat idx', ilat[0], ilat[-1], 'n', len(ilat), 'vals', lat[ilat[0]], lat[ilat[-1]])
print('lon idx', ilon[0], ilon[-1], 'n', len(ilon), 'vals', lon[ilon[0]], lon[ilon[-1]])
# check neighbours just outside
print('lat around:', lat[ilat[0]-1], lat[ilat[-1]+1])
print('lon around:', lon[ilon[0]-1], lon[ilon[-1]+1])
