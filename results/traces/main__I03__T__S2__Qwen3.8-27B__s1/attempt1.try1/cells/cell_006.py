import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']
t = ds['time'].values
ti0 = np.searchsorted(t, np.datetime64('1991-12-27'))
ti1 = np.searchsorted(t, np.datetime64('1991-12-31'))
print('first 10 days of window:', t[ti0:ti0+10])
print('last 10:', t[ti1-5:ti1+1])
lat = ds['latitude'].values.astype(np.float64); lon = ds['longitude'].values.astype(np.float64)
li = np.where((lat>=54.17)&(lat<=55.37))[0]; lo = np.where((lon>=13.25)&(lon<=14.45))[0]
# benchmark: 100 days
t0=time.time()
sub = v.isel(time=slice(ti0, ti0+100), latitude=li, longitude=lo).values
print('100 days in', time.time()-t0, 's, shape', sub.shape, 'dtype', sub.dtype)
print('nan count', np.isnan(sub).sum(), 'of', sub.size)
