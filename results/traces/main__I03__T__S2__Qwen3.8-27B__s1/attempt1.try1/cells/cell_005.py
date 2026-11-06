import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']
print('encoding:', v.encoding)
lat = ds['latitude'].values.astype(np.float64)
lon = ds['longitude'].values.astype(np.float64)
li = np.where((lat>=54.17)&(lat<=55.37))[0]
lo = np.where((lon>=13.25)&(lon<=14.45))[0]
print('lat idx', li[0], li[-1], 'n=',len(li), 'lat first/last', lat[li[0]], lat[li[-1]])
print('lon idx', lo[0], lo[-1], 'n=',len(lo), 'lon first/last', lon[lo[0]], lon[lo[-1]])
t0 = np.where(ds['time'].values==np.datetime64('2014-06-15'))[0]
print('t idx', t0)
sub = v.isel(time=t0[0], latitude=li[10], longitude=lo[10:15]).values
print('sample row:', sub)
sub2 = v.isel(time=t0[0], latitude=li[30:35], longitude=lo[30]).values
print('sample col:', sub2)
