import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']
print('encoding:', v.encoding)
lat = ds['latitude'].values.astype(np.float64)
lon = ds['longitude'].values.astype(np.float64)
print('lat[0:5]', lat[0:5], 'lon[0:5]', lon[0:5])
li = np.where((lat>=54.17)&(lat<=55.37))[0]
lo = np.where((lon>=13.25)&(lon<=14.45))[0]
print('lat idx', li[0], li[-1], 'n=',len(li), 'lat vals', lat[li[0]], lat[li[-1]])
print('lon idx', lo[0], lo[-1], 'n=',len(lo), 'lon vals', lon[lo[0]], lon[lo[-1]])
# sample a sea cell and check land-like values: read one day at a few points
t0 = np.where(ds['time'].values==np.datetime64('2014-06-15'))[0]
print('t idx', t0)
sub = v.values[t0[0], li[10], lo[10:15]]
print('sample row (one lat, 5 lon):', sub)
sub2 = v.values[t0[0], li[30:35], lo[30]]
print('sample col:', sub2)
