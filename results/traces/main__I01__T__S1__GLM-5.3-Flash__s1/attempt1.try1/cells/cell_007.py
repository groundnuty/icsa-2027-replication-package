import fsspec, xarray as xr, numpy as np, time, os, shutil
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# local disk space
tot, used, free = shutil.disk_usage('/tmp')
print('disk /tmp total %.1f GB free %.1f GB' % (tot/1e9, free/1e9))
tot2, used2, free2 = shutil.disk_usage(os.getcwd())
print('disk cwd (%s) free %.1f GB' % (os.getcwd(), free2/1e9))

# time a single open + one day read (full chunk)
t0=time.time()
f = fs.open(p, 'rb')
print('open took %.2f s' % (time.time()-t0))
t0=time.time()
ds = xr.open_dataset(f, engine='h5netcdf')
print('open_dataset (lazy header) took %.2f s' % (time.time()-t0))

t0=time.time()
sl = ds.analysed_sst.sel(time='2008-06-01', latitude=slice(54.13,55.33), longitude=slice(14.67,15.87)).values
print('one day region read: %.2f s, shape %s' % (time.time()-t0, sl.shape))
t0=time.time()
sl2 = ds.analysed_sst.sel(time='2008-06-02', latitude=slice(54.13,55.33), longitude=slice(14.67,15.87)).values
print('second day: %.2f s' % (time.time()-t0))
t0=time.time()
sl3 = ds.analysed_sst.sel(time=slice('2008-06-03','2008-06-12'), latitude=slice(54.13,55.33), longitude=slice(14.67,15.87)).values
print('10-day region read: %.2f s, shape %s' % (time.time()-t0, sl3.shape))
print('region lat:', ds.latitude.sel(latitude=slice(54.13,55.33)).values[[0,-1]])
print('region lon:', ds.longitude.sel(longitude=slice(14.67,15.87)).values[[0,-1]])
print('nan frac day1: %.3f, day2: %.3f, 10day: %.3f' % (np.isnan(sl).mean(), np.isnan(sl2).mean(), np.isnan(sl3).mean()))
