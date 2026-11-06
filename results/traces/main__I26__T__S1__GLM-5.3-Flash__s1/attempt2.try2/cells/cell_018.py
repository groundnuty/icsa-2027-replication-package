import fsspec, io, h5py, numpy as np, json, datetime as dt, os
fs = fsspec.filesystem('onedata')
BASE='icsa2027_data_20261101T090944Z/s1z'
b = fs.cat(f'{BASE}/sst_20070601.nc')
f = h5py.File(io.BytesIO(b),'r')
t = f['time'][0]
lat = f['latitude'][:]; lon = f['longitude'][:]
f.close()
print('time raw:', t, '->', np.datetime64('1981-01-01') + np.timedelta64(int(t),'s'))
# region indices
lat64 = lat.astype('float64'); lon64 = lon.astype('float64')
ym = (lat64>=57.83)&(lat64<=59.03); xm=(lon64>=17.41)&(lon64<=18.61)
yi = np.where(ym)[0]; xi = np.where(xm)[0]
print('y', yi[0], yi[-1], len(yi), 'x', xi[0], xi[-1], len(xi))
print('contiguous y:', np.all(np.diff(yi)==1), 'x:', np.all(np.diff(xi)==1))
print('lat first/last', lat[yi[0]], lat[yi[-1]], 'lon first/last', lon[xi[0]], lon[xi[-1]])
json.dump({'y0':int(yi[0]),'y1':int(yi[-1]),'x0':int(xi[0]),'x1':int(xi[-1])}, open('cache/region_idx.json','w'))
os.makedirs('cache', exist_ok=True)
print('saved idx')
